# Independent reproduction

Results produced by Daniel A. Balderrama-Alvarez (Universidad de Sonora,
ORCID 0009-0002-5180-0406) on his own hardware from the reproduction package
of release tag v1.0.1, run twice on 26 and 27 August 2026. He is not an author
of the manuscript and did not take part in designing the contract, the
experiments or the classification of outputs, which were fixed in
`tools/verify_reproduction.py` before he received the package.

Only the second run is here. The first was incomplete: `requirements.txt` was
not installed because the instructions he was given did not say to, so the
figure and robustness arms did not execute. `run_all.sh` now checks its
dependencies before starting and exits naming the missing one. Both runs
returned the same values for the two findings, which is what makes them
findings.

Files are his, unmodified:

- `PREFLIGHT.txt` -- his machine, tool versions and the run's own summary
- `verify_output.txt` -- the classified comparison against the released results
- `run_all_output.txt` -- the full pipeline log
- `machine_readable/` -- every result file his run emitted

The two deterministic differences his run found, and what they mean, are
reported in Section 7.11 of the manuscript. Neither is a defect of his run:
both trace to his FFmpeg 8.0.1 build behaving differently from the 9.0.1 the
footprints were calibrated against, and both are the failure mode the
"Footprints are declarations" limitation predicts.

The numbers the manuscript quotes from this directory are generated into
`results/numbers.tex` by `tools/make_macros.py`, like every other number in
the paper.
