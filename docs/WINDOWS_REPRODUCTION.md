# Reproducing on Windows

Two paths work. Docker is the one to use if you have it, because the image
pins every tool version and the comparison is then against a known build. The
native path runs the same pipeline directly on Windows and is verified on every
push by a GitHub Actions job on windows-latest.

## What to run

Install Docker Desktop from docker.com and start it. Then, from a PowerShell
prompt:

```powershell
git clone https://github.com/1D-Coda/em-audio
cd em-audio\tools
.\run_on_windows.ps1 -Check
```

The check looks at Docker and runs nothing. When it passes, drop the flag:

```powershell
.\run_on_windows.ps1
```

That builds the pinned image, runs the whole pipeline inside it, compares the
results against the release, and leaves everything in `..\out`.

About twenty-five minutes after the first build, plus a 322 MB corpus download.

## Reading the outcome

Two of the three exit codes are successes.

| Exit | Meaning |
|---|---|
| **0** | Conformance passed and every declared footprint held on this build |
| **3** | Conformance passed, and a declared kernel footprint does not hold on this image's FFmpeg |
| 1 | Something else went wrong, which is a defect worth reporting |

**Exit 3 is a result, not a failure.** The paper's central claim is that the
footprint declarations in Table 3 are calibrated for one FFmpeg build and must
be re-measured for another. An independent reproduction on FFmpeg 8.0.1 already
measured the MP3 encoder reaching 4,317 source samples against 2,304 declared,
and that is published as a finding rather than absorbed by widening the
declaration. The container reproduces the same class of result on its own build.

## Running it natively

```powershell
irm https://raw.githubusercontent.com/1D-Coda/em-audio/main/tools/reproduce.ps1 -OutFile reproduce.ps1
.\reproduce.ps1 -Check
.\reproduce.ps1
```

`-Check` verifies the tools and runs nothing. You need Git, Python 3.12,
FFmpeg, c2patool, Node and eSpeak NG on PATH; the check names whichever is
missing.

This document previously said the native path did not work and that the cause
had not been diagnosed. It has been, and the causes were two defects of this
software rather than anything about Windows or about the evidence contract:

- `c2patool` refused to sign with `resource not found` for a file that was on
  disk. A C2PA ResourceRef identifier is a URI-style path, and `str()` on a
  Windows path writes a backslash, which c2pa-rs does not read as a separator.
- The voice-model fetch called `shasum`, which macOS ships and Git Bash does
  not, so the step exited 127.

Both are fixed. The pipeline now reaches `RUN OK - all conformance checks
passed` on Windows Server 2025 with every experiment run: 30 of 30 tests, no
oracle disagreements across 10,860 cases, and no probe outside its declared
kernel support.

WSL also runs real Linux, and the Linux instructions in `REPRODUCTION_GUIDE.md`
apply unchanged there. The independent reproduction of Section 7.11 was made on
Linux.

## What a native run reports about the footprints

The native run reproduces every conformance property and does **not** reproduce
the measured MP3 kernel reach: 1,541 source samples against the 1,555 the
reference build measured, on the same FFmpeg version number, 9.0.1. Both are
inside the 2,304 declared, so the declaration held.

That difference is the point rather than a problem. It is the paper's own
claim, measured on a third environment: a footprint is a property of a build,
not of a codec, and pinning the version number does not pin the footprint.
Three things differ at once here, though, and one run cannot separate them: the
operating system, the CPU architecture and the FFmpeg build. Do not read this
as "Windows changes the footprint".

## What to send back

The whole `out` directory. It holds the machine-readable results, the preflight
report that records your machine and tool versions, and both logs.

Send it whatever the exit code was. A run that is reported is worth more than a
run that was made to pass: the previous reproduction exited non-zero and found
two real defects in the paper's declared numbers, both of which are now
published as results.

## Honesty about this path

`run_on_windows.ps1` is forty lines and has never been executed on Windows. It
finds Python and hands over to `tools/run_container.py`, which was written and
exercised on the machine that produced it. If the wrapper misbehaves, skip it:

```powershell
python tools\run_container.py
```

Either way, send us the error rather than working around it.
