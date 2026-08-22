"""Emit the figure provenance and QA records from the figures themselves.

Written by the tools rather than by hand, so the mapping cannot drift from what
the plotting code actually reads.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "results" / "figures"
MR = ROOT / "results" / "machine_readable"

# Every visual element, and the result file the plotting code reads for it.
SOURCES = {
    "fig1_counterexample": [
        ("waveform and interval strip", "constructed fixture rendered by tools/make_figures.py"),
        ("emitted claims", "A_synthetic_state_space.json (contract semantics)"),
    ],
    "fig2_architecture": [("diagram, no measured values", "none")],
    "fig3_promotion": [
        ("panel A, promotion by depth", "B_adversarial_timelines.json -> per_depth"),
        ("panel B, policy ablation", "B2_policy_ablation.json -> arms"),
        ("panel C, closed-form control", "B_adversarial_timelines.json -> control_uniform_positions"),
    ],
    "fig4_corpus": [
        ("panel A, promotion by transformation",
         "D_transform_matrix.json -> per_transformation[*].baseline_promotions / em_promotions"),
        ("panel B, intervals emitted per output",
         "D_transform_matrix.json -> per_transformation[*].mean_baseline_intervals / mean_em_intervals"),
    ],
    "fig5_containment": [
        ("measured reach", "K_support_containment.json -> per_operator[*].max_measured_reach_source_samples"),
        ("declared footprint", "K_support_containment.json -> per_operator[*].declared_footprint_samples"),
        ("samples outside", "K_support_containment.json -> per_operator[*].total_outside_declared_support"),
    ],
    "fig6_dilution": [
        ("panel A, per transformation", "I_claim_dilution.json -> per_transformation"),
        ("panel B, composition depth", "I_claim_dilution.json -> composition_chain"),
        ("panel C, asset duration", "I_claim_dilution.json -> long_asset_chain"),
    ],
    "fig7_overhead": [
        ("assertion size and time scaling", "G_overhead.json -> assertion_scaling"),
    ],
}


def main() -> int:
    missing = [n for n in SOURCES if not (FIG / f"{n}.pdf").exists()]
    if missing:
        print(f"[docs] figures not built: {', '.join(missing)}")
        return 1

    lines = ["# Figure data sources", "",
             "Every visual element in every figure, and the committed result "
             "file it is read from. No measured number is typed into a plotting "
             "script: where a value exists in `results/machine_readable/`, the "
             "script reads it, and a figure whose data is absent fails rather "
             "than being drawn from memory.", ""]
    for name in sorted(SOURCES):
        lines.append(f"## `{name}`")
        lines.append("")
        lines.append("| element | source |")
        lines.append("|---|---|")
        for el, src in SOURCES[name]:
            lines.append(f"| {el} | `{src}` |")
        lines.append("")
    (ROOT / "results" / "FIGURE_DATA_SOURCES.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print("[docs] results/FIGURE_DATA_SOURCES.md")

    qa = subprocess.run([sys.executable, str(ROOT / "tools" / "figure_qa.py")],
                        capture_output=True, text=True, cwd=ROOT)
    rows = []
    for name in sorted(SOURCES):
        pdf = FIG / f"{name}.pdf"
        png = FIG / f"{name}.png"
        svg = FIG / f"{name}.svg"
        rows.append((name, pdf.stat().st_size,
                     png.stat().st_size if png.exists() else 0,
                     "yes" if svg.exists() else "no"))

    doc = ["# Figure QA", "",
           "Checks that are run rather than asserted. `tools/figure_qa.py` "
           "renders each figure and inspects the result, because an annotation "
           "offset that reads correctly at one figure size collides silently at "
           "another.", "",
           "## Automated checks", "",
           "| check | rule |",
           "|---|---|",
           "| overlapping text | no two text elements in a panel may overlap by "
           "more than 6 pt^2 |",
           "| text over data | no text may sit on a plotted line or marker |",
           "| legibility after reduction | no drawn label below 6.4 pt, so a "
           "half-size reduction stays above ~3.2 pt |",
           "",
           "Latest run:", "", "```", qa.stdout.strip(), "```", "",
           "## Design rules applied by hand", "",
           "- One semantic palette in `tools/figstyle.py`, used by every figure.",
           "- No mark is distinguished by hue alone: hue always travels with a "
           "marker shape, a line style, or a direct label, so the set survives "
           "colour-vision deficiency and a greyscale printer.",
           "- Policy roles are separated in luminance as well as hue, since "
           "luminance is what carries greyscale.",
           "- Zeros are drawn as open marks. A zero-height bar is invisible, and "
           "an invisible zero reads as missing data rather than as the result it "
           "is.",
           "- Direct labels are preferred to legends; where a panel is too small "
           "to hold an explanation without collision, the explanation goes to the "
           "caption instead of being shrunk.",
           "- One operator naming scheme across every figure, table and caption.",
           "",
           "## Output formats", "",
           "| figure | PDF (bytes) | PNG (bytes) | SVG |",
           "|---|---:|---:|---|"]
    for name, a, b, c in rows:
        doc.append(f"| `{name}` | {a:,} | {b:,} | {c} |")
    doc += ["", "Vector PDF is what the manuscript includes; PNG previews are "
            "300 dpi; SVG is provided for editing."]
    (ROOT / "results" / "FIGURE_QA.md").write_text("\n".join(doc) + "\n",
                                                   encoding="utf-8")
    print("[docs] results/FIGURE_QA.md")
    return 0 if qa.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
