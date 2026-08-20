"""Generate the preflight report from the machine-readable results only.

Every number quoted in the manuscript must appear here.  ``tools/check_numbers.py``
fails the build if a number in the manuscript source is absent from this file.
"""
from __future__ import annotations

import json, platform, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MR = ROOT / "results" / "machine_readable"


def load(name):
    p = MR / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


def _v(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()[0].strip()
    except Exception:
        return "unavailable"


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip() or "UNCOMMITTED"
    except Exception:
        return "UNCOMMITTED"


def main() -> int:
    A, B, C0, C, D = load("A_synthetic_state_space"), load("B_adversarial_timelines"), \
        load("C0_corpus_build"), load("C_public_audio_splice"), load("D_transform_matrix")
    if load("I_claim_dilution") is None:
        print("missing results: I", file=sys.stderr)
        return 2
    E, F, G, H = load("E_manifest_stripping"), load("F_c2pa_roundtrip"), \
        load("G_overhead"), load("H_oracle_differential")
    missing = [n for n, x in [("A", A), ("B", B), ("C0", C0), ("C", C), ("D", D),
                              ("E", E), ("F", F), ("G", G), ("H", H)] if x is None]
    if missing:
        print(f"missing results: {missing}", file=sys.stderr)
        return 2

    d5 = B["per_depth"]["5"]
    lines = []
    add = lines.append
    add("EM-AUDIO PREFLIGHT REPORT")
    add("=" * 72)
    add(f"commit: {git('rev-parse', 'HEAD')}")
    add(f"tag: {git('describe', '--tags', '--always')}")
    add("note: 'commit' is HEAD when this report was generated. Because the report is")
    add("      itself committed, the copy stored in the repository necessarily lags the")
    add("      commit that stores it by one. Re-run tools/preflight.py, or run_all.sh,")
    add("      to regenerate it against the working tree you actually have.")
    add("zenodo_version_doi: PENDING - assign at archive time")
    add("zenodo_concept_doi: PENDING - assign at archive time")
    add("")
    add(f"python: {sys.version.split()[0]}")
    add(f"ffmpeg: {_v(['ffmpeg', '-version'])}")
    add(f"c2patool: {_v(['c2patool', '--version'])}")
    add(f"node: {_v(['node', '-v'])}")
    add(f"espeak_ng: {_v(['espeak-ng', '--version'])}")
    add("c2pa_spec_version: 2.4 (April 2026)")
    add(f"os: {platform.platform()}")
    # The manuscript says this file records the exact processor. platform.machine()
    # gives the architecture only, which does not identify the part a timing
    # result depends on, so take the model recorded by the experiments.
    _env = {}
    for _f in sorted(MR.glob("*.json")):
        try:
            _env = json.loads(_f.read_text()).get("environment") or _env
        except Exception:
            pass
        if _env.get("cpu_model"):
            break
    add(f"cpu: {_env.get('cpu_model', platform.machine())}")
    add(f"cpu_arch: {platform.machine()}")
    add(f"cpu_count_logical: {_env.get('cpu_count_logical', 'unavailable')}")
    _mem = _env.get("memory_bytes", "")
    add(f"memory_gib: {int(_mem) / 2**30:.0f}" if _mem.isdigit() else "memory_gib: unavailable")
    add("")
    add("--- A  exhaustive finite-state conformance ---")
    add(f"words_enumerated: {A['words_enumerated']}")
    add(f"operator_cases: {A['operator_cases']}")
    add(f"checks_total: {A['checks_total']}")
    add(f"checks_failed: {A['checks_failed']}")
    add(f"composition_cases: {A['composition_cases']}")
    add("")
    add("--- B  adversarial timelines ---")
    add(f"synthetic_cases: {B['n_timelines']}")
    add(f"baseline_promotions_depth1: {B['per_depth']['1']['baseline_provenance_promotions']}")
    add(f"baseline_promotion_rate_depth1: {B['per_depth']['1']['baseline_promotion_rate']}")
    add(f"baseline_promotions_depth5: {d5['baseline_provenance_promotions']}")
    add(f"em_promotions: {sum(v['em_provenance_promotions'] for v in B['per_depth'].values())}")
    add(f"em_unverified_to_verified: {sum(v['em_unverified_to_verified'] for v in B['per_depth'].values())}")
    add(f"em_lineage_omissions: {sum(v['em_lineage_omissions'] for v in B['per_depth'].values())}")
    add(f"baseline_lineage_omissions_depth1: {B['per_depth']['1']['baseline_lineage_omissions']}")
    mx = max(abs(c['measured_baseline_rate'] - c['closed_form_baseline_rate'])
             for arm in B['control_uniform_positions'].values() for c in arm.values())
    add(f"control_max_abs_deviation_from_closed_form: {mx:.4f}")
    add("")
    add("--- C  mixed-origin corpus ---")
    add(f"audio_clips: {C['n_clips']}")
    add(f"exact_interval_recovery: {C['exact_interval_recovery']}")
    add(f"generated_interval_recovered: {C['generated_interval_recovered']}")
    add(f"corpus_boundary_mismatches: {C0['boundary_mismatches']}")
    add(f"c_baseline_promotions: {C['baseline_provenance_promotions']}")
    add(f"c_em_promotions: {C['em_provenance_promotions']}")
    add("")
    add("--- D  transformation matrix ---")
    add(f"transformations: {len(D['per_transformation'])}")
    add(f"transformation_runs: {sum(v['n'] for v in D['per_transformation'].values())}")
    add(f"d_baseline_promotions: {sum(v['baseline_promotions'] for v in D['per_transformation'].values())}")
    add(f"d_em_promotions: {sum(v['em_promotions'] for v in D['per_transformation'].values())}")
    add(f"lineage_failures: {sum(v['em_lineage_omissions'] for v in D['per_transformation'].values())}")
    add(f"determinism_rerun_mismatches: {D['determinism_rerun_mismatches']}")
    add(f"max_model_vs_ffmpeg_sample_deviation: "
        f"{max(v['model_vs_ffmpeg_max_abs_sample_dev'] or 0 for v in D['per_transformation'].values())}")
    add(f"guard_bands_all_adequate: "
        f"{all(v['guard_band_covers_deviation'] for v in D['per_transformation'].values())}")
    add("")
    add("--- E  provenance loss ---")
    add(f"e_clips: {E['n_clips']}")
    add(f"e_violations: {E['violations']}")
    for cond, tally in E["state_tally"].items():
        add(f"e_{cond}: {tally}")
    add("")
    add("--- F  signed round-trip ---")
    tot = sum(v["n"] for v in F["per_container"].values())
    add(f"signed_roundtrips: {tot}")
    add(f"validation_failures: {sum(v['n'] - v['validate_valid_or_better'] for v in F['per_container'].values())}")
    add(f"derived_validate_trusted: {sum(v['derived_validate_trusted'] for v in F['per_container'].values())}")
    add(f"parentOf_recorded: {sum(v['parentOf_recorded'] for v in F['per_container'].values())}")
    add(f"assertion_roundtrip_identical: {sum(v['assertion_roundtrip_identical'] for v in F['per_container'].values())}")
    add(f"signal_mismatches: {sum(v['n'] - v['essence_identical_pre_vs_em'] for v in F['per_container'].values())}")
    add(f"file_hash_changed_by_signing: {sum(v['file_hash_changed_by_signing'] for v in F['per_container'].values())}")
    add("")
    add("--- G  overhead ---")
    add(f"median_em_ms_per_audio_minute: {G['em_ms_per_audio_minute']}")
    add(f"median_baseline_ms_per_audio_minute: {G['baseline_ms_per_audio_minute']}")
    add(f"em_over_baseline_ratio: {G['em_over_baseline_ratio']}")
    add(f"em_fraction_of_ffmpeg_time: {G['em_over_ffmpeg_fraction']}")
    add(f"median_manifest_overhead_bytes_per_asset: {G['median_manifest_overhead_bytes_per_asset']}")
    add(f"median_em_assertion_bytes_per_asset: {G['median_em_assertion_bytes_per_asset']}")
    add(f"metadata_bytes_per_audio_minute: {G['manifest_bytes_per_audio_minute']}")
    add(f"median_sign_ms: {G['sign_ms']['median']}")
    add(f"median_validate_ms: {G['validate_ms']['median']}")
    sc = G["assertion_scaling"]
    add(f"assertion_bytes_per_interval: {round((sc[-1]['assertion_bytes'] - sc[0]['assertion_bytes']) / (sc[-1]['emitted_intervals'] - sc[0]['emitted_intervals']), 1)}")
    add("")
    K = load("K_support_containment")
    add("--- K  kernel-support containment ---")
    add(f"k_probes: {K['total_probes']}")
    add(f"k_affected_output_samples: {K['total_affected_output_samples']}")
    add(f"k_outside_declared_support: {K['total_outside_declared_support']}")
    add("")
    C2 = load("C2_robustness")
    add("--- C2  robustness arm ---")
    add(f"c2_neural_exact: {C2['arms']['neural_tts']['exact']}/{C2['arms']['neural_tts']['n']}")
    add(f"c2_neural_em_promotions: {C2['arms']['neural_tts']['em_promote']}")
    add(f"c2_noise_exact: {C2['arms']['noise_overlay']['exact']}/{C2['arms']['noise_overlay']['n']}")
    add(f"c2_noise_em_promotions: {C2['arms']['noise_overlay']['em_promote']}")
    add("")
    J = load("J_c2pa_composition")
    add("--- J  componentOf composition ---")
    add(f"j_fixtures: {J['n_fixtures']}")
    add(f"j_composition_trusted: {J['composition_trusted']}")
    add(f"j_aggregate_mixed: {J['aggregate_mixed']}")
    add(f"j_essence_mismatches: {J['essence_mismatches']}")
    add("")
    I = load("I_claim_dilution")
    add("--- I  claim dilution ---")
    add(f"max_dilution_fraction_any_transformation: "
        f"{max(v['max_dilution_fraction'] for v in I['per_transformation'].values())}")
    add(f"chain_depth5_median_dilution: {I['composition_chain'][-1]['median_dilution_fraction']}")
    add("")
    add("--- H  two-language differential ---")
    add(f"oracle_cases: {H['cases']}")
    add(f"oracle_disagreements: {H['disagreements']}")
    add(f"oracle_max_support_difference: {H['max_support_abs_difference']}")
    add("")
    add("--- totals ---")
    tests = subprocess.run([sys.executable, str(ROOT / "tests" / "test_contract.py")],
                           capture_output=True, text=True)
    npass = tests.stdout.count("  PASS  ")
    nfail = tests.stdout.count("  FAIL  ")
    add(f"tests_total: {npass + nfail}")
    add(f"tests_passed: {npass}")
    add(f"tests_failed: {nfail}")

    out = ROOT / "results" / "PREFLIGHT.txt"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
