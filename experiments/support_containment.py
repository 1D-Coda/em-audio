"""Experiment K -- direct test of kernel-support containment.

Proposition 4 requires that the *declared* required-source set contain the
*actual* dependency set. Agreement between predicted and actual output length,
which the transformation matrix measures, does not establish that: an operator
can emit exactly the predicted number of samples while depending on source
samples outside the declared footprint. This experiment tests the containment
condition itself.

Method, per operator configuration and per probe position k:

  1. build two sources that are identical except at sample k, where one carries
     a full-scale impulse and the other carries silence;
  2. run the SAME stock ffmpeg command on both;
  3. decode both to PCM and subtract.

Every output sample whose difference is non-zero was influenced by source
sample k, and by nothing else, because the inputs differ nowhere else. For each
such output sample the declared required-source range is computed from the
interval model, and containment holds when k lies inside it. A single
non-contained sample is an under-approximation and a conformance failure.

The comparison is on decoded 16-bit PCM and the threshold is one least
significant bit, so the test is maximally sensitive: any influence a listener
could not possibly hear still counts as a dependency.
"""
from __future__ import annotations

import json, shutil, statistics, struct, subprocess, sys, time, wave
from pathlib import Path
from typing import Dict, List, Tuple

from _common import ROOT, emit                                        # noqa: E402
from em_audio import ffmpeg_ops as F
import em_audio.operators as O

WORK = ROOT / "corpus" / "support"
FS = 16_000
N = 4096                     # source length in samples
IMPULSE = 12000              # large enough to dominate, small enough not to clip
BASE_AMP = 6000              # non-silent base: see base_signal()


def base_signal() -> List[int]:
    """A deterministic non-silent carrier.

    Probing against silence under-tests signal-dependent operators: a lossy
    encoder given near-silence, or an overlap-add stretcher given one impulse in
    an empty buffer, may pass the impulse through untouched and appear to have a
    one-sample dependency it does not have in normal operation. The base is a
    fixed low-frequency tone plus a deterministic alternating component, so every
    analysis window has real content to interact with, and it is generated
    without any random source so the probe stays reproducible.
    """
    import math
    return [int(BASE_AMP * (0.7 * math.sin(2 * math.pi * 220.0 * i / FS)
                            + 0.3 * (1 if i % 7 < 3 else -1)))
            for i in range(N)]


def write_wav(path: Path, samples: List[int]) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(FS)
        w.writeframes(b"".join(struct.pack("<h", int(s)) for s in samples))


def decode(path: Path) -> List[int]:
    """Decode at the file's OWN sample rate.

    Forcing a rate here would resample the output of a rate-changing operator
    back to the source rate, so output indices would no longer correspond to the
    model's output coordinates and every comparison downstream would be wrong.
    """
    raw = subprocess.run([F.FFMPEG, "-v", "error", "-i", str(path),
                          "-f", "s16le", "-acodec", "pcm_s16le", "-ac", "1", "-"],
                         capture_output=True, check=True).stdout
    return list(struct.unpack(f"<{len(raw)//2}h", raw[:len(raw)//2*2]))


def probe(name: str, run, model, k: int, wd: Path) -> Dict[str, object]:
    """Return the containment verdict for a single impulse at source sample k."""
    carrier = base_signal()
    base, spike = wd / f"base_{k}.wav", wd / f"spike_{k}.wav"
    write_wav(base, carrier)
    s = list(carrier); s[k] = max(-32768, min(32767, s[k] + IMPULSE))
    write_wav(spike, s)
    ext = "mp3" if "mp3" in name else ("flac" if "flac" in name else "wav")
    ob, os_ = wd / f"ob_{k}.{ext}", wd / f"os_{k}.{ext}"
    run(base, ob); run(spike, os_)
    a, b = decode(ob), decode(os_)
    n = min(len(a), len(b))
    affected = [i for i in range(n) if a[i] != b[i]]

    outside, worst = 0, 0
    margin = None            # smallest distance from k to the edge of a declared range
    for o in affected:
        lo = hi = None
        for p in model.pieces:
            if p.out_start <= o < p.out_end:
                lo, hi = p.source_range(o, o + 1, with_footprint=True)
                break
        if lo is None:                       # output sample no piece claims
            outside += 1; worst = max(worst, N); continue
        if not (lo <= k < hi):
            outside += 1
            worst = max(worst, lo - k if k < lo else k - hi + 1)
        else:
            m = min(k - lo, hi - 1 - k)
            margin = m if margin is None else min(margin, m)
    return {"k": k, "affected_output_samples": len(affected),
            "outside_declared_support": outside,
            "max_samples_outside": worst,
            "min_margin_inside_declared_range": margin,
            "decoded_length": n}


def main() -> int:
    t0 = time.time()
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    gain = 0.0                                # fixed gain keeps the probe well defined
    cases = [
        ("trim_10_90", O.trim("s", N, N // 10, N - N // 10),
         lambda a, b: F.trim(a, b, (N // 10) / FS, (N - 2 * (N // 10)) / FS)),
        ("resample_16_8", O.resample("s", N, 16000, 8000),
         lambda a, b: F.resample(a, b, 8000)),
        ("transcode_flac", O.transcode("s", N, "flac"),
         lambda a, b: F.transcode(a, b, "flac")),
        ("transcode_mp3", O.transcode("s", N, "mp3"),
         lambda a, b: F.transcode(a, b, "mp3")),
        ("normalize", O.normalize("s", N),
         lambda a, b: F.normalize(a, b, gain)),
        ("time_stretch_1.10", O.time_stretch("s", N, 1.10, FS),
         lambda a, b: F.time_stretch(a, b, 1.10)),
        ("silence_removal", O.silence_removal("s", [(0, int(0.4 * N)), (int(0.6 * N), N)]),
         lambda a, b: F.cut_runs(a, b, [(0.0, 0.4 * N / FS), (0.6 * N / FS, N / FS)], FS)),
    ]
    # probe positions: interior, both edges, and either side of the operators'
    # own cut points, where an under-approximation would first show up
    positions = sorted({64, N // 10, N // 10 + 32, int(0.4 * N) - 16, int(0.4 * N) + 16,
                        N // 2, int(0.6 * N) - 16, int(0.6 * N) + 16,
                        N - N // 10 - 32, N - 128})

    results: Dict[str, object] = {}
    total_probes = total_affected = total_outside = 0
    failures: List[str] = []
    for name, model, run in cases:
        wd = WORK / name; wd.mkdir(parents=True)
        rows = [probe(name, run, model, k, wd) for k in positions]
        outside = sum(r["outside_declared_support"] for r in rows)
        affected = sum(r["affected_output_samples"] for r in rows)
        results[name] = {
            "probes": len(rows),
            "total_affected_output_samples": affected,
            "total_outside_declared_support": outside,
            "max_samples_outside": max(r["max_samples_outside"] for r in rows),
            # For containment the worst case is what matters, and the spread is
            # strongly position-dependent for overlap-add operators, so report
            # the maximum alongside a correctly computed median.
            "median_spread_output_samples": statistics.median(
                r["affected_output_samples"] for r in rows),
            "max_spread_output_samples": max(
                r["affected_output_samples"] for r in rows),
            "probes_with_spread_above_one": sum(
                1 for r in rows if r["affected_output_samples"] > 1),
            "declared_footprint_samples": model.pieces[0].footprint,
            "min_margin_inside_declared_range": min(
                [r["min_margin_inside_declared_range"] for r in rows
                 if r["min_margin_inside_declared_range"] is not None] or [None]),
            "per_probe": rows,
        }
        total_probes += len(rows); total_affected += affected; total_outside += outside
        if outside:
            failures.append(f"{name}: {outside} affected output samples outside declared support")
        print(f"  {name:20s} probes {len(rows):2d}  affected {affected:7d}  "
              f"outside {outside}  max_outside {results[name]['max_samples_outside']}")

    payload = {
        "source_length_samples": N, "sample_rate": FS, "impulse_amplitude": IMPULSE,
        "probe_positions": positions,
        "threshold": "one 16-bit LSB on decoded PCM; any non-zero difference counts",
        "method": ("two sources identical except for a single-sample impulse are pushed "
                   "through the same stock ffmpeg command; every output sample whose "
                   "decoded value differs was influenced by that one source sample and by "
                   "nothing else"),
        "total_probes": total_probes,
        "total_affected_output_samples": total_affected,
        "total_outside_declared_support": total_outside,
        "per_operator": results,
        "failures": failures,
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("K_support_containment", payload)
    print(f"\ntotal probes {total_probes}, affected output samples {total_affected}, "
          f"outside declared support {total_outside}")
    return 1 if total_outside else 0


if __name__ == "__main__":
    sys.exit(main())
