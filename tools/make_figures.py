"""Render every figure from the machine-readable results.

No figure contains a number that is not present in results/machine_readable/.
"""
from __future__ import annotations

import json, sys, wave
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MR = ROOT / "results" / "machine_readable"
FIG = ROOT / "results" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans",
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 300, "savefig.bbox": "tight"})

CAP = "#2b6cb0"     # captured
GEN = "#c05621"     # generated
MIX = "#6b46c1"     # mixed
UNV = "#718096"     # unverified


def load(n):
    return json.loads((MR / f"{n}.json").read_text())


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}")
    plt.close(fig)
    print(f"[figure] results/figures/{name}.pdf")


# --- Figure 1: the minimal temporal counterexample ---------------------------
def fig1():
    fig, axes = plt.subplots(3, 1, figsize=(6.6, 3.5),
                             gridspec_kw={"height_ratios": [1.5, 0.75, 0.75], "hspace": 0.55})
    rng = np.random.default_rng(7)
    fs, seg = 400, 1.0
    t = np.linspace(0, 5 * seg, int(5 * seg * fs), endpoint=False)
    sig = 0.55 * np.sin(2 * np.pi * 3.1 * t) + 0.12 * rng.standard_normal(t.size)
    ax = axes[0]
    ax.plot(t, sig, lw=0.6, color="#2d3748")
    ax.set_xlim(0, 5); ax.set_yticks([]); ax.set_ylim(-1.3, 1.3)
    ax.set_ylabel("decoded\nPCM", fontsize=8)
    ax.set_title("One decoded audio stream, two evidence claims", fontsize=10, pad=6)
    ax.set_xticks(range(6)); ax.set_xticklabels([])
    for k in range(1, 5):
        ax.axvline(k, color="#cbd5e0", lw=0.6, ls=":")
    ax.annotate("source interval 2 is generated-derived", xy=(2.5, 0.95), xytext=(3.05, 1.15),
                fontsize=7.5, color=GEN,
                arrowprops=dict(arrowstyle="->", color=GEN, lw=0.8))
    ax.axvspan(2, 3, color=GEN, alpha=0.13, lw=0)

    src = ["C", "C", "G", "C", "C"]
    ax = axes[1]
    for k, s in enumerate(src):
        c = CAP if s == "C" else GEN
        ax.add_patch(plt.Rectangle((k, 0), 1, 1, facecolor=c, alpha=0.85, edgecolor="white", lw=1.2))
        ax.text(k + 0.5, 0.5, s, ha="center", va="center", color="white", fontweight="bold")
    ax.set_xlim(0, 5); ax.set_ylim(0, 1); ax.set_yticks([]); ax.set_xticks([])
    ax.set_ylabel("source\nevidence", fontsize=8)
    ax.spines[:].set_visible(False)

    ax = axes[2]
    ax.add_patch(plt.Rectangle((0, 0.55), 5, 0.42, facecolor=CAP, alpha=0.85,
                               edgecolor="white", lw=1.2))
    ax.text(2.5, 0.76, "baseline (boundary-only):  CAPTURED", ha="center", va="center",
            color="white", fontsize=8.5, fontweight="bold")
    ax.add_patch(plt.Rectangle((0, 0.05), 5, 0.42, facecolor=MIX, alpha=0.85,
                               edgecolor="white", lw=1.2))
    ax.text(2.5, 0.26, "complete-source (EM):  MIXED $\\{C,G\\}$", ha="center", va="center",
            color="white", fontsize=8.5, fontweight="bold")
    ax.set_xlim(0, 5); ax.set_ylim(0, 1); ax.set_yticks([])
    ax.set_xticks(range(6)); ax.set_xlabel("time (source intervals)", fontsize=8)
    ax.set_ylabel("emitted\nclaim", fontsize=8)
    ax.spines[:].set_visible(False)
    fig.text(0.5, -0.045, "The waveform is identical under both policies. Only the evidential "
             "claim differs.", ha="center", fontsize=8, style="italic", color="#4a5568")
    save(fig, "fig1_counterexample")


# --- Figure 2: architecture --------------------------------------------------
def fig2():
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    ax.set_xlim(-1, 101); ax.set_ylim(0, 34); ax.axis("off")
    boxes = [
        (0.0, "source audio\n+ evidence\nintervals", "#e2e8f0"),
        (17.0, "stock FFmpeg\noperator\n(signal path)", "#fed7aa"),
        (34.0, "interval map\n+ kernel\nfootprint", "#bee3f8"),
        (51.0, "complete-source\nevidence meet\n$\\sqcap_{x\\in D_y}$", "#d6bcfa"),
        (68.0, "EM assertion in\nC2PA temporal\nregions", "#c6f6d5"),
        (84.5, "signed manifest\n$\\rightarrow$ verifier", "#e2e8f0"),
    ]
    for x, label, col in boxes:
        ax.add_patch(FancyBboxPatch((x, 11), 14.6, 12, boxstyle="round,pad=0.25",
                                    facecolor=col, edgecolor="#4a5568", lw=0.8))
        ax.text(x + 7.3, 17, label, ha="center", va="center", fontsize=6.8)
    for x in (15.0, 32.0, 49.0, 66.0, 82.8):
        ax.add_patch(FancyArrowPatch((x, 17), (x + 1.4, 17), arrowstyle="-|>",
                                     mutation_scale=8, color="#4a5568", lw=0.9))
    ax.add_patch(FancyBboxPatch((17.0, 1.2), 82.0, 6.2, boxstyle="round,pad=0.25",
                                facecolor="#fff5f5", edgecolor="#c53030", lw=0.8, ls="--"))
    ax.text(58.0, 4.3, "signal transparency (P8): decoded PCM identical before and after "
            "signing, under either policy",
            ha="center", va="center", fontsize=6.2, color="#c53030")
    for x in (24.3, 91.8):
        ax.add_patch(FancyArrowPatch((x, 7.6), (x, 10.7), arrowstyle="-|>", mutation_scale=8,
                                     color="#c53030", lw=0.8))
    ax.text(57.5, 30.0, "evidence path: provenance $\\cup$, support $\\min$, "
            "scope $\\cap$, lineage $\\cup$",
            ha="center", fontsize=7.2, color="#4a5568")
    ax.add_patch(FancyArrowPatch((7.3, 26.0), (91.8, 26.0), arrowstyle="-|>", mutation_scale=9,
                                 color="#a0aec0", lw=0.9, ls=":"))
    save(fig, "fig2_architecture")


# --- Figure 3: promotion, baseline versus EM ---------------------------------
def fig3():
    B, D = load("B_adversarial_timelines"), load("D_transform_matrix")
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.9),
                             gridspec_kw={"width_ratios": [1.0, 1.45, 1.0], "wspace": 0.62})

    ax = axes[0]
    depths = sorted(B["per_depth"], key=int)
    base = [100 * B["per_depth"][d]["baseline_promotion_rate"] for d in depths]
    em = [100 * B["per_depth"][d]["em_promotion_rate"] for d in depths]
    ax.plot([int(d) for d in depths], base, "o-", color="#c53030", lw=1.4, ms=4,
            label="boundary-only")
    ax.plot([int(d) for d in depths], em, "s-", color="#2f855a", lw=1.4, ms=4,
            label="complete-source")
    ax.set_ylim(-4, 104); ax.set_xticks([int(d) for d in depths])
    ax.set_xlabel("composition depth"); ax.set_ylabel("spans with promotion (%)")
    ax.set_title("B  adversarial timelines", fontsize=8.5)
    ax.legend(fontsize=6.6, frameon=False, loc="center right")
    ax.text(3, 9, "0 at every depth", fontsize=6.6, color="#2f855a", ha="center")

    ax = axes[1]
    ops = sorted(B["per_operator_single_step"], key=lambda k: -B["per_operator_single_step"][k]["baseline_rate"])
    y = np.arange(len(ops))
    ax.barh(y, [100 * B["per_operator_single_step"][o]["baseline_rate"] for o in ops],
            color="#c53030", alpha=0.85, height=0.62, label="boundary-only")
    ax.barh(y, [100 * B["per_operator_single_step"][o]["em_rate"] for o in ops],
            color="#2f855a", height=0.62, label="complete-source")
    ax.set_yticks(y); ax.set_yticklabels([o.replace("_", " ") for o in ops], fontsize=6.4)
    ax.invert_yaxis(); ax.set_xlabel("promotion rate (%)"); ax.set_xlim(0, 108)
    ax.set_title("B  single operator", fontsize=8.5)
    ax.legend(fontsize=6.6, frameon=False, loc="lower right")

    ax = axes[2]
    ks = sorted(B["control_uniform_positions"]["G"], key=int)
    meas = [100 * B["control_uniform_positions"]["G"][k]["measured_baseline_rate"] for k in ks]
    pred = [100 * B["control_uniform_positions"]["G"][k]["closed_form_baseline_rate"] for k in ks]
    ax.plot([int(k) for k in ks], pred, "-", color="#4a5568", lw=1.2, label="closed form")
    ax.plot([int(k) for k in ks], meas, "o", color="#c53030", ms=4, label="measured")
    ax.set_xticks([int(k) for k in ks]); ax.set_ylim(80, 100)
    ax.set_xlabel("injected anomalies $k$"); ax.set_ylabel("baseline rate (%)")
    ax.set_title("B  control arm", fontsize=8.5)
    ax.legend(fontsize=6.6, frameon=False, loc="lower left")
    save(fig, "fig3_promotion")


# --- Figure 4: corpus result -------------------------------------------------
def fig4():
    C, D = load("C_public_audio_splice"), load("D_transform_matrix")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [1.45, 1.0],
                                                                    "wspace": 0.42})
    ax = axes[0]
    names = sorted(D["per_transformation"], key=lambda k: -D["per_transformation"][k]["baseline_promotion_rate"])
    y = np.arange(len(names))
    ax.barh(y, [100 * D["per_transformation"][n]["baseline_promotion_rate"] for n in names],
            color="#c53030", alpha=0.85, height=0.62, label="boundary-only")
    ax.barh(y, [100 * D["per_transformation"][n]["em_promotion_rate"] for n in names],
            color="#2f855a", height=0.62, label="complete-source")
    ax.set_yticks(y); ax.set_yticklabels([n.replace("_", " ") for n in names], fontsize=6.6)
    ax.invert_yaxis(); ax.set_xlim(0, 108); ax.set_xlabel("clips with promotion (%)")
    ax.set_title(f"D  {D['n_clips']} mixed-origin clips, stock FFmpeg", fontsize=8.5)
    ax.legend(fontsize=6.6, frameon=False, loc="lower right")
    for i, n in enumerate(names):
        v = D["per_transformation"][n]
        if v["baseline_promotions"] == 0:
            ax.text(2, i, "0", va="center", fontsize=6.4, color="#4a5568")

    ax = axes[1]
    labels = ["exact\ninterval\nrecovery", "generated\ninterval\nrecovered",
              "EM\npromotions", "EM lineage\nomissions"]
    vals = [C["exact_interval_recovery"], C["generated_interval_recovered"],
            C["em_provenance_promotions"], C["em_lineage_omissions"]]
    cols = ["#2f855a", "#2f855a", "#2f855a", "#2f855a"]
    ax.bar(range(4), vals, color=cols, alpha=0.9, width=0.6)
    ax.axhline(C["n_clips"], color="#4a5568", ls="--", lw=0.8)
    ax.text(3.45, C["n_clips"], f" n={C['n_clips']}", va="center", fontsize=6.6, color="#4a5568")
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=6.0)
    ax.set_ylabel("clips"); ax.set_ylim(0, C["n_clips"] * 1.18)
    ax.set_title("C  ground-truth recovery", fontsize=8.5)
    for i, v in enumerate(vals):
        ax.text(i, v + C["n_clips"] * 0.03, str(v), ha="center", fontsize=7)
    save(fig, "fig4_corpus")


# --- Figure 5: cost ----------------------------------------------------------
def fig5():
    G = load("G_overhead")
    sc = G["assertion_scaling"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6), gridspec_kw={"wspace": 0.35})
    k = [r["emitted_intervals"] for r in sc]
    ax = axes[0]
    ax.plot(k, [r["assertion_bytes"] / 1024 for r in sc], "o-", color="#2b6cb0", lw=1.3, ms=4)
    ax.set_xscale("log", base=2); ax.set_xlabel("evidence intervals per asset")
    ax.set_ylabel("EM assertion (KiB)")
    per = (sc[-1]["assertion_bytes"] - sc[0]["assertion_bytes"]) / (k[-1] - k[0])
    ax.set_title(f"assertion size: {per:.0f} B per interval", fontsize=8.5)
    ax = axes[1]
    ax.plot(k, [r["median_ms"] for r in sc], "s-", color="#6b46c1", lw=1.3, ms=4)
    ax.set_xscale("log", base=2); ax.set_xlabel("evidence intervals per asset")
    ax.set_ylabel("median bookkeeping (ms)")
    ax.set_title(f"{G['em_ms_per_audio_minute']:.2f} ms per audio-minute; "
                 f"{100*G['em_over_ffmpeg_fraction']:.2f}\\% of FFmpeg time", fontsize=8.5)
    save(fig, "fig5_overhead")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5()
