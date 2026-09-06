#!/usr/bin/env python3
"""Freeze the current results as the reference an independent run compares against.

This is a release step, not a pipeline step, and the distinction is the whole
point. `verify_reproduction.py` compares a reproduction's results against this
snapshot; if the snapshot were refreshed on every run it would always match what
was just produced and the comparison would be vacuous. It is written once, when
a release is cut, and then left alone until the next one.

The snapshot exists because `git show` cannot serve the reader it was written
for. Someone who downloads a source archive from GitHub or a deposit from Zenodo
has no `.git`, so every reference lookup fails and the tool reports the entire
release as missing. That is exactly the audience an artifact archive is for.

    python3 tools/freeze_reference.py --tag v1.0.2
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MR = ROOT / "results" / "machine_readable"
REF = ROOT / "results" / "reference"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True,
                    help="the release tag these results belong to")
    args = ap.parse_args()

    if not MR.is_dir():
        print("no results to freeze; run ./run_all.sh first", file=sys.stderr)
        return 1

    REF.mkdir(parents=True, exist_ok=True)
    for old in REF.glob("*.json"):
        old.unlink()

    n = 0
    for src in sorted(MR.glob("*.json")):
        shutil.copy2(src, REF / src.name)
        n += 1

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    (REF / "SNAPSHOT.txt").write_text(
        f"Reference results for release {args.tag}\n"
        f"commit at freeze time: {head or 'UNCOMMITTED'}\n\n"
        "These are the values tools/verify_reproduction.py holds a reproduction\n"
        "to. They are a frozen copy of results/machine_readable/ as of the\n"
        "release above, and are refreshed only when a new release is cut. The\n"
        "copy exists so that a reproducer working from a source archive, which\n"
        "has no git history, still has something to compare against.\n\n"
        "The commit recorded here is the one that was current when the snapshot\n"
        "was written, which is necessarily the parent of the commit that stores\n"
        "it. A file cannot contain the hash of the object that contains it.\n")

    print(f"[reference] results/reference/  ({n} files frozen at {args.tag})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
