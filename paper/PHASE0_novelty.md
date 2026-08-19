# Phase 0 — novelty falsification and closest-work matrix (Gate 0A)

**Search dates.** 2026-08-19 (execution).  To be re-run and re-recorded
immediately before submission.

**Databases and interfaces.** Web search over the open literature; arXiv;
IACR Cryptology ePrint Archive; ACM Digital Library and DROPS/LIPIcs listings;
the C2PA specification site (`spec.c2pa.org`); OpenSLR.

**Query strings used.**

1. `provenance semiring non-amplification derived media operator monotone provenance lattice`
2. `C2PA content credentials audio provenance derived asset ingredient inheritance research paper 2026`
3. `"provenance laundering" OR "metadata washing" media provenance attack C2PA`
4. `audio editing provenance preservation composition proof interval lineage trim concatenate resample formal`
5. `Denning lattice model secure information flow non-interference applied to media provenance labels 2025 2026`
6. `audio deepfake detection survey 2026 speech antispoofing ASVspoof 5 generalization`
7. `audio watermarking soft binding C2PA durable content credentials AudioSeal 2026`

## Table N1 — closest-work matrix

Legend: ● provided · ○ not provided · ◐ partial.

| Work | Modality | Cryptographic provenance | Complete-source operator rule | Non-amplification theorem | Interval / temporal lineage | No ML required | C2PA integration | Public reproducibility |
|---|---|---|---|---|---|---|---|---|
| Green, Karvounarakis & Tannen, *Provenance semirings* (PODS 2007) and the semiring-provenance line | none (databases) | ○ | ○ | ● (abstract, as semiring/lattice algebra) | ○ | ● | ○ | ○ |
| Denning, *A lattice model of secure information flow* (CACM 1976); non-interference line | none (systems) | ○ | ○ | ● (abstract, as label lattice) | ○ | ● | ○ | ○ |
| W3C PROV-DM (2013) | any | ○ | ○ | ○ | ◐ (graph, not interval-normative) | ● | ○ | ○ |
| C2PA specification 2.4 (2026) | image/audio/video/doc | ● | ○ | ○ | ◐ (temporal regions of interest exist, no aggregation rule) | ● | ● | ○ |
| Golaszewski et al., *Security analysis of C2PA* (ePrint 2026/804) | multi | ● (analysed) | ○ | ○ | ○ | ● | ● | ◐ |
| Nemecek et al., *Authenticated contradictions from desynchronized provenance and watermarking* (arXiv 2603.02378) | image | ● | ○ | ○ | ○ | ○ (detector/audit) | ● | ◐ |
| Ono, *MerkleSpeech* (arXiv 2602.10166) | speech | ● | ○ | ○ | ● (chunk-localised) | ○ (perceptual fingerprints) | ◐ (compared against) | ◐ |
| Fu et al., *Trust the voice, hide the source* (ePrint 2026/1308) | audio | ● (zero-knowledge) | ○ | ○ | ◐ (segmentation-based edits) | ● | ○ | ◐ |
| Audio deepfake detection (ASVspoof line, surveys) | speech | ○ | ○ | ○ | ◐ (localisation in some systems) | ○ | ○ | ◐ |
| Audio watermarking / soft bindings (AudioSeal, SynthID, C2PA soft bindings) | audio | ◐ | ○ | ○ | ◐ | ○ | ● | ◐ |
| EMTRF (Urias 2026) — prior work by the same author | terrain geometry | ○ | ● (spatial) | ● (spatial instantiation) | ○ (spatial, not temporal) | ● | ○ | ● |
| **This work** | audio | ● | ● | ● (presented as an instance) | ● | ● | ● | ● |

**Columns empty across every prior row:** *complete-source operator rule* and
*C2PA-integrated interval-level enforcement*.  No prior row combines a
complete-source operator rule with a temporal media instantiation and a signed
transport.

## Gate 0A statement

> To our knowledge, searching through 2026-08-19 with the databases and query
> strings recorded above, we found no prior work that combines (X) an
> operator-level complete-source evidence rule for derived media, (Y) a temporal
> interval instantiation over audio with declared kernel footprints, and (Z) a
> signed C2PA transport carrying the resulting interval evidence, together with
> an executable conformance suite.

**Gate 0A: PASS, with mandatory reframing.**  Provenance-semiring and
information-flow work already yields the non-amplification property abstractly.
The theorem is therefore **not claimed as new**.  It is presented as an instance
of a known meet-semilattice construction, and the contribution is relocated to
the executable temporal operator contract, its measured demonstration, and the
signed transport.  This is stated in the Introduction, the Formal model and the
Discussion.
