"""The figures built on the shared visual language in tools/figstyle.py.

Four of the manuscript's seven figures live here: adversarial validation, the
mixed-origin corpus, kernel-support containment and claim dilution. The
remaining three, the counterexample, the architecture diagram and the cost
scaling, are in tools/make_figures.py.

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
            # A structural zero: the baseline cannot promote here either, and
            # the reason belongs on the row rather than in the caption alone.
            ax.scatter([b], [i], s=36, marker=S.M_BASE, facecolor="white",
                       edgecolor=S.BASE, linewidth=1.2, zorder=4)
            ax.text(4.0, i, f"{bn}/{n:,}, a structural zero", fontsize=7.0,
                    va="center", color="#777777")
        ax.scatter([e], [i], s=36, marker=S.M_EM, facecolor="white",
                   edgecolor=S.EM, linewidth=1.2, zorder=5)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([S.label_of(k) for k in rows], fontsize=7.8)
    ax.set_xlabel("clips with promotion (%)")
    ax.set_xlim(-6, 128)
    ax.set_ylim(-1.35, len(rows) - 0.30)
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
    ax.text(0.5, -1.15, "open marks are exact zeros, drawn so that a zero reads "
            "as a result rather than as missing data", fontsize=6.9,
            color="#666666", va="center")
    S.panel_tag(ax, "A", dx=-0.055)

    # Panel B: the mechanism behind panel A, from the same run
    ax = axd["why"]
    bi = [per[k]["mean_baseline_intervals"] for k in rows]
    ei = [per[k]["mean_em_intervals"] for k in rows]
    y = list(range(len(rows)))
    for i, key in enumerate(rows):
        ax.plot([bi[i], ei[i]], [i, i], color=S.MARGIN, linewidth=3.0,
                solid_capstyle="round", zorder=1)
        ax.scatter([bi[i]], [i], s=32, marker=S.M_BASE, color=S.BASE, zorder=4)
        ax.scatter([ei[i]], [i], s=32, marker=S.M_EM, facecolor="white",
                   edgecolor=S.EM, linewidth=1.2, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels([S.label_of(k) for k in rows], fontsize=7.4)
    ax.set_xlabel("mean evidence intervals emitted per output")
    ax.set_xlim(0, max(ei) + 1.1)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.grid(axis="x", linestyle=":", zorder=0)
    ax.set_axisbelow(True)
    S.panel_tag(ax, "B", dx=-0.055)
    tr2 = ax.get_xaxis_transform()          # x in data, y in axes fraction
    ax.annotate("one claim over\nthe whole output", xy=(min(bi), 1.005),
                xytext=(min(bi), 1.115), xycoords=tr2, textcoords=tr2,
                fontsize=6.9, color=S.BASE, ha="center", linespacing=1.3,
                annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6))
    ax.annotate("the intervals that carry\nthe contradicting evidence",
                xy=(max(ei), 1.005), xytext=(max(ei), 1.115),
                xycoords=tr2, textcoords=tr2, fontsize=6.9, color=S.EM,
                ha="center", linespacing=1.3, annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6))
    ax.set_title("Why it happens: the baseline discards the intervals that "
                 "would have contradicted it", fontsize=8.4, loc="left", pad=44)

    save(fig, "fig4_corpus")


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

    Both builds are drawn. The reference build satisfies every declaration; the
    independent reproduction's FFmpeg does not, and its MP3 reach lands well
    inside the violation band. Showing only the reference build would give the
    figure a title that is true of one machine and false of the other, and would
    leave the paper's most informative measurement to a supplement table.
    """
    K = load("K_support_containment")["per_operator"]
    # The other build, when its results are present. A reproduction package
    # ships without them, and the figure is then simply the reference build.
    IND = ROOT / "results" / "independent" / "machine_readable" / "K_support_containment.json"
    ind = json.loads(IND.read_text())["per_operator"] if IND.exists() else {}
    rows = [(k, v) for k, v in K.items() if v["declared_footprint_samples"] > 0]
    rows.sort(key=lambda kv: kv[1]["max_measured_reach_source_samples"] /
              kv[1]["declared_footprint_samples"])
    zeros = [k for k, v in K.items() if v["declared_footprint_samples"] == 0]

    fig, ax = plt.subplots(figsize=(6.4, 2.5), constrained_layout=True)

    # Wide enough for the largest thing drawn, from either build. A fixed
    # ceiling let a mark run off the axis and its connector then crossed the
    # whole width into the labels anchored at the right margin.
    def _pct(v):
        d = v["declared_footprint_samples"]
        return 100.0 * v["max_measured_reach_source_samples"] / d if d else 0.0
    if ind:
        widest = max([_pct(v) for k, v in K.items() if v["declared_footprint_samples"]]
                     + [_pct(ind[k]) for k in K if k in ind and K[k]["declared_footprint_samples"]])
        # Proportional, not fixed: the anchored labels keep a constant pixel
        # width, so as the axis grows they cover more data units and a fixed
        # margin stops being enough.
        xmax = max(205.0, widest + 18.0)
    else:
        xmax = 132
    ax.axvspan(100, xmax, color="#f2dede", alpha=0.55, linewidth=0, zorder=0)
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
        iv_pre = ind.get(key)
        # Anchored, not attached. A label that follows its mark moves with the
        # measurement, and every position that worked for one build collided on
        # another. Both numbers sit at fixed x on their row, distinguished by
        # colour and by the marks they annotate, so the layout is the same
        # whatever the data says.
        if ind:
            ax.text(-1.5, i, f"{reach:,}", fontsize=7.2, va="center",
                    ha="right", color=S.MEASURED)
        else:
            ax.text(pct - 2.2, i, f"{reach:,}", fontsize=7.2, va="center",
                    ha="right", color="#222222")
        # the same operator measured on the independent build
        iv = iv_pre
        crossed = bool(iv and iv["max_measured_reach_source_samples"] != reach)
        # The "of N" label sits just right of the declaration line, which is
        # where the second build's connector now runs. Put it below the row for
        # the crossing operator so the two do not overlap.
        # Just right of the declaration line is where the second build's
        # connector runs, so on a row that has one the declaration label drops
        # below its own row. With both reach numbers now anchored at the
        # margins, there is nothing down there to hit.
        # Always below the row when a second build is drawn, never beside it.
        # Beside it is where the connectors run, and which connector passes
        # through that point depends on whether a measurement exceeded its
        # declaration, so a conditional offset only moved the collision around.
        ax.text(101.5, i - (0.34 if ind else 0.0), f"of {decl:,}",
                fontsize=7.2, va="center", color="#555555")
        if iv:
            ireach = iv["max_measured_reach_source_samples"]
            if crossed:
                ipct = 100.0 * ireach / decl
                ax.plot([100, ipct], [i, i], color=S.BASE, linewidth=1.6,
                        linestyle=(0, (2, 1.6)), zorder=3)
                ax.scatter([ipct], [i], s=40, marker="X", color=S.BASE,
                           zorder=5)
                # Below its own mark. Anchoring it at the right margin kept it
                # clear of the marks but not of the connectors, which reach
                # further the larger the measurement is. Nothing else is drawn
                # below the row line, so this is clear by construction rather
                # than by arithmetic about the current data.
                ax.text(ipct, i - 0.30, f"{ireach:,}", fontsize=7.2,
                        va="center", ha="center", color=S.BASE)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([S.label_of(k) for k, _ in rows])
    ax.set_xlabel("measured reach as a percentage of the declared footprint")
    ax.set_xlim(-14 if ind else 0, xmax)
    ax.set_ylim(-1.15, len(rows) - 0.42)
    ax.set_xticks([0, 25, 50, 75, 100] + ([150, 200] if ind else []))
    ax.grid(axis="x", linestyle=":", zorder=0)
    ax.set_axisbelow(True)

    top = len(rows) - 1
    tp = (100.0 * rows[top][1]["max_measured_reach_source_samples"] /
          rows[top][1]["declared_footprint_samples"])
    tr = ax.get_xaxis_transform()          # x in data, y in axes fraction
    # Only without a legend. The callout is anchored to the top row's
    # measurement, so it moves with the data and collided with the fixed
    # "declaration" label whenever that measurement approached the declaration.
    # Where there is a legend, it already says what the marks are.
    if not ind:
        ax.annotate("measured reach", xy=(tp, 1.005), xytext=(tp - 13, 1.10),
                    xycoords=tr, textcoords=tr, fontsize=7.3, ha="center",
                    color="#222222", annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6))
    if ind:
        from matplotlib.lines import Line2D
        ax.legend(handles=[
            Line2D([], [], marker=S.M_MEASURED, color=S.MEASURED, linestyle="",
                   markersize=5, label="reference build"),
            Line2D([], [], marker="X", color=S.BASE, linestyle="",
                   markersize=6, label="independent build"),
        # Below the axes rather than inside it. Placed inside, the legend
        # collided with the independent build's label as soon as that label
        # moved, and the label's position is a measurement: any other build
        # puts it somewhere else. A legend whose correctness depends on the
        # data it describes is not a legend.
        ], loc="upper center", bbox_to_anchor=(0.5, -0.34), ncol=2,
            fontsize=6.9, frameon=False, handletextpad=0.4, borderpad=0.1)
    ax.annotate("declaration", xy=(100, 1.005), xytext=(100, 1.10),
                xycoords=tr, textcoords=tr, fontsize=7.3, ha="center",
                color="#222222", annotation_clip=False,
                arrowprops=dict(arrowstyle="-", color="#999999", lw=0.6))
    ax.text(100 + (xmax - 100) / 2, -0.78,
            "violation: reach exceeds the declaration" if ind
            else "a violation would land in here",
            fontsize=6.9, ha="center", va="center", color=S.BASE)

    outside = sum(v["total_outside_declared_support"] for v in K.values())
    if ind:
        iout = sum(v["total_outside_declared_support"] for v in ind.values())
        # A title true of one build and false of the other is the defect here,
        # not the failing measurement.
        title = (f"Declarations hold on the reference build ({outside} samples "
                 f"outside) and not on another ({iout:,})")
    else:
        title = (f"Every declaration contains its own measurement "
                 f"({outside} influenced samples fell outside)")
    ax.set_title(title, fontsize=8.6, loc="left", pad=22)
    if zeros:
        fig.text(0.0, -0.055,
                 "Zero-footprint operators ("
                 + ", ".join(S.label_of(z) for z in sorted(zeros))
                 + ") are omitted: reach and declaration are both zero, so the "
                   "ratio is undefined.",
                 fontsize=6.8, color="#666666")
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

    # Panel B: one row per operator, baseline against complete-source
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
    S.panel_tag(ax, "A", dx=-0.055)
    # No series labels here. Panel A already keys the same two series with the
    # same marker shapes, and this panel is too narrow to carry both without
    # them colliding; a second key would be clutter, not clarity.

    # Panel C: measured against the closed form
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
    S.panel_tag(ax, "C", dx=-0.14)
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
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([S.label_of(k) for k, _ in rows], fontsize=7.0)
    ax.set_xlabel("output samples diluted (%)")
    ax.set_xlim(-3, 62)
    ax.grid(axis="x", linestyle=":")
    ax.set_axisbelow(True)
    S.panel_tag(ax, "B", dx=-0.30)
    ax.text(0.98, 0.06, "dot: median   bar: maximum\nopen: exact zero",
            transform=ax.transAxes, fontsize=6.8, ha="right", va="bottom",
            color="#555555", linespacing=1.4)

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
    ax.set_xlabel("composition depth")
    ax.set_ylabel("diluted (%)")
    ax.set_xticks(d)
    ax.set_ylim(-4, 108)
    ax.grid(axis="y", linestyle=":")
    ax.set_axisbelow(True)
    S.panel_tag(ax, "A", dx=-0.055)
    ax.set_xlim(0.75, 5.62)
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
