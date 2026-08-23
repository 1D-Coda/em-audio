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
from em_audio.evidence import Evidence, aggregate, claim_of, promotes
from em_audio.interval_map import SourceInterval, Timeline, em_intervals, span_evidence
from em_audio.manifest_schema import em_assertion
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


def main() -> int:
    t0 = time.time()
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
            })
            st["n"] += 1

            actual = None
            if ext == "wav":
                actual = frames(dst)
            elif ci < DETERMINISM_SUBSET:
                actual = len(decoded_pcm(dst)) // 2       # mono s16le
            if actual is not None:
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

            e_em = aggregate([iv.ev for iv in ivs])
            e_bs = aggregate([iv.ev for iv in spans])
            if promotes(truth, e_bs.P):
                st["baseline_promotions"] += 1
            if promotes(truth, e_em.P):
                st["em_promotions"] += 1
            if not frozenset(rep_lineage) <= e_em.L:
                st["em_lineage_omissions"] += 1
            if not frozenset(rep_lineage) <= e_bs.L:
                st["baseline_lineage_omissions"] += 1

            st["runtime_ms"].append(round(elapsed_ms, 4))
            assertion = em_assertion(ivs, FS, model.n_out, "complete-source",
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
    emit("D_transform_matrix", payload)
    (ROOT / "results" / "machine_readable" / "D_essence_hashes.json").write_text(
        json.dumps(essence_records, indent=1) + "\n")
    for k, v in sorted(summary.items()):
        print(f"  {k:20s} base {v['baseline_promotions']:4d}/{v['n']}  EM {v['em_promotions']}  "
              f"model_dev {v['model_vs_ffmpeg_max_abs_sample_dev']}")
    fail = det_mismatch or any(v["em_promotions"] or v["em_lineage_omissions"]
                               or not v["guard_band_covers_deviation"]
                               for v in summary.values())
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
