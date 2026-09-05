# Phase 0 — novelty falsification and closest-work matrix (Gate 0A)

**Search dates.** First pass 2026-08-19 (execution); re-run 2026-09-05,
immediately before submission.  The re-run is recorded below alongside the
first pass, since what a novelty search establishes depends on when it was
last attempted.

**Databases and interfaces.** Web search over the open literature; arXiv;
IACR Cryptology ePrint Archive; ACM Digital Library and DROPS/LIPIcs listings;
the C2PA specification site (`spec.c2pa.org`); OpenSLR.

**Query strings used (first pass).**  Left as executed; the re-run's targets
are recorded separately below.

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

> To our knowledge, searching through 2026-09-05 with the databases recorded
> above, the first-pass query strings recorded above and the re-run targets
> recorded below, we found no prior work that combines (X) an
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
Discussion.  The re-run of 2026-09-05 recorded below did not disturb this
verdict.

## Re-run 2026-09-05 — outcome

Executed 2026-09-05, immediately before submission, over the databases and
interfaces listed above.  The re-run was conducted to **falsify** the novelty
claim rather than to support it, and it targeted the three statements this work
depends on:

1. that a derived segment must not carry provenance stronger than its weakest
   required source;
2. that per-operator kernel support is declared and calibrated rather than
   assumed;
3. that the resulting interval evidence is carried in a signed C2PA manifest
   over temporal regions.

These are search *targets*, not query strings.  The strings listed above are
those of the first pass and are left as executed.

**No prior work stating any of the three was found.**

What the searches did return is the established algebraic material this paper
takes as given, which is the outcome the claim predicts: the meet-semilattice
construction, and the restriction of semiring provenance to monotone queries,
are prior art and are cited as such.  The theorem therefore remains **not
claimed as new**.

The closest adjacent work remains two 2026 preprints, both already rows in
Table N1 and both cited before the re-run:

- Fu et al., *Trust the voice, hide the source* (ePrint 2026/1308) — anonymous
  provenance for verifiably edited audio;
- Golaszewski et al., *Security analysis of C2PA* (ePrint 2026/804) — a
  security analysis of C2PA and its implementations.

**Neither defines an inheritance rule over media time.**  C2PA itself records
multiple sources as ingredients but specifies no rule constraining what a
derived asset may claim relative to them, which is the gap this work addresses.

**Effect on the paper: none.**  Nothing found in the re-run changed a claim or
added a reference.  No row was added to Table N1 and no cell in it was changed,
because the re-run surfaced no work not already represented there.  A search
that surfaces only works already cited is the result recorded here, not
evidence that none was sought.
