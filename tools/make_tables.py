"""Emit LaTeX table bodies from the machine-readable results.

No number in these tables is typed by hand.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MR = ROOT / "results" / "machine_readable"
OUT = ROOT / "results" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

import em_audio.operators as O


def load(n):
    return json.loads((MR / f"{n}.json").read_text())


PRETTY = {
    "transcode_mp3": "transcode to MP3", "transcode_flac": "transcode to FLAC",
    "resample_16_8": "resample 16 to 8 kHz", "normalize": "amplitude normalisation",
    "trim_10_90": "trim to the middle 80\\%", "time_stretch_1.10": "time stretch 1.10",
    "silence_removal": "silence removal", "overlay_generated": "overlay a generated source",
}


def esc(s):
    return PRETTY.get(str(s), str(s).replace("_", r"\_"))


def write(name, body, colspec=None, header=None):
    """Emit a complete tabular.

    The fragment carries its own ``\begin{tabular}``/``\end{tabular}``: an
    ``\input`` *inside* an alignment misbehaves at end of file and surfaces as a
    misplaced ``\noalign``, so the manuscript inputs a finished tabular instead
    of a bare list of rows.
    """
    body = body.rstrip()
    parts = []
    if colspec:
        parts.append(r"\begin{tabular}{" + colspec + "}")
        parts.append(r"\toprule")
        if header:
            parts.append(header + r" \\")
            parts.append(r"\midrule")
    parts.append(body)
    if colspec:
        parts.append(r"\bottomrule")
        parts.append(r"\end{tabular}")
    (OUT / f"{name}.tex").write_text("\n".join(parts) + "\n")
    print(f"[table] results/tables/{name}.tex")


def operator_table():
    rows = []
    spec = [
        ("trim / crop", "1:1 on the retained range", "0", "exact"),
        ("concatenate", "1:1 per part", "0", "exact"),
        ("resample", r"$n_\mathrm{out}\!\cdot\!f_\mathrm{in}/f_\mathrm{out}$",
         f"{O._fp_resample(16000, 8000)}", "polyphase FIR"),
        ("transcode (MP3)", "1:1", f"{max(O.MP3_FOOTPRINT, O.GUARD_BAND['transcode'])}",
         "MDCT window + encoder delay"),
        ("transcode (FLAC)", "1:1", f"{O.FLAC_FOOTPRINT}", "lossless"),
        ("amplitude normalisation", "1:1", "0 (strict: whole signal)", "scalar gain"),
        ("time stretch", r"$t_\mathrm{src}=\tau\,t_\mathrm{out}$",
         f"{int(0.030*16000*1.10)+1+O.GUARD_BAND['time_stretch']}", "overlap-add window"),
        ("silence removal", "explicit retained runs", f"{O.GUARD_BAND['silence_removal']}",
         "frame-granular selector"),
        ("mix / overlay", "1:1 from every covering source", "0", "sample-wise sum"),
    ]
    for name, mapping, fp, why in spec:
        rows.append(f"{name} & {mapping} & {fp} & {why} \\\\")
    write("operator_table", "\n".join(rows),
          colspec=r"p{0.24\linewidth}p{0.24\linewidth}rp{0.27\linewidth}",
          header="Operator & Source mapping & Footprint & Reason")


def main_results():
    A, B, C, D, H = (load("A_synthetic_state_space"), load("B_adversarial_timelines"),
                     load("C_public_audio_splice"), load("D_transform_matrix"),
                     load("H_oracle_differential"))
    r = []
    r.append(r"\multicolumn{4}{l}{\textit{A\quad Exhaustive finite-state conformance}} \\")
    r.append(f"Source words over $\\{{C,G,\\bot\\}}$, length $\\le 8$ & {A['words_enumerated']:,} & "
             f"--- & --- \\\\")
    r.append(f"Operator cases & {A['operator_cases']:,} & --- & --- \\\\")
    r.append(f"Contract checks & {A['checks_total']:,} & {A['checks_failed']} failed & --- \\\\")
    r.append(r"\addlinespace")
    r.append(r"\multicolumn{4}{l}{\textit{B\quad Deterministic adversarial timelines "
             r"(10\,000 frozen fixtures, 64 intervals)}} \\")
    for d in ("1", "3", "5"):
        v = B["per_depth"][d]
        r.append(f"Chain depth {d} & {v['timelines']:,} & "
                 f"{v['baseline_provenance_promotions']:,} ({100*v['baseline_promotion_rate']:.1f}\\%) & "
                 f"{v['em_provenance_promotions']} \\\\")
    r.append(f"Lineage omissions (depth 1) & {B['per_depth']['1']['timelines']:,} & "
             f"{B['per_depth']['1']['baseline_lineage_omissions']:,} & "
             f"{B['per_depth']['1']['em_lineage_omissions']} \\\\")
    r.append(f"Unverified $\\to$ verified (depth 1) & --- & "
             f"{B['per_depth']['1']['baseline_unverified_to_verified']:,} & "
             f"{B['per_depth']['1']['em_unverified_to_verified']} \\\\")
    r.append(r"\addlinespace")
    r.append(r"\multicolumn{4}{l}{\textit{C--D\quad Mixed-origin audio corpus, "
             r"stock-FFmpeg processing}} \\")
    r.append(f"Exact interval recovery & {C['n_clips']} & --- & "
             f"{C['exact_interval_recovery']} \\\\")
    for k in sorted(D["per_transformation"]):
        v = D["per_transformation"][k]
        r.append(f"{esc(k)} & {v['n']} & {v['baseline_promotions']} "
                 f"({100*v['baseline_promotion_rate']:.1f}\\%) & {v['em_promotions']} \\\\")
    r.append(r"\addlinespace")
    r.append(r"\multicolumn{4}{l}{\textit{H\quad Two-language differential oracle}} \\")
    r.append(f"Frozen cases & {H['cases']:,} & --- & {H['disagreements']} disagreements \\\\")
    write("main_results", "\n".join(r), colspec="lrrr",
          header="Check & Cases & Boundary-only & Complete-source")


def transport_table():
    E, F = load("E_manifest_stripping"), load("F_c2pa_roundtrip")
    r = []
    for ext, v in F["per_container"].items():
        r.append(f"{ext.upper()} & {v['n']} & {v['validate_trusted']} & "
                 f"{v['derived_validate_trusted']} & {v['parentOf_recorded']} & "
                 f"{v['assertion_roundtrip_identical']} & "
                 f"{v['n'] - v['essence_identical_pre_vs_em']} \\\\")
    write("transport_table", "\n".join(r), colspec="lrrrrrr",
          header=("Container & Assets & Trusted & Derived & \\texttt{parentOf} & "
                  "Assertion & Essence"))
    order = ["valid_manifest", "manifest_removed", "asset_modified_after_signing",
             "reencoded_without_manifest", "valid_derived_manifest"]
    label = {"valid_manifest": "valid manifest",
             "manifest_removed": "manifest removed",
             "asset_modified_after_signing": "asset modified after signing",
             "reencoded_without_manifest": "re-encoded without manifest preservation",
             "valid_derived_manifest": "valid derived manifest with complete lineage"}
    rows = []
    for c in order:
        t = E["state_tally"][c]
        rows.append(f"{label[c]} & {E['n_clips']} & "
                    + ", ".join(f"{k} ({v})" for k, v in sorted(t.items())) + r" \\")
    write("stripping_table", "\n".join(rows), colspec="p{0.46\\linewidth}rl",
          header="Condition & Clips & Reported state")


def ablation_table():
    A = load("B2_policy_ablation")
    label = {"B0_boundary_blind": ("boundary-only", "no"),
             "B1_boundary_footprint": ("boundary-only", "yes"),
             "B2_complete_blind": ("complete-source", "no"),
             "B3_complete_footprint": ("complete-source", "yes")}
    rows = []
    for k in ("B0_boundary_blind", "B1_boundary_footprint",
              "B2_complete_blind", "B3_complete_footprint"):
        inh, fp = label[k]
        i = A["arms"]["interior"]["per_policy"][k]
        f = A["arms"]["footprint"]["per_policy"][k]
        rows.append(f"{k.split('_')[0]} & {inh} & {fp} & "
                    f"{i['promotions']:,} ({100*i['promotion_rate']:.0f}\\%) & "
                    f"{f['promotions']:,} ({100*f['promotion_rate']:.0f}\\%) \\\\".replace(",", "\\,"))
    write("ablation_table", "\n".join(rows), colspec="llccc",
          header=("Policy & Inheritance & Kernel footprint & Interior anomaly & "
                  "Footprint anomaly"))


def dilution_table():
    I = load("I_claim_dilution")
    rows = []
    for k in sorted(I["per_transformation"]):
        v = I["per_transformation"][k]
        rows.append(f"{esc(k)} & {v['clips']} & "
                    f"{100*v['median_dilution_fraction']:.2f}\\% & "
                    f"{100*v['max_dilution_fraction']:.2f}\\% & "
                    f"{v['clips_with_any_dilution']} \\\\")
    for c in I["composition_chain"]:
        rows.append(f"composition depth {c['depth']} & {c['clips']} & "
                    f"{100*c['median_dilution_fraction']:.2f}\\% & "
                    f"{100*c['max_dilution_fraction']:.2f}\\% & --- \\\\")
    for r in I["long_asset_chain"]:
        rows.append(f"same depth-3 chain, {r['asset_seconds']}\\,s asset & 1 & "
                    f"{100*r['dilution_fraction']:.2f}\\% & --- & --- \\\\")
    write("dilution_table", "\n".join(rows), colspec="lrrrr",
          header=("Transformation & Clips & Median dilution & Max dilution & "
                  "Clips affected"))


def overhead_table():
    G = load("G_overhead")
    mins = G["audio_minutes_per_repetition"]
    em, bs = G["em_bookkeeping_ms_per_repetition"], G["baseline_bookkeeping_ms_per_repetition"]
    r = [
        f"EM bookkeeping & {G['em_ms_per_audio_minute']:.3f} ms / audio-minute & "
        f"{em['q1']/mins:.3f}--{em['q3']/mins:.3f} ms / audio-minute \\\\",
        f"Boundary-only bookkeeping & {G['baseline_ms_per_audio_minute']:.3f} ms / audio-minute & "
        f"{bs['q1']/mins:.3f}--{bs['q3']/mins:.3f} ms / audio-minute \\\\",
        f"EM $/$ boundary-only ratio & {G['em_over_baseline_ratio']:.2f}$\\times$ & --- \\\\",
        f"EM as a fraction of FFmpeg time & {100*G['em_over_ffmpeg_fraction']:.3f}\\% & --- \\\\",
        f"C2PA signing & {G['sign_ms']['median']:.1f} ms / asset & "
        f"{G['sign_ms']['q1']:.1f}--{G['sign_ms']['q3']:.1f} \\\\",
        f"C2PA validation & {G['validate_ms']['median']:.1f} ms / asset & "
        f"{G['validate_ms']['q1']:.1f}--{G['validate_ms']['q3']:.1f} \\\\",
        f"Manifest size overhead & {G['median_manifest_overhead_bytes_per_asset']:,} B / asset & "
        f"{int(G['manifest_overhead_bytes']['q1']):,}--{int(G['manifest_overhead_bytes']['q3']):,} \\\\",
        f"EM assertion & {G['median_em_assertion_bytes_per_asset']:,} B / asset & "
        f"{int(G['em_assertion_bytes']['q1']):,}--{int(G['em_assertion_bytes']['q3']):,} \\\\",
    ]
    sc = G["assertion_scaling"]
    per = (sc[-1]["assertion_bytes"] - sc[0]["assertion_bytes"]) / \
          (sc[-1]["emitted_intervals"] - sc[0]["emitted_intervals"])
    r.append(f"EM assertion marginal cost & {per:.0f} B / evidence interval & --- \\\\")
    write("overhead_table", "\n".join(r), colspec="lll",
          header="Quantity & Median & IQR")


if __name__ == "__main__":
    operator_table(); main_results(); transport_table(); ablation_table()
    dilution_table(); overhead_table()
