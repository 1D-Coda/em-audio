#!/usr/bin/env python3
"""Compare a reproduction's results against the released ones, by class.

The manuscript states which outputs a correct reimplementation must match
exactly and which should be expected to differ. This applies that split
mechanically, so a reproducer does not have to decide case by case which
category a difference falls into, and so the criteria cannot be adjusted after
seeing the result.

    python3 tools/verify_reproduction.py               # against the current release
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

# The tag whose results ship in results/reference/. It labels the left-hand side
# of every comparison this tool prints, so a stale value mislabels a
# reproducer's report: the first independent run was told it differed from
# v1.0.0 when the snapshot it was given was v1.0.1.
RELEASE = "v1.0.1"

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
    # These three carry headline claims and were absent from this list, so the
    # tool reported a comparison as complete while never opening them. They
    # agree on the reproduction that exposed the gap, which is luck rather than
    # coverage: the corpus recovery rate, the C2PA composition wiring and the
    # robustness arm are all results the paper states.
    "C_public_audio_splice": ["n_clips", "exact_interval_recovery",
                              "generated_interval_recovered",
                              "baseline_provenance_promotions",
                              "em_provenance_promotions",
                              "baseline_lineage_omissions",
                              "em_lineage_omissions",
                              "worst_boundary_error_samples", "per_operator"],
    "J_c2pa_composition": ["n_fixtures", "composition_trusted", "derived_trusted",
                           "sources_trusted", "aggregate_mixed", "derived_mixed",
                           "derived_parentOf", "component_ingredients_recorded",
                           "placed_actions_reference_both",
                           "assertion_roundtrip_identical", "essence_mismatches"],
    "C2_robustness": ["arms"],
}

# Outputs that should differ, and whose difference is not a defect. Matched on
# the final path segment as a whole, never as a substring. An earlier version
# listed bare tokens including "max", "min" and "ms", which matched
# max_measured_reach_source_samples and model_vs_ffmpeg_max_abs_sample_dev: the
# two measurements the containment claims rest on. It reported both as expected
# and not a defect, in the one tool whose job is to decide what counts as a real
# failure.
ENV_FIELDS = frozenset({
    "runtime_s", "median_runtime_ms", "median_ms",
    "median_sign_ms", "median_validate_ms",
    "em_ms_per_audio_minute", "baseline_ms_per_audio_minute",
    "em_over_baseline_ratio", "em_over_ffmpeg_fraction",
    "em_bookkeeping_ms_per_repetition", "baseline_bookkeeping_ms_per_repetition",
    "ffmpeg_transcode_ms_per_repetition", "cv_pct", "range_pct",
    "measured_utc", "load_average_1_5_15", "first_iteration_effect_pct",
    "tightness_factor_cv", "median_manifest_overhead_bytes",
    "manifest_overhead_bytes", "median_em_assertion_bytes",
})

# Path prefixes whose whole subtree is environment-dependent.
ENV_SUBTREES = ("environment", "runs", "assertion_scaling")


def _is_env(path: str) -> bool:
    parts = path.split(".")
    if any(p.split("[")[0] in ENV_SUBTREES for p in parts):
        return True
    leaf = parts[-1].split("[")[0]
    if leaf in ENV_FIELDS:
        return True
    # the min/max/mean of a timing distribution, but only under a timing key
    if leaf in {"min", "max", "mean"}:
        return any(k in path for k in ("_ms_", "ratio", "cv"))
    return False


def _flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


REFERENCE_DIR = ROOT / "results" / "reference"


def _reference(tag: str, name: str):
    """The released values, from git where available and from a snapshot where not.

    A reproducer working from a source archive has no .git, so reading the
    reference with `git show` fails for every file and the tool reports the
    entire release as missing. That is the situation this script exists to serve,
    so the snapshot in results/reference/ is the path that matters and git is the
    convenience.
    """
    snap = REFERENCE_DIR / f"{name}.json"
    if snap.exists():
        try:
            return json.loads(snap.read_text())
        except json.JSONDecodeError:
            pass
    try:
        out = subprocess.run(["git", "show", f"{tag}:results/machine_readable/{name}.json"],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        return json.loads(out.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return None


def _reference_source(tag: str) -> str:
    if REFERENCE_DIR.is_dir() and any(REFERENCE_DIR.glob("*.json")):
        return f"results/reference/ (snapshot shipped with the release)"
    return f"git tag {tag}"


def _unclassified_timings():
    """Timing fields that are not marked environment-dependent.

    The list of such fields was maintained by hand and drifted: median_sign_ms
    and median_validate_ms were absent, so two wall-clock measurements were held
    to exact equality and a reproduction was told its clock differed from the
    reference's. Enumerating the actual result files makes the gap visible
    instead of waiting for a reproducer to hit it.
    """
    suspicious = []
    for name, keys in DETERMINISTIC.items():
        f = MR / f"{name}.json"
        if not f.exists():
            continue
        try:
            doc = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for key in keys:
            if key not in doc:
                continue
            for path, _ in _flatten(doc[key], key):
                leaf = path.split(".")[-1].split("[")[0]
                if leaf.endswith("_ms") and not _is_env(path):
                    suspicious.append(f"{name}.{leaf}")
    return sorted(set(suspicious))


def _inherited_results(tag: str):
    """Result files that still carry the reference machine's environment.

    A reproduction that ships with the reference results in place will leave
    them there whenever an experiment fails, and every comparison against such a
    file reports a match. The failure then looks like a success, which is the
    opposite of what this tool is for. The environment block is the tell: it
    names the machine that produced the file.
    """
    # Every result file, not only those carrying a deterministic claim: an
    # experiment whose output is not compared can still be inherited, and the
    # robustness arm was exactly that case.
    matching, differing = [], []
    for cur in sorted(MR.glob("*.json")):
        name = cur.stem
        try:
            doc = json.loads(cur.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(doc, dict):      # some results are bare arrays
            continue
        cur_env = doc.get("environment") or {}
        ref = _reference(tag, name) or {}
        ref_env = ref.get("environment") or {}
        if not cur_env or not ref_env:
            continue
        same = all(cur_env.get(k) == ref_env.get(k)
                   for k in ("platform", "python", "ffmpeg")
                   if k in ref_env)
        (matching if same else differing).append(
            (name, ref_env.get("platform", "?"), ref_env.get("python", "?")))

    # If every file names the reference machine, this is the reference machine
    # and nothing was inherited. Only a mixture is evidence that some experiments
    # ran here and others left the shipped file untouched.
    if not differing:
        return []
    return [f"{n}.json records {plat}, Python {py}" for n, plat, py in matching]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=RELEASE,
                    help=f"release tag to compare against (default {RELEASE})")
    args = ap.parse_args()

    print(f"Comparing the working tree against {_reference_source(args.ref)}.")
    print("Deterministic outputs must match exactly. Environment-dependent "
          "outputs are reported\nand are expected to differ.\n")

    unclassified = _unclassified_timings()
    if unclassified:
        print(f"UNCLASSIFIED TIMING FIELDS ({len(unclassified)}): these are "
              f"wall-clock measurements\nheld to exact equality, which no "
              f"reproduction can satisfy. Add them to ENV_FIELDS.")
        for u in unclassified:
            print(f"  {u}")
        print()

    stale = _inherited_results(args.ref)
    if stale:
        print(f"INHERITED RESULTS ({len(stale)}): these files record the "
              f"reference machine, not this one.\nThe experiment did not run "
              f"and the shipped file was left in place, so a comparison\n"
              f"against it would report a match that never happened.")
        for r in stale:
            print(f"  {r}")
        print()

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

    if mismatches or missing or stale:
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
