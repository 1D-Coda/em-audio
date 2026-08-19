"""Fail the build if the manuscript contains a hand-typed result number.

Rule: every numeric *result* must reach the manuscript through a macro defined
in results/numbers.tex.  Structural numbers are allowed and enumerated below:
specification section references, standard constants that are properties of the
formats rather than measurements, years, and layout dimensions.
"""
from __future__ import annotations

import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper" / "manuscript.tex"
NUMBERS = ROOT / "results" / "numbers.tex"

# Numbers that are structural, not measured.
ALLOWED = {
    # format and specification constants, quoted with their source in the text
    "1152", "50", "16", "2", "1", "0", "8", "4", "5", "3", "6", "7", "9", "10",
    "2024", "2026", "1689", "2.4", "18.2", "18.16", "15.11", "18.10", "4.0",
    "256", "0.27", "1.0", "24", "26", "27", "30", "31", "33", "34", "36",
    "1.52", "9.0", "3.11", "20", "40", "60", "80", "100",
}
NUM = re.compile(r"(?<![\\A-Za-z0-9._{])(\d[\d.,]*)(?![\d}])")


def main() -> int:
    if not NUMBERS.exists():
        print("results/numbers.tex missing; run tools/make_macros.py", file=sys.stderr)
        return 2
    macros = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", NUMBERS.read_text()))
    text = TEX.read_text()
    # strip preamble, comments, verbatim-ish structural blocks and \input lines
    text = text[text.index(r"\begin{document}"):]
    # author block: ORCID and postal address are identifiers, not results
    text = re.sub(r"\\cortext\[[^\]]*\]\{[^}]*\}", " ", text)
    text = re.sub(r"\\address\[[^\]]*\]\{[^}]*\}", " ", text)
    text = text.replace("[0,1]", " ")
    text = re.sub(r"(?m)%.*$", "", text)
    text = re.sub(r"\\(includegraphics|input|label|ref|eqref|cite\w*|usepackage|graphicspath|section|subsection)\s*(\[[^\]]*\])?\{[^}]*\}", " ", text)
    text = re.sub(r"\\(begin|end)\{[^}]*\}(\{[^}]*\})?", " ", text)
    text = re.sub(r"p\{[0-9.]+\\linewidth\}", " ", text)
    text = re.sub(r"width=\\linewidth", " ", text)

    offenders = []
    for m in NUM.finditer(text):
        tok = m.group(1).rstrip(".,")
        if tok in ALLOWED:
            continue
        ctx = text[max(0, m.start() - 60):m.start() + 40].replace("\n", " ")
        offenders.append((tok, ctx.strip()))

    print(f"macros available: {len(macros)}")
    if offenders:
        print(f"{len(offenders)} possible hand-typed number(s) in the manuscript:")
        for tok, ctx in offenders[:25]:
            print(f"  {tok!r}  ...{ctx}...")
        return 1
    print("no hand-typed result numbers found in the manuscript source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
