# Phase 0 — feasibility log (Gates 0B and 0C)

## Gate 0B — C2PA transport feasibility

Verified by running, not by reading.  Executed 2026-08-19.

| Check | Result |
|---|---|
| c2patool version | 0.27.2 |
| C2PA specification version | 2.4 (April 2026), read from `spec.c2pa.org` |
| Test credential | locally generated ECDSA P-256, EKU `emailProtection` (1.3.6.1.5.5.7.3.4), PKCS#8 private key |
| Sign + validate WAV | **PASS** — `validation_state: Trusted` under the declared local anchor |
| Sign + validate MP3 | **PASS** |
| Sign + validate FLAC | **PASS** |
| Custom namespaced assertion round-trip | **PASS** — `mx.aurtech.emaudio.evidence` returns byte-equivalent after signing |
| Custom assertion survives re-signing on a derived asset | **PASS** |
| Ingredient round-trip | **PASS** — `parentOf` recorded; c2patool inserts the required `c2pa.opened` action with the hashed-URI reference (C2PA 2.4 §18.16.3, §15.11.3.2) |
| Temporal region of interest in the EM assertion | **PASS** — npt ranges round-trip (C2PA 2.4 §18.2.2.3) |

**Decision: Plan A (C2PA as the signed transport) adopted.**  No fallback to a
COSE sidecar is needed.  Two pitfalls were found and are recorded so that a
replicating reader does not lose time on them: the private key must be PKCS#8
and supplied as PEM *content* rather than a path, and a hand-written
`c2pa.opened` action without an `ingredients` parameter is rejected with
`assertion.action.ingredientMismatch` — the correct move is to let the claim
generator insert it.

**Declared limitation.** The credential is not on the C2PA Conformance Program
trust list.  `Trusted` in the results means trusted under the declared local
anchor.

## Gate 0C — corpus feasibility

| Requirement | Resolution |
|---|---|
| One licensing-clean public captured-audio source, redistribution verified from primary licence text | LibriSpeech `dev-clean`, CC BY 4.0, verified from `LICENSE.TXT` inside the archive; SHA-256 pinned; fetch scripted; no login wall |
| One openly licensed synthetic-speech source | eSpeak NG 1.52.0 formant synthesis, generated locally from phrases written for this study; no voice model of any real person |
| Uncertain voice rights | none — no speaker is identified and no voice is cloned |
| Redistribution of derived clips | permitted (CC BY 4.0 with attribution for the captured part; MIT for the generated part) |

**Gate 0C: PASS.**  The real-audio experiment is retained; no narrowing to
fully synthetic audio is required.

## Phase 0 decision

**GO.**  Scope frozen at the v1 operator set.  Title fixed to the
audio-specific form.  Theorem framed as an instance of known algebra.
