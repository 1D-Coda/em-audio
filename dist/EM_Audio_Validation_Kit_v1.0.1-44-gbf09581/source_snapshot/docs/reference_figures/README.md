# Reference renders, kept out of the pipeline's way

`results/figures/` is regenerated on every run from whatever results the run
produced, which is correct: a figure that did not come from your own data would
be misleading. It also means the copies shipped in a reproduction package are
overwritten the first time you run the pipeline.

This directory is not touched by `run_all.sh`. It holds the renders as they
appear in the manuscript, so you can compare yours against them.

## fig5_containment_both_builds.pdf

Kernel-support containment, drawn with **two** builds: the reference machine's
FFmpeg and the independent reproduction's. It is the version printed in the
paper, and it exists in this form only where both sets of results are present.

Your run will regenerate `results/figures/fig5_containment.pdf` from your data
alone, so it will show a single build, yours, and carry the single-build title.
That is the expected difference and not a defect.

What to look for when comparing:

- your filled circles are your measured reaches; the open diamonds are the
  declarations, which are fixed and should be identical
- if any of your circles crosses the 100% line into the shaded band, your build
  has a footprint the declaration does not contain, which is a finding and the
  most useful thing this exercise can produce
- the manuscript's version shows exactly that for the MP3 encoder on FFmpeg
  8.0.1: a reach of 4,317 source samples against 2,304 declared
