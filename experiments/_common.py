from __future__ import annotations
import json, os, platform, subprocess, sys, time
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "results" / "machine_readable"
RESULTS.mkdir(parents=True, exist_ok=True)

from em_audio.evidence import BOT, C, G, Evidence, claim_of          # noqa: E402
from em_audio.interval_map import SourceInterval, Timeline           # noqa: E402

CHANNEL = "capture-support"
SCOPE = frozenset({"digital-asset"})


def element(kind: str, k: int, n: int, src: str = "s") -> Evidence:
    """Deterministic evidence element for symbol ``kind`` at position ``k``."""
    if kind == "B":                                   # ⊥ : unverified
        return Evidence(P=BOT, S={}, A={}, L=frozenset({f"urn:emaudio:{src}#el={k}"}))
    val = round((k + 1) / float(n + 1), 12)
    return Evidence(P=claim_of([kind]), S={CHANNEL: val}, A={CHANNEL: SCOPE},
                    L=frozenset({f"urn:emaudio:{src}#el={k}"}))


def timeline_from_word(word: Sequence[str], width: int = 1, src: str = "s") -> Timeline:
    n = len(word)
    ivs = [SourceInterval(src, k * width, (k + 1) * width, element(ch, k, n, src))
           for k, ch in enumerate(word)]
    return Timeline(src, ivs)


def env() -> Dict[str, str]:
    def _v(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()[0].strip()
        except Exception:
            return "unavailable"
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or platform.machine(),
        "ffmpeg": _v(["ffmpeg", "-version"]),
        "c2patool": _v(["c2patool", "--version"]),
        "node": _v(["node", "-v"]),
        "espeak_ng": _v(["espeak-ng", "--version"]),
    }


def emit(name: str, payload: Dict[str, object]) -> Path:
    payload = dict(payload)
    payload.setdefault("experiment", name)
    payload.setdefault("environment", env())
    p = RESULTS / f"{name}.json"
    p.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    print(f"[emit] {p.relative_to(ROOT)}")
    return p
