"""Signed transport layer: C2PA via the official ``c2patool`` CLI.

Plan A of the feasibility gate.  The bridge never re-implements C2PA; it drives
the official tool and reads back its JSON report, so the transport guarantees
are the tool's, not this project's.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .manifest_schema import ASSERTION_LABEL

C2PATOOL = shutil.which("c2patool") or "c2patool"


def version() -> str:
    return subprocess.run([C2PATOOL, "--version"], capture_output=True, text=True).stdout.strip()


@dataclass
class Signer:
    cert_chain_pem: Path
    private_key_pk8_pem: Path
    trust_anchor_pem: Path
    settings_path: Optional[Path] = None

    def env(self) -> Dict[str, str]:
        e = dict(os.environ)
        e["C2PA_SIGN_CERT"] = self.cert_chain_pem.read_text()
        e["C2PA_PRIVATE_KEY"] = self.private_key_pk8_pem.read_text()
        return e

    def settings(self, workdir: Path) -> Path:
        if self.settings_path and self.settings_path.exists():
            return self.settings_path
        p = workdir / "c2pa_settings.toml"
        p.write_text(
            "[verify]\nverify_trust = true\n\n[trust]\ntrust_anchors = \"\"\"\n"
            + self.trust_anchor_pem.read_text()
            + "\"\"\"\ntrust_config = \"1.3.6.1.5.5.7.3.4\"\n"
        )
        self.settings_path = p
        return p


def _c2pa(argv: Sequence[str], signer: Optional[Signer] = None,
          workdir: Optional[Path] = None) -> subprocess.CompletedProcess:
    env = signer.env() if signer else None
    return subprocess.run([C2PATOOL, *argv], capture_output=True, text=True, env=env)


def sign(asset: Path, out: Path, manifest: Dict[str, object], signer: Signer,
         workdir: Path, parent: Optional[Path] = None) -> Dict[str, object]:
    mpath = workdir / f"{out.stem}.manifest.json"
    mpath.write_text(json.dumps(manifest, indent=1))
    argv = [str(asset), "-m", str(mpath), "-o", str(out), "-f",
            "--settings", str(signer.settings(workdir))]
    if parent is not None:
        argv += ["-p", str(parent)]
    p = _c2pa(argv, signer, workdir)
    if p.returncode != 0:
        raise RuntimeError(f"c2patool sign failed:\n{p.stderr[-2000:]}")
    return json.loads(p.stdout)


def validate(asset: Path, signer: Signer, workdir: Path) -> Dict[str, object]:
    p = _c2pa([str(asset), "--settings", str(signer.settings(workdir))], signer, workdir)
    if p.returncode != 0:
        return {"validation_state": "NoManifest", "error": p.stderr.strip()[-500:]}
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"validation_state": "Unparseable", "raw": p.stdout[:500]}


def state_of(report: Dict[str, object]) -> str:
    return str(report.get("validation_state", "NoManifest"))


def failures(report: Dict[str, object]) -> List[str]:
    vr = report.get("validation_results") or {}
    am = vr.get("activeManifest") or {}
    return [f["code"] for f in am.get("failure", [])]


def em_assertion_of(report: Dict[str, object]) -> Optional[Dict[str, object]]:
    active = report.get("active_manifest")
    if not active:
        return None
    man = report["manifests"][active]
    for a in man.get("assertions", []):
        if a["label"].split(".v")[0] == ASSERTION_LABEL or a["label"] == ASSERTION_LABEL:
            return a["data"]
    return None


def ingredients_of(report: Dict[str, object]) -> List[Dict[str, object]]:
    active = report.get("active_manifest")
    if not active:
        return []
    return report["manifests"][active].get("ingredients", [])


def build_manifest(title: str, em_assertion: Dict[str, object],
                   actions: Sequence[Dict[str, object]],
                   generator: str = "em-audio", version_str: str = "1.0.0") -> Dict[str, object]:
    return {
        "claim_generator_info": [{"name": generator, "version": version_str}],
        "title": title,
        "assertions": [
            {"label": "c2pa.actions.v2", "data": {"actions": list(actions)}},
            {"label": ASSERTION_LABEL, "data": em_assertion},
        ],
    }
