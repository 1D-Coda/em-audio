"""Emit every manuscript number as a LaTeX macro.

The manuscript source contains no typed numeric results: it uses these macros.
``tools/check_numbers.py`` verifies that no bare result number appears in the
LaTeX source outside this file.
"""
from __future__ import annotations

import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
MR = ROOT / "results" / "machine_readable"
OUT = ROOT / "results" / "numbers.tex"


def load(n):
    return json.loads((MR / f"{n}.json").read_text())


def fmt(x):
    if isinstance(x, int):
        return f"{x:,}".replace(",", r"\,")
    return str(x)


IND = ROOT / "results" / "independent"


def independent_macros():
    """Numbers from the third-party reproduction, taken from its own files.

    Both this run and the reference run write the same schema, so the
    comparisons the manuscript makes are computed here from the two files
    rather than typed into the text from a terminal transcript.
    """
    import verify_reproduction as V

    ind = IND / "machine_readable"
    L = lambda d, n: json.loads((d / f"{n}.json").read_text())
    m = {}

    env = L(ind, "D_transform_matrix")["environment"]
    m["IRpython"] = env["python"]
    m["IRffmpeg"] = env["ffmpeg"].split()[2]
    m["IRcTwopatool"] = env["c2patool"].split()[-1]
    m["IRnode"] = env["node"]
    m["IRos"] = "Linux " + env["platform"].split("-")[1].split("-micro")[0]
    # The architecture string carries an underscore, which is not text-mode
    # LaTeX; escape it here rather than leaving the one macro in the file that
    # the manuscript may not use verbatim like all the others.
    m["IRarch"] = env.get("machine", "").replace("_", r"\_")
    # The CPU model is recorded in the preflight report rather than in each
    # result file's environment block.
    pre = {}
    for line in (IND / "PREFLIGHT.txt").read_text().splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            pre.setdefault(k.strip(), v.strip())
    m["IRcpu"] = pre.get("cpu", "").replace("(R)", "").replace("(TM)", "").strip()
    m["IRcores"] = pre.get("cpu_count_logical", "")
    m["IRmem"] = pre.get("memory_gib", "")
    esp = pre.get("espeak_ng", "").split()
    m["IRespeak"] = esp[3] if len(esp) > 3 else ""
    # The dates of the two runs, from the timestamp each one stamped into its
    # own stability record rather than from a covering email.
    m["IRdate"] = json.loads(
        (ind / "M_overhead_stability.json").read_text())["measured_utc"][:10]

    # How many of the compared files differ, computed with the same classifier
    # the reproducer ran, so the count in the text is the count the tool printed.
    clean = det = envd = 0
    for name, keys in V.DETERMINISTIC.items():
        cur, ref = L(ind, name), V._reference("v1.0.1", name)
        n = 0
        for key in keys:
            flat_cur = dict(V._flatten(cur[key], key))
            for path, rv in V._flatten(ref[key], key):
                cv = flat_cur.get(path, "<absent>")
                if cv == rv:
                    continue
                if V._is_env(path):
                    envd += 1
                else:
                    n += 1
        det += n
        clean += (n == 0)
    m["IRfiles"] = fmt(len(V.DETERMINISTIC))
    m["IRclean"] = fmt(clean)
    m["IRdet"] = fmt(det)
    m["IRenv"] = fmt(envd)

    # the two operators whose declared numbers his build did not satisfy
    k = L(ind, "K_support_containment")["per_operator"]["transcode_mp3"]
    km = L(MR, "K_support_containment")["per_operator"]["transcode_mp3"]
    m["IRmpDeclared"] = fmt(k["declared_footprint_samples"])
    m["IRmpReach"] = fmt(k["max_measured_reach_source_samples"])
    m["IRmpReachRef"] = fmt(km["max_measured_reach_source_samples"])
    m["IRmpExcess"] = fmt(k["max_samples_outside"])
    m["IRmpOutside"] = fmt(k["total_outside_declared_support"])
    m["IRmpContext"] = ", ".join(sorted(c for c, v in k["per_context_outside"].items() if v))

    d = L(ind, "D_transform_matrix")["per_transformation"]["silence_removal"]
    dm = L(MR, "D_transform_matrix")["per_transformation"]["silence_removal"]
    m["IRsilGuard"] = fmt(d["declared_guard_band_samples"])
    m["IRsilDev"] = fmt(d["model_vs_ffmpeg_max_abs_sample_dev"])
    m["IRsilDevRef"] = fmt(dm["model_vs_ffmpeg_max_abs_sample_dev"])
    # Not int(): the median of an even number of runs is a half-integer, and
    # truncating it prints a number the result file does not contain.
    med = d["model_vs_ffmpeg_median_abs_sample_dev"]
    m["IRsilMedian"] = fmt(int(med)) if med == int(med) else f"{med:,.1f}".replace(",", r"\,")

    # How many operators reproduced their measured reach, counted among those
    # that declare a non-zero footprint. Counting all seven would credit three
    # operators whose reach is zero on both machines, which reproduces trivially
    # and would overstate the agreement.
    ki, km = L(ind, "K_support_containment")["per_operator"], L(MR, "K_support_containment")["per_operator"]
    nz = [o for o in km if km[o]["declared_footprint_samples"] > 0]
    agree = [o for o in nz if km[o]["max_measured_reach_source_samples"]
             == ki[o]["max_measured_reach_source_samples"]]
    m["IRopsNonzero"] = fmt(len(nz))
    m["IRopsAgree"] = fmt(len(agree))
    m["IRopsZero"] = fmt(len(km) - len(nz))
    # the mechanism: his silencremove leaves a longer output than the reference's
    probes = L(ind, "K_support_containment")["per_operator"]["silence_removal"]["per_probe"]
    probes_ref = L(MR, "K_support_containment")["per_operator"]["silence_removal"]["per_probe"]
    m["IRsilLen"] = fmt(max(p["decoded_length"] for p in probes))
    m["IRsilLenRef"] = fmt(max(p["decoded_length"] for p in probes_ref))

    # cost: the absolute figure travels badly, the ratio travels well
    g, gm = L(ind, "G_overhead"), L(MR, "G_overhead")
    s, sm = L(ind, "M_overhead_stability"), L(MR, "M_overhead_stability")
    m["IRratio"] = f"{g['em_over_baseline_ratio']:.2f}"
    m["IRratioRef"] = f"{gm['em_over_baseline_ratio']:.2f}"
    m["IRabs"] = f"{g['em_ms_per_audio_minute']:.2f}"
    m["IRabsRef"] = f"{gm['em_ms_per_audio_minute']:.2f}"
    m["IRabsGap"] = f"{100*abs(g['em_ms_per_audio_minute']/gm['em_ms_per_audio_minute'] - 1):.0f}"
    m["IRratioGap"] = f"{100*abs(g['em_over_baseline_ratio']/gm['em_over_baseline_ratio'] - 1):.1f}"
    m["IRabsCv"] = f"{s['em_ms_per_audio_minute']['cv_pct']:.1f}"
    m["IRratioCv"] = f"{s['em_over_baseline_ratio']['cv_pct']:.1f}"
    return m



# A stable key for each supplement section the manuscript points at, matched on
# a distinctive substring of its title rather than on its position.
SUPPLEMENT_NOTES = {
    "NoteNovelty": "Novelty search",
    "NoteThreat": "Threat-model matrix",
    "NoteSchema": "EM assertion schema",
    "NoteComposition": "Composition manifest wiring",
    "NoteRobustness": "Robustness-arm materials",
    "NoteRepro": "Reproduction",
    "NoteIndependent": "Independent reproduction",
    "NoteRawRows": "Raw rows behind two summary figures",
    "NoteFeasibility": "Feasibility log",
}


def supplement_notes():
    """Map each key to the number the supplement actually gives that section."""
    import re
    sp = ROOT / "paper" / "supplementary.tex"
    if not sp.exists():
        # Reproduction package: no paper/, so no supplement notes to resolve.
        return {}
    supp = sp.read_text()
    titles = re.findall(r"^\\section\{([^}]+)\}", supp, re.M)
    out = {}
    for key, needle in SUPPLEMENT_NOTES.items():
        hits = [i for i, t in enumerate(titles, 1) if needle in t]
        if len(hits) != 1:
            raise SystemExit(
                f"[macros] supplement section for {key} ({needle!r}) matched "
                f"{len(hits)} of {len(titles)} sections; the manuscript cannot "
                f"point at it unambiguously")
        out[key] = f"S{hits[0]}"
    return out



# Numbers the supplement needs to cite from the manuscript. The supplement is a
# separate document and cannot \ref across, so the two stale references it
# carried were typed by hand and went wrong silently. These are read from the
# manuscript's own .aux, which is what LaTeX resolved, so they cannot disagree
# with what the manuscript prints.
MANUSCRIPT_LABELS = {
    "PropFootprint": "prop:footprint",
    "PropUnion": "prop:union",
    "ThmComposition": "thm:composition",
    "TabOperators": "tab:operators",
}


def manuscript_labels():
    import re
    aux = ROOT / "paper" / "manuscript.aux"
    if not aux.exists():
        print("[macros] paper/manuscript.aux absent; the manuscript's own "
              "numbering is not available, so cross-document labels are skipped")
        return {}
    text = aux.read_text(errors="ignore")
    out = {}
    for key, label in MANUSCRIPT_LABELS.items():
        mm = re.search(r"\\newlabel\{" + re.escape(label) + r"\}\{\{([^}]*)\}", text)
        if not mm:
            raise SystemExit(f"[macros] manuscript.aux has no label {label!r}; "
                             f"build the manuscript before generating macros")
        out[key] = mm.group(1)
    return out


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
    m["KoutsideTotal"] = fmt(sum(v["total_outside_declared_support"] for v in po.values()))
    Dm = load("D_transform_matrix")["per_transformation"]
    m["DbasePromo"] = fmt(sum(v["baseline_promotions"] for v in Dm.values()))
    m["DemPromo"] = fmt(sum(v["em_promotions"] for v in Dm.values()))
    m["DtotalRuns"] = fmt(load("D_transform_matrix")["n_clips"] * len(Dm))
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
    L = load("L_scope_battery")
    m["LscopeCases"] = fmt(L["enlargement_cases"])
    m["LscopeScopes"] = fmt(L["distinct_scopes"])
    m["LscopeViolations"] = fmt(L["violations"])
    m["LscopeFailBad"] = fmt(L["violations_under_superseded_rule"])
    M = load("M_overhead_stability")
    G = load("G_overhead")
    m["Vcpu"] = G["environment"]["cpu_model"]
    # Not every platform reports this. Windows returned "unavailable" and the
    # int() then ended the whole run inside the tables step, which names neither
    # the value nor the platform. A machine that cannot say how many cores it
    # has is not a reason to fail a reproduction.
    _cores = G["environment"].get("cpu_count_logical", "")
    m["Vcores"] = fmt(int(_cores)) if str(_cores).isdigit() else "unavailable"
    # memory_bytes is "unavailable" wherever the platform has no /proc and no
    # sysctl, which is Windows. This is where the int() ended a whole run.
    _mem = G["environment"].get("memory_bytes", "")
    m["Vram"] = (f"{int(_mem) / 2**30:.0f}" if str(_mem).isdigit() else "unavailable")
    m["GfirstIterPct"] = f"{G['first_iteration_effect_pct']:.2f}"
    m["Gclips"] = fmt(G["clips_per_repetition"])
    m["MstabRepeats"] = fmt(M["repeats"])
    m["MstabAbsPct"] = f"{M['em_ms_per_audio_minute']['cv_pct']:.2f}"
    m["MstabRatioPct"] = f"{M['em_over_baseline_ratio']['cv_pct']:.2f}"
    m["MstabFactor"] = f"{M['tightness_factor_cv']:.1f}" if M.get("tightness_factor_cv") else "--"
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
    # independent reproduction
    #
    # Read from the reproducer's own result files rather than transcribed, so
    # that a number quoted in Section 7.11 cannot drift from the files shipped
    # in results/independent/. Absent that directory the macros are simply not
    # emitted and the manuscript fails to build, which is the correct failure:
    # a claim about someone else's run must not survive the loss of their data.
    # A reproduction package deliberately ships without results/independent/,
    # because those are someone else's measurements and shipping them lets a
    # failed experiment leave a file in place that a comparison then reports as
    # a match. So this block is optional: absent inputs mean the macros are not
    # emitted, not that the run dies. Testing the package caught this; the
    # working tree always has the directory, so it could not fail here.
    ind_dir = ROOT / "results" / "independent" / "machine_readable"
    if ind_dir.is_dir() and any(ind_dir.glob("*.json")):
        m.update(independent_macros())
    else:
        print("[macros] results/independent/ absent: the independent-reproduction "
              "macros are not emitted. Expected in a reproduction package.")
    # The C2PA assertion label and schema identifier, read from the module that
    # defines them. They were typed into the manuscript and the supplement by
    # hand, so changing the namespace in code left the paper describing an
    # assertion the implementation no longer emits.
    from em_audio import manifest_schema as _ms
    m["Clabel"] = _ms.ASSERTION_LABEL.replace("_", r"\_")
    m["Cschema"] = _ms.SCHEMA.replace("_", r"\_").replace("#", r"\#")
    m["Cnamespace"] = _ms.NAMESPACE.replace("_", r"\_")

    # Supplementary note numbers, derived from the supplement's own section
    # order. They were typed into the manuscript as "Supplementary Note~S8",
    # and inserting a section ahead of the one they meant silently repointed all
    # three at the wrong note while the checker still reported them as
    # resolving, because it only asked whether a note with that number existed.
    m.update(supplement_notes())
    m.update(manuscript_labels())

    # The tag the independent reproducer actually ran, which is not the same
    # fact as the repository's current release tag. The manuscript said \Rtag,
    # which is generated from `git describe` and silently fills in whatever tag
    # is current, so the sentence claimed he ran a release that did not exist
    # when he ran it.
    rec = ROOT / "results" / "independent" / "RUN_RECORD.txt"
    if rec.exists():
        for line in rec.read_text().splitlines():
            if line.startswith("tag_run:"):
                m["IRtag"] = line.split(":", 1)[1].strip()
                break
        else:
            raise SystemExit("[macros] RUN_RECORD.txt exists but has no tag_run")

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
