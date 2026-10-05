"""Experiment P -- can a consumer check a derived asset's claims?

Each derived output's assertion carries a dependency declaration, the map its
producer used. A consumer that reads only JSON, the assertion and each source's
own interval assertion, rebuilds the map, checks it covers the output, and
recomputes every interval's record (em_audio.consumer.verify).

Over the mixed-origin corpus and the eight transformations of Experiment D:

  honest        the producer's own complete-source claims, declared and strict
                profiles: every one should verify;
  baseline      boundary-only claims under the same honest declaration: every
                promotion Experiment D counts should be flagged;
  tampered      one interval promoted to captured-only, or one lineage entry
                dropped, after the claims were computed: each should be flagged;
  gap           the declaration's last piece removed: a coverage failure;
  narrowed      footprints declared as zero and claims computed to match: the
                limit of the check, which this should NOT catch.
"""
from __future__ import annotations

import json, statistics, sys, time
from typing import Dict

from _common import CAPTURE_SUPPORT, CHANNEL, ROOT, SCOPE, emit  # noqa: E402
from em_audio.consumer import verify
from em_audio.evidence import Evidence, claim_of, promotes, aggregate
from em_audio.interval_map import (DerivedOutput, MapPiece, OutputInterval, SourceInterval,
                                   Timeline, conform_to_decoded, em_intervals, span_evidence,
                                   strict_profile)
from em_audio.manifest_schema import (dependency_declaration, em_assertion, interval_to_json,
                                      with_declaration)
import em_audio.operators as O

FS = 16000
CORPUS = ROOT / "corpus"


def timeline_of(rec) -> Timeline:
    return Timeline("clip", [SourceInterval(
        "clip", s["start"], s["end"],
        Evidence(P=claim_of([s["kind"]]), S={CHANNEL: CAPTURE_SUPPORT[s["kind"]]},
                 A={CHANNEL: SCOPE}, L=frozenset({s["lineage"]})))
        for s in rec["ground_truth"]])


def source_assertion(tl: Timeline) -> Dict[str, object]:
    ivs = [OutputInterval(i.start, i.end, i.ev) for i in tl.intervals]
    return json.loads(json.dumps(em_assertion(ivs, FS, tl.end, "source", "capture", {})))


def assertion_for(model, ivs, profile, n_src):
    a = em_assertion(ivs, FS, model.n_out, "complete-source", model.operator, model.params)
    # Serialised and parsed, so the consumer sees exactly what a manifest carries.
    return json.loads(json.dumps(with_declaration(a, dependency_declaration(model, profile, n_src))))


def main() -> int:
    t0 = time.time()
    ps = "--partialspoof" in sys.argv
    if ps:
        from transform_matrix import partialspoof_index
        index = partialspoof_index()
    else:
        index = json.loads((CORPUS / "corpus_index.json").read_text())
    tone_ev = Evidence(P=claim_of(["G"]), S={CHANNEL: 0.05}, A={CHANNEL: SCOPE},
                       L=frozenset({"urn:emaudio:ffmpeg-lavfi-sine:660Hz"}))
    n_tone = FS // 2
    tone_tl = Timeline("tone", [SourceInterval("tone", 0, n_tone, tone_ev)])
    jobs = {
        "trim_10_90": lambda n: O.trim("clip", n, n // 10, n - n // 10),
        "resample_16_8": lambda n: O.resample("clip", n, 16000, 8000),
        "transcode_mp3": lambda n: O.transcode("clip", n, "mp3"),
        "transcode_flac": lambda n: O.transcode("clip", n, "flac"),
        "normalize": lambda n: O.normalize("clip", n),
        "time_stretch_1.10": lambda n: O.time_stretch("clip", n, 1.10, FS),
        "silence_removal": lambda n: O.silence_removal("clip", [(0, int(0.4 * n)), (int(0.6 * n), n)]),
        "overlay_generated": lambda n: O.overlay(("clip", n), ("tone", n_tone), n // 2),
    }
    c = {k: 0 for k in ("outputs", "honest_declared_ok", "honest_strict_ok", "baseline_promoting",
                        "baseline_promoting_flagged", "baseline_clean_flagged",
                        "tamper_promote_cases", "tamper_promote_flagged",
                        "tamper_lineage_cases", "tamper_lineage_flagged",
                        "gap_cases", "gap_flagged", "narrowed_cases", "narrowed_passed",
                        "shortened_cases", "shortened_flagged")}
    bytes_plain, bytes_decl, verify_ms = [], [], []
    for rec in index:
        n = rec["n_samples"]
        tl = timeline_of(rec)
        tls = {"clip": tl, "tone": tone_tl}
        srcs = {"clip": source_assertion(tl), "tone": source_assertion(tone_tl)}
        truth = claim_of({s["kind"] for s in rec["ground_truth"]})
        for name, mk in jobs.items():
            model = mk(n)
            n_src = {s: (n if s == "clip" else n_tone) for s in {p.src for p in model.pieces}}
            c["outputs"] += 1
            ivs = em_intervals(model, tls)
            plain = em_assertion(ivs, FS, model.n_out, "complete-source", model.operator, model.params)
            bytes_plain.append(len(json.dumps(plain).encode()))
            honest = assertion_for(model, ivs, "declared", n_src)
            bytes_decl.append(len(json.dumps(honest).encode()))
            t1 = time.perf_counter()
            c["honest_declared_ok"] += verify(honest, srcs)["consistent"]
            verify_ms.append((time.perf_counter() - t1) * 1000.0)
            sm = strict_profile(model, n_src)
            c["honest_strict_ok"] += verify(assertion_for(sm, em_intervals(sm, tls), "strict", n_src),
                                            srcs)["consistent"]
            # Boundary-only claims under the honest declaration.
            spans = span_evidence(model, tls, "boundary")
            v = verify(assertion_for(model, spans, "declared", n_src), srcs)
            src_truth = aggregate([iv.ev for iv in em_intervals(model, tls, footprint_aware=False)]).P
            if promotes(src_truth, aggregate([s.ev for s in spans]).P):
                c["baseline_promoting"] += 1
                c["baseline_promoting_flagged"] += v["verdict"] == "PROMOTION"
            else:
                c["baseline_clean_flagged"] += v["verdict"] == "PROMOTION"
            # Tampering after the claims were computed.
            a = assertion_for(model, ivs, "declared", n_src)
            mixed = [i for i in a["intervals"] if i["provenance"] == ["C", "G"]]
            if mixed:
                c["tamper_promote_cases"] += 1
                mixed[0]["provenance"], mixed[0]["state"] = ["C"], "CAPTURED"
                c["tamper_promote_flagged"] += verify(a, srcs)["verdict"] == "PROMOTION"
            a = assertion_for(model, ivs, "declared", n_src)
            multi = [i for i in a["intervals"] if len(i["lineage"]) > 1]
            if multi:
                c["tamper_lineage_cases"] += 1
                multi[0]["lineage"] = multi[0]["lineage"][:-1]
                c["tamper_lineage_flagged"] += verify(a, srcs)["verdict"] == "PROMOTION"
            a = assertion_for(model, ivs, "declared", n_src)
            if len(a["dependencyDeclaration"]["pieces"]) >= 1 and model.pieces[-1].out_end == model.n_out \
                    and all(p.out_end < model.n_out for p in model.pieces[:-1]):
                c["gap_cases"] += 1
                a["dependencyDeclaration"]["pieces"].pop()
                c["gap_flagged"] += verify(a, srcs)["verdict"] == "COVERAGE_FAILURE"
            # A declaration shortened consistently, map and length together,
            # over unchanged audio: caught only by a consumer that decodes.
            if model.n_out > 200:
                short = conform_to_decoded(model, model.n_out - 100, n_src)
                c["shortened_cases"] += 1
                c["shortened_flagged"] += verify(assertion_for(short, em_intervals(short, tls), "declared",
                                                              n_src), srcs, model.n_out)["verdict"] == "LENGTH_MISMATCH"
            # The limit: a producer that under-declares and stays consistent with it.
            if any(p.footprint for p in model.pieces):
                narrow = DerivedOutput(model.n_out, [MapPiece(p.out_start, p.out_end, p.src, p.src_start,
                                                              p.src_end, 0, p.label) for p in model.pieces],
                                       model.operator, model.params)
                c["narrowed_cases"] += 1
                c["narrowed_passed"] += verify(assertion_for(narrow, em_intervals(narrow, tls), "declared",
                                                             n_src), srcs)["consistent"]
    cost = {"median_assertion_bytes_without_declaration": int(statistics.median(bytes_plain)),
            "median_assertion_bytes_with_declaration": int(statistics.median(bytes_decl)),
            "median_verify_ms": round(statistics.median(verify_ms), 3),
            "max_verify_ms": round(max(verify_ms), 3)}
    emit("Q_partialspoof_consumer" if ps else "P_consumer_verification", dict(c, cost=cost, n_clips=len(index), transformations=sorted(jobs),
                                         runtime_s=round(time.time() - t0, 3)))
    for k, v in c.items():
        print(f"  {k:28s} {v}")
    ok = (c["honest_declared_ok"] == c["outputs"] == c["honest_strict_ok"]
          and c["baseline_promoting_flagged"] == c["baseline_promoting"]
          and c["tamper_promote_flagged"] == c["tamper_promote_cases"]
          and c["tamper_lineage_flagged"] == c["tamper_lineage_cases"]
          and c["gap_flagged"] == c["gap_cases"]
          and c["shortened_flagged"] == c["shortened_cases"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
