# Final adversarial self-review

Scored 1–5 with written justification, as required before submission. Any score
below 4 blocks submission.

| # | Dimension | Score | Justification |
|---|---|---|---|
| 1 | Novelty | **4** | The algebra is explicitly *not* claimed as new: the non-amplification property is presented as an instance of a meet in a lattice, with provenance semirings and information-flow models cited, in the Introduction, the Formal model and the Discussion. What is new is the temporal operator contract over sample-exact intervals, the kernel-footprint rule with declared guard bands validated against real processing software, the footprint-monotonicity proposition, requirement (iv′), the signed transport carrying interval evidence inside C2PA temporal regions of interest, and the measured demonstration. The three closest 2026 works in this medium state no aggregation rule for disagreeing sources. Not a 5: this is an instantiation plus engineering plus measurement, and a spatial predecessor by the same author exists. |
| 2 | Mathematical correctness | **5** | The claim order and its meet are defined explicitly before any proposition, so every property is one line from the definition. Verified by 787,443 exhaustive checks over all 9,840 source words of length ≤ 8, by a closed-form oracle that recomputes expected states without the evidence algebra, and by a 9,804-case differential against a second implementation using a different algorithm, with zero disagreements and zero support difference. |
| 3 | Claim–evidence consistency | **5** | Every number is emitted by code, converted to a LaTeX macro by a generator, and used only through that macro; a checker fails the build if any bare result number appears in the source, and it passes. A claim–evidence boundary table gives a "not established by that evidence" column per experiment family. Fixture rates are labelled a mechanism stress rate in caption, text and abstract. Negative results (two operators with no baseline promotion) and a defect found in the author's own code are both reported. |
| 4 | Reproducibility | **4** | One-command reproduction from a clean clone; pinned tool versions; checksum-pinned corpus fetch; frozen fixtures and frozen manifests; commit and tag in the manuscript; `SHA256SUMS`; auto-generated preflight report; `run_all.sh` exits non-zero on any conformance failure. **Not a 5, and this is the top item to close:** no independent clean reproduction on a second machine has been performed, and the Zenodo version and concept DOIs are not yet assigned. |
| 5 | Threat-model precision | **5** | In-scope conditions enumerated; out-of-scope list explicit; required behaviour on absent or invalid evidence stated; malicious-signer limitation stated in the abstract, the threat model, the discussion and the conclusion; replay/analogue-hole limitation given its own paragraph; threat-model matrix in the supplement pairs capability against behaviour against what is not prevented. |
| 6 | Standards accuracy | **5** | Every C2PA statement carries a specification section number read from the 2.4 text: ingredient relationships (Table 10, §18.16.3), the `c2pa.opened` ingredient-reference rule (§15.11.3.2), temporal ranges in npt (§18.2.2.3). The absence of a conservativity rule is stated as an observation about the text, not as a defect. Security limitations are cited to a published analysis rather than asserted. The contract is implemented entirely inside the standard's own extension points and requires no specification change. |
| 7 | Licensing | **5** | LibriSpeech CC BY 4.0 verified from `LICENSE.TXT` inside the archive, checksum-pinned, no login wall, redistribution of derived clips permitted with attribution. Generated speech is original local output from phrases written for the study, with no voice model of any real person. Every tool licence recorded. The local test credential is documented as not being on the conformance-program trust list. |
| 8 | Publication ethics | **5** | Competing interest declared with the specific mitigations enumerated; generative-AI use declared in the form the target journal's policy requires; a non-conformance found in the author's own implementation reported in Results; no product named, evaluated or compared against; every reference verified against its primary source during preparation, with zero fabricated citations. |
| 9 | Clarity | **4** | The minimal counterexample figure is readable in ten seconds; the structure follows the required arc; the abstract follows the six-move form and ends on the boundary sentence. Not a 5: the paper is dense at 21 pages, two tables are wide, and a professional copy-edit pass would improve it. |
| 10 | Venue fit | **5** | The target journal's official aims and scope names its primary pillar as "digital evidence and multimedia, with the core qualities of provenance, integrity and authenticity", and runs an explicit track for work strengthening the rigour and reliability of digital-evidence processes. Formal-plus-systems work with no learned model fits without special pleading. |

## Post-review hardening pass (2026-08-19, second session)

An external-style review of the compiled manuscript surfaced four verifiable
issues; all were confirmed against the code and fixed, and one fix produced a
new scientific result:

1. **Timing units bug (real).** The overhead table printed the median per
   audio-minute but the IQR per repetition, putting the median outside its own
   IQR. Fixed in the table generator; median 0.805 now sits inside 0.798–0.813.
2. **Case-count arithmetic (real, explainable).** 98,385 ≠ 9,840 × 10 because
   two operator configurations are length-gated: 3×8 + 9×9 + 9,828×10 = 98,385.
   The breakdown is now recorded in the experiment payload and stated in Methods.
3. **References (real).** Pham et al. updated to *Computer Science Review* 57,
   100757 (2025), DOI 10.1016/j.cosrev.2025.100757; ASVspoof 5 updated to
   *Computer Speech and Language* 95, 101825 (2026), DOI 10.1016/j.csl.2025.101825.
   Both verified against publisher records before editing.
4. **"Usefulness unmeasured" (real, and the most valuable).** The new
   claim-dilution experiment measured the evidential cost of conservatism — and
   its first run returned 100 % dilution for filtered operators, exposing a
   genuine defect: footprint widening was applied at interval granularity
   rather than sample granularity. Safe (footprint monotonicity) but uselessly
   conservative. Fixed by refining the partition at ±footprint pull-backs;
   dilution is now confined to footprint-wide boundary bands. The two-language
   oracle had missed this because its fixtures used intervals narrower than
   every footprint; a wide-interval battery was added and the fixed
   implementation agrees with the per-sample oracle on all cases. Both catches
   are reported in the manuscript.

Additional positioning work from the same review: the C2PA argument now
distinguishes "the specification preserves component histories" from "the
specification does not prescribe the aggregate conservative claim computed over
them" (with §18.16.3 cited); the inherited-vs-new comparison moved from the
supplement into a main-text table; and the representational-versus-computational
dependency distinction is now named explicitly in the model section, resolving
the normalisation ambiguity.

## Round-2 hardening (2026-08-19, same day)

A second review round requested three substantive items and several
positioning changes. Disposition:

**Applied with new experiments (all numbers measured, none asserted):**
- **Experiment J — C2PA-native heterogeneous composition (30 fixtures).**
  Signed captured + generated sources become `componentOf` ingredients carrying
  their full manifests, with spec-conformant `c2pa.placed` hashed-URI
  references and the EM aggregate; derived and re-signed with `parentOf`.
  30/30 trusted, 30/30 aggregate MIXED, 0 essence mismatches. This closes the
  gap between the vocabulary-vs-reduction argument and the signed transport.
- **Experiment C2 — robustness arm.** 50 clips rebuilt with a neural TTS
  (Piper/VITS, public-domain LJSpeech voice; the lessac voices were rejected on
  licence grounds) and 50 clips buried under −18 dB pink noise. 100/100 exact
  recovery, 0 EM promotions — the "clean data only" critique is now answered
  empirically, not argumentatively.
- **Dilution extensions.** Overlay added to the dilution table (measured 0%,
  with the structural reason stated); the five-operator chain is now defined
  operator-by-operator in the text; and a long-asset arm measures the same
  depth-3 broadcast-style chain at 2.40% dilution on a 30 s asset and 0.24% on
  a five-minute asset — the reviewer's requested contextualization, but with
  computed numbers instead of asserted ones.

**Applied as text:** the constructed-baseline qualifier and corpus-scoped
dilution figure now appear in the abstract; figures relocated to their first
citations (Figure 1: page 20 → page 4); pitch shifting addressed as a composite
with a named regression test; automated footprint calibration and
specification-derived footprints proposed as future work; the per-sample-oracle
independence rationale stated with its honest limit; a deployment-path
paragraph (library at the operator invocation, no spec change); a concrete
PROV example; and an explicit information-flow-integrity reading.

**Declined:** quoting an uncomputed "<5% for typical broadcast workflows"
claim (replaced by the measured long-asset arm); naming commercial editors in
the standardization paragraph; a second speech corpus behind a login wall
(Common Voice) — the LJSpeech-voiced neural arm covers the external-validity
concern within Gate 0C's licence discipline.

## Round-3 hardening (2026-08-19)

A third review round raised three items; all were verified and applied, and one
correction was found in our own documentation.

1. **Robustness-arm documentation was incomplete, and one line was wrong.**
   `DATA_LICENSES.md` claimed the voice model files were "committed under
   `corpus/piper_voices/`", which stopped being true when the 63 MB model was
   untracked in favour of a fetch script. Corrected, and the entry now records
   engine version (piper-tts 1.7.0), voice, model-card version, sample rate,
   training-data licence quoted verbatim from the primary source with URL and
   access date, SHA-256 digests for both files, and the rejected `lessac`
   alternative with the reason. `tools/fetch_voice.sh` now verifies both
   digests and fails on mismatch; tested from a clean state. The pink-noise
   recipe is recorded as the exact executed command in both `DATA_LICENSES.md`
   and a new supplementary section.

2. **`c2pa.placed` versus `c2pa.mixed` now justified from the spec text.**
   Verified against C2PA 2.4 Table 8: `c2pa.mixed` covers the case where
   "multiple, previously placed (via `c2pa.placed` actions) audio ingredients
   (e.g., stems, vocals, drums, bass, etc) are combined and optionally
   transformed". Our fixture concatenates rather than sums, so `c2pa.placed`
   alone is accurate; `c2pa.mixed` also presupposes `c2pa.placed`, so the
   placed actions are required either way. An overlay composition would warrant
   `c2pa.mixed` in addition. Stated in the manuscript.

3. **"We searched the specification" now has empirical support.** The claim is
   backed by our own composition experiment rather than by assertion alone:
   every composition carries two ingredients whose declared source types
   disagree, and the official validator reports each as valid without
   computing, requiring or remarking on any aggregate over them.

Also added: one paragraph noting that chunk-localised perceptual binding and
this contract are complementary (transport resilience versus aggregation), with
an explicit statement that the combination has not been built.

**Not done, on the advice of the same review:** no further experiments. The
study now covers formal enumeration, adversarial fixtures, a labelled audio
corpus, neural-TTS and noise robustness, third-party signal processing,
C2PA-native composition, signed derivation, provenance-loss behaviour, claim
dilution, two-language differential testing and cost. More would dilute rather
than strengthen.

## Round-4 hardening (2026-08-20)

A fourth review round raised eight points; all eight were verified against the
source and the C2PA specification text, and all eight were correct.

**The substantive one.** The manuscript treated agreement between predicted and
actual output length as satisfying the condition Proposition 4 requires. It does
not. Proposition 4 requires the declared required-source set to *contain* the
actual dependency set, and an operator can emit exactly the predicted sample
count while depending on source samples outside its declared footprint. The
transformation matrix bounds mapping and alignment; it is silent on local
dependency.

The fix was to test containment directly rather than only to weaken the
sentence. Experiment K builds two sources identical except at one sample, where
one carries an added impulse, pushes both through the same stock ffmpeg command
and subtracts the decoded outputs. Across 70 probes over 7 operator
configurations, 19,582 output samples were influenced and none fell outside the
declared support. The margins also justify the particular bands rather than
merely permitting them: 65 samples of headroom against a declared 97 for
resampling, 898 against 2,304 for MP3, 688 against 2,577 for time stretching.

Building it exposed three further defects, all reported in the manuscript: a
harness bug that produced 695 false violations by decoding rate-changed output
at the source rate; the discovery that probing against silence under-tests
signal-dependent operators, since an impulse in an empty buffer is copied
through unchanged; and a spread statistic that was both miscomputed and the
wrong statistic, since containment is worst-case and overlap-add stretching has
a median spread of 1 against a maximum of 2,021.

**The other seven**, all applied: three stray uses of "lattice" where the paper
proves meet-semilattice; an inaccurate characterisation of provenance semirings
as idempotent, which they are not in general; a results table placing section
A's "0 failed" under the boundary-only comparison column, plus a cited
regression-test row that did not exist; a timing machine that Methods claimed
was declared but never was; a robustness arm missing from Data Availability; an
unconditioned inverse-proportion claim about duration; and a preprint described
as a published analysis.

## Verdict

No dimension scores below 4, so no substantive scientific blocker remains.

**Two administrative conditions must be closed before the submit button is
pressed**, both of which are stop conditions in the protocol and neither of
which can be satisfied by the author alone in this session:

1. **Independent clean reproduction.** `run_all.sh` must be executed from a clean
   clone on second hardware by a named person, and their short reproduction
   statement included in the supplement.
2. **Zenodo deposit.** Archive the tagged release and add the version and concept
   DOIs to the manuscript at proof stage.

Until both are done, the correct status is *submission-ready pending external
reproduction*, not *submitted*.
