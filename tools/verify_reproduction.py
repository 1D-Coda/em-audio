#!/usr/bin/env python3
"""Compare a reproduction's results against the released ones, by class.

The manuscript states which outputs a correct reimplementation must match
exactly and which should be expected to differ. This applies that split
mechanically, so a reproducer does not have to decide case by case which
category a difference falls into, and so the criteria cannot be adjusted after
seeing the result.

    python3 tools/verify_reproduction.py               # against tag v1.0.0
    python3 tools/verify_reproduction.py --ref v1.1.0  # against another tag

Exit status is 0 when every deterministic output matches, 1 otherwise. A
difference in an environment-dependent output is reported for the record and
does not fail the run: wall-clock timings that matched exactly would be the
surprising outcome, not a reassuring one.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MR = ROOT / "results" / "machine_readable"

# Outputs a correct reimplementation must reproduce exactly. Each entry is a
# result file and the dotted paths within it that carry a scientific claim.
DETERMINISTIC = {
    "A_synthetic_state_space": ["words_enumerated", "operator_cases",
                                "checks_total", "checks_failed",
                                "composition_cases", "per_check"],
    "B_adversarial_timelines": ["n_timelines", "per_depth"],
    "B2_policy_ablation": ["arms"],
    "D_transform_matrix": ["n_clips", "per_transformation"],
    "H_oracle_differential": ["cases", "disagreements"],
    "K_support_containment": ["total_probes", "total_affected_output_samples",
                              "per_operator"],
    "L_scope_battery": ["enlargement_cases", "monotone", "violations",
                        "violations_under_superseded_rule"],
    "I_claim_dilution": ["per_transformation", "composition_chain",
                         "long_asset_chain"],
    "F_c2pa_roundtrip": ["n_clips", "containers", "per_container"],
    "E_manifest_stripping": ["n_clips", "conditions", "state_tally",
                             "violations"],
}

# Outputs that should differ, and whose difference is not a defect. Listed
# explicitly so that a reproducer can see the distinction was decided in
# advance rather than invoked to explain away a mismatch.
ENVIRONMENT_DEPENDENT = (
    "ms", "cv_pct", "runtime_s", "range_pct", "mean", "min", "max",
    "measured_utc", "load_average", "environment", "median_runtime",
    "sign_ms", "validate_ms", "runs", "assertion_scaling",
    "first_iteration_effect_pct",
)


def _is_env(path: str) -> bool:
    low = path.lower()
    return any(tok in low for tok in ENVIRONMENT_DEPENDENT)


def _flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def _reference(tag: str, name: str):
    try:
        out = subprocess.run(["git", "show", f"{tag}:results/machine_readable/{name}.json"],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        return json.loads(out.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="v1.0.0",
                    help="release tag to compare against (default v1.0.0)")
    args = ap.parse_args()

    print(f"Comparing the working tree against {args.ref}.")
    print("Deterministic outputs must match exactly. Environment-dependent "
          "outputs are reported\nand are expected to differ.\n")

    mismatches, env_diffs, missing = [], [], []
    for name, keys in sorted(DETERMINISTIC.items()):
        cur_path = MR / f"{name}.json"
        if not cur_path.exists():
            missing.append(f"{name}.json not produced by this run")
            continue
        ref = _reference(args.ref, name)
        if ref is None:
            missing.append(f"{name}.json absent from {args.ref}")
            continue
        cur = json.loads(cur_path.read_text())
        for key in keys:
            if key not in cur or key not in ref:
                missing.append(f"{name}.{key} missing on one side")
                continue
            for path, rv in _flatten(ref[key], key):
                cv = dict(_flatten(cur[key], key)).get(path, "<absent>")
                if cv == rv:
                    continue
                (env_diffs if _is_env(path) else mismatches).append(
                    f"{name}.{path}: {args.ref}={rv!r} here={cv!r}")

    for label, rows in (("MISSING", missing),
                        ("DETERMINISTIC MISMATCH", mismatches)):
        if rows:
            print(f"{label} ({len(rows)}):")
            for r in rows[:25]:
                print(f"  {r}")
            if len(rows) > 25:
                print(f"  ... and {len(rows) - 25} more")
            print()

    if env_diffs:
        print(f"Environment-dependent differences ({len(env_diffs)}), expected "
              f"and not a defect:")
        for r in env_diffs[:8]:
            print(f"  {r}")
        if len(env_diffs) > 8:
            print(f"  ... and {len(env_diffs) - 8} more")
        print()

    if mismatches or missing:
        print("REPRODUCTION INCOMPLETE: a deterministic output differs.")
        print("Classify each difference before reporting it: an environment or "
              "tool-version\ndifference, an ambiguity in the contract's "
              "specification, or a genuine discrepancy.\nDo not record it as "
              "environment variation without establishing that it is.")
        return 1

    print("Every deterministic output matches the release.")
    if env_diffs:
        print(f"{len(env_diffs)} environment-dependent difference(s), which is "
              f"the expected outcome.")
    else:
        # The comparison reads the fields carrying scientific claims; wall-clock
        # timings are not among them, so silence here means they were not
        # examined rather than that they were identical. Claiming zero
        # differences would assert something this tool never checked.
        print("Environment-dependent outputs such as timings were not compared: "
              "they are\nreported in PREFLIGHT.txt for the record, not as "
              "reproduction targets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
