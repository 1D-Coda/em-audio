# EM-Audio — evidence-monotone audio representation

Reference implementation and reproducibility package for an **operator contract
on derived audio representations**: a representation-only transformation may
change, simplify, compress, aggregate or reorganise content, but it must not
silently increase the evidential authority of the output relative to the
complete source material that output represents.

This repository accompanies the manuscript *Evidence-Monotone Audio
Representation: Preventing Provenance Promotion Across Derived Audio
Transformations*.  It does **not** detect deepfakes, does not prove audio is
real, and makes no claim about the truthfulness of speech.

## One-command reproduction

```bash
git clone <repo> && cd em-audio && git checkout v1.0.1 && ./run_all.sh
```

`run_all.sh` exits non-zero if any conformance check fails.  It fetches the
public corpus (checksum-pinned), generates the test signing credential, runs
every experiment, regenerates every table and figure from the machine-readable
results, and writes `results/PREFLIGHT.txt`.

### Requirements

| Tool | Version used | Role |
|---|---|---|
| Python | 3.11.15 | reference implementation (standard library only) |
| FFmpeg | 9.0.1 | the only software in the audio signal path |
| c2patool | 0.27.2 | C2PA signing and validation |
| Node.js | 26.0.0 | second-language differential oracle |
| Piper (piper-tts) | 1.7.0 | neural-TTS robustness arm only |
| eSpeak NG | 1.52.0 | locally generated synthetic speech |
| matplotlib | 3.11.1 | figure rendering only |

## Layout

```
em_audio/            reference implementation
  evidence.py        provenance/support/scope/lineage algebra; the meet
  interval_map.py    temporal interval maps and the two evidence policies
  operators.py       the v1 operator set and its declared kernel footprints
  conformance.py     executable checks for properties P1-P7
  ffmpeg_ops.py      stock-FFmpeg command lines (no project code in the signal path)
  essence.py         decoded-PCM essence hashing (signal transparency, P8)
  manifest_schema.py EM assertion, serialised with C2PA temporal regions
  c2pa_bridge.py     signing and validation through the official c2patool
oracle_js/oracle.js  independent second implementation (different algorithm)
tests/               named regression tests
experiments/         experiments A-I, each emitting machine-readable results
fixtures/            frozen timelines, frozen oracle cases, frozen manifests
results/             machine_readable/ + tables/ + figures/ + PREFLIGHT.txt
tools/               corpus and voice fetch, test credential, tables, figures, preflight
```

## What each experiment establishes

| Experiment | Question | Pass condition |
|---|---|---|
| A | Does the contract hold on every finite source word over `{C, G, ⊥}`? | zero failed checks |
| B | How often does boundary-only inheritance promote, and does EM ever? | EM zero at every depth and operator |
| C | Is the generated interval still identifiable after transformation? | exact recovery on every clip |
| D | Does the interval model match real FFmpeg output, and does EM promote? | guard bands adequate, EM zero |
| E | What happens when provenance is absent or broken? | never CAPTURED; stripped ⇒ UNVERIFIED |
| F | Does the signed round-trip work, and is the signal unchanged? | validation passes; decoded essence identical |
| G | What does the bookkeeping cost? | reported, not gated |
| H | Do two independent algorithms agree, in both interval geometries? | exact agreement |
| B2 | Which baseline shortcut causes which failure? | each shortcut fails exactly one arm |
| I | What does the conservatism cost in evidence? | dilution confined to footprint-wide boundary bands |
| J | Does the contract ride inside a real C2PA `componentOf` composition? | all compositions trusted, aggregate MIXED, zero essence mismatches |
| C2 | Does the result survive neural TTS and buried boundaries? | exact recovery, EM zero, on both arms |

## Scope

**In scope.** Provenance promotion through representation-only transformations,
when source evidence exists, the processing system holds the source-to-output
mapping, the operator is expected to conform, and cryptographic primitives and
signing keys are intact.

**Out of scope.** Lying capture devices, compromised signing keys, dishonest
certificate authorities, unsigned media of unknown origin, speaker identity,
truthfulness of speech content, waveform-artefact deepfake detection, watermark
removal, and full provenance stripping followed by a fresh dishonest trust
chain.

A cryptographically valid signature proves that an assertion was signed, not
that it is true.

## Licence

MIT (see `LICENSE`).  Third-party data and tool licences are recorded in
`DATA_LICENSES.md`.
