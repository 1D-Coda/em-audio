"""The two figures added in the visualisation upgrade.

Both are generated entirely from results/machine_readable/. No measured number
is typed here: if a value is absent from the result files the figure fails
rather than being drawn from a remembered figure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import figstyle as S                                              # noqa: E402

MR = ROOT / "results" / "machine_readable"
FIG = ROOT / "results" / "figures"


def load(n):
    p = MR / f"{n}.json"
    if not p.exists():
        raise SystemExit(f"[figure] required data missing: {p}")
    return json.loads(p.read_text())


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(FIG / f"{name}.{ext}")
    plt.close(fig)
    print(f"[figure] results/figures/{name}.pdf")


# --- Figure: declared footprint versus measured dependency reach ------------

def fig_containment():
    """Measured reach against declared footprint.

    The operators span two orders of magnitude, from a 97-sample resampler to a
    4,096-sample silence remover, so a shared linear axis in samples renders the
    smallest declaration as a dot at the origin and hides exactly the row whose
    headroom is tightest. The axis is therefore the measurement expressed as a
    fraction of its own declaration, which is precisely the containment claim:
    every operator is comparable, and a violation is anything crossing 100%.
    Absolute sample counts are carried as direct labels so nothing is lost.
    """
    K = load("K_support_containment")["per_operator"]
    rows = [(k, v) for k, v in K.items() if v["declared_footprint_samples"] > 0]
    rows.sort(key=lambda kv: kv[1]["max_measured_reach_source_samples"] /
              kv[1]["declared_footprint_samples"])
    zeros = [k for k, v in K.items() if v["declared_footprint_samples"] == 0]

    fig, ax = plt.subplots(figsize=(6.4, 2.5), constrained_layout=True)

    ax.axvspan(100, 132, color="#f2dede", alpha=0.55, linewidth=0, zorder=0)
    ax.axvline(100, color=S.BASE, linewidth=1.0, zorder=2)

    for i, (key, v) in enumerate(rows):
        reach = v["max_measured_reach_source_samples"]
        decl = v["declared_footprint_samples"]
        pct = 100.0 * reach / decl
        ax.plot([pct, 100], [i, i], color=S.MARGIN, linewidth=3.0,
                solid_capstyle="round", zorder=1)
        ax.scatter([pct], [i], s=34, marker=S.M_MEASURED, color=S.MEASURED,
                   zorder=4)
        ax.scatter([100], [i], s=34, marker=S.M_DECLARED, facecolor="white",
                   edgecolor=S.DECLARED, linewidth=1.2, zorder=4)
        ax.text(pct - 2.2, i, f"{reach:,}", fontsize=7.2, va="center",
                ha="right", color="#222222")
        ax.text(103.5, i, f"of {decl:,}", fontsize=7.2, va="center",
                color="#555555")

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([S.label_of(k) for k, _ in rows])
    ax.set_xlabel("measured reach as a percentage of the declared footprint")
    ax.set_xlim(0, 132)
    ax.set_ylim(-1.15, len(rows) - 0.42)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.grid(axis="x", linestyle=":", zorder=0)
    ax.set_axisbelow(True)

    top = len(rows) - 1
    tp = (100.0 * rows[top][1]["max_measured_reach_source_samples"] /
          rows[top][1]["declared_footprint_samples"])
    tr = ax.get_xaxis_transform()          # x in data, y in axes fraction
    ax.annotate("measured reach", xy=(tp, 1.005), xytext=(tp - 13, 1.10),
                xycoords=tr, textcoords=tr, fontsize=7.3, ha="center",
                color="#222222", annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6))
    ax.annotate("declaration", xy=(100, 1.005), xytext=(100, 1.10),
                xycoords=tr, textcoords=tr, fontsize=7.3, ha="center",
                color="#222222", annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6))
    ax.text(116, -0.78, "a violation would land in here", fontsize=6.9,
            ha="center", va="center", color=S.BASE)

    outside = sum(v["total_outside_declared_support"] for v in K.values())
    probes = load("K_support_containment").get("total_probes", "")
    ax.set_title(f"Every declaration contains its own measurement "
                 f"({outside} influenced samples fell outside)",
                 fontsize=8.6, loc="left", pad=22)
    if zeros:
        fig.text(0.0, -0.055,
                 "Zero-footprint operators ("
                 + ", ".join(S.label_of(z) for z in sorted(zeros))
                 + ") are omitted: reach and declaration are both zero, so the "
                   "ratio is undefined.",
                 fontsize=6.8, color="#666666")
    save(fig, "fig5_containment")


# --- Figure: the cost of conservatism ---------------------------------------

def fig_dilution():
    I = load("I_claim_dilution")
    per = I["per_transformation"]
    chain = I["composition_chain"]
    longa = I["long_asset_chain"]

    fig, axes = plt.subplots(1, 3, figsize=(7.1, 2.7), constrained_layout=True,
                             gridspec_kw={"width_ratios": [1.5, 1.0, 1.0]})

    # Panel A: single transformation, median with maximum whisker
    ax = axes[0]
    rows = sorted(per.items(), key=lambda kv: kv[1]["median_dilution_fraction"])
    for i, (key, v) in enumerate(rows):
        med = 100 * v["median_dilution_fraction"]
        mx = 100 * v["max_dilution_fraction"]
        if mx > 0:
            ax.plot([med, mx], [i, i], color=S.MARGIN, linewidth=2.6,
                    solid_capstyle="round", zorder=1)
            ax.scatter([mx], [i], s=12, marker="|", color="#8a8a8a", zorder=3)
            ax.scatter([med], [i], s=26, marker=S.M_MEASURED, color=S.MEASURED,
                       zorder=4)
            if mx < 3:            # too small to read off the axis
                ax.text(mx + 1.6, i, f"{med:.2f}% median", fontsize=6.8,
                        va="center", color="#555555")
        else:
            S.zero_marker(ax, 0, i, colour=S.MEASURED, marker=S.M_MEASURED,
                          size=22)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([S.label_of(k) for k, _ in rows], fontsize=7.2)
    ax.set_xlabel("output samples diluted (%)")
    ax.set_xlim(-3, 62)
    ax.grid(axis="x", linestyle=":")
    ax.set_axisbelow(True)
    S.panel_tag(ax, "A", dx=-0.34)
    ax.text(0.98, 0.04, "dot: median\nbar: maximum\nopen: exact zero",
            transform=ax.transAxes, fontsize=6.8, ha="right", va="bottom",
            color="#555555", linespacing=1.4)

    # Panel B: dilution through composition depth
    ax = axes[1]
    d = [r["depth"] for r in chain]
    med = [100 * r["median_dilution_fraction"] for r in chain]
    mx = [100 * r["max_dilution_fraction"] for r in chain]
    ax.fill_between(d, med, mx, color=S.MARGIN, alpha=0.75, linewidth=0,
                    zorder=1)
    ax.plot(d, mx, color="#9a9a9a", linewidth=0.8, linestyle=(0, (3, 2)),
            zorder=2)
    ax.plot(d, med, color=S.MEASURED, marker=S.M_MEASURED, markersize=3.6,
            zorder=3)
    ax.set_xlabel("composition depth")
    ax.set_ylabel("diluted (%)")
    ax.set_xticks(d)
    ax.set_ylim(-4, 108)
    ax.grid(axis="y", linestyle=":")
    ax.set_axisbelow(True)
    S.panel_tag(ax, "B", dx=-0.20)
    ax.set_xlim(0.6, 6.9)
    ax.annotate("maximum", xy=(d[-1], mx[-1]), xytext=(7, 3),
                textcoords="offset points", fontsize=6.9, ha="left",
                color="#777777")
    ax.annotate("median", xy=(d[-1], med[-1]), xytext=(7, -4),
                textcoords="offset points", fontsize=6.9, ha="left",
                color="#222222")
    flat = [i for i in range(1, len(d))
            if abs(med[i] - med[i - 1]) < 1e-9 and med[i] > 0]
    if flat:
        i = flat[0]
        ax.annotate("normalisation adds\nnone; its declared\nfootprint is zero",
                    xy=(d[i], med[i]), xytext=(4.35, 21),
                    fontsize=6.6, ha="left", va="center", color="#444444",
                    linespacing=1.3,
                    arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6))

    # Panel C: one fixed chain, longer assets
    ax = axes[2]
    secs = [r["asset_seconds"] for r in longa]
    frac = [100 * r["dilution_fraction"] for r in longa]
    ax.plot(secs, frac, color=S.MEASURED, marker=S.M_MEASURED, markersize=3.8,
            zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("asset duration (s, log)")
    ax.set_ylabel("diluted (%, log)")
    ax.grid(True, which="major", linestyle=":")
    ax.set_axisbelow(True)
    offsets = [(7, 4), (7, 5), (-4, -11)]
    aligns = ["left", "left", "right"]
    for (x, y), off, ha in zip(zip(secs, frac), offsets, aligns):
        ax.annotate(f"{y:.2f}%", xy=(x, y), xytext=off,
                    textcoords="offset points", fontsize=6.9, ha=ha,
                    color="#444444")
    S.panel_tag(ax, "C", dx=-0.20)
    ax.set_ylim(min(frac) * 0.42, max(frac) * 2.6)
    # The explanation of this trend belongs in the caption: a three-line note
    # cannot sit in a panel this size without landing on the curve or on a data
    # label, and cramming it in would cost the legibility it is meant to add.

    save(fig, "fig6_dilution")


if __name__ == "__main__":
    S.apply()
    fig_containment()
    fig_dilution()
