# Reproducing on Windows

Use Docker. The native Windows path does not currently work, and this document
says so up front rather than letting you find out twenty minutes in.

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

## Why not run it natively

The pipeline was run on a Windows Server 2025 machine with FFmpeg, eSpeak NG and
c2patool installed. Experiments C2, D and E failed there: two inside FFmpeg and
one with `c2patool sign failed: Error: embedding manifest`. The cause has not
been diagnosed, and until it is, a native Windows package would be a package
that fails.

The environment check, the download, the clone and the dependency install all
work natively on Windows and are verified by continuous integration on a real
Windows runner. It is the experiments themselves that do not.

If you would rather not use Docker, WSL runs real Linux and the Linux
instructions in `REPRODUCTION_GUIDE.md` apply unchanged. That path is known to
work: the independent reproduction of Section 7.11 was made on Linux.

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
