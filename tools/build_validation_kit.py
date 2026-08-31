#!/usr/bin/env python3
"""Build the Windows/Docker validation kit as a self-contained archive.

The kit ships the source under test rather than cloning it, so a reproducer
needs Docker and nothing else, and so the archive is immutable: what they run is
what this build put there, not whatever the default branch says later.

The previous kit told the reader that only Docker was required while its wrapper
called git and python on the host. This build asserts the claim instead of
repeating it: it refuses to produce an archive whose entry points reach for a
host tool that the documentation does not require.

    python3 tools/build_validation_kit.py
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "release_kits" / "reproduction"
DIST = ROOT / "dist"

# Everything the pipeline needs, and nothing else. The paper, its drafts and the
# reviews are not part of what a reproducer runs.
INCLUDE = ["run_all.sh", "requirements.txt", "Dockerfile", "LICENSE",
           "DATA_LICENSES.md", "README.md", "CITATION.cff",
           "em_audio", "experiments", "tools", "tests", "oracle_js",
           "fixtures", "docs"]
# results/ is handled specially below.
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache"}
EXCLUDE_SUFFIX = {".pyc", ".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".blg"}

# A host tool the entry points must not need. Docker is the only dependency the
# documentation promises.
FORBIDDEN_HOST_TOOLS = ("git clone", "Get-Command python", "Get-Command git",
                        "python3 ", "py -3")


def copy_tree(src: Path, dst: Path) -> int:
    n = 0
    for p in src.rglob("*"):
        rel = p.relative_to(src)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.is_dir():
            continue
        if p.suffix in EXCLUDE_SUFFIX:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        n += 1
    return n


def main() -> int:
    tag = subprocess.run(["git", "describe", "--tags", "--always"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip() or "dev"
    stage = DIST / f"EM_Audio_Validation_Kit_{tag}"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "source_snapshot").mkdir(parents=True)

    n = 0
    for item in INCLUDE:
        src = ROOT / item
        if not src.exists():
            print(f"[kit] missing from the repository: {item}", file=sys.stderr)
            return 1
        if src.is_dir():
            n += copy_tree(src, stage / "source_snapshot" / item)
        else:
            shutil.copy2(src, stage / "source_snapshot" / item)
            n += 1

    # results/: the reference snapshot the verifier compares against, and an
    # empty machine_readable so a failed experiment cannot leave a shipped file
    # in place and have the comparison report a match that never happened.
    res = stage / "source_snapshot" / "results"
    (res / "machine_readable").mkdir(parents=True)
    n += copy_tree(ROOT / "results" / "reference", res / "reference")
    for extra in ("PREFLIGHT.txt",):
        if (ROOT / "results" / extra).exists():
            shutil.copy2(ROOT / "results" / extra, res / extra); n += 1
    # results/independent is another reproducer's data and is deliberately absent.

    for f in KIT.iterdir():
        if f.is_file():
            shutil.copy2(f, stage / f.name)

    # Assert the promise rather than repeat it.
    problems = []
    for entry in stage.glob("*"):
        if entry.suffix.lower() not in (".cmd", ".ps1", ".sh"):
            continue
        text = entry.read_text(errors="replace")
        for tool in FORBIDDEN_HOST_TOOLS:
            if tool in text:
                problems.append(f"{entry.name} reaches for a host tool: {tool!r}")
    if problems:
        print("[kit] the entry points need more than Docker, which the "
              "documentation does not promise:", file=sys.stderr)
        for p in problems:
            print(f"       {p}", file=sys.stderr)
        return 1

    # Manifest, so a reader can tell what they received.
    lines = []
    for p in sorted(stage.rglob("*")):
        if p.is_file():
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  "
                         f"{p.relative_to(stage)}")
    (stage / "FILES.sha256").write_text("\n".join(lines) + "\n")

    DIST.mkdir(exist_ok=True)
    zp = DIST / f"{stage.name}.zip"
    if zp.exists():
        zp.unlink()
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                z.write(p, str(Path(stage.name) / p.relative_to(stage)))
    digest = hashlib.sha256(zp.read_bytes()).hexdigest()
    (DIST / f"{zp.name}.sha256").write_text(f"{digest}  {zp.name}\n")

    print(f"[kit] {zp}  ({zp.stat().st_size/1e6:.1f} MB, {n} source files)")
    print(f"[kit] sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
