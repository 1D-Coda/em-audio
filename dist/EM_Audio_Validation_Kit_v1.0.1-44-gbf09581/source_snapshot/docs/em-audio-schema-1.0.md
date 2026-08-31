# EM-Audio evidence assertion, version 1.0

A C2PA vendor assertion carrying evidence-monotone provenance for derived audio,
one entry per output evidence interval.

- **Assertion label**: `io.github.1d-coda.emaudio.evidence`
- **Schema identifier**: `https://github.com/1D-Coda/em-audio/blob/main/docs/em-audio-schema-1.0.md`
- **Namespace**: `io.github.1d-coda`

This is a vendor extension built entirely on extension points the specification
already defines. It proposes no change to C2PA, has not been submitted to the
C2PA working group, and no endorsement is claimed or implied. The reference
implementation is `em_audio/manifest_schema.py`; this document describes what
that module emits and is generated from it.

## Where the extension points come from

Temporal extent uses a C2PA region of interest with an `npt` temporal range
(C2PA 2.4 §18.2.2.3), which is the specification's own mechanism for making an
assertion apply to part of an asset. Sample-exact bounds are carried alongside
because `npt` strings are lossy at sample resolution: the npt value is for
readers that understand only time, and the sample bounds are normative.

## Fields

Per interval:

| Field | Meaning |
|---|---|
| `regionOfInterest` | C2PA temporal region, `npt` start and end in seconds |
| `samples` | sample-exact `start` and `end`, half-open, normative |
| `provenance` | sorted list of source atoms, or `null` for unverified |
| `state` | presentation label, for convenience only |
| `support` | per-channel support values, or unavailable |
| `applicability` | channels the claim is applicable to |
| `lineage` | union of contributing source identifiers |

`provenance` is `null` when the interval is unverified, and never an atom. This
is the absorbing bottom of the claim order, and a reader that treats a missing
`provenance` as an empty set rather than as unverified has broken the contract's
central guarantee.

The normative fields are `provenance`, `support`, `applicability` and `lineage`.
`state` is derived from `provenance` for human display and carries no
information a conforming reader should act on.

## What a conforming producer must do

Emit one entry per output evidence interval, over the **complete required source
set** of that interval as determined by the operator's declared kernel
footprint, not over the interval's endpoints. The footprint declarations are
build-specific and must be calibrated for the processing configuration in use;
`tools/calibrate_footprint.py` performs that calibration and exits non-zero when
a declaration fails to contain its own measured reach.

## Versioning

The version in the identifier changes when the meaning of an existing field
changes or a normative field is added. Additive, non-normative fields do not
change it. A reader encountering an unknown version should treat the assertion
as unverified rather than guess.
