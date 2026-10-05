"""Experiment P2 -- the consumer workflow end to end, through signed files.

Experiment P evaluates the verifier on assertions as JSON. Here every input it
uses is read back from signed C2PA assets: the derived asset's assertion and
dependency declaration from its active manifest, the source's interval evidence
from the source manifest the ingredient graph carries, and the output length by
decoding the asset. Each derived clip is signed twice, once with its honest
claims and once with one interval promoted, so the experiment separates
cryptographic validity from semantic consistency: both validate, only one
verifies.
"""
from __future__ import annotations

import json, sys, time
from pathlib import Path

from _common import CAPTURE_SUPPORT, CHANNEL, ROOT, SCOPE, emit  # noqa: E402
import _signing
import em_audio.c2pa_bridge as B
import em_audio.ffmpeg_ops as F
import em_audio.operators as O
from em_audio import fsutil as _fsutil
from em_audio.consumer import verify
from em_audio.essence import decoded_pcm
from em_audio.evidence import Evidence, claim_of
from em_audio.interval_map import SourceInterval, Timeline, em_intervals, strict_profile
from em_audio.manifest_schema import dependency_declaration, em_assertion, with_declaration

FS = 16000
N_CLIPS = 20
WORK = ROOT / "corpus" / "signed_consumer"


def timeline_of(rec) -> Timeline:
    return Timeline("clip", [SourceInterval(
        "clip", s["start"], s["end"],
        Evidence(P=claim_of([s["kind"]]), S={CHANNEL: CAPTURE_SUPPORT[s["kind"]]},
                 A={CHANNEL: SCOPE}, L=frozenset({s["lineage"]})))
        for s in rec["ground_truth"]])


def source_evidence_from(report) -> dict:
    """The source's own interval assertion, found through the derived asset's
    parentOf ingredient, never from a local copy."""
    ing = next(i for i in B.ingredients_of(report) if i.get("relationship") == "parentOf")
    man = report["manifests"][ing["active_manifest"]]
    return next(a["data"] for a in man["assertions"]
                if a["label"].split(".v")[0] == B.ASSERTION_LABEL)


def main() -> int:
    t0 = time.time()
    index = json.loads((ROOT / "corpus" / "corpus_index.json").read_text())[:N_CLIPS]
    if WORK.exists():
        _fsutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    sg = _signing.signer()
    c = {k: 0 for k in ("clips", "honest_valid", "wrong_valid", "honest_verified",
                        "wrong_flagged", "evidence_from_ingredient")}
    for rec in index:
        n = rec["n_samples"]
        tl = timeline_of(rec)
        src = ROOT / rec["path"]
        # Source asset, signed with its own interval evidence.
        src_ivs = em_intervals(O.transcode("clip", n, "wav"), {"clip": tl})
        src_assert = em_assertion(src_ivs, FS, n, "complete-source", "capture", {})
        src_signed = WORK / f"{rec['id']:04d}_src.wav"
        B.sign(src, src_signed, B.build_manifest(f"clip {rec['id']}", src_assert,
                                                 [{"action": "c2pa.created"}]), sg, WORK)
        # Derived asset: a trim by stock FFmpeg, strict profile, with declaration.
        a, b = n // 10, n - n // 10
        derived = WORK / f"{rec['id']:04d}_derived.wav"
        F.trim(src_signed, derived, a / FS, (b - a) / FS)
        model = strict_profile(O.trim("clip", n, a, b), {"clip": n})
        ivs = em_intervals(model, {"clip": tl})
        honest = with_declaration(
            em_assertion(ivs, FS, model.n_out, "complete-source", model.operator, model.params),
            dependency_declaration(model, "strict", {"clip": n}, build=F.versions()["ffmpeg"]))
        wrong = json.loads(json.dumps(honest))
        for iv in wrong["intervals"]:
            if iv["provenance"] != ["C"]:
                iv["provenance"], iv["state"] = ["C"], "CAPTURED"
                break
        c["clips"] += 1
        for tag, assertion in (("honest", honest), ("wrong", wrong)):
            out = WORK / f"{rec['id']:04d}_{tag}.wav"
            B.sign(derived, out, B.build_manifest(f"clip {rec['id']} {tag}", assertion,
                                                  [{"action": "c2pa.cropped"}]),
                   sg, WORK, parent=src_signed)
            rep = B.validate(out, sg, WORK)
            valid = B.state_of(rep) in ("Trusted", "Valid")
            c[f"{tag}_valid"] += valid
            back = B.em_assertion_of(rep)
            srcs = {"clip": source_evidence_from(rep)}
            c["evidence_from_ingredient"] += srcs["clip"] == json.loads(json.dumps(src_assert))
            decoded = len(decoded_pcm(out)) // 2
            verdict = verify(back, srcs, decoded)["verdict"]
            if tag == "honest":
                c["honest_verified"] += verdict == "CONSISTENT"
            else:
                c["wrong_flagged"] += verdict == "PROMOTION"
    _fsutil.rmtree(WORK)
    emit("P2_signed_consumer", dict(c, c2patool=B.version(), runtime_s=round(time.time() - t0, 1)))
    for k, v in c.items():
        print(f"  {k:26s} {v}")
    ok = (c["honest_valid"] == c["wrong_valid"] == c["honest_verified"] == c["wrong_flagged"]
          == c["clips"] and c["evidence_from_ingredient"] == 2 * c["clips"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
