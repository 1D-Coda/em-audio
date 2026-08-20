# Clean-clone reproduction record

Performed 2026-08-20 by the author, on the same machine that produced the
original results. This is **not** independent reproduction and is not offered as
such. What it establishes is narrower and still worth having: that the tagged
release's code and reproducibility workflow are self-contained **conditional on
the two checksum-pinned external artefacts**, and that no reported result
depends on a file left behind in a working directory. It is not a claim that the
repository carries everything it needs with no network at all; it carries
everything except two artefacts it fetches and verifies.

## Method

```
git clone <repo> /tmp/cleanclone/em-audio
cd /tmp/cleanclone/em-audio && git checkout v1.0.0
./verify_release.sh          # 113 tracked files, all digests match
./run_all.sh
```

## What was and was not exercised

The clone began re-downloading the 337 MB LibriSpeech archive at roughly
7 kB/s, an external rate limit that would have taken about fifteen hours. The
archive and the neural voice were therefore copied in from the working copy
rather than re-fetched, and both fetch scripts were run against them and
re-verified their pinned digests inside the clone. So:

- **exercised:** repository completeness, every experiment, every generator,
  the number checker, the prose audit, the LaTeX build, checksum verification of
  both fetched artefacts;
- **not exercised in this run:** the network download itself, which was
  exercised successfully earlier in the same session against the same pinned
  digests.

## Result

`RUN OK`, exit 0. Every conformance check passed.

Comparing all 17 machine-readable result files between the working copy and the
clone, with timing fields excluded because they are machine-dependent by
construction:

| Outcome | Files |
|---|---|
| Byte-identical | 16 |
| Differing | 1 (`F_essence_rows.json`) |
| Missing from the clone | 0 |

## The one difference is the result worth reporting

`F_essence_rows.json` records, for 120 signed assets, both the decoded-essence
hash and the whole-file hash. Between the two runs:

- decoded-essence hashes identical: **120 of 120**
- signed-file hashes identical: **0 of 120**

Each C2PA signature carries its own timestamp, so the file bytes differ on every
re-signing while the audio does not. A reproducibility check defined on file
bytes would have declared this pipeline irreproducible. Defined on decoded
essence, which is what the manuscript's signal-transparency property uses, it
reproduces exactly.

That is independent corroboration of a methodological choice the paper argues
for on other grounds, and it arrived from a direction the paper did not
anticipate.

## Still open

Reproduction by another person on different hardware. Nothing in this record
substitutes for it.
