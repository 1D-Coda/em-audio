"""Experiment D -- transformation matrix over the mixed-origin corpus.

Every transformation is executed by stock ffmpeg through its command line.  For
each transformation the experiment records:

  * predicted vs actual output sample count (validates the interval model
    against the behaviour of software the authors do not control),
  * EM and baseline provenance state and lineage completeness,
  * promotion violations against sample-exact ground truth,
  * decoded-essence hash of the produced asset,
  * wall-clock runtime and metadata size of the emitted EM assertion.
"""
from __future__ import annotations

import json, statistics, sys, time, wave
from pathlib import Path
from typing import Dict, List, Tuple

from _common import CAPTURE_SUPPORT, CHANNEL, ROOT, SCOPE, emit  # noqa: E402
from em_audio import ffmpeg_ops as F
from em_audio.essence import decoded_pcm, essence_hash
from em_audio.evidence import Evidence, aggregate, claim_of, leq_claim, promotes
from em_audio.consumer import verify
from consumer_verification import assertion_for, source_assertion
from em_audio.interval_map import (SourceInterval, Timeline, conform_to_decoded, em_intervals,
                                   span_evidence, strict_profile)
from em_audio.manifest_schema import em_assertion
import em_audio.manifest_schema as M
import em_audio.operators as O
from em_audio.operators import GUARD_BAND

CORPUS = ROOT / "corpus"
WORK = CORPUS / "transformed"
FS = 16_000
DETERMINISM_SUBSET = 100


def frames(p: Path) -> int:
    with wave.open(str(p), "rb") as w:
        return w.getnframes()


def timeline_of(rec) -> Timeline:
    ivs = []
    for seg in rec["ground_truth"]:
        k = seg["kind"]
        ivs.append(SourceInterval("clip", seg["start"], seg["end"],
                                  Evidence(P=claim_of([k]), S={CHANNEL: CAPTURE_SUPPORT[k]},
                                           A={CHANNEL: SCOPE},
                                           L=frozenset({seg["lineage"]}))))
    return Timeline("clip", ivs)


def interval_promotes(claimed, model, tls) -> bool:
    """True if any claimed interval asserts more than the complete-source record
    over the nominal map for exactly its own output samples: promotion at
    interval level, which a whole-output aggregate can hide."""
    from em_audio.interval_map import _sources_for
    for c in claimed:
        srcs = []
        for p in model.pieces:
            if p.out_start < c.out_end and c.out_start < p.out_end:
                srcs.extend(_sources_for(p, tls, c.out_start, c.out_end, footprint_aware=False))
        if srcs and not leq_claim(c.ev.P, aggregate([s.ev for s in srcs]).P):
            return True
    return False


def partialspoof_index():
    """PartialSpoof utterances as corpus records, ground truth from the dataset.

    Bona fide spans are captured and spoofed spans generated. Non-speech spans
    (label 2 in the timestamp files) take the dataset's own 10 ms frame label at
    their midpoint, so no provenance is assigned that the dataset does not give.
    """
    sub = json.loads((CORPUS / "partialspoof" / "partialspoof_subset.json").read_text())
    recs = []
    for i, (uid, u) in enumerate(sorted(sub["utterances"].items())):
        path = CORPUS / "partialspoof" / "wav" / f"{uid}.wav"
        n = frames(path)
        lab = u["seglab_0.01"]
        rows = []
        for a, b, c in u["vad"]:
            if c == 2:
                k = min(len(lab) - 1, int((a + b) / 2 / 0.01))
                c = lab[k] if lab else 1
            kind = "C" if c == 1 else "G"
            s, e = min(n, round(a * FS)), min(n, round(b * FS))
            if e <= s:
                continue
            if rows and rows[-1][0] == kind:
                rows[-1][2] = e
            else:
                rows.append([kind, s, e])
        if not rows:
            continue
        rows[0][1] = 0
        rows[-1][2] = n
        for x, y in zip(rows, rows[1:]):
            y[1] = x[2]
        gt = [{"kind": k, "start": s, "end": e, "lineage": f"urn:partialspoof:{uid}:{j}"}
              for j, (k, s, e) in enumerate(rows) if e > s]
        recs.append({"id": i, "uid": uid, "path": str(path.relative_to(ROOT)),
                     "n_samples": n, "ground_truth": gt})
    return recs


def main() -> int:
    global WORK
    t0 = time.time()
    ps = "--partialspoof" in sys.argv
    if ps:
        index = partialspoof_index()
        WORK = CORPUS / "partialspoof" / "transformed"
    else:
        index = json.loads((CORPUS / "corpus_index.json").read_text())
    WORK.mkdir(parents=True, exist_ok=True)

    gen_tone = WORK / "_overlay_tone.wav"
    F.sine(gen_tone, 0.5, FS, 660.0)
    n_tone = frames(gen_tone)
    tone_ev = Evidence(P=claim_of(["G"]), S={CHANNEL: 0.05}, A={CHANNEL: SCOPE},
                       L=frozenset({"urn:emaudio:ffmpeg-lavfi-sine:660Hz"}))
    tone_tl = Timeline("tone", [SourceInterval("tone", 0, n_tone, tone_ev)])

    stats: Dict[str, Dict[str, object]] = {}
    essence_records: List[Dict[str, str]] = []
    det_mismatch = 0

    for ci, rec in enumerate(index):
        src = ROOT / rec["path"]
        tl = timeline_of(rec)
        tls = {"clip": tl, "tone": tone_tl}
        n = rec["n_samples"]
        gt = rec["ground_truth"]
        dur = n / float(FS)

        jobs: List[Tuple[str, object, object]] = [
            ("transcode_mp3", O.transcode("clip", n, "mp3"),
             lambda d, s=src: F.transcode(s, d, "mp3")),
            ("transcode_flac", O.transcode("clip", n, "flac"),
             lambda d, s=src: F.transcode(s, d, "flac")),
            ("resample_16_8", O.resample("clip", n, 16000, 8000),
             lambda d, s=src: F.resample(s, d, 8000)),
            ("normalize", O.normalize("clip", n),
             lambda d, s=src: F.normalize(s, d, F.peak_gain_db(s))),
            ("trim_10_90", O.trim("clip", n, n // 10, n - n // 10),
             lambda d, s=src, n=n: F.trim(s, d, (n // 10) / FS, (n - 2 * (n // 10)) / FS)),
            ("time_stretch_1.10", O.time_stretch("clip", n, 1.10, FS),
             lambda d, s=src: F.time_stretch(s, d, 1.10)),
            ("silence_removal", O.silence_removal("clip", [(0, int(0.4 * n)), (int(0.6 * n), n)]),
             lambda d, s=src, dur=dur: F.cut_runs(s, d, [(0.0, 0.4 * dur), (0.6 * dur, dur)], FS)),
            ("overlay_generated", O.overlay(("clip", n), ("tone", n_tone), n // 2),
             lambda d, s=src, g=gen_tone, n=n: F.overlay(s, g, d, (n // 2) / FS)),
        ]

        for name, model, run in jobs:
            ext = "mp3" if name == "transcode_mp3" else ("flac" if name == "transcode_flac" else "wav")
            dst = WORK / f"{rec['id']:04d}_{name}.{ext}"
            t1 = time.perf_counter()
            run(dst)
            elapsed_ms = (time.perf_counter() - t1) * 1000.0

            st = stats.setdefault(name, {
                "n": 0, "baseline_promotions": 0, "em_promotions": 0,
                "baseline_lineage_omissions": 0, "em_lineage_omissions": 0,
                "predicted_vs_actual_abs_dev": [], "runtime_ms": [],
                "em_assertion_bytes": [], "em_intervals": 0, "baseline_intervals": 0,
                "container": ext,
                "strict_promotions": 0, "strict_lineage_omissions": 0,
                "fallback_samples": 0, "outputs_with_fallback": 0,
                "baseline_interval_promotions": 0, "baseline_either_promotions": 0,
                "em_interval_promotions": 0,
                "declared_rejected_on_decoded_length": 0, "strict_verified_on_decoded_length": 0,
            })
            st["n"] += 1

            # Every output's decoded length, so the emitted map can be fitted to
            # the samples that actually exist (conform_to_decoded).
            actual = frames(dst) if ext == "wav" else len(decoded_pcm(dst)) // 2
            # The reported mapping deviation keeps its original population:
            # every PCM output and the determinism subset of compressed ones.
            if ext == "wav" or ci < DETERMINISM_SUBSET:
                st["predicted_vs_actual_abs_dev"].append(abs(actual - model.n_out))

            ivs = em_intervals(model, tls, footprint_aware=True)
            spans = span_evidence(model, tls, "boundary")
            st["em_intervals"] += len(ivs)
            st["baseline_intervals"] += len(spans)

            rep_lineage, rep_atoms = set(), set()
            for pc in model.pieces:
                if pc.src == "tone":
                    rep_atoms.add("G"); rep_lineage |= set(tone_ev.L)
                    continue
                for s in gt:
                    if s["start"] < pc.src_end and s["end"] > pc.src_start:
                        rep_atoms.add(s["kind"]); rep_lineage.add(s["lineage"])
            truth = claim_of(rep_atoms)

            n_src = {"clip": n, "tone": n_tone}
            conf = conform_to_decoded(model, actual, n_src)
            st["fallback_samples"] += conf.params["fallback_samples"]
            st["outputs_with_fallback"] += conf.params["fallback_samples"] > 0
            e_st = aggregate([iv.ev for iv in em_intervals(strict_profile(conf, n_src), tls)])
            if promotes(truth, e_st.P):
                st["strict_promotions"] += 1
            if not frozenset(rep_lineage) <= e_st.L:
                st["strict_lineage_omissions"] += 1

            b_local = interval_promotes(spans, model, tls)
            st["baseline_interval_promotions"] += b_local
            st["em_interval_promotions"] += interval_promotes(ivs, model, tls)
            # Consumer, given the decoded length: the declared profile's map
            # stops at the modelled length; the strict profile's is fitted.
            srcs = {"clip": source_assertion(tl), "tone": source_assertion(tone_tl)}
            n_src_d = {s: n_src[s] for s in {pc.src for pc in model.pieces}}
            st["declared_rejected_on_decoded_length"] += not verify(
                assertion_for(model, ivs, "declared", n_src_d), srcs, actual)["consistent"]
            sm = strict_profile(conf, n_src)
            st["strict_verified_on_decoded_length"] += verify(
                assertion_for(sm, em_intervals(sm, tls), "strict", n_src_d), srcs, actual)["consistent"]

            e_em = aggregate([iv.ev for iv in ivs])
            e_bs = aggregate([iv.ev for iv in spans])
            if promotes(truth, e_bs.P):
                st["baseline_promotions"] += 1
            st["baseline_either_promotions"] += promotes(truth, e_bs.P) or b_local
            if promotes(truth, e_em.P):
                st["em_promotions"] += 1
            if not frozenset(rep_lineage) <= e_em.L:
                st["em_lineage_omissions"] += 1
            if not frozenset(rep_lineage) <= e_bs.L:
                st["baseline_lineage_omissions"] += 1

            st["runtime_ms"].append(round(elapsed_ms, 4))
            fs_out = M.output_sample_rate(model.operator, model.params, FS)
            assertion = em_assertion(ivs, fs_out, model.n_out, "complete-source",
                                     model.operator, model.params)
            st["em_assertion_bytes"].append(len(json.dumps(assertion).encode()))

            if ci < DETERMINISM_SUBSET:
                h1 = essence_hash(dst)
                dst2 = WORK / f"_rerun.{ext}"
                run(dst2)
                h2 = essence_hash(dst2)
                if h1 != h2:
                    det_mismatch += 1
                essence_records.append({"clip": rec["id"], "transformation": name,
                                        "essence_sha256": h1, "rerun_identical": h1 == h2})
        if (ci + 1) % 100 == 0:
            print(f"  {ci+1}/{len(index)} clips ({time.time()-t0:.0f}s)")

    summary = {}
    for name, st in stats.items():
        devs = st["predicted_vs_actual_abs_dev"]
        summary[name] = {
            "n": st["n"], "container": st["container"],
            "baseline_promotions": st["baseline_promotions"],
            "em_promotions": st["em_promotions"],
            "baseline_promotion_rate": round(st["baseline_promotions"] / st["n"], 6),
            "em_promotion_rate": round(st["em_promotions"] / st["n"], 6),
            "baseline_lineage_omissions": st["baseline_lineage_omissions"],
            "em_lineage_omissions": st["em_lineage_omissions"],
            "strict_promotions": st["strict_promotions"],
            "baseline_interval_promotions": st["baseline_interval_promotions"],
            "baseline_either_promotions": st["baseline_either_promotions"],
            "em_interval_promotions": st["em_interval_promotions"],
            "declared_rejected_on_decoded_length": st["declared_rejected_on_decoded_length"],
            "strict_verified_on_decoded_length": st["strict_verified_on_decoded_length"],
            "strict_lineage_omissions": st["strict_lineage_omissions"],
            "fallback_samples": st["fallback_samples"],
            "outputs_with_fallback": st["outputs_with_fallback"],
            "mean_em_intervals": round(st["em_intervals"] / st["n"], 3),
            "mean_baseline_intervals": round(st["baseline_intervals"] / st["n"], 3),
            "model_vs_ffmpeg_max_abs_sample_dev": (max(devs) if devs else None),
            "model_vs_ffmpeg_median_abs_sample_dev": (statistics.median(devs) if devs else None),
            "median_runtime_ms": round(statistics.median(st["runtime_ms"]), 3),
            "median_em_assertion_bytes": int(statistics.median(st["em_assertion_bytes"])),
            "declared_guard_band_samples": GUARD_BAND.get(
                {"transcode_mp3": "transcode", "transcode_flac": "transcode",
                 "resample_16_8": "resample", "normalize": "normalize",
                 "trim_10_90": "trim", "time_stretch_1.10": "time_stretch",
                 "silence_removal": "silence_removal",
                 "overlay_generated": "overlay"}[name]),
            "guard_band_covers_deviation": (
                (max(devs) if devs else 0) <= GUARD_BAND.get(
                    {"transcode_mp3": "transcode", "transcode_flac": "transcode",
                     "resample_16_8": "resample", "normalize": "normalize",
                     "trim_10_90": "trim", "time_stretch_1.10": "time_stretch",
                     "silence_removal": "silence_removal",
                     "overlay_generated": "overlay"}[name])),
        }

    payload = {
        "n_clips": len(index), "transformations": sorted(summary),
        "processing_path": "stock ffmpeg CLI only; no project code in the signal path",
        "determinism_subset_clips": DETERMINISM_SUBSET,
        "determinism_rerun_mismatches": det_mismatch,
        "per_transformation": summary,
        "ffmpeg": F.versions()["ffmpeg"],
        "runtime_s": round(time.time() - t0, 3),
    }
    if ps:
        payload["corpus"] = ("PartialSpoof v1.2 development subset (Zhang et al.; CC BY 4.0); "
                             "ground truth from the dataset's own timestamps")
        payload["mixed_utterances"] = sum(1 for r in index if len({g["kind"] for g in r["ground_truth"]}) > 1)
        segs = [len(r["ground_truth"]) for r in index]
        gen = [sum(g["end"] - g["start"] for g in r["ground_truth"] if g["kind"] == "G") / r["n_samples"]
               for r in index]
        payload["structure"] = {
            "median_intervals_per_utterance": statistics.median(segs), "max_intervals": max(segs),
            "median_duration_s": round(statistics.median(r["n_samples"] for r in index) / FS, 3),
            "median_generated_fraction": round(statistics.median(gen), 4),
            "boundary_source": "dataset timestamps rounded to the nearest sample; non-speech spans "
                               "labelled from the 10 ms segment labels"}
        payload["utterance_ids"] = [r["uid"] for r in index]
        emit("Q_partialspoof_matrix", payload)
    else:
        emit("D_transform_matrix", payload)
        (ROOT / "results" / "machine_readable" / "D_essence_hashes.json").write_text(
            json.dumps(essence_records, indent=1) + "\n", newline="\n")
    for k, v in sorted(summary.items()):
        print(f"  {k:20s} base {v['baseline_promotions']:4d}/{v['n']}  EM {v['em_promotions']}  "
              f"model_dev {v['model_vs_ffmpeg_max_abs_sample_dev']}")
    # On third-party audio a mapping-margin excess is a reported finding, not a
    # pipeline failure; promotions and lineage omissions remain failures.
    fail = det_mismatch or any(v["em_promotions"] or v["em_lineage_omissions"]
                               or v["strict_promotions"] or v["strict_lineage_omissions"]
                               or v["em_interval_promotions"]
                               or v["strict_verified_on_decoded_length"] != v["n"]
                               or (not v["guard_band_covers_deviation"] and not ps)
                               for v in summary.values())
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
