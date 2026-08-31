#!/usr/bin/env python3
"""Fetch, check, run and package an independent reproduction, on any platform.

The orchestration lives here rather than in a shell script because this file can
be tested on the machine that wrote it and a PowerShell script cannot. The
Windows entry point is a thin wrapper that finds Python and calls this; every
decision, every check and every error message is in this file, so what a Windows
user hits is code that has been exercised.

    python3 tools/bootstrap_reproduction.py            # fetch, check, run, collect
    python3 tools/bootstrap_reproduction.py --check    # environment only, no run
    python3 tools/bootstrap_reproduction.py --dir D:\\repro --ref v1.0.2

Run it from anywhere; it clones into --dir. If you already have the repository,
run it from inside and it will use what is there.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = "https://github.com/1D-Coda/em-audio.git"
WINDOWS = sys.platform.startswith("win")


def say(msg):   print(f"\n=== {msg}", flush=True)
def ok(msg):    print(f"  {msg}", flush=True)
def bad(msg):   print(f"  ** {msg}", flush=True)


def run(argv, cwd=None, log=None):
    """Run a command, streaming to the console and optionally to a log file."""
    print(f"  $ {' '.join(str(a) for a in argv)}", flush=True)
    proc = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines = []
    for line in proc.stdout:
        sys.stdout.write(line)
        lines.append(line)
    proc.wait()
    if log:
        Path(log).write_text("".join(lines), encoding="utf-8", errors="replace")
    return proc.returncode


def find_bash():
    """bash, which run_all.sh needs. Git for Windows ships one."""
    found = shutil.which("bash")
    if found:
        return found
    if WINDOWS:
        for guess in (r"C:\Program Files\Git\bin\bash.exe",
                      r"C:\Program Files (x86)\Git\bin\bash.exe"):
            if Path(guess).exists():
                return guess
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None,
                    help="where to clone (default: em-audio-repro beside you)")
    ap.add_argument("--ref", default="main",
                    help="branch, tag or commit to reproduce (default main)")
    ap.add_argument("--check", action="store_true",
                    help="check the environment and stop, running nothing")
    args = ap.parse_args()

    if WINDOWS and "WindowsApps" in sys.executable:
        bad("This is the Microsoft Store's Python stub, not a real install.")
        bad("Install Python properly:  winget install Python.Python.3.12")
        bad("Then close and reopen the terminal so PATH picks it up.")
        return 2

    print("EM-Audio independent reproduction")
    print(f"platform: {platform.platform()}")
    print(f"python  : {sys.version.split()[0]}")

    # If we are already inside the repository, use it.
    here = Path(__file__).resolve().parents[1]
    inside = (here / "run_all.sh").exists()
    target = here if inside else Path(args.dir or (Path.cwd() / "em-audio-repro"))

    say("Tools")
    missing = []
    for name, why, how in (
        ("git", "fetching the repository",
         "winget install Git.Git" if WINDOWS else "brew install git"),
        ("ffmpeg", "audio processing",
         "winget install Gyan.FFmpeg" if WINDOWS else "brew install ffmpeg"),
        ("c2patool", "C2PA signing and validation",
         "github.com/contentauth/c2pa-rs/releases"),
        ("node", "the second-language oracle",
         "winget install OpenJS.NodeJS" if WINDOWS else "brew install node"),
    ):
        if shutil.which(name):
            ok(f"found    {name}")
        else:
            bad(f"MISSING  {name} ({why}) -> {how}")
            missing.append(name)
    for names in (("espeak-ng", "espeak"),):
        if any(shutil.which(n) for n in names):
            ok(f"found    {names[0]}")
        else:
            bad(f"MISSING  {' or '.join(names)} (speech synthesis) -> "
                f"{'winget install eSpeak-NG.eSpeak-NG' if WINDOWS else 'brew install espeak-ng'}")
            missing.append(names[0])

    bash = find_bash()
    if bash:
        ok(f"found    bash ({bash})")
    else:
        bad("MISSING  bash. run_all.sh is a bash script; install Git for "
            "Windows, which provides Git Bash, or use WSL.")
        missing.append("bash")

    if missing and not args.check:
        bad(f"{len(missing)} tool(s) missing. Install them and run this again; "
            f"nothing was run, so nothing was wasted.")
        return 2

    if not inside:
        say(f"Fetching {args.ref}")
        if target.exists():
            # Existence is not completeness. A clone interrupted partway leaves
            # a directory that looks right and is missing files, and "using it
            # as is" then fails much later with a confusing error about the
            # first file that happens to be absent. Check for the files the run
            # actually needs before trusting it.
            need = ["run_all.sh", "requirements.txt", "tools/repro_selftest.py",
                    "tools/verify_reproduction.py", "em_audio/evidence.py"]
            absent = [n for n in need if not (target / n).exists()]
            if absent:
                bad(f"{target} exists but is incomplete: missing "
                    f"{', '.join(absent)}")
                bad("This is what an interrupted clone looks like. Delete the "
                    "directory and run this again, or pass a different --dir.")
                return 1
            ok(f"{target} exists and looks complete; using it")
        else:
            # --branch takes a branch or a tag and rejects a commit hash, which
            # this accepts and documents. Try the cheap shallow path, and fall
            # back to fetching the object by name when it is a commit. A
            # validator handed a commit rather than a tag would otherwise get a
            # clone failure that says nothing about why.
            rc = run(["git", "clone", "--depth", "1", "--branch", args.ref,
                      REPO, str(target)])
            if rc != 0:
                ok(f"{args.ref} is not a branch or tag; fetching it as a commit")
                shutil.rmtree(target, ignore_errors=True)
                target.mkdir(parents=True, exist_ok=True)
                steps = [
                    ["git", "init", "-q"],
                    ["git", "remote", "add", "origin", REPO],
                    ["git", "fetch", "-q", "--depth", "1", "origin", args.ref],
                    ["git", "checkout", "-q", "FETCH_HEAD"],
                ]
                for step in steps:
                    if run(step, cwd=target) != 0:
                        bad(f"could not fetch {args.ref}: check that it exists")
                        return 1
    else:
        ok(f"already inside a checkout at {target}")

    say("Python packages")
    if run([sys.executable, "-m", "pip", "install", "-q", "-r",
            str(target / "requirements.txt")], cwd=target) != 0:
        bad("pip install failed; send this output and stop here")
        return 1
    ok("installed")

    say("Package self-test")
    rc = run([sys.executable, str(target / "tools" / "repro_selftest.py")],
             cwd=target)
    if rc != 0:
        bad("the self-test found problems; resolve them and run this again")
        return 1

    if args.check or missing:
        say("Check only; stopping before the run as asked")
        return 0

    # Detect a CRLF checkout before bash reports it as "$'\r': command not
    # found", which names neither the file nor the cause.
    first = (target / "run_all.sh").read_bytes()[:200]
    if b"\r\n" in first:
        bad("run_all.sh has Windows line endings and bash cannot run it.")
        bad("Your git rewrote it on checkout. Fix with:")
        bad(f"    git -C {target} config core.autocrlf false")
        bad(f"    git -C {target} rm --cached -r . && git -C {target} reset --hard")
        return 1

    say("Pipeline (about 25 minutes, plus the corpus download)")
    run_log = target / "run_all_output.txt"
    # Not "-lc": a login shell sources profile scripts, and Git Bash profiles
    # commonly cd to the home directory, which would run the pipeline from the
    # wrong place. Git Bash also wants forward slashes, and run_all.sh resolves
    # its own root, so an absolute path works from any working directory.
    script = str(target / "run_all.sh").replace("\\", "/")
    run_rc = run([bash, "-c", f'"{script}"'], cwd=target, log=run_log)
    (ok if run_rc == 0 else bad)(f"run_all.sh exited {run_rc}")

    say("Comparison against the released results")
    ver_log = target / "verify_output.txt"
    ver_rc = run([sys.executable, str(target / "tools" / "verify_reproduction.py")],
                 cwd=target, log=ver_log)
    ok(f"verify_reproduction.py exited {ver_rc}")
    ok("a non-zero exit here is a result to report, not a failure on your part")

    say("Collecting")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = target / f"EM_Audio_results_{stamp}.zip"
    env = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version.split()[0],
        "ref_requested": args.ref,
        "run_all_exit": run_rc,
        "verify_exit": ver_rc,
        "collected_utc": datetime.now(timezone.utc).isoformat(),
    }
    (target / "WINDOWS_RUN.json").write_text(json.dumps(env, indent=2))

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in ("results/PREFLIGHT.txt", "run_all_output.txt",
                    "verify_output.txt", "WINDOWS_RUN.json"):
            f = target / rel
            if f.exists():
                z.write(f, rel)
        mr = target / "results" / "machine_readable"
        for f in sorted(mr.glob("*.json")):
            z.write(f, f"results/machine_readable/{f.name}")
    ok(f"send this back: {out}")

    say("Done")
    print(f"  run_all.sh exit {run_rc}, verify exit {ver_rc}")
    print("  Send the zip whatever the exit codes were. A failed run that is")
    print("  reported is worth more than a run that was made to pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
