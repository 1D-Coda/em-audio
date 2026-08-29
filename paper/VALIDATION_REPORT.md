# Validation report

Run against the pipeline outputs in `results/machine_readable/`, not against
prose summaries of them. Every number below was recomputed from the raw result
files or predicted independently and then compared.

## Overall assessment: ready to share, with the caveats listed at the end

## Methodology review

**Question framing.** The paper answers "may this derived interval emit this
claim", not "is this audio synthetic". The distinction is stated in the
abstract, the introduction, the threat model and the conclusion, and no metric
in the paper is a detector metric. Correct framing for the evidence presented.

**Population definition.** The analysis population is the set of derived output
intervals, not clips or files. Rates are reported per clip where the clip is the
natural unit (promotion is a property of the whole-asset claim) and per sample
where the sample is the natural unit (dilution is a property of extent). Both
choices are stated.

**Baseline fairness.** The comparison policy is declared a constructed reference
policy, motivated from the specification's own `parentOf` definition, and is
never attributed to a product. The policy ablation removes one shortcut at a
time, so the comparison is not a single strawman but a 2x2.

**Metric definitions.** Promotion, dilution, lineage omission and essence
identity each have a stated definition and a code path. Dilution's denominator
(output samples where both policies have a record) is documented.

## Checks run

| Check family | Count | Result |
|---|---|---|
| Internal consistency of raw results (rates vs counts, subtotals, bounds) | 114 | all pass |
| Independent recomputation of the case-count arithmetic | 1 | 3x8 + 9x9 + 9828x10 = 98,385, matches |
| Independent geometric prediction of every measured promotion count in D | 8 | all 8 match after correction |
| Unit-of-analysis sensitivity (median-of-ratios vs pooled ratio) | 4 | max divergence 0.28 pp, immaterial |
| Determinism across three independent full runs | 3 | identical counts; only timing varies |
| Citation integrity (keys, orphans, status labels) | 15 | no orphans, no missing, all preprints labelled |
| Figure axis and labelling audit | 5 figures | all bar charts start at zero; one truncated axis, now disclosed |

## Issues found and fixed during this validation

1. **[High] Confounded comparison between chain depth and asset duration.** The
   text compared a five-operator chain on 2.85 s clips (85.74% dilution) with a
   three-operator chain on a 30 s asset (2.40%) and attributed the difference to
   duration. Two variables moved at once. Fixed by measuring the *same*
   three-operator chain at 2.85 s, 30 s and 300 s: 25.13%, 2.40%, 0.240%. Each
   tenfold increase in duration divides the fraction by ten, which isolates
   duration and matches the fixed-band prediction. The abstract's claim of "the
   same three-operator chain" now has a referent; before, it had none.

2. **[Medium] Preprint status not labelled on three of four preprints.** The
   research-integrity standard requires distinguishing peer-reviewed work from
   preprints. Only one of four carried the label. All four now do.

3. **[Low] Truncated vertical axis undisclosed.** Figure 3's control panel runs
   80--100%. The truncation is defensible (it makes divergence between
   measurement and closed form more visible, not less) but was not stated. The
   caption now states it.

## Calculation spot-checks

- Case count 98,385: **verified** by independent arithmetic from the battery
  breakdown.
- Baseline promotion counts across all eight transformations: **verified** by a
  prediction computed from corpus geometry alone, with no shared code path.
- Overhead median inside its own IQR in matched units: **verified**
  (0.933 within 0.925--0.941 ms per audio-minute on the validation run).
- Assertion-size linearity: **verified**, slope varies by less than 1.35x across
  the whole 1 to 256 interval range.
- Long-asset dilution scaling: **verified**, 10.0x reduction per 10x duration.

## Pitfalls checked and cleared

- **Join explosion analogue (double-counted intervals).** Output partitions are
  built globally across overlapping pieces; the overlay regression test and the
  interval-count consistency checks confirm no duplication.
- **Average of averages.** Dilution is reported as a median of per-clip ratios.
  The pooled sample-weighted ratio differs by at most 0.28 percentage points, so
  the choice does not distort any reported figure.
- **Survivorship bias.** The corpus is constructed rather than sampled from
  survivors, and the eight clips whose generated segment falls entirely inside
  the removed band are retained and correctly reported as captured-only rather
  than being dropped.
- **Denominator shifting.** Every rate in the paper uses a denominator stated in
  the same table row. The dilution chain arm uses 200 clips against the
  per-transformation arm's 600; both counts are printed in the table.
- **Selection bias in segmentation.** Segments are defined by construction at
  corpus build time, before any measurement.
- **Incomplete period comparison.** The confounded chain comparison above was
  the analogue of this and has been fixed.

## Required caveats for readers

- Fixture rates are a mechanism stress rate on a frozen adversarial family, not
  a prevalence estimate for any deployed system.
- Timing figures are single-machine medians for a Python reference
  implementation and are not language-independent constants.
- Guard bands are validated for the exact processing configurations used here
  and no others.
- The differential oracle is author-written; it tests transcription and
  interval-arithmetic error, not author independence.
- The signing credential is trusted under a locally declared anchor, not under
  the C2PA Conformance Program.
- Independent reproduction on second hardware has been performed by
  D. A. Balderrama-Alvarez and is reported in Section 7.11; it returned every
  headline count unchanged and found two declared footprints his FFmpeg 8.0.1
  build does not satisfy. A third-party reimplementation of the contract itself
  is still outstanding, and the Zenodo DOIs are not yet assigned.
