"""Check rendered figures for overlapping text and unreadable type.

Reading a figure and judging it by eye does not scale and does not regenerate.
This renders each figure, walks every text artist and every data mark, and fails
when two pieces of text collide, when text sits on top of a data mark, or when a
label would fall below the legible size at the printed column width.

The checks are deliberately about the RENDERED result rather than the source,
because a matplotlib annotation offset that reads correctly at one figure size
silently collides at another.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.text import Text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

# Read the pin rather than restating it, so this cannot drift from the file that
# actually governs the install.
def _pinned_matplotlib() -> str:
    req = ROOT / "requirements.txt"
    for line in req.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("matplotlib=="):
            return line.split("==", 1)[1].strip()
    return ""


PINNED_MPL = _pinned_matplotlib()

# The freetype the thresholds were calibrated against. Recorded rather than
# inferred, because the point is to know when the measurement is comparable.
PINNED_FREETYPE = "2.14.3"

# A journal single column is about 3.5 in; a figure drawn 7.1 in wide is printed
# at roughly half size, so 6.5 pt drawn becomes about 3.3 pt on paper. Below this
# drawn size a label is not readable after reduction.
MIN_DRAWN_PT = 6.4
# Ignore overlaps smaller than this many square points: antialiased glyph boxes
# touch at the corners without being visually confusable.
MIN_OVERLAP_AREA = 6.0


def _boxes(fig):
    """Every visible, non-empty text bounding box in display coordinates."""
    fig.canvas.draw()
    out = []
    for ax in fig.get_axes():
        artists = (list(ax.texts) + [ax.title, ax.xaxis.label, ax.yaxis.label]
                   + list(ax.get_xticklabels()) + list(ax.get_yticklabels()))
        axbb = ax.get_window_extent(fig.canvas.get_renderer())
        ticks = set(map(id, list(ax.get_xticklabels()) + list(ax.get_yticklabels())))
        for t in artists:
            if not isinstance(t, Text) or not t.get_visible():
                continue
            if not (t.get_text() or "").strip():
                continue
            if id(t) in ticks:
                # A tick generated outside the current limits is clipped and
                # never drawn, so it cannot collide with anything on the page.
                try:
                    tb = t.get_window_extent(fig.canvas.get_renderer())
                except Exception:
                    continue
                pad = 26.0
                if (tb.x1 < axbb.x0 - pad or tb.x0 > axbb.x1 + pad
                        or tb.y1 < axbb.y0 - pad or tb.y0 > axbb.y1 + pad):
                    continue
            try:
                bb = t.get_window_extent(fig.canvas.get_renderer())
            except Exception:
                continue
            if bb.width <= 0 or bb.height <= 0:
                continue
            out.append((t, bb, ax))
    # Legend text lives on its own artist, outside ax.texts, so a label
    # colliding with a legend entry passed every check. Figure 5's legend
    # overlapped its own violation caption and the gate called the figure clean,
    # which is the one failure mode a gate must not have.
    for ax in fig.get_axes():
        leg = ax.get_legend()
        if leg is None:
            continue
        for t in leg.get_texts():
            if not (t.get_text() or "").strip():
                continue
            try:
                bb = t.get_window_extent(fig.canvas.get_renderer())
            except Exception:
                continue
            if bb.width > 0 and bb.height > 0:
                out.append((t, bb, ax))

    for t in fig.texts:
        if isinstance(t, Text) and t.get_visible() and (t.get_text() or "").strip():
            bb = t.get_window_extent(fig.canvas.get_renderer())
            out.append((t, bb, None))
    return out


def _overlap_area(a, b):
    dx = min(a.x1, b.x1) - max(a.x0, b.x0)
    dy = min(a.y1, b.y1) - max(a.y0, b.y0)
    return dx * dy if dx > 0 and dy > 0 else 0.0


def check(fig, name):
    problems = []
    boxes = _boxes(fig)

    # 1. text against text
    for i in range(len(boxes)):
        ti, bi, axi = boxes[i]
        for j in range(i + 1, len(boxes)):
            tj, bj, axj = boxes[j]
            if axi is not axj:
                continue                       # different panels cannot collide
            # tick labels on the same axis are laid out by matplotlib
            if ti in list(axi.get_xticklabels()) and tj in list(axi.get_xticklabels()):
                continue
            if ti in list(axi.get_yticklabels()) and tj in list(axi.get_yticklabels()):
                continue
            area = _overlap_area(bi, bj)
            if area > MIN_OVERLAP_AREA:
                problems.append(
                    f"text overlaps text ({area:.0f} pt^2): "
                    f"{ti.get_text()[:34]!r} / {tj.get_text()[:34]!r}")

    # 2. text sitting on top of plotted data
    #    Text over a light fill stays readable, so only lines and markers are
    #    checked: those are the marks a reader has to trace.
    import numpy as np
    from matplotlib.lines import Line2D
    from matplotlib.collections import PathCollection
    for t, bb, ax in boxes:
        if ax is None:
            continue
        pad = 2.5
        hits = 0
        for artist in list(ax.lines) + list(ax.collections):
            if isinstance(artist, Line2D):
                xy = artist.get_xydata()
                if len(xy) == 0:
                    continue
                pts = ax.transData.transform(xy)
                # sample along each segment, not just at the vertices
                dense = []
                for k in range(len(pts) - 1):
                    a, b = pts[k], pts[k + 1]
                    for f in np.linspace(0, 1, 24):
                        dense.append(a + (b - a) * f)
                pts = np.array(dense) if dense else pts
            elif isinstance(artist, PathCollection):
                off = artist.get_offsets()
                if len(off) == 0:
                    continue
                pts = ax.transData.transform(off)
            else:
                continue
            inside = ((pts[:, 0] > bb.x0 - pad) & (pts[:, 0] < bb.x1 + pad) &
                      (pts[:, 1] > bb.y0 - pad) & (pts[:, 1] < bb.y1 + pad))
            hits += int(inside.sum())
        if hits:
            problems.append(f"text sits on plotted data ({hits} points): "
                            f"{t.get_text()[:40]!r}")

    # 3. type too small to survive reduction
    for t, _, _ in boxes:
        size = t.get_fontsize()
        if size < MIN_DRAWN_PT:
            problems.append(f"font {size:.1f}pt below {MIN_DRAWN_PT}pt: "
                            f"{t.get_text()[:34]!r}")

    if problems:
        print(f"[qa] {name}: {len(problems)} problem(s)")
        for p in problems[:12]:
            print(f"     {p}")
    else:
        print(f"[qa] {name}: clean ({len(boxes)} text elements)")
    return problems


def main() -> int:
    import figstyle as S
    import make_figures_shared as N

    S.apply()
    bad = 0
    for builder, name in ((N.fig_adversarial, "fig3_promotion"),
                          (N.fig_corpus, "fig4_corpus"),
                          (N.fig_containment, "fig5_containment"),
                          (N.fig_dilution, "fig6_dilution")):
        # rebuild without saving so the live figure can be inspected
        saved, captured = N.save, {}

        def grab(fig, nm, _c=captured):
            _c["fig"], _c["name"] = fig, nm

        N.save = grab
        builder()
        N.save = saved
        bad += len(check(captured["fig"], captured["name"]))
        plt.close(captured["fig"])
    if bad:
        print(f"[qa] {bad} problem(s) across the figure set")
        # This test measures rendered glyph boxes, so its thresholds are only
        # calibrated for the matplotlib pinned in requirements.txt. The font
        # family is fixed in figstyle, but layout and text extents still move
        # between library versions, and the independent reproduction of Section
        # 7.11 hit exactly that: two collisions on a build whose Python version
        # would not resolve the pin, on figures the reference environment
        # renders clean. Report the findings either way; gate only where the
        # measurement is calibrated, so the check cannot fail a reproduction for
        # a difference that is not about the figures.
        # Text extents are measured by freetype, not by matplotlib, so pinning
        # matplotlib alone does not pin the geometry. The same pinned version
        # inside a Linux container reported four collisions on a figure the
        # reference environment renders clean. Gate where the measurement is
        # calibrated; report everywhere.
        try:
            ft = matplotlib.ft2font.__freetype_version__
        except Exception:
            ft = "unknown"
        if matplotlib.__version__ != PINNED_MPL or ft != PINNED_FREETYPE:
            print(f"[qa] matplotlib {matplotlib.__version__} / freetype {ft} "
                  f"is not the calibrated {PINNED_MPL} / {PINNED_FREETYPE}; "
                  f"text extents are measured by freetype, so the geometric "
                  f"thresholds are not comparable here. Findings are reported "
                  f"and do not fail the run.")
            return 0
        return 1
    print("[qa] every figure clean: no overlapping text, no unreadable type")
    return 0


if __name__ == "__main__":
    sys.exit(main())
