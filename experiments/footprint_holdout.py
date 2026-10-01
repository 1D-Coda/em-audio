"""Experiment K2 -- a holdout challenge to the declared kernel footprints.

Experiment K measures dependency reach at ten positions in four signal
contexts, all chosen while the declarations were being set, so passing it
shows the declarations contain what was measured there and nothing more. A
finite probe family can refute a declared bound; it cannot establish one for
an adaptive operator, which may re-decide when its input changes.

This experiment challenges the declarations with inputs that played no part in
setting them, fixed here before it was run:

  * two further signal contexts, white noise and a speech-like voice;
  * perturbation amplitudes from the K floor up to a large legal impulse;
  * probe positions disjoint from K's.

It reports every exceedance. A declaration exceeded here is not contained for
that operator at all operating points, and the paper says so: the declared
footprint then characterises the tested operating points only, and a strict
deployment uses whole-asset dependency for that operator.

Normalisation is run in two modes. With the gain fixed it is a sample-wise
scaling and its content footprint is zero. With the gain estimated from each
input, as peak normalisation does, every output sample depends on the whole
input through the gain: a control dependency, not a content one. The contract
labels origin by represented content, so this dependency is measured and
reported, not counted against the content footprint.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from _common import emit, env, ROOT                 # noqa: E402
import support_containment as K                            # noqa: E402
import em_audio.operators as O                             # noqa: E402
import em_audio.ffmpeg_ops as F                            # noqa: E402
from em_audio import fsutil as _fsutil                      # noqa: E402

N, FS = K.N, K.FS
WORK = ROOT / "corpus" / "support" / "holdout"

CONTEXTS = ("tone", "near_threshold", "transient", "dense", "noise", "speech_like")
HOLDOUT_CONTEXTS = ("noise", "speech_like")
AMPLITUDES = (256, 1000, 3000, 12000)
# Disjoint from Experiment K's positions, spread over the interior and both
# retained runs of the selection operator, fixed before the run.
POSITIONS = (900, 2900, 4500, 7100, 9300, 11800, 13500, 15600)


def _cases():
    return [
        ("resample_16_8", "content", O.resample("s", N, 16000, 8000),
         lambda a, b: F.resample(a, b, 8000)),
        ("transcode_mp3", "content", O.transcode("s", N, "mp3"),
         lambda a, b: F.transcode(a, b, "mp3")),
        ("time_stretch_1.10", "content", O.time_stretch("s", N, 1.10, FS),
         lambda a, b: F.time_stretch(a, b, 1.10)),
        ("silence_removal", "content",
         O.silence_removal("s", [(0, int(0.4 * N)), (int(0.6 * N), N)]),
         lambda a, b: F.cut_runs(a, b, [(0.0, 0.4 * N / FS), (0.6 * N / FS, N / FS)], FS)),
        ("normalize_fixed_gain", "content", O.normalize("s", N),
         lambda a, b: F.normalize(a, b, 0.0)),
        ("normalize_estimated_gain", "control", O.normalize("s", N),
         lambda a, b: F.normalize(a, b, F.peak_gain_db(a))),
    ]


def main() -> int:
    if WORK.exists():
        _fsutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    saved = (K.IMPULSE_FLOOR, K.IMPULSE_RATIO)
    results: Dict[str, object] = {}
    exceeded: List[str] = []
    try:
        for name, kind, model, run in _cases():
            wd = WORK / name
            wd.mkdir(parents=True)
            rows = []
            for amp in AMPLITUDES:
                # An absolute amplitude: the floor is the amplitude, the ratio off.
                K.IMPULSE_FLOOR, K.IMPULSE_RATIO = amp, 0.0
                for ctx in CONTEXTS:
                    for k in POSITIONS:
                        r = K.probe(name, run, model, k, wd, ctx)
                        rows.append({"amplitude": amp, "context": ctx, "k": k,
                                     "reach": r["max_measured_reach_source_samples"],
                                     "outside": r["outside_declared_support"],
                                     "outside_or_unmapped_strict": r["outside_or_unmapped_strict"],
                                     "affected": r["affected_output_samples"]})
            decl = model.pieces[0].footprint
            bad = [r for r in rows if r["outside_or_unmapped_strict"]]
            results[name] = {
                "dependency_kind": kind,
                "declared_footprint_samples": decl,
                "probes": len(rows),
                "max_measured_reach_source_samples": max(r["reach"] for r in rows),
                "probes_exceeding_declaration": len(bad),
                "total_outside_or_unmapped_strict": sum(r["outside_or_unmapped_strict"] for r in rows),
                "exceeding_contexts": sorted({r["context"] for r in bad}),
                "exceeding_amplitudes": sorted({r["amplitude"] for r in bad}),
                "exceeds_only_on_holdout_contexts": bool(bad) and all(
                    r["context"] in HOLDOUT_CONTEXTS for r in bad),
                "per_probe": rows,
            }
            verdict = (f"EXCEEDED in {len(bad)} of {len(rows)} probes" if bad
                       else "no exceedance observed")
            print(f"  {name:26s} {kind:8s} decl {decl:5d}  max reach "
                  f"{results[name]['max_measured_reach_source_samples']:6d}  {verdict}")
            if bad and kind == "content":
                exceeded.append(name)
    finally:
        K.IMPULSE_FLOOR, K.IMPULSE_RATIO = saved

    payload = {
        "purpose": ("challenge the declared footprints with contexts, amplitudes and "
                    "positions that played no part in setting them"),
        "signal_contexts": list(CONTEXTS),
        "holdout_contexts": list(HOLDOUT_CONTEXTS),
        "impulse_amplitudes": list(AMPLITUDES),
        "probe_positions": list(POSITIONS),
        "source_length_samples": N, "sample_rate": FS,
        "content_operators_exceeding": exceeded,
        "per_operator": results,
        "scope_note": ("a finite challenge can refute a declaration and cannot establish "
                       "one; no exceedance observed here is not containment at every input"),
        "environment": env(),
    }
    emit("K2_footprint_holdout", payload)
    print(f"\ncontent operators exceeding a declaration: {exceeded or 'none'}")
    # Exceedances are the measurement, not a pipeline failure: they are what
    # this experiment exists to find, and the paper reports them.
    return 0


if __name__ == "__main__":
    sys.exit(main())
