"""Experiment K -- direct test of kernel-support containment.

Proposition 2 requires that the *declared* required-source set contain the
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
from em_audio import fsutil as _fsutil
import em_audio.operators as O
from em_audio.interval_map import conform_to_decoded, strict_profile

WORK = ROOT / "corpus" / "support"
FS = 16_000
# 16384 rather than 4096: the largest declared footprint is 2577 samples, and at
# 4096 that spans the whole source, so every containment check would pass
# trivially for the large-footprint operators. At 16384 the footprint covers
# about a sixth of the source and the test can actually fail.
N = 16384                    # source length in samples
# The perturbation is scaled to each context's carrier rather than fixed. A
# fixed amplitude was 200x the near-threshold carrier, which does not perturb an
# adaptive operator's input so much as replace it: a lossy encoder re-allocates
# bits globally and a WSOLA correlation search locks onto the injected sample
# instead of the signal, so the measured "dependency" is really the operator
# choosing a different mode. A proportionate probe measures dependency at a
# fixed operating point, which is what the footprint is meant to bound.
IMPULSE_RATIO = 2.0          # impulse amplitude as a multiple of carrier peak
IMPULSE_FLOOR = 256          # keep the perturbation clear of the 16-bit floor
BASE_AMP = 6000              # non-silent base: see base_signal()


CONTEXTS = ("tone", "near_threshold", "transient", "dense")


def base_signal(kind: str = "tone") -> List[int]:
    """A deterministic non-silent carrier, in one of four signal contexts.

    Probing against silence under-tests signal-dependent operators: a lossy
    encoder given near-silence, or an overlap-add stretcher given one impulse in
    an empty buffer, may pass the impulse through untouched and appear to have a
    one-sample dependency it does not have in normal operation. Four contexts are
    used because encoder and stretcher behaviour is content-dependent, and a
    single carrier would leave the bound validated against one operating regime:

      tone            a steady low-frequency tone, the ordinary case;
      near_threshold  the same at roughly one part in a hundred amplitude, where
                      a lossy encoder allocates fewest bits and quantisation is
                      coarsest;
      transient       repeated sharp onsets followed by decay, which is what
                      drives an overlap-add stretcher hardest;
      dense           a sum of many inharmonic partials, spectrally crowded so
                      the encoder's masking decisions are most active.

    All four are generated arithmetically with no random source, so the probe is
    reproducible.
    """
    import math
    out = []
    state = 0
    for i in range(N):
        t = i / FS
        if kind == "tone":
            v = BASE_AMP * (0.7 * math.sin(2 * math.pi * 220.0 * t)
                            + 0.3 * (1 if i % 7 < 3 else -1))
        elif kind == "near_threshold":
            v = (BASE_AMP / 100.0) * (0.7 * math.sin(2 * math.pi * 220.0 * t)
                                      + 0.3 * (1 if i % 7 < 3 else -1))
        elif kind == "transient":
            phase = i % 512
            env = math.exp(-phase / 40.0)
            v = BASE_AMP * env * math.sin(2 * math.pi * 1500.0 * t)
        elif kind == "dense":
            v = 0.0
            for h, f in enumerate((311.0, 523.7, 787.1, 1103.3, 1471.9, 1873.7), 1):
                v += (BASE_AMP / 6.0) * math.sin(2 * math.pi * f * t + h)
        elif kind == "noise":
            # Holdout only (Experiment K2): deterministic white noise from a
            # linear congruential generator, so no random module and no seed state.
            state = (1103515245 * (state if i else 12345) + 12345) % 2**31
            v = (BASE_AMP / 3.0) * (2.0 * state / 2**31 - 1.0)
        elif kind == "speech_like":
            # Holdout only (Experiment K2): a 140 Hz harmonic voice with a 4 Hz
            # syllable envelope and a pause in every third syllable.
            syl = int(t * 4.0)
            env = 0.0 if syl % 3 == 2 else math.sin(math.pi * ((t * 4.0) % 1.0)) ** 2
            v = sum((BASE_AMP / (2.0 * h)) * math.sin(2 * math.pi * 140.0 * h * t)
                    for h in range(1, 9)) * env
        else:
            raise ValueError(kind)
        out.append(max(-32768, min(32767, int(v))))
    return out


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


def probe(name: str, run, model, k: int, wd: Path, ctx: str = "tone") -> Dict[str, object]:
    """Return the containment verdict for a single impulse at source sample k."""
    carrier = base_signal(ctx)
    peak = max(1, max(abs(x) for x in carrier))
    amp = int(max(IMPULSE_FLOOR, min(24000, IMPULSE_RATIO * peak)))
    base, spike = wd / f"base_{ctx}_{k}.wav", wd / f"spike_{ctx}_{k}.wav"
    write_wav(base, carrier)
    s = list(carrier); s[k] = max(-32768, min(32767, s[k] + amp))
    write_wav(spike, s)
    ext = "mp3" if "mp3" in name else ("flac" if "flac" in name else "wav")
    ob, os_ = wd / f"ob_{ctx}_{k}.{ext}", wd / f"os_{ctx}_{k}.{ext}"
    run(base, ob); run(spike, os_)
    a, b = decode(ob), decode(os_)
    n = min(len(a), len(b))
    affected = [i for i in range(n) if a[i] != b[i]]

    outside, worst, beyond_extent, reach, unmapped_outside = 0, 0, 0, 0, 0
    margin = None            # smallest distance from k to the edge of a declared range
    for o in affected:
        lo = hi = None
        for p in model.pieces:
            if p.out_start <= o < p.out_end:
                lo, hi = p.source_range(o, o + 1, with_footprint=True)
                break
        if lo is None:
            # The operator emitted an output sample the model does not claim,
            # i.e. it produced more output than predicted. That is a MAPPING
            # deviation, bounded by the guard band and measured by the
            # transformation matrix; it is not a support-containment violation,
            # and counting it as one would repeat the exact conflation this
            # experiment exists to avoid. Containment for such a sample is
            # checked against the covering piece's whole declared source range.
            beyond_extent += 1
            p = model.pieces[-1]
            lo, hi = p.source_range(p.out_start, p.out_end, with_footprint=True)
            if not (lo <= k < hi):
                unmapped_outside += 1
        if not (lo <= k < hi):
            outside += 1
            worst = max(worst, lo - k if k < lo else k - hi + 1)
        else:
            m = min(k - lo, hi - 1 - k)
            margin = m if margin is None else min(margin, m)
        # How far outside the NOMINAL (footprint-free) source range this
        # influence reached. This is the quantity a declared footprint has to
        # cover, so reporting it makes the declaration checkable against a
        # measurement rather than against an assertion, and it regenerates on
        # every run instead of being quoted from a past one.
        for p2 in model.pieces:
            if p2.out_start <= o < p2.out_end:
                nlo, nhi = p2.source_range(o, o + 1, with_footprint=False)
                if k < nlo:
                    reach = max(reach, nlo - k)
                elif k >= nhi:
                    reach = max(reach, k - nhi + 1)
                break
    return {"k": k, "context": ctx, "impulse_amplitude": amp,
            "carrier_peak": peak,
            "affected_output_samples": len(affected),
            "output_samples_beyond_modelled_extent": beyond_extent,
            "outside_declared_support": outside,
            "max_samples_outside": worst,
            "min_margin_inside_declared_range": margin,
            "max_measured_reach_source_samples": reach,
            "decoded_length": n,
            # Strict outcome, reported beside the original: an affected sample
            # the model does not map is not contained by a declaration the
            # emitted map never makes, and a length change is itself an effect
            # of the perturbation that min(len) discarded.
            "length_change_samples": abs(len(a) - len(b)),
            "outside_or_unmapped_strict": (outside - unmapped_outside) + beyond_extent
                                          + abs(len(a) - len(b)),
            # Interior alignment: where the model puts source sample k in the
            # output against where the difference actually peaks. A correct
            # length says nothing about alignment; this measures it.
            "alignment_offset_samples": _alignment_offset(model, k, a, b, n),
            # The map an implementation would emit: conformed to the length the
            # perturbed run actually decoded to, with whole-asset dependency on
            # any tail the model does not cover. Every influenced sample of that
            # output is checked, including a tail the unperturbed run lacks.
            **_conformed_outcome(model, k, a, b)}


def _conformed_outcome(model, k: int, a, b) -> Dict[str, int]:
    n_emit = len(b)
    common = min(len(a), len(b))
    affected = [i for i in range(common) if a[i] != b[i]] + list(range(common, n_emit))
    conf = conform_to_decoded(model, n_emit, {"s": N})
    strict = strict_profile(conf, {"s": N})
    return {"emitted_length": n_emit,
            "fallback_samples": conf.params["fallback_samples"],
            "outside_conformed_map": _outside_under(conf, affected, k),
            "outside_strict_profile": _outside_under(strict, affected, k),
            "first_outside_conformed_sample": _first_outside(conf, affected, k)}


def _first_outside(model, affected, k: int):
    for o in affected:
        if _outside_under(model, [o], k):
            return o
    return None


def _outside_under(model, affected, k: int) -> int:
    """Affected output samples whose declared source ranges all miss sample k.

    Every covering piece contributes, so an output sample several pieces cover
    is contained when any of them reaches k; a sample no piece covers counts as
    outside, since no declaration was made for it.
    """
    bad = 0
    for o in affected:
        ok = False
        for p in model.pieces:
            if p.out_start <= o < p.out_end:
                lo, hi = p.source_range(o, o + 1, with_footprint=True)
                if lo <= k < hi:
                    ok = True
                    break
        bad += not ok
    return bad


def _alignment_offset(model, k: int, a, b, n: int):
    """Peak of |a-b| minus the model's predicted output index of source sample k."""
    if n == 0:
        return None
    peak = max(range(n), key=lambda i: abs(a[i] - b[i]))
    if a[peak] == b[peak]:
        return None
    for p in model.pieces:
        if p.src_start <= k < p.src_end:
            scale = (p.out_end - p.out_start) / (p.src_end - p.src_start)
            return peak - round(p.out_start + (k - p.src_start) * scale)
    return None


def main() -> int:
    t0 = time.time()
    if WORK.exists():
        _fsutil.rmtree(WORK)
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
        rows = [probe(name, run, model, k, wd, ctx)
                for ctx in CONTEXTS for k in positions]
        outside = sum(r["outside_declared_support"] for r in rows)
        affected = sum(r["affected_output_samples"] for r in rows)
        by_ctx = {c: [r for r in rows if r["context"] == c] for c in CONTEXTS}
        results[name] = {
            "probes": len(rows),
            "contexts": list(CONTEXTS),
            "per_context_outside": {c: sum(r["outside_declared_support"] for r in v)
                                    for c, v in by_ctx.items()},
            "per_context_max_spread": {c: max(r["affected_output_samples"] for r in v)
                                       for c, v in by_ctx.items()},
            "output_samples_beyond_modelled_extent": sum(
                r["output_samples_beyond_modelled_extent"] for r in rows),
            "max_measured_reach_source_samples": max(
                r["max_measured_reach_source_samples"] for r in rows),
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
            "probes_with_length_change": sum(1 for r in rows if r["length_change_samples"]),
            "total_outside_or_unmapped_strict": sum(r["outside_or_unmapped_strict"] for r in rows),
            "total_outside_conformed_map": sum(r["outside_conformed_map"] for r in rows),
            "total_outside_strict_profile": sum(r["outside_strict_profile"] for r in rows),
            "total_fallback_samples": sum(r["fallback_samples"] for r in rows),
            "max_abs_alignment_offset_samples": max(
                [abs(r["alignment_offset_samples"]) for r in rows
                 if r["alignment_offset_samples"] is not None] or [None]),
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
        "source_length_samples": N, "sample_rate": FS, "impulse_ratio_to_carrier_peak": IMPULSE_RATIO,
        "probe_positions": positions,
        "signal_contexts": list(CONTEXTS),
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
