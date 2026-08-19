# Phase 0 deliverable 3.1 — transfer memo

Written before any code.  Every row in the first column is **prior work** and is
cited rather than claimed.

| Transfers unchanged (prior work — cite) | Transfers with modification (new here) | Does not transfer |
|---|---|---|
| Evidence record `e = (P, S, A, L)`: provenance set, typed support channels, applicability/scope, complete-source lineage | The **domain of `D_y`** becomes a *temporal* required-source set over half-open sample intervals rather than a spatial vertex/cell set | Douglas–Peucker and every polyline-simplification result; there is no geometric tolerance in audio |
| Provenance as a **set** of ancestry atoms, mixed produced only by union | Atom alphabet changes from measured/interpolated `{M, I}` to captured/generated `{C, G}`; the semantic content is different even though the algebra is the same | Terrain support profiles `C_M`, `C_I`, the directional eight-ray classifier, Horn slope roughness |
| Same-channel meet (`min`) as the conservative representation rule | Unchanged as an operation; the audio channel is `capture-support`, which is a different measurand | Marching-squares corner rules, the asymptotic decider, closed-ring lexicographic anchoring |
| Absence of verified evidence is an absorbing state, never an atom | Unchanged, plus a new consequence: a `⊥` element also makes every numeric channel unavailable over the represented span (requirement iv′) | Any terrain/LiDAR result, table or figure |
| Applicability/scope intersection and lineage union | Unchanged | EC-DP itself |
| Non-promotion propositions in the *spatial* setting | Restated modality-independently and, per the Phase-0 novelty finding, presented as an **instance of known lattice/provenance algebra**, not as a new theorem | The OpenLiDARViewer source audit and its grade-as-provenance counterexample |
| Conformance-test philosophy: exhaustive finite-state enumeration, deterministic adversarial fixtures, independent oracle, frozen expected results, explicit non-prevalence language | Reused as a **method template**; all results are new | GDAL `gdal_contour` third-party audit (its audio analogue, stock FFmpeg, is new work) |
| — | **New in audio and with no spatial analogue:** the kernel-footprint rule with declared per-operator guard bands and a measured model-versus-implementation deviation; the footprint-monotonicity proposition; signal transparency verified on decoded PCM; a signed C2PA transport with temporal regions of interest; the unverified/`⊥` state as an operational validation outcome of a real verifier | — |

**Consequence for the title.** Because the shared theorem is presented as an
instance of known algebra rather than as a new modality-independent result, the
five conditions for a "cross-modal" title are not all met.  The audio-specific
title is used.
