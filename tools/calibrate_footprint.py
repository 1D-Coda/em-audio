#!/usr/bin/env python3
"""Calibrate a declared footprint for an operator configuration.

The manuscript describes two passes and, until now, implemented neither as a
tool. This is that tool.

  * the MAPPING pass pushes a deterministic reference signal through the
    configuration and reports the largest output-length deviation from the
    interval model, which is what the implementation margin has to cover;
  * the SUPPORT pass sweeps a proportionate impulse across the input and
    reports the furthest any single source sample influenced the output beyond
    the nominal source range, which is what the declared footprint has to cover.

Substituting the first for the second is the conflation the paper had to correct
in its own draft: output length can be exact while the dependency is wider than
declared. Both are reported separately here for that reason.

The recommendation errs large on purpose. Proposition 4 guarantees that a
declaration containing the true dependency cannot promote, so a calibration that
over-shoots costs dilution and nothing else, while one that under-shoots is the
single direction the contract does not forgive.

Usage:
    python3 tools/calibrate_footprint.py                # every v1 operator
    python3 tools/calibrate_footprint.py transcode_mp3  # one of them
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

import em_audio.ffmpeg_ops as F                                  # noqa: E402
import em_audio.operators as O                                   # noqa: E402
from support_containment import (CONTEXTS, FS, N, base_signal,    # noqa: E402
                                 decode, probe, write_wav)

WORK = ROOT / "corpus" / "calibration"

# Margin policy applied to the measured reach. A flat constant is wrong here: it
# is either negligible for a large-footprint codec or absurd for a resampler
# whose whole dependency is a few dozen samples. The margin is therefore
# proportional, with a floor so that a near-zero reach still clears a frame
# boundary. Both numbers are policy, not measurement, and are reported as such.
MARGIN_FRACTION = 0.25
MARGIN_FLOOR_SAMPLES = 64


def mapping_pass(name, run, model, wd):
    """Largest |actual - predicted| output length over the signal contexts."""
    worst = 0
    ext = "mp3" if "mp3" in name else ("flac" if "flac" in name else "wav")
    for ctx in CONTEXTS:
        src, dst = wd / f"map_src_{ctx}.wav", wd / f"map_out_{ctx}.{ext}"
        write_wav(src, base_signal(ctx))
        run(src, dst)
        worst = max(worst, abs(len(decode(dst)) - model.n_out))
    return worst


def support_pass(name, run, model, wd, positions):
    """Furthest measured influence beyond the nominal source range."""
    reach = outside = 0
    for ctx in CONTEXTS:
        for k in positions:
            r = probe(name, run, model, k, wd, ctx)
            reach = max(reach, r["max_measured_reach_source_samples"])
            outside += r["outside_declared_support"]
    return reach, outside


def cases():
    gain = 0.0
    return [
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


def main() -> int:
    want = sys.argv[1] if len(sys.argv) > 1 else None
    selected = [c for c in cases() if want is None or c[0] == want]
    if not selected:
        print(f"no such operator: {want}")
        print("known:", ", ".join(c[0] for c in cases()))
        return 2

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    # The same positions the containment experiment uses. A calibration that
    # probed fewer places than the validation could report a smaller reach than
    # the validation later measures, and so recommend a declaration the
    # validation rejects. It must not under-measure relative to its own check.
    positions = sorted({64, N // 10, N // 10 + 32, int(0.4 * N) - 16,
                        int(0.4 * N) + 16, N // 2, int(0.6 * N) - 16,
                        int(0.6 * N) + 16, N - N // 10 - 32, N - 128})

    print(f"{'operator':20s} {'declared':>9s} {'reach':>7s} {'map dev':>8s} "
          f"{'recommend':>10s}  verdict")
    rows, under = [], []
    for name, model, run in selected:
        wd = WORK / name
        wd.mkdir(parents=True)
        dev = mapping_pass(name, run, model, wd)
        reach, outside = support_pass(name, run, model, wd, positions)
        declared = model.pieces[0].footprint
        recommend = (int(reach * (1 + MARGIN_FRACTION)) + MARGIN_FLOOR_SAMPLES
                     if reach else 0)
        # Containment is the requirement; the advisory margin is policy. An
        # existing declaration that contains its measured reach is sound even if
        # it sits below what this tool would have proposed from scratch, and
        # conflating the two would either overstate a problem or hide one.
        ok = declared >= reach and outside == 0
        if not ok:
            under.append(name)
            verdict = "UNDER-DECLARED"
        elif reach and declared < recommend:
            verdict = "ok, below advisory"
        else:
            verdict = "ok"
        print(f"{name:20s} {declared:9d} {reach:7d} {dev:8d} {recommend:10d}  "
              f"{verdict}")
        rows.append({"operator": name, "declared_footprint_samples": declared,
                     "measured_reach_source_samples": reach,
                     "max_output_length_deviation_samples": dev,
                     "recommended_footprint_samples": recommend,
                     "samples_outside_declared_support": outside,
                     "contains_measurement": ok,
                     "meets_advisory_margin": bool(ok and (not reach or declared >= recommend))})

    out = ROOT / "results" / "machine_readable" / "CALIBRATION.json"
    out.write_text(json.dumps({
        "tool": "calibrate_footprint",
        "note": ("mapping and support are measured separately on purpose: an "
                 "exact output length does not imply a contained dependency"),
        "margin_policy": {"fraction_of_reach": MARGIN_FRACTION,
                          "floor_samples": MARGIN_FLOOR_SAMPLES},
        "probe_positions": len(positions),
        "signal_contexts": list(CONTEXTS),
        "operators": rows,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\n[emit] {out.relative_to(ROOT)}")

    if under:
        print(f"under-declared: {', '.join(under)}")
        return 1
    print("every declared footprint contains its measured reach")
    return 0


if __name__ == "__main__":
    sys.exit(main())
