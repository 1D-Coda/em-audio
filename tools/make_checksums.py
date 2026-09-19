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


def _refuse_if_worktree_differs_from_checkout() -> None:
    """A manifest is only useful if it verifies for the person who downloaded.

    These hashes are taken from the working tree. For any path governed by an
    eol attribute the working tree can differ from what a clone checks out, and
    29 entries once did: they were written from bytes that existed only on the
    machine that generated them, so the manifest failed on every fresh clone.

    The first guard here asked `git status`, and `git status` normalises line
    endings before comparing, so it reported a clean tree while 23 files copied
    in from a Windows machine sat on disk with CRLF under an eol=lf attribute.
    The manifest hashed them that way and failed in a clean clone, which is the
    defect the guard existed to stop. `git ls-files --eol` reports the working
    tree's actual endings beside the attribute, so compare those. Refuse to
    write rather than ship a checksum file that cannot verify.
    """
    import re
    import subprocess
    r = subprocess.run(["git", "ls-files", "--eol"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return  # no git: an archive, where the working tree is all there is
    wrong = []
    for line in r.stdout.splitlines():
        # "i/lf    w/crlf  attr/text eol=lf      <TAB>path": the attribute
        # field contains spaces, so split on the tab, not on whitespace.
        meta, _, path = line.partition("\t")
        wt_m = re.search(r"\bw/(\S+)", meta)
        eol = re.search(r"\beol=(lf|crlf)\b", meta)
        if not wt_m or not eol or not path:
            continue  # no declared ending
        wt = wt_m.group(1)
        if wt in ("none", "-text"):
            continue  # an empty or binary file
        if wt != eol.group(1):
            wrong.append(f"{path}: on disk {wt}, a clone gets {eol.group(1)}")
    if wrong:
        print("[checksums] REFUSING: the working tree's line endings differ from "
              "what a clone checks out, so a manifest written now would fail "
              "for whoever downloads it:")
        for w in wrong:
            print("   ", w)
        print("    Rewrite them from the index first: "
              "rm the files and `git checkout HEAD -- <path>`.")
        raise SystemExit(2)


def main() -> int:
    _refuse_if_worktree_differs_from_checkout()
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
    OUT.write_text("\n".join(rows) + "\n", newline="\n")
    print(f"[checksums] SHA256SUMS  ({len(rows)} tracked files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
