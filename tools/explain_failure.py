#!/usr/bin/env python3
"""Say why a pipeline run failed, from its log.

Shell greps kept cutting off the part that matters. A RuntimeError raised by the
FFmpeg or c2patool wrapper carries the tool's own stderr after the command line,
and that stderr is the only text that says what went wrong; the traceback frames
above it name the raising line, which is never the cause.

    python3 tools/explain_failure.py run_all_output.txt
    python3 tools/explain_failure.py run_all_output.txt --github   # annotations
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

def read_log(path: Path) -> str:
    """Decode a log whichever shell produced it.

    Windows PowerShell 5.1 writes Tee-Object output as UTF-16LE with a byte
    order mark, so reading this file at the default encoding yields text with
    a NUL between every character and no line that matches anything here. This
    tool then reported "no traceback in this log" for the one real Windows
    failure the project has, whose log names the missing voice file on the
    line that matters, and CI emitted no annotation for four failed runs in a
    row. Sniff the mark, and fall back to UTF-8 for every other shell.
    """
    raw = path.read_bytes()
    for mark, enc in ((b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16"),
                      (b"\xef\xbb\xbf", "utf-8-sig")):
        if raw.startswith(mark):
            return raw.decode(enc, errors="replace")
    return raw.decode("utf-8", errors="replace")


STEP = re.compile(r"^=== (.+?) ===\s*$")
START = re.compile(r"^Traceback \(most recent call last\):")
# The wrapper's message is "<tool> failed: <argv>\n<stderr>", so the useful text
# begins at that line and continues to the end of the block.
CAUSE = re.compile(r"(ffmpeg failed|c2patool \w+ failed|RuntimeError|Error|error):", re.I)


def blocks(lines):
    """Each failure, with the step it happened in and the lines that follow."""
    step = "(before any step)"
    i = 0
    while i < len(lines):
        m = STEP.match(lines[i])
        if m:
            step = m.group(1).strip()
        if START.match(lines[i]):
            j = i + 1
            while j < len(lines) and not STEP.match(lines[j]) and j - i < 60:
                j += 1
            yield step, lines[i:j]
            i = j
            continue
        i += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--github", action="store_true",
                    help="emit ::error:: lines, readable from the annotations API")
    ap.add_argument("--max", type=int, default=2, help="failures to explain")
    args = ap.parse_args()

    lines = read_log(Path(args.log)).splitlines()
    found = list(blocks(lines))
    if not found:
        print("no traceback in this log")
        return 0

    def emit(text, err=False):
        t = text.strip()[:200]
        if not t:
            return
        print(f"::{'error' if err else 'notice'}::{t}" if args.github else f"  {t}")

    for step, blk in found[:args.max]:
        emit(f"failure during: {step}", err=True)
        # A traceback is "Traceback...", then indented frames, then one
        # unindented line: the exception. Taking the last unindented line in the
        # window instead picks up whatever the next step printed, which is how
        # this first reported "[docs] results/14_Figure_QA.md" as an exception.
        k = None
        seen_frame = False
        for n, l in enumerate(blk):
            if l.startswith("  File "):
                seen_frame = True
            elif seen_frame and l and not l[0].isspace():
                k = n
                break
        if k is None:
            emit("a traceback with no exception line; log may be truncated", True)
            continue
        emit(f"exception: {blk[k]}", err=True)
        # Everything after the exception line is the tool's own stderr, carried
        # into the message by the wrapper.
        for l in [x for x in blk[k + 1:] if x.strip()][:8]:
            emit(f"tool said: {l}", err=True)
        if args.github:
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
