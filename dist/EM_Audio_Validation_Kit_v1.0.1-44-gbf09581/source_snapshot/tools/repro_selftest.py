#!/usr/bin/env python3
"""Check the reproduction package before spending twenty-five minutes on it.

The last package cost its reproducer a full run that ended in RUN FAILED for two
reasons he could not have known about: a result file no pipeline step wrote, and
a figure gate calibrated for a library version his Python could not install.
Both were detectable in seconds. This runs those checks first, so a defect in the
package surfaces before the run rather than twenty minutes into it.

It is deliberately read-only and fast. It does not run any experiment.

    python3 tools/repro_selftest.py
"""
from __future__ import annotations

import importlib.util
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (command, what it is for, how to install it on this platform). espeak-ng ships
# its Windows executable as espeak-ng.exe but some installers expose it as
# espeak.exe, so both names are accepted rather than failing on the spelling.
WINDOWS = sys.platform.startswith("win")

TOOLS = [
    (["ffmpeg"], "audio processing",
     "winget install Gyan.FFmpeg" if WINDOWS else "brew install ffmpeg"),
    (["ffprobe"], "audio inspection",
     "installed with ffmpeg"),
    (["node"], "the second-language oracle",
     "winget install OpenJS.NodeJS" if WINDOWS else "brew install node"),
    (["c2patool"], "C2PA signing and validation",
     "download from github.com/contentauth/c2pa-rs/releases"),
    (["espeak-ng", "espeak"], "formant speech synthesis",
     "winget install eSpeak-NG.eSpeak-NG" if WINDOWS else "brew install espeak-ng"),
]
PY_REQUIRED = [("matplotlib", "matplotlib", "figures"),
               ("numpy", "numpy", "figures"),
               ("piper", "piper-tts", "the neural robustness arm")]
PY_OPTIONAL = [("c2pa", "c2pa-python", "the optional second-reader check")]


def main() -> int:
    problems, notes = [], []
    print("EM-Audio reproduction package self-test\n")

    print(f"Platform: {sys.platform}, Python {sys.version.split()[0]}\n")
    print("External tools")
    def locate(name):
        """shutil.which, plus the places Windows installers use without
        touching PATH. eSpeak NG in particular installs to Program Files and
        leaves PATH alone, so a machine with the tool present reports it
        missing, which sends the reader off to reinstall something they have."""
        hit = shutil.which(name)
        if hit or not WINDOWS:
            return hit
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     r"C:\ProgramData\chocolatey\bin"):
            for sub in ("", "eSpeak NG", "eSpeak", "espeak-ng"):
                cand = Path(base) / sub / f"{name}.exe"
                if cand.exists():
                    return str(cand)
        return None

    for names, why, how in TOOLS:
        found = next((n for n in names if locate(n)), None)
        if found:
            print(f"  found     {found:12} ({why})")
        else:
            shown = " or ".join(names)
            print(f"  MISSING   {shown:12} ({why})")
            problems.append(f"{shown} is not on PATH, needed for {why}. "
                            f"Install: {how}")

    print("\nPython packages")
    for mod, pkg, why in PY_REQUIRED:
        if importlib.util.find_spec(mod):
            print(f"  found     {pkg:16} ({why})")
        else:
            print(f"  MISSING   {pkg:16} ({why})")
            problems.append(f"{pkg} is not installed; run "
                            f"pip install -r requirements.txt")
    for mod, pkg, why in PY_OPTIONAL:
        state = "found    " if importlib.util.find_spec(mod) else "absent   "
        print(f"  {state} {pkg:16} ({why}; optional, the run skips it)")

    if WINDOWS:
        print("\nShell")
        if shutil.which("bash"):
            print("  found     bash (Git Bash or WSL); ./run_all.sh will run")
        else:
            print("  MISSING   bash")
            problems.append("run_all.sh is a bash script and no bash was found. "
                            "Git for Windows provides Git Bash, or use WSL.")

    print("\nPackage integrity")
    # Every file a pipeline step reads but no step writes is a latent leftover.
    # This is the class of defect that ended the previous reproduction.
    mr = ROOT / "results" / "machine_readable"
    stale = sorted(p.name for p in mr.glob("*.json")) if mr.is_dir() else []
    # Only meaningful inside a delivered package. The development tree keeps its
    # results, and flagging that would train the reader to ignore the check.
    in_package = (ROOT / ".reproduction_package").exists()
    if stale and in_package:
        print(f"  results/machine_readable/ is NOT empty ({len(stale)} files)")
        problems.append(
            "results/machine_readable/ should ship empty so that an experiment "
            "which fails cannot leave a shipped file in place and have the "
            "comparison report a match that never happened")
    elif in_package:
        print("  results/machine_readable/ is empty, as intended")
    else:
        print(f"  results/machine_readable/ has {len(stale)} files "
              f"(a development tree, not a package: not checked)")

    ref = ROOT / "results" / "reference"
    n_ref = len(list(ref.glob("*.json"))) if ref.is_dir() else 0
    if n_ref:
        print(f"  results/reference/ has {n_ref} comparison files")
    else:
        print("  results/reference/ is MISSING")
        problems.append("results/reference/ is absent; verify_reproduction.py "
                        "would have nothing to compare against")

    for rel in ("run_all.sh", "requirements.txt", "tools/verify_reproduction.py",
                "tools/calibrate_footprint.py", "experiments/second_reader.py"):
        if (ROOT / rel).exists():
            print(f"  present   {rel}")
        else:
            print(f"  MISSING   {rel}")
            problems.append(f"{rel} is absent from the package")

    print("\nVersion notes (differences here are the point, not a problem)")
    pre = ROOT / "results" / "PREFLIGHT.txt"
    if pre.exists():
        for line in pre.read_text().splitlines():
            if line.split(":")[0] in ("python", "ffmpeg", "c2patool", "node",
                                      "espeak_ng"):
                print(f"  reference used  {line.strip()[:78]}")
    if importlib.util.find_spec("matplotlib"):
        import matplotlib                                    # noqa: PLC0415
        pin = ""
        for line in (ROOT / "requirements.txt").read_text().splitlines():
            if line.startswith("matplotlib=="):
                pin = line.split("==", 1)[1].strip()
        if pin and matplotlib.__version__ != pin:
            notes.append(f"matplotlib {matplotlib.__version__} is not the "
                         f"pinned {pin}. The figure check reports its findings "
                         f"but will not fail the run, because its thresholds "
                         f"are calibrated for the pinned version.")

    print()
    for n in notes:
        print(f"NOTE: {n}")
    if problems:
        print(f"\n{len(problems)} problem(s) to resolve before running:")
        for p in problems:
            print(f"  - {p}")
        print("\nDo not start ./run_all.sh until these are cleared.")
        return 1
    print("Package looks complete. Run ./run_all.sh next.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
