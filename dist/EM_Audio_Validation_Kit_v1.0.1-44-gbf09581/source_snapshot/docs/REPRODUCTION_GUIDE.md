# Independent reproduction — what to run and what to send back

Two ways in. Both end in the same place: a zip to send back, whatever the
outcome. **A run that fails and is reported is worth more to us than a run that
was made to pass.** The last reproduction found two real defects that way.

## Before anything: the sixty-second check

    python3 tools/repro_selftest.py

It looks for the five external tools, the Python packages, and the files the
pipeline needs, and it names anything missing along with how to install it. It
runs no experiment. The previous package cost its reproducer a full run that
died twenty minutes in on a missing file; this exists so that cannot happen
again.

Do not start the pipeline until this passes.

## Linux and macOS

    pip install -r requirements.txt
    ./run_all.sh 2>&1 | tee run_all_output.txt
    python3 tools/verify_reproduction.py 2>&1 | tee verify_output.txt

## Windows

From a PowerShell prompt:

    .\tools\reproduce.ps1

It fetches the repository, installs the pinned packages, runs the self-test,
runs the pipeline and the comparison, and collects everything into a zip.

Be warned that **this script has never been executed on Windows.** It was
written on macOS. If it breaks, that is a defect in the bootstrapper and not in
your machine: send the error text and we will fix it. You can also run the
Linux commands above under Git Bash or WSL, which is the better-tested path.

The pipeline itself is a bash script, so Git for Windows or WSL is required
either way.

## What you need installed

FFmpeg and ffprobe, Node, eSpeak NG, and `c2patool`. The self-test names them
and gives the install command for your platform. The Python packages are pinned
in `requirements.txt`; `c2pa-python` there is optional and only enables one
extra check.

Roughly twenty-five minutes, plus a 322 MB corpus download the first time.

## What the run tells you

`RUN OK` on the last line means every conformance check passed. Anything else is
a result we want to see.

`verify_reproduction.py` then compares your results against the released ones and
splits them in two, using criteria fixed in code before you ran anything:

- **deterministic** outputs must match exactly, and any difference makes it exit
  non-zero: conformance counts, promotion classifications, lineage sets,
  interval structure, support-channel behaviour, corpus recovery, composition
  wiring, decoded-essence digests
- **environment-dependent** outputs are expected to differ and do not fail it:
  wall-clock timings and their dispersion, and the bytes of a freshly signed
  file, which change because signing carries a timestamp

If your timings matched ours exactly, we would distrust the measurement.

## Comparing your figures against the paper's

`results/figures/` is rebuilt from your own results, which is the point, so the
copies shipped in this package are replaced the first time you run. The renders
as printed in the manuscript are kept in `docs/reference_figures/`, which the
pipeline never touches, with a note on what to look for.

The one worth comparing is containment. The manuscript's version draws two
builds; yours will draw one, because it only has your data. If any measured
reach in yours crosses into the shaded band, your build has a dependency its
declaration does not contain, and that is the most useful thing this exercise
can produce.

## What to send back

Everything the run wrote:

- `results/machine_readable/` in full
- `results/PREFLIGHT.txt`, which records your machine and tool versions
- `run_all_output.txt` and `verify_output.txt`
- your operating system, hardware and the date

On Windows the script collects these for you.

## If something does not match

Do not smooth it over and do not assume it is your environment. Send it as it
is. We classify it together into one of four kinds: an environment difference, a
tool-version difference, an ambiguity in how the contract is specified, or a
genuine discrepancy. Only the last is a defect, and the third is the most
interesting outcome, because it locates a hole in the specification rather than
in the code.

## What the previous reproduction found, so you know what to expect

On FFmpeg 8.0.1 rather than 9.0.1, two declared numbers did not hold: the MP3
kernel footprint measured a reach of 4,317 source samples against 2,304
declared, and the silence-removal mapping deviation reached 12,505 samples
against a declared margin of 4,096. Those are reported in the paper as results
and the declarations were not widened to absorb them.

If your build reproduces those two numbers, that tells us they track the FFmpeg
version. If it produces different ones, that is more interesting still, and it
is exactly the sort of thing this exercise is for.
