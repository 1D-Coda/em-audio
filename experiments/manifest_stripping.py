"""Experiment E -- behaviour when provenance is absent, broken or preserved.

Five conditions per clip.  The pass condition is a *classification* condition:
a stripped or invalid asset must be reported UNVERIFIED / INVALID and must never
be reported CAPTURED.  Nothing here claims that stripping is detected as
malicious intent: an asset can lose its manifest for entirely benign reasons.
"""
from __future__ import annotations

import json, shutil, sys, time
from pathlib import Path
from typing import Dict, List

from _common import CAPTURE_SUPPORT, CHANNEL, ROOT, SCOPE, emit  # noqa: E402
from _signing import signer                                          # noqa: E402
from em_audio import c2pa_bridge as B, ffmpeg_ops as F
from em_audio.essence import essence_hash
from em_audio.evidence import Evidence, aggregate, claim_of
from em_audio.interval_map import SourceInterval, Timeline, em_intervals
from em_audio.manifest_schema import em_assertion
import em_audio.operators as O

CORPUS = ROOT / "corpus"
WORK = CORPUS / "stripping"
FS = 16_000
N_CLIPS = 60


def timeline_of(rec) -> Timeline:
    ivs = []
    for seg in rec["ground_truth"]:
        k = seg["kind"]
        ivs.append(SourceInterval("clip", seg["start"], seg["end"],
                                  Evidence(P=claim_of([k]), S={CHANNEL: CAPTURE_SUPPORT[k]},
                                           A={CHANNEL: SCOPE}, L=frozenset({seg["lineage"]}))))
    return Timeline("clip", ivs)


def read_state(report: Dict[str, object]) -> str:
    """The provenance state a conforming consumer must report."""
    st = B.state_of(report)
    if st in ("NoManifest", "Unparseable"):
        return "UNVERIFIED"
    if st == "Invalid":
        return "INVALID"
    a = B.em_assertion_of(report)
    if not a:
        return "UNVERIFIED"
    states = {i["state"] for i in a["intervals"]}
    if "UNVERIFIED" in states:
        return "UNVERIFIED"
    if states == {"CAPTURED"}:
        return "CAPTURED"
    if states == {"GENERATED"}:
        return "GENERATED"
    return "MIXED"


def main() -> int:
    t0 = time.time()
    index = json.loads((CORPUS / "corpus_index.json").read_text())[:N_CLIPS]
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    sg = signer()

    conditions = ["valid_manifest", "manifest_removed", "asset_modified_after_signing",
                  "reencoded_without_manifest", "valid_derived_manifest"]
    tally = {c: {} for c in conditions}
    violations: List[str] = []
    per_clip: List[Dict[str, object]] = []

    for rec in index:
        src = ROOT / rec["path"]
        tl = timeline_of(rec)
        n = rec["n_samples"]
        model = O.transcode("clip", n, "wav")
        ivs = em_intervals(model, {"clip": tl}, footprint_aware=True)
        assertion = em_assertion(ivs, FS, n, "complete-source", "capture", {})
        manifest = B.build_manifest(f"clip {rec['id']}", assertion, [
            {"action": "c2pa.created",
             "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/algorithmicMedia"}])

        signed = WORK / f"{rec['id']:04d}_signed.wav"
        B.sign(src, signed, manifest, sg, WORK)
        row = {"clip": rec["id"]}

        # 1. valid manifest
        r = B.validate(signed, sg, WORK)
        s1 = read_state(r); row["valid_manifest"] = (B.state_of(r), s1)

        # 2. manifest removed (re-mux through ffmpeg, which does not carry it)
        stripped = WORK / f"{rec['id']:04d}_stripped.wav"
        F.transcode(signed, stripped, "wav")
        r2 = B.validate(stripped, sg, WORK)
        s2 = read_state(r2); row["manifest_removed"] = (B.state_of(r2), s2)

        # 3. asset modified after signing (flip bytes inside the audio payload)
        tampered = WORK / f"{rec['id']:04d}_tampered.wav"
        data = bytearray(signed.read_bytes())
        mid = len(data) // 2                      # inside the audio payload
        for k in range(mid, mid + 512):
            data[k] ^= 0xFF
        tampered.write_bytes(bytes(data))
        r3 = B.validate(tampered, sg, WORK)
        s3 = read_state(r3); row["asset_modified_after_signing"] = (B.state_of(r3), s3)

        # 4. re-encoded to another container without manifest preservation
        reenc = WORK / f"{rec['id']:04d}_reenc.mp3"
        F.transcode(signed, reenc, "mp3")
        r4 = B.validate(reenc, sg, WORK)
        s4 = read_state(r4); row["reencoded_without_manifest"] = (B.state_of(r4), s4)

        # 5. valid derived manifest with complete lineage
        derived = WORK / f"{rec['id']:04d}_derived.wav"
        F.trim(signed, derived, 0.0, n / float(FS))
        dmodel = O.trim("clip", n, 0, n)
        divs = em_intervals(dmodel, {"clip": tl}, footprint_aware=True)
        dassert = em_assertion(divs, FS, dmodel.n_out, "complete-source",
                               dmodel.operator, dmodel.params)
        dman = B.build_manifest(f"clip {rec['id']} derived", dassert,
                                [{"action": "c2pa.cropped"}])
        dsigned = WORK / f"{rec['id']:04d}_derived_signed.wav"
        B.sign(derived, dsigned, dman, sg, WORK, parent=signed)
        r5 = B.validate(dsigned, sg, WORK)
        s5 = read_state(r5)
        ing = [i.get("relationship") for i in B.ingredients_of(r5)]
        need = frozenset(seg["lineage"] for seg in rec["ground_truth"])
        got = frozenset().union(*[frozenset(i["lineage"]) for i in
                                  (B.em_assertion_of(r5) or {"intervals": []})["intervals"]]) \
            if B.em_assertion_of(r5) else frozenset()
        row["valid_derived_manifest"] = (B.state_of(r5), s5, ing, sorted(need - got))

        for cond, st in [("valid_manifest", s1), ("manifest_removed", s2),
                         ("asset_modified_after_signing", s3),
                         ("reencoded_without_manifest", s4),
                         ("valid_derived_manifest", s5)]:
            tally[cond][st] = tally[cond].get(st, 0) + 1
            if cond in ("manifest_removed", "reencoded_without_manifest") and st != "UNVERIFIED":
                violations.append(f"clip {rec['id']} {cond} -> {st}")
            if cond == "asset_modified_after_signing" and st not in ("INVALID", "UNVERIFIED"):
                violations.append(f"clip {rec['id']} {cond} -> {st}")
            if st == "CAPTURED" and cond != "valid_manifest":
                violations.append(f"clip {rec['id']} {cond} -> CAPTURED")
        if row["valid_derived_manifest"][3]:
            violations.append(f"clip {rec['id']} derived lineage incomplete")
        per_clip.append(row)

    payload = {
        "n_clips": len(index), "conditions": conditions,
        "state_tally": tally, "violations": len(violations),
        "violation_sample": violations[:20],
        "scope_note": ("an absent or invalid manifest is reported UNVERIFIED or INVALID; "
                       "no claim is made that stripping indicates malicious intent"),
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("E_manifest_stripping", payload)
    (ROOT / "results" / "machine_readable" / "E_per_clip.json").write_text(
        json.dumps(per_clip, indent=1, default=str) + "\n")
    print(json.dumps(tally, indent=1))
    print(f"violations={len(violations)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
