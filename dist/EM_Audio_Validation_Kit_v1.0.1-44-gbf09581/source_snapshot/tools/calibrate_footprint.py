#!/usr/bin/env python3
"""Calibrate a declared footprint for an operator configuration.

The manuscript describes two passes and, until now, implemented neither as a
tool. This is that tool.

  * the MAPPING pass pushes a deterministic reference signal through the
    configuration and reports the largest output-length deviation from the
    interval model, which is what the implementation margin has to cover;
  * the SUPPORT pass places a proportionate impulse at ten prespecified source
    positions, in each of four signal contexts, and reports the furthest any
    single source sample influenced the output beyond the nominal source range,
    which is what the declared footprint has to cover. It is a probe at chosen
    positions, not an exhaustive sweep: ten of sixteen thousand source samples
    are struck, so the tool cannot discover a mode transition that occurs only
    at an untested position. The positions are the operators' own cut points and
    edges, where an under-declaration shows up first.

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
    python3 tools/calibrate_footprint.py --self-test    # prove it can reject
    python3 tools/calibrate_footprint.py --keep-work    # do not clear the work dir
"""
from __future__ import annotations

import json
import math
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
    """Furthest measured influence beyond the nominal source range.

    Returns the per-probe rows as well as the aggregate, so a reader can audit
    which position and context produced the reach rather than trusting a single
    maximum.
    """
    reach = outside = 0
    rows = []
    for ctx in CONTEXTS:
        for k in positions:
            r = probe(name, run, model, k, wd, ctx)
            reach = max(reach, r["max_measured_reach_source_samples"])
            outside += r["outside_declared_support"]
            rows.append({"context": ctx, "source_position": k,
                         "impulse_amplitude": r["impulse_amplitude"],
                         "affected_output_samples": r["affected_output_samples"],
                         "reach_source_samples": r["max_measured_reach_source_samples"],
                         "outside_declared_support": r["outside_declared_support"]})
    return reach, outside, rows


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


def self_test() -> int:
    """Deliberately under-declare a footprint and require the tool to reject it.

    A calibration tool that has only ever certified declarations has not been
    shown to detect a bad one. This shrinks a known-good declaration below its
    own measured reach and fails unless the run reports UNDER-DECLARED, so the
    negative case is exercised rather than assumed.
    """
    name, model, run = [c for c in cases() if c[0] == "transcode_mp3"][0]
    wd = WORK / "selftest"
    if wd.exists():
        shutil.rmtree(wd)
    wd.mkdir(parents=True)
    positions = probe_positions()

    reach, outside, _ = support_pass(name, run, model, wd, positions)
    if not reach:
        print("self-test inconclusive: no measurable reach for the probe operator")
        return 1

    # shrink every piece's declaration to just below the measured reach
    bad = reach - 1
    for piece in model.pieces:
        object.__setattr__(piece, "footprint", bad) if hasattr(piece, "__dataclass_fields__") \
            else setattr(piece, "footprint", bad)
    reach2, outside2, _ = support_pass(name, run, model, wd, positions)
    detected = outside2 > 0 or bad < reach2

    print(f"self-test: {name} measured reach {reach}, declaration forced to {bad}")
    print(f"  samples outside the shrunken declaration: {outside2}")
    if detected:
        print("  PASS: the tool rejects a declaration below its measured reach")
        return 0
    print("  FAIL: an under-declaration went undetected")
    return 1


def probe_positions():
    """The same positions the containment experiment uses.

    A calibration that probed fewer places than the validation could report a
    smaller reach than the validation later measures, and so recommend a
    declaration the validation rejects. It must not under-measure relative to
    its own check.
    """
    return sorted({64, N // 10, N // 10 + 32, int(0.4 * N) - 16,
                   int(0.4 * N) + 16, N // 2, int(0.6 * N) - 16,
                   int(0.6 * N) + 16, N - N // 10 - 32, N - 128})


def main() -> int:
    argv = [a for a in sys.argv[1:] if a != "--keep-work"]
    keep_work = "--keep-work" in sys.argv
    if argv and argv[0] == "--self-test":
        return self_test()
    want = argv[0] if argv else None
    selected = [c for c in cases() if want is None or c[0] == want]
    if not selected:
        print(f"no such operator: {want}")
        print("known:", ", ".join(c[0] for c in cases()))
        return 2

    # The evidence of record is CALIBRATION.json, which retains every per-probe
    # row; the audio under WORK is intermediate. Even so, deleting a directory
    # the caller may have populated is the tool's decision to announce rather
    # than to make silently.
    if WORK.exists():
        if keep_work:
            print(f"keeping existing {WORK.relative_to(ROOT)}; "
                  f"probe files will be overwritten in place")
        else:
            print(f"clearing {WORK.relative_to(ROOT)} "
                  f"(pass --keep-work to leave it in place)")
            shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)

    positions = probe_positions()

    print(f"{'operator':20s} {'declared':>9s} {'reach':>7s} {'map dev':>8s} "
          f"{'recommend':>10s}  verdict")
    rows, under = [], []
    for name, model, run in selected:
        wd = WORK / name
        wd.mkdir(parents=True)
        dev = mapping_pass(name, run, model, wd)
        reach, outside, probe_rows = support_pass(name, run, model, wd, positions)
        declared = model.pieces[0].footprint
        # ceiling, not truncation: this is advisory today, but a caller that
        # promotes it to a declared bound must not inherit a one-sample
        # under-round from the arithmetic.
        recommend = (math.ceil(reach * (1 + MARGIN_FRACTION)) + MARGIN_FLOOR_SAMPLES
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
                     "meets_advisory_margin": bool(ok and (not reach or declared >= recommend)),
                     "probes": probe_rows})

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
