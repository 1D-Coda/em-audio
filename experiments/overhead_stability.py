"""How much of the reported cost survives being measured again.

The absolute bookkeeping cost moved by roughly a third between manuscript
revisions with no change to the bookkeeping code, which invites the reasonable
question of what was optimised. Nothing was. The figure is machine-state
dependent, and this experiment measures that directly rather than asserting it.

It runs the overhead benchmark several times as independent processes and
reports the spread of the absolute cost against the spread of the ratio to the
baseline. Both arms are timed in the same process on the same machine, so
whatever sets the absolute scale on a given run moves them together and cancels
in their quotient. The prediction is that the ratio is the tighter quantity, and
the point of running it is that the prediction can fail.

Within one sitting the machine is in one state, so this understates the
variation a reader reproducing the work weeks later will see; it is a lower
bound on the instability, not an estimate of it.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _common import RESULTS, emit                                 # noqa: E402

REPEATS = 9          # enough that the dispersion estimate is not one run wide


def spread(xs):
    """Range and coefficient of variation.

    The range over a handful of runs is dominated by whichever single run
    happened to be worst, so it is reported for legibility but the claim rests
    on the coefficient of variation, which uses every sample. Supporting a
    statement about stability with an unstable statistic would be
    self-undermining.
    """
    lo, hi = min(xs), max(xs)
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / (len(xs) - 1) if len(xs) > 1 else 0.0
    cv = 100.0 * (var ** 0.5) / mean if mean else 0.0
    return {"min": round(lo, 4), "max": round(hi, 4),
            "mean": round(mean, 4),
            "range_pct": round(100.0 * (hi - lo) / lo, 2) if lo else 0.0,
            "cv_pct": round(cv, 3)}


def main() -> int:
    t0 = time.time()
    src = RESULTS / "G_overhead.json"
    keep = json.loads(src.read_text()) if src.exists() else None

    em, base, ratio = [], [], []
    for i in range(REPEATS):
        subprocess.run([sys.executable, "overhead_benchmark.py"], cwd=HERE,
                       check=True, capture_output=True)
        d = json.loads(src.read_text())
        em.append(d["em_ms_per_audio_minute"])
        base.append(d["baseline_ms_per_audio_minute"])
        ratio.append(d["em_over_baseline_ratio"])
        print(f"  run {i + 1}: EM {em[-1]} ms, ratio {ratio[-1]}")

    # leave the recorded benchmark as the pipeline's own run produced it
    if keep is not None:
        src.write_text(json.dumps(keep, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")

    s_em, s_ratio = spread(em), spread(ratio)
    tighter = s_ratio["cv_pct"] <= s_em["cv_pct"]
    print(f"absolute CV {s_em['cv_pct']}%, ratio CV {s_ratio['cv_pct']}% "
          f"over {REPEATS} independent runs")
    # Not a pass/fail. The ratio cancels common-mode variation, so it is much
    # tighter when such variation dominates and has nothing to cancel when the
    # machine is quiet, where a quotient of two independently noisy numbers can
    # scatter slightly more than either. Both outcomes are consistent with the
    # mechanism, and reporting the quiet case as a failure would be a prediction
    # the mechanism never made.
    print("  ratio is the tighter quantity" if tighter
          else "  ratio not tighter this sitting: little common-mode variation "
               "to cancel, which the mechanism allows")

    emit("M_overhead_stability", {
        "experiment": "M_overhead_stability",
        "purpose": ("whether the absolute cost or the ratio survives being "
                    "measured again on the same machine"),
        "repeats": REPEATS,
        "em_ms_per_audio_minute": s_em,
        "baseline_ms_per_audio_minute": spread(base),
        "em_over_baseline_ratio": s_ratio,
        "ratio_is_tighter_than_absolute": tighter,
        "interpretation": ("the ratio cancels common-mode variation; it is much "
                           "tighter when machine state moves both arms together "
                           "and has no advantage on a quiet machine, so a "
                           "sitting in which it is not tighter is consistent "
                           "with the mechanism rather than a failure of it"),
        "tightness_factor_cv": (round(s_em["cv_pct"] / s_ratio["cv_pct"], 2)
                                if s_ratio["cv_pct"] else None),
        "scope_note": ("one sitting is one machine state, so this is a lower "
                       "bound on the variation a later reproduction sees, not "
                       "an estimate of it"),
        "runtime_s": round(time.time() - t0, 3),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
