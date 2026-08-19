"""Experiment G -- overhead of evidence-monotone bookkeeping.

Reported as medians with interquartile ranges over >=30 repetitions on one
machine.  These are machine-dependent measurements of a Python reference
implementation, not a language-independent constant.
"""
from __future__ import annotations

import json, shutil, statistics, sys, time
from pathlib import Path
from typing import Dict, List

from _common import CHANNEL, ROOT, SCOPE, emit                        # noqa: E402
from _signing import signer                                          # noqa: E402
from em_audio import c2pa_bridge as B, ffmpeg_ops as F
from em_audio.evidence import Evidence, aggregate, claim_of
from em_audio.interval_map import SourceInterval, Timeline, em_intervals, span_evidence
from em_audio.manifest_schema import em_assertion
import em_audio.operators as O

CORPUS = ROOT / "corpus"
WORK = CORPUS / "overhead"
FS = 16_000
REPS = 30
N_CLIPS = 30
CAPTURE_SUPPORT = {"C": 0.90, "G": 0.10}


def iqr(xs: List[float]):
    q = statistics.quantiles(xs, n=4, method="inclusive")
    return round(q[0], 4), round(q[2], 4)


def summarise(xs: List[float]) -> Dict[str, float]:
    lo, hi = iqr(xs)
    return {"median": round(statistics.median(xs), 4), "q1": lo, "q3": hi,
            "min": round(min(xs), 4), "max": round(max(xs), 4), "n": len(xs)}


def timeline_of(rec) -> Timeline:
    ivs = []
    for seg in rec["ground_truth"]:
        k = seg["kind"]
        ivs.append(SourceInterval("clip", seg["start"], seg["end"],
                                  Evidence(P=claim_of([k]), S={CHANNEL: CAPTURE_SUPPORT[k]},
                                           A={CHANNEL: SCOPE}, L=frozenset({seg["lineage"]}))))
    return Timeline("clip", ivs)


def main() -> int:
    t0 = time.time()
    index = json.loads((CORPUS / "corpus_index.json").read_text())[:N_CLIPS]
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    sg = signer()

    total_minutes = sum(r["n_samples"] for r in index) / float(FS) / 60.0

    # --- bookkeeping cost, EM versus baseline, per repetition --------------
    em_ms, base_ms, ffmpeg_ms = [], [], []
    for _ in range(REPS):
        t1 = time.perf_counter()
        for rec in index:
            tl = timeline_of(rec)
            m = O.transcode("clip", rec["n_samples"], "flac")
            ivs = em_intervals(m, {"clip": tl}, footprint_aware=True)
            em_assertion(ivs, FS, m.n_out, "complete-source", m.operator, m.params)
        em_ms.append((time.perf_counter() - t1) * 1000)

        t1 = time.perf_counter()
        for rec in index:
            tl = timeline_of(rec)
            m = O.transcode("clip", rec["n_samples"], "flac")
            sp = span_evidence(m, {"clip": tl}, "boundary")
            em_assertion(sp, FS, m.n_out, "boundary-only", m.operator, m.params)
        base_ms.append((time.perf_counter() - t1) * 1000)

    for _ in range(REPS):
        t1 = time.perf_counter()
        for rec in index:
            F.transcode(ROOT / rec["path"], WORK / "bench.flac", "flac")
        ffmpeg_ms.append((time.perf_counter() - t1) * 1000)

    # --- manifest size and signing/validation cost -------------------------
    sign_ms, val_ms, man_bytes, assertion_bytes, size_delta = [], [], [], [], []
    for rec in index:
        src = ROOT / rec["path"]
        tl = timeline_of(rec)
        m = O.transcode("clip", rec["n_samples"], "wav")
        ivs = em_intervals(m, {"clip": tl}, footprint_aware=True)
        a = em_assertion(ivs, FS, m.n_out, "complete-source", m.operator, m.params)
        man = B.build_manifest(f"bench {rec['id']}", a, [{"action": "c2pa.transcoded"}])
        out = WORK / f"{rec['id']:04d}.wav"
        t1 = time.perf_counter(); B.sign(src, out, man, sg, WORK)
        sign_ms.append((time.perf_counter() - t1) * 1000)
        t1 = time.perf_counter(); B.validate(out, sg, WORK)
        val_ms.append((time.perf_counter() - t1) * 1000)
        delta = out.stat().st_size - src.stat().st_size
        size_delta.append(delta); man_bytes.append(delta)
        assertion_bytes.append(len(json.dumps(a).encode()))

    minutes_per_clip = statistics.median(r["n_samples"] for r in index) / float(FS) / 60.0

    # --- scaling of the EM assertion with the number of evidence intervals --
    scaling = []
    for k in (1, 2, 4, 8, 16, 32, 64, 128, 256):
        n = k * 4096
        ivs_src = []
        for j in range(k):
            kind = "C" if j % 2 == 0 else "G"
            ivs_src.append(SourceInterval("clip", j * 4096, (j + 1) * 4096,
                                          Evidence(P=claim_of([kind]),
                                                   S={CHANNEL: CAPTURE_SUPPORT[kind]},
                                                   A={CHANNEL: SCOPE},
                                                   L=frozenset({f"urn:emaudio:seg{j}"}))))
        tl = Timeline("clip", ivs_src)
        m = O.transcode("clip", n, "flac")
        reps = []
        for _ in range(REPS):
            t1 = time.perf_counter()
            ivs = em_intervals(m, {"clip": tl}, footprint_aware=True)
            a = em_assertion(ivs, FS, m.n_out, "complete-source", m.operator, m.params)
            reps.append((time.perf_counter() - t1) * 1000)
        scaling.append({"source_intervals": k, "emitted_intervals": len(ivs),
                        "assertion_bytes": len(json.dumps(a).encode()),
                        "median_ms": round(statistics.median(reps), 4),
                        "audio_seconds": round(n / FS, 3)})
    payload = {
        "repetitions": REPS, "clips_per_repetition": N_CLIPS,
        "audio_minutes_per_repetition": round(total_minutes, 4),
        "em_bookkeeping_ms_per_repetition": summarise(em_ms),
        "baseline_bookkeeping_ms_per_repetition": summarise(base_ms),
        "ffmpeg_transcode_ms_per_repetition": summarise(ffmpeg_ms),
        "em_ms_per_audio_minute": round(statistics.median(em_ms) / total_minutes, 4),
        "baseline_ms_per_audio_minute": round(statistics.median(base_ms) / total_minutes, 4),
        "em_over_baseline_ratio": round(statistics.median(em_ms) / statistics.median(base_ms), 4),
        "em_over_ffmpeg_fraction": round(statistics.median(em_ms) / statistics.median(ffmpeg_ms), 6),
        "sign_ms": summarise(sign_ms), "validate_ms": summarise(val_ms),
        "manifest_overhead_bytes": summarise([float(x) for x in man_bytes]),
        "em_assertion_bytes": summarise([float(x) for x in assertion_bytes]),
        "median_manifest_overhead_bytes_per_asset": int(statistics.median(man_bytes)),
        "median_em_assertion_bytes_per_asset": int(statistics.median(assertion_bytes)),
        "manifest_bytes_per_audio_minute": round(statistics.median(man_bytes) / minutes_per_clip, 1),
        "em_assertion_bytes_per_audio_minute": round(
            statistics.median(assertion_bytes) / minutes_per_clip, 1),
        "per_minute_caveat": ("the corpus clips have a median duration of "
                              f"{minutes_per_clip*60:.2f} s, and the C2PA manifest overhead is "
                              "dominated by a fixed per-asset cost (certificate chain, COSE "
                              "structure, hard binding) rather than by audio duration, so the "
                              "per-audio-minute figures are extrapolations of a mostly fixed "
                              "cost and should be read together with the per-asset figures and "
                              "the interval-scaling table"),
        "assertion_scaling": scaling,
        "machine_dependence_note": ("single-machine medians for a Python reference "
                                    "implementation; a compiled implementation will differ, so "
                                    "these are not language-independent constants"),
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("G_overhead", payload)
    print(f"EM {payload['em_ms_per_audio_minute']} ms/audio-minute, "
          f"ratio to baseline {payload['em_over_baseline_ratio']}x, "
          f"{payload['em_over_ffmpeg_fraction']*100:.2f}% of ffmpeg time")
    return 0


if __name__ == "__main__":
    sys.exit(main())
