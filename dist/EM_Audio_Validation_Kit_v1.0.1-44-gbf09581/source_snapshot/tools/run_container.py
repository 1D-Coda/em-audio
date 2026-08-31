#!/usr/bin/env python3
"""Run the reproduction inside the pinned container, on any host.

This is the path for Windows. The native Windows path does not currently work:
experiments C2, D and E fail there in FFmpeg and c2patool for reasons that have
not been diagnosed, and shipping it while it fails would waste a validator's
afternoon. The container sidesteps that entirely, because what runs inside it is
Linux and is the same on every host.

    python3 tools/run_container.py            build, run, collect
    python3 tools/run_container.py --check    check Docker only, run nothing

Exit codes mirror the container's, and two of them are successes:

    0   conformance passed and every declared footprint held here
    3   conformance passed and a declared footprint does not hold on this
        image's FFmpeg. That is the finding of Section 7.11 measured again,
        not a failure of your run.
    1   something else went wrong, which is a defect worth reporting
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

IMAGE = "em-audio:repro"


def say(m):  print(f"\n=== {m}", flush=True)
def ok(m):   print(f"  {m}", flush=True)
def bad(m):  print(f"  ** {m}", flush=True)


def run(argv, cwd=None):
    print(f"  $ {' '.join(str(a) for a in argv)}", flush=True)
    return subprocess.run(argv, cwd=cwd).returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="check Docker and stop, building and running nothing")
    ap.add_argument("--out", default="out", help="where results are written")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    print("EM-Audio reproduction, container path")
    print(f"host: {platform.platform()}")

    say("Docker")
    if not shutil.which("docker"):
        bad("Docker was not found.")
        bad("Windows and macOS: install Docker Desktop from docker.com.")
        bad("Linux: your distribution's docker.io or docker-ce package.")
        return 2
    ok(subprocess.run(["docker", "--version"], capture_output=True,
                      text=True).stdout.strip())
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        bad("Docker is installed but its daemon is not running.")
        bad("On Windows, start Docker Desktop and wait for it to say Running.")
        return 2
    ok("daemon is running")

    if not (root / "Dockerfile").exists():
        bad(f"no Dockerfile at {root}; run this from inside the repository")
        return 2
    ok(f"repository at {root}")

    if args.check:
        say("Check only; nothing was built or run")
        return 0

    say("Building the image (a few minutes the first time, cached after)")
    if run(["docker", "build", "-t", IMAGE, "."], cwd=root) != 0:
        bad("the build failed; send this output")
        return 1

    out = (root / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    say(f"Running (about 25 minutes, plus the corpus download); results in {out}")
    t0 = time.time()
    rc = run(["docker", "run", "--rm", "-v", f"{out}:/out", IMAGE], cwd=root)
    mins = (time.time() - t0) / 60

    say("What this run concluded")
    if rc == 0:
        ok("conformance passed, and every declared footprint held on this build")
    elif rc == 3:
        ok("conformance passed.")
        ok("A declared kernel footprint does not hold on this image's FFmpeg.")
        ok("That is the paper's own finding measured again, not a failure of")
        ok("your run, and it is the result we most want to see.")
    else:
        bad(f"the container exited {rc}, which is neither of the expected")
        bad("outcomes. That is a defect. Please send everything.")

    say("What to send back")
    files = sorted(p.name for p in out.iterdir()) if out.is_dir() else []
    ok(f"the whole {out} directory ({len(files)} entries), which holds your")
    ok("machine-readable results, your preflight report and both logs")
    ok(f"the run took {mins:.0f} minutes")
    print()
    print("  Send it whatever the exit code was. A run that is reported is worth")
    print("  more than a run that was made to pass; the last reproduction found")
    print("  two real defects that way.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
