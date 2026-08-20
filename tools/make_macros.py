"""Emit every manuscript number as a LaTeX macro.

The manuscript source contains no typed numeric results: it uses these macros.
``tools/check_numbers.py`` verifies that no bare result number appears in the
LaTeX source outside this file.
"""
from __future__ import annotations

import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    bb = A.get("battery_breakdown", {})
    if bb:
        m["AwordsShortOne"] = fmt(bb["words_len1_battery8"])
        m["AwordsShortTwo"] = fmt(bb["words_len2_battery9"])
        m["AwordsFull"] = fmt(bb["words_len3plus_battery10"])
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
    m["CmeanDurS"] = f"{C0['total_samples'] / C0['n_clips'] / C0['sample_rate']:.2f}"
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
    # C2 robustness
    C2 = load("C2_robustness")
    m["CtwoNeuralN"] = fmt(C2["arms"]["neural_tts"]["n"])
    m["CtwoNeuralExact"] = fmt(C2["arms"]["neural_tts"]["exact"])
    m["CtwoNeuralBase"] = fmt(C2["arms"]["neural_tts"]["base_promote"])
    m["CtwoNeuralEm"] = fmt(C2["arms"]["neural_tts"]["em_promote"])
    m["CtwoNoiseN"] = fmt(C2["arms"]["noise_overlay"]["n"])
    m["CtwoNoiseExact"] = fmt(C2["arms"]["noise_overlay"]["exact"])
    m["CtwoNoiseEm"] = fmt(C2["arms"]["noise_overlay"]["em_promote"])
    # J componentOf composition
    J = load("J_c2pa_composition")
    m["Jfixtures"] = fmt(J["n_fixtures"])
    m["JsourcesTrusted"] = fmt(J["sources_trusted"])
    m["JcompTrusted"] = fmt(J["composition_trusted"])
    m["Jcomponents"] = fmt(J["component_ingredients_recorded"])
    m["Jplaced"] = fmt(J["placed_actions_reference_both"])
    m["Jroundtrip"] = fmt(J["assertion_roundtrip_identical"])
    m["Jmixed"] = fmt(J["aggregate_mixed"])
    m["JderivedTrusted"] = fmt(J["derived_trusted"])
    m["JderivedMixed"] = fmt(J["derived_mixed"])
    m["Jessence"] = fmt(J["essence_mismatches"])
    # K support containment
    K = load("K_support_containment")
    m["Kprobes"] = fmt(K["total_probes"])
    m["Kaffected"] = fmt(K["total_affected_output_samples"])
    m["Koutside"] = fmt(K["total_outside_declared_support"])
    m["Kops"] = fmt(len(K["per_operator"]))
    m["KimpulseN"] = fmt(K["source_length_samples"])
    po = K["per_operator"]
    m["KresampleMargin"] = fmt(po["resample_16_8"]["min_margin_inside_declared_range"])
    m["KresampleFp"] = fmt(po["resample_16_8"]["declared_footprint_samples"])
    m["KmpThreeMargin"] = fmt(po["transcode_mp3"]["min_margin_inside_declared_range"])
    m["KmpThreeFp"] = fmt(po["transcode_mp3"]["declared_footprint_samples"])
    m["KstretchMargin"] = fmt(po["time_stretch_1.10"]["min_margin_inside_declared_range"])
    m["KstretchFp"] = fmt(po["time_stretch_1.10"]["declared_footprint_samples"])
    m["KmpThreeSpread"] = fmt(po["transcode_mp3"]["max_spread_output_samples"])
    m["KstretchSpread"] = fmt(po["time_stretch_1.10"]["max_spread_output_samples"])
    m["KstretchAboveOne"] = fmt(po["time_stretch_1.10"]["probes_with_spread_above_one"])
    m["Kcontexts"] = fmt(len(K["signal_contexts"]))
    m["KsilenceFp"] = fmt(po["silence_removal"]["declared_footprint_samples"])
    m["KsilenceMargin"] = fmt(po["silence_removal"]["min_margin_inside_declared_range"])
    m["KsilenceReach"] = fmt(po["silence_removal"]["max_measured_reach_source_samples"])
    m["KmpThreeReach"] = fmt(po["transcode_mp3"]["max_measured_reach_source_samples"])
    m["KstretchReach"] = fmt(po["time_stretch_1.10"]["max_measured_reach_source_samples"])
    m["KresampleReach"] = fmt(po["resample_16_8"]["max_measured_reach_source_samples"])
    # MP3 footprint constants, so the manuscript never types them
    import em_audio.operators as _O
    m["MpThreeKernel"] = fmt(_O.MP3_FOOTPRINT)
    m["MpThreeGuard"] = fmt(_O.GUARD_BAND["transcode"])
    m["MpThreeDeclared"] = fmt(_O.MP3_FOOTPRINT + _O.GUARD_BAND["transcode"])
    m["MpThreeWindow"] = fmt(_O.MP3_WINDOW)
    # the v1 channel's two declaration-derived values, from one definition
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
    from _common import CAPTURE_SUPPORT as _CS
    m["CaptSupport"] = f"{_CS['C']:.2f}"
    m["GenSupport"] = f"{_CS['G']:.2f}"
    m["KresampleSpread"] = fmt(po["resample_16_8"]["max_spread_output_samples"])
    # I claim dilution
    I = load("I_claim_dilution")
    pt_i = I["per_transformation"]
    worst = max(pt_i.values(), key=lambda v: v["median_dilution_fraction"])
    m["IclipsPerTf"] = fmt(pt_i["resample_16_8"]["clips"])
    m["IresampleMedianPct"] = f"{100*pt_i['resample_16_8']['median_dilution_fraction']:.2f}"
    m["ImpThreeMedianPct"] = f"{100*pt_i['transcode_mp3']['median_dilution_fraction']:.2f}"
    m["IstretchMedianPct"] = f"{100*pt_i['time_stretch_1.10']['median_dilution_fraction']:.2f}"
    m["IsilenceMedianPct"] = f"{100*pt_i['silence_removal']['median_dilution_fraction']:.2f}"
    m["ImaxAnyPct"] = f"{100*max(v['max_dilution_fraction'] for v in pt_i.values()):.2f}"
    m["IzeroTf"] = fmt(sum(1 for v in pt_i.values() if v["max_dilution_fraction"] == 0))
    m["ItfCount"] = fmt(len(pt_i))
    cd = I["composition_chain"]
    m["IchainDeep"] = f"{100*cd[-1]['median_dilution_fraction']:.2f}"
    m["IchainDeepMax"] = f"{100*cd[-1]['max_dilution_fraction']:.2f}"
    m["IchainDepth"] = fmt(cd[-1]["depth"])
    m["IchainClips"] = fmt(I["chain_subset_clips"])
    la = {r["asset_seconds"]: r for r in I["long_asset_chain"]}
    m["IlongShortPct"] = f"{100*la[2.85]['dilution_fraction']:.2f}"
    m["IlongThirtyPct"] = f"{100*la[30]['dilution_fraction']:.2f}"
    m["IlongThreeHundredPct"] = f"{100*la[300]['dilution_fraction']:.3f}"
    m["IoverlayMedianPct"] = f"{100*pt_i['overlay_generated']['median_dilution_fraction']:.2f}"
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
    # Machine declaration, generated rather than typed: the manuscript states the
    # timing platform and the checker must not have to whitelist a version string.
    plat = env.get("platform", "")
    mac = plat.split("-")[1] if plat.startswith("macOS-") and "-" in plat else ""
    m["Vos"] = ("macOS " + mac) if mac else plat.split("-")[0]
    m["Varch"] = env.get("machine", "")

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
