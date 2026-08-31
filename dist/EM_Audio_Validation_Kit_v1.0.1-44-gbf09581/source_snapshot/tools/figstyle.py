"""One visual language for every figure in the manuscript.

The palette is chosen so that each semantic role survives three separate
degradations a printed figure has to endure: colour-vision deficiency, a
greyscale printer, and a reviewer reading a single-column reduction on paper.
No mark in this paper is distinguished by hue alone; hue always travels with a
marker shape, a line style, or a direct label.

Luminance is the property that carries greyscale, so the roles that must never
be confused, the baseline policy and the complete-source contract, are separated
by luminance as well as hue rather than by hue alone.
"""
from __future__ import annotations

import matplotlib.pyplot as plt

# --- semantic roles ---------------------------------------------------------
# Evidence states
CAP = "#1b6ca8"          # captured-derived        (blue,   L* ~ 42)
GEN = "#c1591a"          # generated-derived       (orange, L* ~ 53)
MIX = "#6a3d9a"          # mixed                   (purple, L* ~ 35)
UNV = "#7a7a7a"          # unverified / unavailable(grey,   L* ~ 51)

# Policies under comparison. Kept far apart in luminance so a greyscale reader
# can still tell which mark is which without the legend.
BASE = "#b2182b"         # boundary-only baseline  (dark red,  L* ~ 39)
EM = "#1a7f74"           # complete-source / EM    (teal,      L* ~ 47)

# Quantity kinds
MEASURED = "#1a1a1a"     # measured data: strong solid mark
PREDICT = "#4d4d4d"      # analytical / closed-form prediction: dark grey line
DECLARED = "#1a1a1a"     # declared conservative bound: outlined marker
MARGIN = "#c8c8c8"       # headroom / connector: light neutral

# Marker shapes carry the same information as colour, for grayscale and CVD.
M_BASE = "o"             # baseline policy
M_EM = "D"               # complete-source policy
M_MEASURED = "o"         # a measurement
M_DECLARED = "D"         # a declaration

RC = {
    "font.size": 8.5,
    "font.family": "DejaVu Sans",
    "axes.labelsize": 8.5,
    "axes.titlesize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "lines.linewidth": 1.2,
    "grid.linewidth": 0.5,
    "grid.alpha": 0.35,
    "figure.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "pdf.fonttype": 42,          # embed as TrueType so text stays selectable
    "ps.fonttype": 42,
}


def apply():
    plt.rcParams.update(RC)


def panel_tag(ax, letter, dx=-0.02, dy=1.06):
    """Panel letter, placed outside the axes so it never covers data."""
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=9,
            fontweight="bold", va="bottom", ha="right")


def zero_marker(ax, x, y, colour=EM, marker=M_EM, size=26):
    """Draw an explicit zero.

    A zero-height bar is invisible, and an invisible zero reads as missing data
    rather than as the result it actually is. Every zero in this paper is drawn
    as a mark with an outline so that it is legible as a measured zero.
    """
    ax.scatter([x], [y], s=size, marker=marker, facecolor="white",
               edgecolor=colour, linewidth=1.1, zorder=5, clip_on=False)


def note(ax, text, xy, xytext, fontsize=7.4, arrow=True):
    """Annotation that explains a result rather than repeating an axis label."""
    kw = dict(fontsize=fontsize, color="#333333", va="center",
              zorder=6, linespacing=1.25)
    if arrow:
        ax.annotate(text, xy=xy, xytext=xytext, arrowprops=dict(
            arrowstyle="-", color="#8a8a8a", linewidth=0.6,
            shrinkA=0, shrinkB=2), **kw)
    else:
        ax.annotate(text, xy=xytext, **kw)


def dumbbell(ax, y, lo, hi, lo_colour, hi_colour, lo_marker, hi_marker,
             connector=MARGIN, size=30):
    """A paired-value row: two marks and the interval between them.

    Used wherever the scientific content is the gap between two quantities
    rather than either quantity on its own.
    """
    ax.plot([lo, hi], [y, y], color=connector, linewidth=3.2,
            solid_capstyle="round", zorder=1)
    ax.scatter([lo], [y], s=size, marker=lo_marker, color=lo_colour,
               zorder=4, clip_on=False)
    ax.scatter([hi], [y], s=size, marker=hi_marker, facecolor="white",
               edgecolor=hi_colour, linewidth=1.2, zorder=4, clip_on=False)


OPERATOR_LABELS = {
    "normalize": "amplitude normalisation",
    "overlay_generated": "generated-source overlay",
    "resample_16_8": "resample 16 to 8 kHz",
    "silence_removal": "silence removal",
    "time_stretch_1.10": "time stretch 1.10",
    "transcode_flac": "transcode to FLAC",
    "transcode_mp3": "transcode to MP3",
    "trim_10_90": "trim to middle 80%",
}


def label_of(key):
    """One operator naming scheme across every figure, table and caption."""
    return OPERATOR_LABELS.get(key, key.replace("_", " "))
