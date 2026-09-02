"""One place that decides where an external tool is.

The self-test searched PATH and, on Windows, the directories installers use
without touching PATH; the experiments searched PATH alone. A validator who
installed eSpeak NG with winget - which lands in C:\\Program Files\\eSpeak NG and
leaves PATH untouched - would therefore be told the tool was found, start a
25-minute run, and have it die in the first experiment that needed it.

Standard library only: the self-test runs before `pip install`.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

WINDOWS = sys.platform.startswith("win")

# Where Windows installers put these without adding them to PATH.
_WINDOWS_DIRS = ("", "eSpeak NG", "eSpeak", "espeak-ng", "c2patool")


def locate(name: str) -> str | None:
    """Absolute path to ``name``, or None. PATH first, then the usual places."""
    hit = shutil.which(name)
    if hit or not WINDOWS:
        return hit
    bases = [os.environ.get("ProgramFiles", r"C:\Program Files"),
             os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
             os.environ.get("LOCALAPPDATA", ""),
             r"C:\ProgramData\chocolatey\bin"]
    for base in filter(None, bases):
        for sub in _WINDOWS_DIRS:
            cand = Path(base) / sub / f"{name}.exe"
            if cand.is_file():
                return str(cand)
    return None


def require(name: str, why: str) -> str:
    """Locate ``name`` or raise with the reason and how to install it."""
    hit = locate(name)
    if hit:
        return hit
    raise RuntimeError(
        f"{name} was not found, and it is needed for {why}.\n"
        f"  Searched PATH"
        + (" and the usual Windows install directories." if WINDOWS else ".")
        + "\n  Run tools/repro_selftest.py, which names how to install it.")
