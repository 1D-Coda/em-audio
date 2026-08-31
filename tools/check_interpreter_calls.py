#!/usr/bin/env python3
"""Fail if any shipped script invokes a bare `python3`.

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
            bad.append(f"{rel}:{n}: {stripped}")

    if bad:
        print("scripts invoking a bare python3, which is the Microsoft Store")
        print("alias on a normal Windows install:")
        for b in bad:
            print(f"  {b}")
        print("Use \"$PY\", or source tools/resolve_python.sh when the script")
        print("can be run on its own.")
        return 1
    print("[interpreter] no shipped script invokes a bare python3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
