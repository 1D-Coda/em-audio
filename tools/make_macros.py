"""Emit every manuscript number as a LaTeX macro.

The manuscript source contains no typed numeric results: it uses these macros.
``tools/check_numbers.py`` verifies that no bare result number appears in the
LaTeX source outside this file.
"""
from __future__ import annotations

import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MR = ROOT / "results" / "machine_readable"
OUT = ROOT / "results" / "numbers.tex"


def load(n):
    return json.loads((MR / f"{n}.json").read_text())


def fmt(x):
    if isinstance(x, int):
        return f"{x:,}".replace(",", r"\,")
    return str(x)


def main() -> int:
    A, B, C0, C, D = (load("A_synthetic_state_space"), load("B_adversarial_timelines"),
                      load("C0_corpus_build"), load("C_public_audio_splice"),
                      load("D_transform_matrix"))
    E, F, G, H = (load("E_manifest_stripping"), load("F_c2pa_roundtrip"),
                  load("G_overhead"), load("H_oracle_differential"))
    m = {}
    # A
    m["Awords"] = fmt(A["words_enumerated"]); m["Acases"] = fmt(A["operator_cases"])
    m["Achecks"] = fmt(A["checks_total"]); m["Afailed"] = fmt(A["checks_failed"])
    m["Amaxlen"] = fmt(A["max_word_length"]); m["Acomp"] = fmt(A["composition_cases"])
    # B
    m["Btimelines"] = fmt(B["n_timelines"]); m["Bintervals"] = fmt(B["n_intervals"])
    m["Bdepths"] = fmt(B["max_depth"])
    d1 = B["per_depth"]["1"]; d5 = B["per_depth"]["5"]
    m["BbaseOne"] = fmt(d1["baseline_provenance_promotions"])
    m["BbaseOnePct"] = f"{100*d1['baseline_promotion_rate']:.1f}"
    m["BbaseFive"] = fmt(d5["baseline_provenance_promotions"])
    m["BemAll"] = fmt(sum(v["em_provenance_promotions"] for v in B["per_depth"].values()))
    m["BemUnver"] = fmt(sum(v["em_unverified_to_verified"] for v in B["per_depth"].values()))
    m["BemLineage"] = fmt(sum(v["em_lineage_omissions"] for v in B["per_depth"].values()))
    m["BbaseLineageOne"] = fmt(d1["baseline_lineage_omissions"])
    m["BbaseUnverOne"] = fmt(d1["baseline_unverified_to_verified"])
    m["BbaseSupportOne"] = fmt(d1["baseline_support_promotions"])
    ops = B["per_operator_single_step"]
    m["BopMin"] = f"{100*min(v['baseline_rate'] for v in ops.values()):.1f}"
    m["BopMax"] = f"{100*max(v['baseline_rate'] for v in ops.values()):.1f}"
    m["BopCount"] = fmt(len(ops))
    m["BemOpAll"] = fmt(sum(v["em_promotions"] for v in ops.values()))
    dev = max(abs(c["measured_baseline_rate"] - c["closed_form_baseline_rate"])
              for arm in B["control_uniform_positions"].values() for c in arm.values())
    m["BctrlDev"] = f"{dev:.4f}"
    m["BctrlDevPct"] = f"{100*dev:.2f}"
    # C
    m["Cclips"] = fmt(C["n_clips"]); m["Cexact"] = fmt(C["exact_interval_recovery"])
    m["Cgen"] = fmt(C["generated_interval_recovered"])
    m["Cbase"] = fmt(C["baseline_provenance_promotions"]); m["Cem"] = fmt(C["em_provenance_promotions"])
    m["CbaseLineage"] = fmt(C["baseline_lineage_omissions"])
    m["CemLineage"] = fmt(C["em_lineage_omissions"])
    m["CcorpusFs"] = fmt(C0["sample_rate"])
    m["CcorpusMismatch"] = fmt(C0["boundary_mismatches"])
    # D
    pt = D["per_transformation"]
    m["Dtransforms"] = fmt(len(pt)); m["Druns"] = fmt(sum(v["n"] for v in pt.values()))
    m["Dbase"] = fmt(sum(v["baseline_promotions"] for v in pt.values()))
    m["Dem"] = fmt(sum(v["em_promotions"] for v in pt.values()))
    m["DemLineage"] = fmt(sum(v["em_lineage_omissions"] for v in pt.values()))
    m["DbaseLineage"] = fmt(sum(v["baseline_lineage_omissions"] for v in pt.values()))
    m["Ddeterm"] = fmt(D["determinism_rerun_mismatches"])
    m["DdetermN"] = fmt(D["determinism_subset_clips"])
    m["DmaxDev"] = fmt(max(v["model_vs_ffmpeg_max_abs_sample_dev"] or 0 for v in pt.values()))
    m["DsilenceDev"] = fmt(pt["silence_removal"]["model_vs_ffmpeg_max_abs_sample_dev"] or 0)
    m["DstretchDev"] = fmt(pt["time_stretch_1.10"]["model_vs_ffmpeg_max_abs_sample_dev"] or 0)
    m["DmpThreeDev"] = fmt(pt["transcode_mp3"]["model_vs_ffmpeg_max_abs_sample_dev"] or 0)
    m["DresampleDev"] = fmt(pt["resample_16_8"]["model_vs_ffmpeg_max_abs_sample_dev"] or 0)
    m["DguardOK"] = "all" if all(v["guard_band_covers_deviation"] for v in pt.values()) else "NOT ALL"
    m["DzeroBase"] = fmt(sum(1 for v in pt.values() if v["baseline_promotions"] == 0))
    m["DmeanEmIv"] = f"{sum(v['mean_em_intervals'] for v in pt.values())/len(pt):.2f}"
    # E
    m["Eclips"] = fmt(E["n_clips"]); m["Eviol"] = fmt(E["violations"])
    m["Econds"] = fmt(len(E["conditions"]))
    m["Estripped"] = fmt(E["state_tally"]["manifest_removed"].get("UNVERIFIED", 0))
    m["Etampered"] = fmt(E["state_tally"]["asset_modified_after_signing"].get("INVALID", 0))
    m["Ereenc"] = fmt(E["state_tally"]["reencoded_without_manifest"].get("UNVERIFIED", 0))
    m["Evalid"] = fmt(E["state_tally"]["valid_manifest"].get("MIXED", 0))
    m["Ederived"] = fmt(E["state_tally"]["valid_derived_manifest"].get("MIXED", 0))
    # F
    pc = F["per_container"]
    m["Fclips"] = fmt(F["n_clips"]); m["Fcontainers"] = fmt(len(pc))
    m["Ftotal"] = fmt(sum(v["n"] for v in pc.values()))
    m["Ftrusted"] = fmt(sum(v["validate_trusted"] for v in pc.values()))
    m["Fderived"] = fmt(sum(v["derived_validate_trusted"] for v in pc.values()))
    m["Fparent"] = fmt(sum(v["parentOf_recorded"] for v in pc.values()))
    m["Fassertion"] = fmt(sum(v["assertion_roundtrip_identical"] for v in pc.values()))
    m["Fmismatch"] = fmt(sum(v["n"] - v["essence_identical_pre_vs_em"] for v in pc.values()))
    m["FmismatchPolicy"] = fmt(sum(v["n"] - v["essence_identical_em_vs_baseline"] for v in pc.values()))
    m["Ffilechanged"] = fmt(sum(v["file_hash_changed_by_signing"] for v in pc.values()))
    m["Fvalfail"] = fmt(sum(v["n"] - v["validate_valid_or_better"] for v in pc.values()))
    # G
    m["Gem"] = f"{G['em_ms_per_audio_minute']:.2f}"
    m["Gbase"] = f"{G['baseline_ms_per_audio_minute']:.2f}"
    m["Gratio"] = f"{G['em_over_baseline_ratio']:.2f}"
    m["GffmpegPct"] = f"{100*G['em_over_ffmpeg_fraction']:.3f}"
    m["Gsign"] = f"{G['sign_ms']['median']:.1f}"
    m["GsignQa"] = f"{G['sign_ms']['q1']:.1f}"; m["GsignQb"] = f"{G['sign_ms']['q3']:.1f}"
    m["Gval"] = f"{G['validate_ms']['median']:.1f}"
    m["GvalQa"] = f"{G['validate_ms']['q1']:.1f}"; m["GvalQb"] = f"{G['validate_ms']['q3']:.1f}"
    m["Gmanifest"] = fmt(G["median_manifest_overhead_bytes_per_asset"])
    m["Gassertion"] = fmt(G["median_em_assertion_bytes_per_asset"])
    m["Greps"] = fmt(G["repetitions"])
    sc = G["assertion_scaling"]
    m["GperInterval"] = f"{(sc[-1]['assertion_bytes']-sc[0]['assertion_bytes'])/(sc[-1]['emitted_intervals']-sc[0]['emitted_intervals']):.0f}"
    m["GperIntervalUs"] = f"{1000*(sc[-1]['median_ms']-sc[0]['median_ms'])/(sc[-1]['emitted_intervals']-sc[0]['emitted_intervals']):.1f}"
    m["GmaxIntervals"] = fmt(sc[-1]["emitted_intervals"])
    # B2 ablation
    AB = load("B2_policy_ablation")
    m["ABcases"] = fmt(AB["arms"]["interior"]["cases"])
    for key, short in (("B0_boundary_blind", "BZero"), ("B1_boundary_footprint", "BOne"),
                       ("B2_complete_blind", "BTwo"), ("B3_complete_footprint", "BThree")):
        m[short + "Interior"] = fmt(AB["arms"]["interior"]["per_policy"][key]["promotions"])
        m[short + "Footprint"] = fmt(AB["arms"]["footprint"]["per_policy"][key]["promotions"])
    # H
    m["Hcases"] = fmt(H["cases"]); m["Hdis"] = fmt(H["disagreements"])
    m["Hdelta"] = f"{H['max_support_abs_difference']:.0f}"
    # tests
    t = subprocess.run([sys.executable, str(ROOT / "tests" / "test_contract.py")],
                       capture_output=True, text=True)
    m["Tpass"] = fmt(t.stdout.count("  PASS  ")); m["Tfail"] = fmt(t.stdout.count("  FAIL  "))
    m["Ttotal"] = fmt(t.stdout.count("  PASS  ") + t.stdout.count("  FAIL  "))
    # release identity
    def _git(*a):
        try:
            return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                                  text=True).stdout.strip() or "UNCOMMITTED"
        except Exception:
            return "UNCOMMITTED"
    m["Rcommit"] = _git("rev-parse", "HEAD")
    m["Rtag"] = _git("describe", "--tags", "--always")
    # environment
    env = D["environment"]
    m["Vffmpeg"] = env["ffmpeg"].split()[2]
    m["Vpython"] = env["python"]
    m["Vc2patool"] = env["c2patool"].split()[-1]
    m["Vnode"] = env["node"]
    m["Vespeak"] = env["espeak_ng"].split()[3] if len(env["espeak_ng"].split()) > 3 else env["espeak_ng"]

    # LaTeX control sequences may contain letters only.
    digits = str.maketrans({"0": "Zero", "1": "One", "2": "Two", "3": "Three",
                            "4": "Four", "5": "Five", "6": "Six", "7": "Seven",
                            "8": "Eight", "9": "Nine"})
    body = ["% Generated by tools/make_macros.py -- do not edit by hand.",
            "% Every numeric result in the manuscript comes from this file."]
    for k, v in sorted(m.items()):
        body.append(rf"\newcommand{{\{k.translate(digits)}}}{{{v}\xspace}}")
    OUT.write_text("\n".join(body) + "\n")
    print(f"[macros] results/numbers.tex  ({len(m)} macros)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
