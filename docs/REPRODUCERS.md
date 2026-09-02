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
with 189 deterministic differences, and both were reported rather than adjusted.
Found the two packaging defects behind the failed run.

**Run 2, 2026-08-31, Windows 11, Intel, FFmpeg 9.0.1 gyan.dev full build.**
Produced all 21 result files. Measured MP3 kernel reach 1,541 source samples
against the reference build's 1,555, on the same FFmpeg version number, both
inside the 2,304 declared. 30/30 tests, 0 oracle disagreements over 10,860
cases, 0 probes outside declared support. Experiment C2 was completed by hand
after `tools/fetch_voice.sh` failed, so this was not a clean single pass.

Found: `fetch_voice.sh` still invoked a bare `python3`.

The CPU family suggests runs 1 and 2 were the same machine. Two runs by one
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

Has the package. Nothing run yet, so nothing to attribute.
