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
