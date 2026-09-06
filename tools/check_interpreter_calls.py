#!/usr/bin/env python3
"""Fail on portability defects that CI on a hosted runner cannot catch.

Two so far, both found by independent reproducers on their own Windows
machines and both invisible to our Windows CI:

  * a bare `python3`, which on a normal Windows install is the Microsoft
    Store alias: on PATH, and not an interpreter;
  * a bare `shutil.rmtree`, which fails with WinError 5 while a scanner
    holds a file open, or when anything inside is read-only.

run_all.sh resolves the interpreter by running it, because on Windows the name
python3 is usually a Microsoft Store alias: on PATH, and not an interpreter.
That fix covered run_all.sh's own 34 invocations and missed the scripts it
calls. An independent reproducer's experiment C2 then failed on the one line in
tools/fetch_voice.sh that still said python3, while every other step passed.

CI cannot catch this by running: the hosted Windows runner installs a Python
that does provide python3, so the bad call works there. It is caught by reading
instead.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The resolver names the candidates; the container pins its own interpreter.
EXEMPT = {"tools/resolve_python.sh", "tools/container_entrypoint.sh"}

CALL = re.compile(r"(?<![\w./$-])python3(?![\w.-])")


def main() -> int:
    bad = []
    for path in sorted(ROOT.rglob("*.sh")):
        rel = path.relative_to(ROOT).as_posix()
        if rel in EXEMPT or ".git" in path.parts or "dist" in path.parts:
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#") or not CALL.search(line):
                continue
            bad.append(("python3", f"{rel}:{n}: {stripped}"))

    # Same shape, second defect: shutil.rmtree without the Windows handling.
    RM = re.compile(r"(?<![\w.])shutil\.rmtree\(")
    RM_EXEMPT = {"em_audio/fsutil.py", "tools/bootstrap_reproduction.py",
                 "tools/build_reproduction_package.py",
                 "tools/build_validation_kit.py"}
    for path in sorted(list(ROOT.rglob("experiments/*.py"))
                       + list(ROOT.rglob("em_audio/*.py"))
                       + list(ROOT.rglob("tools/*.py"))):
        rel = path.relative_to(ROOT).as_posix()
        if rel in RM_EXEMPT or ".git" in path.parts or "dist" in path.parts:
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if line.strip().startswith("#") or not RM.search(line):
                continue
            bad.append(("rmtree", f"{rel}:{n}: {line.strip()}"))

    if bad:
        py = [b for k, b in bad if k == "python3"]
        rm = [b for k, b in bad if k == "rmtree"]
        if py:
            print("bare python3, which is the Microsoft Store alias on a normal")
            print("Windows install: on PATH, and not an interpreter.")
            for b in py:
                print(f"  {b}")
            print('  Use "$PY", or source tools/resolve_python.sh when the script')
            print("  can be run on its own.")
        if rm:
            if py:
                print()
            print("bare shutil.rmtree, which fails with WinError 5 while a scanner")
            print("holds a file open, or when anything inside is read-only.")
            for b in rm:
                print(f"  {b}")
            print("  Use em_audio.fsutil.rmtree, which retries and clears the bit.")
        return 1
    print("[interpreter] no shipped script invokes a bare python3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
