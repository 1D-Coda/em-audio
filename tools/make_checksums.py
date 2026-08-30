#!/usr/bin/env python3
"""Regenerate SHA256SUMS over the tracked files.

The manifest was written by hand once and then never again, so by the time the
repository was published 61 of its 140 entries no longer matched the files they
name. An integrity manifest that fails on legitimate files is worse than none:
it cannot distinguish a stale line from a tampered one, so a reader who checks
it learns nothing and a reader who does not check it was better served by
silence. It is generated here and refreshed on every run.

Only tracked files are covered. Generated audio, working directories and
anything gitignored are excluded, because they are not part of what the release
distributes and their digests would differ on every machine.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "SHA256SUMS"
# The manifest cannot contain its own digest, and a macOS directory-metadata
# file is not part of the release.
SKIP = {"SHA256SUMS", ".DS_Store"}


def main() -> int:
    # git lists exactly what the release distributes, but a reproduction package
    # has no history, and a tool that needs git to run is the same defect this
    # project already fixed once in verify_reproduction.py. Fall back to walking
    # the tree, skipping what the release never contained.
    try:
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                               text=True, check=True).stdout.split()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[checksums] no git history; walking the tree instead")
        skip_dirs = {".git", "__pycache__", "corpus", "node_modules"}
        files = []
        for p in ROOT.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT)
            if any(part in skip_dirs for part in rel.parts):
                continue
            if rel.suffix in {".aux", ".log", ".out", ".fls", ".fdb_latexmk", ".blg"}:
                continue
            files.append(str(rel))
    rows = []
    for rel in sorted(files):
        if rel in SKIP or Path(rel).name in SKIP:
            continue
        p = ROOT / rel
        if not p.is_file():
            continue
        rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
    OUT.write_text("\n".join(rows) + "\n")
    print(f"[checksums] SHA256SUMS  ({len(rows)} tracked files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
