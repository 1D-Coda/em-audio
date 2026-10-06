"""The figures built on the shared visual language in tools/figstyle.py.

Four of the seven generated figures live here: adversarial validation, the
mixed-origin corpus, kernel-support containment and claim dilution. The
remaining three, the counterexample, the architecture diagram and the cost
scaling, are in tools/make_figures.py; the manuscript prints the first six.

Every figure is generated entirely from results/machine_readable/. No measured
number is typed here: if a value is absent from the result files the figure
fails rather than being drawn from a remembered one.
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


# --- Figure: promotion on the mixed-origin corpus ---------------------------

def fig_corpus():
    """Per-transformation promotion, as a paired row rather than as bars.

    Six baseline values sit at 100%, two at zero, and complete-source is zero
    everywhere, so a bar chart spends its whole width restating that most bars
    are full and draws the series that matters as nothing at all. The pair of
    marks per row makes the comparison the gap, and the counts are written
    directly so the reader does not have to read a rate off an axis.
    """
    D = load("D_transform_matrix")
    per = D["per_transformation"]
    n = D["n_clips"]
    rows = sorted(per, key=lambda k: (-per[k]["baseline_promotion_rate"], k))

    # Two panels, because the promotion count alone is the least informative
    # quantity this experiment produced: six identical values, two structural
    # zeros and a series that is zero throughout. The uniformity is the result
    # and is not made truer by decoration. What the run also measured, and never
    # showed, is why it happens: the boundary-only policy collapses a
    # five-interval timeline into one claim, and an interval that no longer
    # exists cannot carry the evidence that contradicts the endpoints.
    fig, axd = plt.subplot_mosaic([["outcome", "outcome"], ["why", "why"]],
                                  figsize=(6.9, 5.8), constrained_layout=True,
                                  height_ratios=[1.0, 0.86])
    ax = axd["outcome"]

    for i, key in enumerate(rows):
        b = 100 * per[key]["baseline_promotion_rate"]
        e = 100 * per[key]["em_promotion_rate"]
        bn, en = per[key]["baseline_promotions"], per[key]["em_promotions"]
        if b > 0:
            ax.plot([e, b], [i, i], color=S.MARGIN, linewidth=3.0,
                    solid_capstyle="round", zorder=1)
            ax.scatter([b], [i], s=36, marker=S.M_BASE, color=S.BASE, zorder=4)
            ax.text(b + 3.0, i, f"{bn:,}/{n:,}", fontsize=7.2, va="center",
                    color=S.BASE)
        else:
            # A zero in this corpus, which depends on where its retained
            # boundaries fall; it is not a property of the operator.
            ax.scatter([b], [i], s=36, marker=S.M_BASE, facecolor="white",
                       edgecolor=S.BASE, linewidth=1.2, zorder=4)
            ax.text(4.0, i, f"{bn}/{n:,} whole output", fontsize=7.0,
                    va="center", color="#777777")
        ax.scatter([e], [i], s=36, marker=S.M_EM, facecolor="white",
                   edgecolor=S.EM, linewidth=1.2, zorder=5)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([S.label_of(k) for k in rows], fontsize=7.8)
    ax.set_xlabel("clips with promotion (%)")
    ax.set_xlim(-6, 128)
    ax.set_ylim(-0.7, len(rows) - 0.30)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.grid(axis="x", linestyle=":", zorder=0)
    ax.set_axisbelow(True)

    tr = ax.get_xaxis_transform()
    ax.annotate("complete-source", xy=(0, 1.005), xytext=(0, 1.085),
                xycoords=tr, textcoords=tr, fontsize=7.3, color=S.EM,
                ha="left", annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6))
    ax.annotate("boundary-only", xy=(100, 1.005), xytext=(100, 1.085),
                xycoords=tr, textcoords=tr, fontsize=7.3, color=S.BASE,
                ha="center", annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6))

    tot_b = sum(per[k]["baseline_promotions"] for k in per)
    tot_e = sum(per[k]["em_promotions"] for k in per)
    tot_runs = n * len(per)
    ax.set_title(f"Boundary-only promoted in {tot_b:,} of {tot_runs:,} "
                 f"transformation runs; complete-source in {tot_e:,}",
                 fontsize=8.6, loc="left", pad=26)
    S.panel_tag(ax, "A", dx=-0.055)

    # Panel B: the same runs scored per interval, on both corpora. A correct
    # whole-output MIXED claim can still hide intervals that claim more than
    # their sources, so the interval-level count is the contract's own endpoint.
    ax = axd["why"]
    Qf = MR / "Q_partialspoof_matrix.json"
    corpora = [("ours", per)]
    if Qf.exists():
        corpora.append(("PartialSpoof", json.loads(Qf.read_text())["per_transformation"]))
    Rf = MR / "R_partialedit_matrix.json"
    if Rf.exists():
        corpora.append(("PartialEdit", json.loads(Rf.read_text())["per_transformation"]))
    off = {0: -0.24, 1: 0.0, 2: 0.24} if len(corpora) == 3 else {0: -0.17, 1: 0.17}
    shapes = [S.M_BASE, "s", "^"]
    for ci, (lab, pt) in enumerate(corpora):
        for i, key in enumerate(rows):
            v = pt.get(key)
            if not v or "baseline_either_promotions" not in v:
                continue
            w = 100 * v["baseline_promotions"] / v["n"]
            a = 100 * v["baseline_either_promotions"] / v["n"]
            y = i + off[ci]
            ax.plot([w, a], [y, y], color=S.MARGIN, linewidth=2.4,
                    solid_capstyle="round", zorder=1)
            ax.scatter([w], [y], s=24, marker=shapes[ci],
                       color=S.BASE, zorder=4)
            ax.scatter([a], [y], s=24, marker=shapes[ci],
                       facecolor="white", edgecolor=S.BASE, linewidth=1.1, zorder=5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([S.label_of(k) for k in rows], fontsize=7.4)
    ax.set_xlabel("boundary-only runs with promotion (%): filled, whole output; "
                  "open, any interval", fontsize=7.6)
    ax.set_xlim(-6, 106)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.grid(axis="x", linestyle=":", zorder=0)
    ax.set_axisbelow(True)
    S.panel_tag(ax, "B", dx=-0.055)
    names = ", ".join(f"{['circles', 'squares', 'triangles'][i]} {lab}"
                      for i, (lab, _) in enumerate(corpora))
    ax.set_title(f"Whole-output versus interval-level promotion ({names})",
                 fontsize=8.4, loc="left", pad=8)

    save(fig, "fig4_corpus")


# --- Figure: declared footprint versus measured dependency reach ------------

def fig_containment():
    """Measured reach against the declared footprint, every recorded run.

    One row per operator with a non-zero declaration, the reach of each run as a
    percentage of its declaration on a logarithmic axis, and the exact values in
    a table beneath. Every run on record is drawn, not a chosen pair, and the
    holdout challenge on the reference build is drawn beside them, because it is
    the measurement that shows where a declaration stops holding. A reproduction
    package carries neither the independent runs nor K2; the figure then draws
    what is present and says so in its title.
    """
    import math
    ops = [("resample_16_8", "resample 16 to 8 kHz"),
           ("transcode_mp3", "transcode to MP3"),
           ("time_stretch_1.10", "time stretch 1.10"),
           ("silence_removal", "retained-run selection")]
    runs = [("reference build", "o", S.MEASURED, MR / "K_support_containment.json")]
    for label, marker, colour, sub in [
            ("independent macOS", "s", "#5b5b5b", "independent_mac"),
            ("independent Windows", "^", "#2c6fb0", "independent_windows"),
            ("independent Linux", "X", S.BASE, "independent")]:
        f = ROOT / "results" / sub / "machine_readable" / "K_support_containment.json"
        if f.exists():
            runs.append((label, marker, colour, f))
    data = [(lab, mk, col, json.loads(f.read_text())["per_operator"]) for lab, mk, col, f in runs]
    K2F = MR / "K2_footprint_holdout.json"
    hold = json.loads(K2F.read_text())["per_operator"] if K2F.exists() else None
    decl = {k: data[0][3][k]["declared_footprint_samples"] for k, _ in ops}

    def pct(reach, d):
        return 100.0 * max(reach, 1) / d

    fig = plt.figure(figsize=(6.8, 4.6))
    ax = fig.add_axes([0.25, 0.47, 0.72, 0.43])
    ys = list(range(len(ops)))[::-1]
    offs = [0.24, 0.08, -0.08, -0.24][:len(data)]
    allx = []
    for (lab, mk, col, po), dy in zip(data, offs):
        xs = [pct(po[k]["max_measured_reach_source_samples"], decl[k]) for k, _ in ops]
        allx += xs
        ax.scatter(xs, [y + dy for y in ys], marker=mk, s=30, color=col, zorder=4,
                   label=lab, linewidths=0)
    if hold:
        hx = [pct(hold[k]["max_measured_reach_source_samples"], decl[k]) for k, _ in ops]
        allx += hx
        ax.scatter(hx, ys, marker="*", s=95, facecolor="white", edgecolor=S.BASE,
                   linewidth=1.1, zorder=5, label="holdout, reference build")
    xmax = max(130.0, max(allx) * 1.6)
    ax.set_xscale("log")
    ax.set_xlim(20, xmax)
    ax.axvspan(100, xmax, color="#f6e3e3", alpha=0.6, linewidth=0, zorder=0)
    ax.axvline(100, color=S.BASE, linestyle=(0, (4, 2)), linewidth=1.0, zorder=2)
    ticks = [t for t in (25, 50, 100, 200, 400, 800) if t < xmax]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{t}" for t in ticks])
    ax.minorticks_off()
    ax.set_yticks(ys)
    ax.set_yticklabels([lab for _, lab in ops], fontsize=8.0)
    ax.set_ylim(-0.6, len(ops) - 0.4)
    ax.set_xlabel("measured reach as % of the declared footprint (log)", fontsize=8.0)
    ax.tick_params(axis="x", labelsize=7.5)
    ax.grid(axis="x", linestyle=":", zorder=0)
    ax.text(100 * 1.04, len(ops) - 0.48, "exceeds the declaration", fontsize=7.2,
            color=S.BASE, va="bottom", ha="left")
    ax.legend(loc="lower center", bbox_to_anchor=(0.42, 1.02), ncol=3 if hold else len(data),
              fontsize=7.2, frameon=False, handletextpad=0.3, columnspacing=1.0)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)

    # Exact values beneath: the plot shows where each run falls, the table what
    # it measured, in source samples.
    cols = ["declared"] + [lab.replace("independent ", "ind. ").replace(" build", "")
                           for lab, *_ in data] + (["holdout"] if hold else [])
    rows = []
    for k, _ in ops:
        r = [f"{decl[k]:,}"] + [f"{po[k]['max_measured_reach_source_samples']:,}" for *_, po in data]
        if hold:
            r.append(f"{hold[k]['max_measured_reach_source_samples']:,}")
        rows.append(r)
    tab = fig.add_axes([0.25, 0.02, 0.72, 0.30]); tab.axis("off")
    tb = tab.table(cellText=rows, rowLabels=[lab for _, lab in ops], colLabels=cols,
                   loc="center", cellLoc="right", rowLoc="right", edges="horizontal")
    tb.auto_set_font_size(False); tb.set_fontsize(7.4); tb.scale(1.0, 1.25)
    for (r, c), cell in tb.get_celld().items():
        if r == 0:
            cell.set_text_props(fontweight="bold")
        if r > 0 and c >= 1:
            k = ops[r - 1][0]
            v = int(cell.get_text().get_text().replace(",", ""))
            if v > decl[k]:
                cell.set_text_props(color=S.BASE, fontweight="bold")
    fig.text(0.25, 0.335, "reach in source samples; red: exceeds the declaration",
             fontsize=7.0, color="#555555")
    # No title in the figure: the caption carries it, as the journal requires.
    save(fig, "fig5_containment")


# --- Figure: adversarial validation -----------------------------------------

def fig_adversarial():
    """Experiment B, in three panels.

    The middle panel was a bar chart in which every bar reached past 90%, which
    spends most of its width restating that the baseline promotes almost always
    and leaves the complete-source series with no extent to draw. It is now a
    paired row per operator, so the comparison is the gap between two marks and
    the zero is a mark rather than an absence.
    """
    B = load("B_adversarial_timelines")
    # Three panels in a row give each about a third of the width, which is not
    # enough for the nine operator labels in panel B. The two small line panels
    # share the top row and the label-hungry panel takes the full width below.
    fig, axd = plt.subplot_mosaic([["A", "C"], ["B", "B"]],
                                  figsize=(7.0, 5.0), constrained_layout=True,
                                  height_ratios=[1.0, 1.25])

    # Panel A: promotion against composition depth
    ax = axd["A"]
    depths = sorted(B["per_depth"], key=int)
    xs = [int(d) for d in depths]
    base = [100 * B["per_depth"][d]["baseline_promotion_rate"] for d in depths]
    em = [100 * B["per_depth"][d]["em_promotion_rate"] for d in depths]
    ax.plot(xs, base, marker=S.M_BASE, color=S.BASE, lw=1.3, ms=4.2, zorder=3)
    ax.plot(xs, em, marker=S.M_EM, color=S.EM, lw=1.3, ms=4.0,
            markerfacecolor="white", markeredgewidth=1.1, zorder=3)
    ax.set_ylim(-6, 112)
    ax.set_xlim(0.6, 5.4)
    ax.set_xticks(xs)
    ax.set_xlabel("composition depth")
    ax.set_ylabel("spans with promotion (%)")
    ax.grid(axis="y", linestyle=":")
    ax.set_axisbelow(True)
    ax.annotate("boundary-only", xy=(xs[1], base[1]), xytext=(0, 10),
                textcoords="offset points", fontsize=7.0, color=S.BASE,
                ha="center")
    # Placed in the empty band between the two series, with a leader, rather
    # than beside the marks it describes: at this scale the two series sit at
    # the extremes of the axis and any label level with the zero line lands on
    # top of it.
    ax.annotate("complete-source:\n0 at every depth", xy=(3, em[2]),
                xytext=(3, 34), fontsize=7.0, color=S.EM, ha="center",
                va="center", linespacing=1.35,
                arrowprops=dict(arrowstyle="-", color=S.EM, lw=0.6))
    ax.set_title("adversarial timelines", fontsize=8.4, loc="left")
    S.panel_tag(ax, "A", dx=-0.13)

    # Panel C (bottom, full width): one row per operator, baseline against complete-source
    ax = axd["B"]
    per = B["per_operator_single_step"]
    ops = sorted(per, key=lambda k: per[k]["baseline_rate"])
    for i, o in enumerate(ops):
        b = 100 * per[o]["baseline_rate"]
        e = 100 * per[o]["em_rate"]
        ax.plot([e, b], [i, i], color=S.MARGIN, linewidth=2.6,
                solid_capstyle="round", zorder=1)
        ax.scatter([b], [i], s=26, marker=S.M_BASE, color=S.BASE, zorder=4)
        ax.scatter([e], [i], s=26, marker=S.M_EM, facecolor="white",
                   edgecolor=S.EM, linewidth=1.1, zorder=4)
    ax.set_yticks(range(len(ops)))
    ax.set_yticklabels([S.label_of(o) for o in ops], fontsize=7.6)
    ax.set_xlabel("promotion rate (%)")
    ax.set_xlim(-9, 112)
    ax.set_ylim(-0.8, len(ops) - 0.2)
    ax.grid(axis="x", linestyle=":")
    ax.set_axisbelow(True)
    ax.set_title("single operator", fontsize=8.4, loc="left")
    S.panel_tag(ax, "C", dx=-0.055)
    # No series labels here. Panel A already keys the same two series with the
    # same marker shapes, and this panel is too narrow to carry both without
    # them colliding; a second key would be clutter, not clarity.

    # Panel B (top right): measured against the closed form
    ax = axd["C"]
    ks = sorted(B["control_uniform_positions"]["G"], key=int)
    kx = [int(k) for k in ks]
    meas = [100 * B["control_uniform_positions"]["G"][k]["measured_baseline_rate"]
            for k in ks]
    pred = [100 * B["control_uniform_positions"]["G"][k]["closed_form_baseline_rate"]
            for k in ks]
    ax.plot(kx, pred, "-", color=S.PREDICT, lw=1.2, zorder=2)
    ax.plot(kx, meas, linestyle="none", marker=S.M_MEASURED, color=S.MEASURED,
            ms=4.2, zorder=3)
    ax.set_xticks(kx)
    ax.set_xlim(0.6, 4.4)
    ax.set_ylim(80, 101)
    ax.set_xlabel("injected anomalies $k$")
    ax.set_ylabel("baseline rate (%)")
    ax.grid(axis="y", linestyle=":")
    ax.set_axisbelow(True)
    ax.annotate("closed form", xy=(kx[-1], pred[-1]), xytext=(-3, -11),
                textcoords="offset points", fontsize=7.0, color=S.PREDICT,
                ha="right")
    ax.annotate("measured", xy=(kx[0], meas[0]), xytext=(4, 4),
                textcoords="offset points", fontsize=7.0, color=S.MEASURED,
                ha="left")
    ax.set_title("control arm", fontsize=8.4, loc="left")
    S.panel_tag(ax, "B", dx=-0.14)
    ax.text(0.97, 0.95, "axis truncated", transform=ax.transAxes,
            fontsize=6.8, ha="right", va="top", color="#666666")

    save(fig, "fig3_promotion")


# --- Figure: the cost of conservatism ---------------------------------------

def fig_dilution():
    I = load("I_claim_dilution")
    per = I["per_transformation"]
    chain = I["composition_chain"]
    longa = I["long_asset_chain"]

    # The composition-depth panel carries the headline of this figure, that the
    # cost compounds to most of a short asset by depth five, so it takes the
    # full width. The per-transformation rows and the duration trend share the
    # row beneath; the operator labels still fit at half width.
    fig, axd = plt.subplot_mosaic([["depth", "depth"], ["ops", "dur"]],
                                  figsize=(7.0, 5.2), constrained_layout=True,
                                  height_ratios=[1.0, 1.05])

    # Panel B: single transformation, median with maximum whisker
    ax = axd["ops"]
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
        # Whole-asset comparator: safe, and dilutes almost everything.
        ax.scatter([100 * v["whole_asset_median_dilution_fraction"]], [i], s=22,
                   marker="x", color=S.BASE, linewidth=1.0, zorder=4)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([S.label_of(k) for k, _ in rows], fontsize=7.0)
    ax.set_xlabel("output samples diluted (%)\n"
                  "dot median, bar maximum, \u00d7 whole-asset median", fontsize=7.4)
    ax.set_xlim(-3, 106)
    ax.grid(axis="x", linestyle=":")
    ax.set_axisbelow(True)
    S.panel_tag(ax, "B", dx=-0.30)

    # Panel A: dilution through composition depth, the headline of this figure
    ax = axd["depth"]
    d = [r["depth"] for r in chain]
    med = [100 * r["median_dilution_fraction"] for r in chain]
    mx = [100 * r["max_dilution_fraction"] for r in chain]
    ax.fill_between(d, med, mx, color=S.MARGIN, alpha=0.75, linewidth=0,
                    zorder=1)
    ax.plot(d, mx, color="#9a9a9a", linewidth=0.8, linestyle=(0, (3, 2)),
            zorder=2)
    ax.plot(d, med, color=S.MEASURED, marker=S.M_MEASURED, markersize=3.6,
            zorder=3)
    ax.set_xlabel("composition depth (operator added at each step)")
    ax.set_ylabel("diluted (%)")
    ax.set_xticks(d)
    # Which operator each step adds, so the jumps can be read off the axis.
    steps = ["trim", "+resample", "+MP3", "+normalise", "+stretch"]
    ax.set_xticklabels([f"{x}\n{s}" for x, s in zip(d, steps[:len(d)])], fontsize=7.0)
    ax.set_ylim(-4, 108)
    ax.grid(axis="y", linestyle=":")
    ax.set_axisbelow(True)
    S.panel_tag(ax, "A", dx=-0.055)
    ax.set_xlim(0.75, 5.62)
    ax.text(0.01, 0.97, "declared-map simulation at 8 kHz; adaptive stages "
            "not validated", transform=ax.transAxes, fontsize=6.9,
            ha="left", va="top", color="#555555")
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
    ax = axd["dur"]
    secs = [r["asset_seconds"] for r in longa]
    frac = [100 * r["dilution_fraction"] for r in longa]
    ax.plot(secs, frac, color=S.MEASURED, marker=S.M_MEASURED, markersize=3.8,
            zorder=3)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("asset duration (s, log); boundary count fixed")
    ax.set_ylabel("diluted (%, log)")
    ax.grid(True, which="major", linestyle=":")
    ax.set_axisbelow(True)
    offsets = [(7, 4), (7, 5), (-4, -11)]
    aligns = ["left", "left", "right"]
    for (x, y), off, ha in zip(zip(secs, frac), offsets, aligns):
        ax.annotate(f"{y:.2f}%", xy=(x, y), xytext=off,
                    textcoords="offset points", fontsize=6.9, ha=ha,
                    color="#444444")
    S.panel_tag(ax, "C", dx=-0.14)
    ax.set_ylim(min(frac) * 0.42, max(frac) * 2.6)
    # The explanation of this trend belongs in the caption: a three-line note
    # cannot sit in a panel this size without landing on the curve or on a data
    # label, and cramming it in would cost the legibility it is meant to add.

    save(fig, "fig6_dilution")


if __name__ == "__main__":
    S.apply()
    fig_adversarial()
    fig_corpus()
    fig_containment()
    fig_dilution()
