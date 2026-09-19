# Independent reproducers

Who ran the software, on what, and what it found. Kept because the manuscript's
acknowledgements and Section 7.11 must both describe what actually happened, and
because "ran it" and "reported a defect" are different contributions that are
easy to blur once several people are involved.

A person is added here when they run something, not when they agree to.

## Daniel A. Balderrama-Alvarez

Universidad de Sonora. ORCID 0009-0002-5180-0406.

**Run 1, release v1.0.0, Linux, x86_64, FFmpeg 8.0.1.** The reproduction
reported in Section 7.11. Ended in `RUN FAILED` and `REPRODUCTION INCOMPLETE`,
with 189 build-dependent deterministic differences (192 against the current
reference, the extra 3 being the size fields of Experiment A, whose suite grew
in v1.0.4 after this run), and both were reported rather than adjusted.
Found the two packaging defects behind the failed run.

**Run 2, 2026-08-31, Windows 11, Intel, FFmpeg 9.0.1 gyan.dev full build.**
Produced all 21 result files. Measured MP3 kernel reach 1,541 source samples
against the reference build's 1,555, on the same FFmpeg version number, both
inside the 2,304 declared. 30/30 tests, 0 oracle disagreements over 10,860
cases, 0 probes outside declared support. Experiment C2 was completed by hand
after `tools/fetch_voice.sh` failed, so this was not a clean single pass.

Found: `fetch_voice.sh` still invoked a bare `python3`.

**Run 3, 2026-09-15, release v1.0.7, same Windows 11 machine.** The first
single unattended pass of a released package on Windows: `results/PREFLIGHT.txt`
names the tag itself, `run_all.sh` ended in `RUN OK`, and
`verify_reproduction.py` exited 1 with 69 deterministic differences, all of
them in the MP3 kernel measurements of Experiment K and in the time-stretch
model deviation (463 samples against the reference build's 471, both inside
the 2,048-sample guard band). Every other deterministic output is the
reference value. Against his own Run 2 the only deterministic difference is
the size of Experiment A, which grew between the two packages. This is the
run Section 7.11 now reads its Windows numbers from; Run 2 is kept in
`results/independent_windows_2026-08-31/`.

Found, in the two attempts before this one succeeded: the v1.0.5 one-click
script took `C:\Windows\system32\bash.exe` (the WSL launcher) for bash; the
v1.0.6 one died at the corpus download because Windows curl could not reach a
certificate-revocation server, and, underneath that, because PowerShell 5.1
turned any native stderr line into a terminating error under the script's
`$ErrorActionPreference = "Stop"`. Both fixed in v1.0.6 and v1.0.7.

The CPU family suggests runs 1 to 3 were the same machine. Two runs by one
person on one machine are not two independent validators, and the manuscript's
single-validator limitation stands.

## Miguel Arroyo

Nagoya Industries Promotion Corporation, Nagoya, Aichi, JP.
ORCID 0009-0008-8423-8345.

**Windows 11, Surface Pro 9, 12th Gen Intel Core i7-1265U.** Independent
hardware and a different CPU generation from Daniel's. Produced all 21 result
files with 30/30 tests, 0 oracle disagreements and 0 probes outside declared
support. The run did not complete: `tools/calibrate_footprint.py` died on
`shutil.rmtree` with WinError 5, and the tables step failed downstream because
`CALIBRATION.json` was never written.

Found: the dependency check and the experiments located installed tools
differently, so a tool installed outside PATH was reported present and would
have failed the run; and directory removal did not handle Windows file locking.
Nine call sites had the second defect.

Acknowledged in the manuscript for the defect reports, not for a reproduction,
because the run has not completed.

## Brenda Cecilia Guerra Flores

ORCID 0009-0000-8932-683X. No affiliation on the ORCID record; ask before
printing one.

**MacBook Air, Apple Silicon, macOS 26.3.1, FFmpeg 9.0.1 Homebrew.** Reached
`RUN OK`, and `verify_reproduction.py` exited 0: every deterministic output
matches the release, with 17 environment-dependent differences, all of them
timings. 30/30 tests, 0 oracle disagreements over 10,860 cases, 0 probes outside
declared support.

This is the first independent run to reproduce every deterministic output
exactly, and it did so on a different machine from the reference and with
c2patool 0.27.16 against the reference's 0.27.2, node 26.8.1 and Python 3.11.16.
The deterministic results are therefore not sensitive to those versions.

Measured MP3 kernel reach 1,555 source samples, the reference value exactly.

A second run on another of her machines is expected.


## What the MP3 reach measurements now show

| run | platform | FFmpeg 9.0.1 build | measured reach |
|---|---|---|---|
| reference (author) | macOS arm64 | Homebrew | 1,555 |
| Guerra Flores | macOS arm64 | Homebrew | 1,555 |
| Balderrama-Alvarez | Windows x86-64 | gyan.dev full | 1,541 |
| CI (author) | Windows x86-64 | gyan.dev essentials | 1,541 |

Four runs, one FFmpeg version number, two builds, two values. Runs on the same
build agree exactly, including across different machines and different people;
runs on a different build differ, and agree with each other. The measurement is
a property of the build rather than of the machine or of the version number,
which is what the paper claims and what a reader who replies "pin the version"
needs to see.

The declaration held in all four: 2,304 declared, every measurement inside it,
no probe outside declared support.