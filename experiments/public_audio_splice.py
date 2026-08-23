"""Experiment C -- ground-truth recovery on the mixed-origin audio corpus.

No detector is trained and no acoustic feature is computed.  The question is
whether the evidence carried through a representation-only transformation still
identifies the generated interval of each clip at sample resolution.
"""
from __future__ import annotations

import json, sys, time
from typing import Dict, List

from _common import CAPTURE_SUPPORT, CHANNEL, ROOT, SCOPE, emit  # noqa: E402
from em_audio.evidence import (BOT, Evidence, _Bot, aggregate, claim_of, label_of, promotes)
from em_audio.interval_map import SourceInterval, Timeline, em_intervals, span_evidence
import em_audio.operators as O

CORPUS = ROOT / "corpus"


def timeline_of(rec: Dict[str, object]) -> Timeline:
    ivs = []
    for seg in rec["ground_truth"]:
        k = seg["kind"]
        ev = Evidence(P=claim_of([k]),
                      S={CHANNEL: CAPTURE_SUPPORT[k]},
                      A={CHANNEL: SCOPE},
                      L=frozenset({seg["lineage"]}))
        ivs.append(SourceInterval("clip", seg["start"], seg["end"], ev))
    return Timeline("clip", ivs)


def state_per_sample(intervals, n) -> List[str]:
    out = [None] * n
    for iv in intervals:
        for k in range(iv.out_start, min(iv.out_end, n)):
            out[k] = iv.ev.label
    return out


def main() -> int:
    t0 = time.time()
    index = json.loads((CORPUS / "corpus_index.json").read_text())
    exact = 0
    gen_recovered = 0
    base_promotions = 0
    em_promotions = 0
    base_lineage_omissions = 0
    em_lineage_omissions = 0
    boundary_err_samples = 0
    worst_boundary_err = 0
    per_op: Dict[str, Dict[str, int]] = {}

    for rec in index:
        tl = timeline_of(rec)
        tls = {"clip": tl}
        n = rec["n_samples"]
        gt = rec["ground_truth"]
        need = frozenset(seg["lineage"] for seg in gt)

        # representation-only chain that keeps the whole clip
        out = O.transcode("clip", n, "flac")
        ivs = em_intervals(out, tls, footprint_aware=True)
        got = [(iv.out_start, iv.out_end, iv.ev.label) for iv in ivs]
        want = [(s["start"], s["end"],
                 {"C": "CAPTURED", "G": "GENERATED"}[s["kind"]]) for s in gt]
        if got == want:
            exact += 1
        else:
            err = max(abs(a[0] - b[0]) for a, b in zip(got, want)) if len(got) == len(want) else n
            boundary_err_samples += err
            worst_boundary_err = max(worst_boundary_err, err)

        # is the generated interval still identifiable?
        gen_seg = [s for s in gt if s["kind"] == "G"][0]
        marked = [iv for iv in ivs if iv.ev.label == "GENERATED"]
        if marked and marked[0].out_start == gen_seg["start"] and marked[-1].out_end == gen_seg["end"]:
            gen_recovered += 1

        ev_em = aggregate([iv.ev for iv in ivs])
        ev_bs = aggregate([iv.ev for iv in span_evidence(out, tls, "boundary")])
        truth = claim_of({s["kind"] for s in gt})
        if promotes(truth, ev_bs.P):
            base_promotions += 1
        if promotes(truth, ev_em.P):
            em_promotions += 1
        if not need <= ev_em.L:
            em_lineage_omissions += 1
        if not need <= ev_bs.L:
            base_lineage_omissions += 1

        for name, o in [("trim_10pct", O.trim("clip", n, n // 10, n - n // 10)),
                        ("resample_16_8", O.resample("clip", n, 16000, 8000)),
                        ("transcode_mp3", O.transcode("clip", n, "mp3")),
                        ("normalize", O.normalize("clip", n)),
                        ("time_stretch_1.10", O.time_stretch("clip", n, 1.10, 16000))]:
            d = per_op.setdefault(name, {"baseline_promotions": 0, "em_promotions": 0,
                                         "baseline_lineage_omissions": 0, "em_lineage_omissions": 0})
            rep = set()
            for pc in o.pieces:
                for si, s in enumerate(gt):
                    if s["start"] < pc.src_end and s["end"] > pc.src_start:
                        rep.add(si)
            t_atoms = {gt[si]["kind"] for si in rep}
            t = claim_of(t_atoms)
            need_op = frozenset(gt[si]["lineage"] for si in rep)
            e_em = aggregate([iv.ev for iv in em_intervals(o, tls, footprint_aware=True)])
            e_bs = aggregate([iv.ev for iv in span_evidence(o, tls, "boundary")])
            if promotes(t, e_bs.P):
                d["baseline_promotions"] += 1
            if promotes(t, e_em.P):
                d["em_promotions"] += 1
            if not need_op <= e_em.L:
                d["em_lineage_omissions"] += 1
            if not need_op <= e_bs.L:
                d["baseline_lineage_omissions"] += 1

    payload = {
        "n_clips": len(index),
        "exact_interval_recovery": exact,
        "generated_interval_recovered": gen_recovered,
        "worst_boundary_error_samples": worst_boundary_err,
        "baseline_provenance_promotions": base_promotions,
        "em_provenance_promotions": em_promotions,
        "baseline_lineage_omissions": base_lineage_omissions,
        "em_lineage_omissions": em_lineage_omissions,
        "per_operator": per_op,
        "note": ("no classifier is trained and no acoustic feature is used; the generated "
                 "interval is recovered from carried evidence, not detected from the signal"),
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("C_public_audio_splice", payload)
    print(f"clips={len(index)} exact={exact} gen_recovered={gen_recovered} "
          f"baseline_promotions={base_promotions} em_promotions={em_promotions}")
    fail = (exact != len(index)) or em_promotions or em_lineage_omissions
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
