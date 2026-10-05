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
    # An upstream experiment that failed leaves its result file absent, and
    # reading it then raised FileNotFoundError from inside pathlib. That is
    # what an independent reproducer saw: seven frames of the standard library
    # and no mention of the step that actually failed, several screens above.
    p = MR / f"{n}.json"
    if not p.exists():
        raise SystemExit(
            f"[figure] {p.name} is missing, so the experiment that writes it "
            f"did not finish. This is a consequence, not the cause: look "
            f"further up the log, or run "
            f"`python3 tools/explain_failure.py run_all_output.txt`.")
    return json.loads(p.read_text(encoding="utf-8"))


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
    ax.set_ylabel("illustrative\nsignal", fontsize=8)
    ax.set_title("One audio stream, two whole-asset claims", fontsize=10, pad=6)
    ax.set_xticks(range(6)); ax.set_xticklabels([])
    for k in range(1, 5):
        ax.axvline(k, color="#cbd5e0", lw=0.6, ls=":")
    ax.annotate("third source interval [2,3) is generated-derived", xy=(2.5, 0.95), xytext=(3.05, 1.15),
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
    ax.set_ylabel("whole-asset\nclaim", fontsize=8)
    ax.spines[:].set_visible(False)
    fig.text(0.5, -0.045, "Illustrative signal, not a corpus clip. The waveform is identical under both "
             "policies; only the evidential claim differs.", ha="center", fontsize=8, style="italic", color="#4a5568")
    save(fig, "fig1_counterexample")


# --- Figure 2: architecture --------------------------------------------------
def fig2():
    # Two lanes, so the audio and the evidence are visibly separate paths that
    # meet only at signing, and a third row for what a consumer does with the
    # signed result.
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.set_xlim(-1, 101); ax.set_ylim(0, 48); ax.axis("off")

    def box(x, y, w, label, col):
        ax.add_patch(FancyBboxPatch((x, y), w, 8.6, boxstyle="round,pad=0.25",
                                    facecolor=col, edgecolor="#4a5568", lw=0.8))
        ax.text(x + w / 2, y + 4.3, label, ha="center", va="center", fontsize=6.6)

    def arrow(x0, y0, x1, y1, col="#4a5568", ls="-"):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                     mutation_scale=8, color=col, lw=0.9, ls=ls))

    ax.text(-0.5, 44.5, "audio path", fontsize=7.0, color="#4a5568", style="italic")
    box(0, 34, 16, "source audio", "#e2e8f0")
    box(22, 34, 18, "stock FFmpeg\noperator", "#fed7aa")
    box(46, 34, 16, "derived audio", "#e2e8f0")
    arrow(16.6, 38.3, 21.6, 38.3); arrow(40.6, 38.3, 45.6, 38.3)

    ax.text(-0.5, 28.0, "evidence path", fontsize=7.0, color="#4a5568", style="italic")
    box(0, 17, 16, "source evidence\nintervals", "#e2e8f0")
    box(22, 17, 18, "interval map +\nfootprints, fitted\nto decoded length", "#bee3f8")
    box(46, 17, 16, "complete-source\nmeet $\\sqcap_{x\\in D_y}$", "#d6bcfa")
    box(68, 17, 15, "assertion +\ndependency\ndeclaration", "#c6f6d5")
    arrow(16.6, 21.3, 21.6, 21.3); arrow(40.6, 21.3, 45.6, 21.3); arrow(62.6, 21.3, 67.6, 21.3)

    box(86, 25.5, 14, "signed C2PA\nmanifest", "#e2e8f0")
    arrow(62.6, 38.3, 92.8, 34.6); arrow(83.6, 22.5, 88.0, 25.2)
    arrow(48.0, 33.6, 36.0, 26.0, col="#a0aec0", ls=":")
    ax.text(43.5, 29.8, "decoded length", fontsize=6.0, color="#718096")

    ax.text(-0.5, 10.8, "consumer", fontsize=7.0, color="#4a5568", style="italic")
    box(44, 0.5, 40, "decode the asset; rebuild the declared map;\n"
        "recompute every claim and report the verdict", "#fefcbf")
    arrow(93.0, 25.0, 83.6, 6.0)

    ax.text(0, 3.4, "signal transparency (P8): decoded PCM identical\nbefore and after signing, "
            "under either policy", fontsize=6.1, color="#c53030", va="center")
    save(fig, "fig2_architecture")


# --- Figure 3: promotion, baseline versus EM ---------------------------------

# --- Figure 4: corpus result -------------------------------------------------

# --- Figure 5: cost ----------------------------------------------------------
def fig5():
    G = load("G_overhead")
    sc = G["assertion_scaling"]
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.6), gridspec_kw={"wspace": 0.35})
    k = [r["emitted_intervals"] for r in sc]
    per = (sc[-1]["assertion_bytes"] - sc[0]["assertion_bytes"]) / (k[-1] - k[0])
    per_ms = (sc[-1]["median_ms"] - sc[0]["median_ms"]) / (k[-1] - k[0])

    # Linear axes on both: the claim under test is that cost is LINEAR in the
    # number of evidence intervals, and only linear axes let a reader check that
    # by eye.  A log x-axis renders a straight line as an exploding curve and
    # would argue against the very claim the panel supports.
    ax = axes[0]
    ax.plot(k, [r["assertion_bytes"] / 1024 for r in sc], "o", color="#2b6cb0", ms=4,
            label="measured")
    ax.plot([0, k[-1]], [sc[0]["assertion_bytes"] / 1024 - per * (sc[0]["emitted_intervals"]) / 1024,
                         (sc[0]["assertion_bytes"] + per * (k[-1] - k[0])) / 1024],
            "-", color="#a0aec0", lw=1.0, zorder=0, label="linear fit")
    ax.set_xlabel("evidence intervals per asset")
    ax.set_ylabel("EM assertion (KiB)")
    ax.set_xlim(0, k[-1] * 1.04); ax.set_ylim(0, None)
    ax.set_title(f"assertion size: {per:.0f} B per interval", fontsize=8.5)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left")

    ax = axes[1]
    ax.plot(k, [r["median_ms"] for r in sc], "s", color="#6b46c1", ms=4, label="measured")
    ax.plot([0, k[-1]], [sc[0]["median_ms"] - per_ms * sc[0]["emitted_intervals"],
                         sc[0]["median_ms"] + per_ms * (k[-1] - k[0])],
            "-", color="#a0aec0", lw=1.0, zorder=0, label="linear fit")
    ax.set_xlabel("evidence intervals per asset")
    ax.set_ylabel("median bookkeeping (ms)")
    ax.set_xlim(0, k[-1] * 1.04); ax.set_ylim(0, None)
    ax.set_title(f"{G['em_ms_per_audio_minute']:.2f} ms per audio-minute; "
                 f"{100*G['em_over_ffmpeg_fraction']:.2f}% of FFmpeg time", fontsize=8.5)
    ax.legend(fontsize=6.6, frameon=False, loc="upper left")
    save(fig, "fig7_overhead")


if __name__ == "__main__":
    # fig3 to fig6 are built by tools/make_figures_shared.py, which uses the
    # shared palette in tools/figstyle.py
    fig1(); fig2(); fig5()
