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
    "1.52", "9.0", "3.11", "18", "20", "40", "60", "80", "100", "1.10",
}
NUM = re.compile(r"(?<![\\A-Za-z0-9._{])(\d[\d.,]*)(?![\d}])")


def check_supplement_pointers(manuscript: str, supplement: str) -> list[str]:
    """Every 'Supplementary Note/Table SN' must resolve to something the
    supplement actually numbers. A pointer at a table is only valid if the
    supplement captions that many tables, which it will not do while its
    longtables carry no caption."""
    import re
    problems = []
    n_sections = len(re.findall(r"^\\section\{", supplement, re.M))
    n_captions = len(re.findall(r"\\caption\{", supplement))
    for kind, num in re.findall(r"Supplementary (Note|Table)~?S(\d+)", manuscript):
        n = int(num)
        limit = n_sections if kind == "Note" else n_captions
        if n > limit:
            problems.append(
                f"Supplementary {kind} S{n} does not resolve: the supplement has "
                f"{limit} numbered {'sections' if kind == 'Note' else 'captioned tables'}")
    return problems


def check_bundle_docs():
    """Internal bundle documents must not contradict the manuscript.

    These are hand-written and nothing regenerates them, so they drift silently:
    one shipped a superseded conformance total for two days while the manuscript
    carried the current one, and a reader comparing the two would have found the
    paper disagreeing with its own record.

    The match is on a number together with the words naming it, not on magnitude.
    A first version of this check flagged anything within a factor of four of a
    live value, which reported the correct influenced-sample count as a stale
    operator-case count. A check that cries wolf gets ignored, which is worse
    than not having it.
    """
    import json
    sub = ROOT.parent / "EM_Audio_Submission_2026-08-19"
    if not sub.is_dir():
        return []
    mr = ROOT / "results" / "machine_readable"
    A = json.loads((mr / "A_synthetic_state_space.json").read_text())
    K = json.loads((mr / "K_support_containment.json").read_text())

    # (regex naming the quantity, current value). The number may sit on either
    # side of the words, so both orders are matched.
    # [ \t] rather than \s: \s crosses newlines, so a machine-readable dump with
    # "operator_cases: 98385" on one line and "checks_total: ..." on the next
    # matched as though the first number named checks. The guard reported two
    # such phantoms before this was tightened.
    live = [
        # up to two intervening words, so "885,828 exhaustive checks" is caught
        (r"([\d,]{5,})[ \t]+(?:[a-z-]+[ \t]+){0,2}checks", A["checks_total"]),
        (r"([\d,]{5,})[ \t]+(?:[a-z-]+[ \t]+){0,2}operator cases",
         A["operator_cases"]),
        (r"([\d,]{5,})[ \t]+(?:[a-z-]+[ \t]+){0,2}output samples",
         K["total_affected_output_samples"]),
    ]

    problems = []
    for doc in sorted(sub.glob("*.md")) + sorted(sub.glob("*.txt")):
        # The audit report is an append-only history and quotes superseded
        # values on purpose, to record what changed and why.
        if "Audit_Graphs_Formulas" in doc.name:
            continue
        text = doc.read_text(encoding="utf-8", errors="ignore")
        for pat, cur in live:
            for tok in set(re.findall(pat, text, re.I)):
                try:
                    val = int(tok.replace(",", ""))
                except ValueError:
                    continue
                if val != cur:
                    problems.append(f"{doc.name}: {tok} where the current "
                                    f"value is {cur:,}")
    return sorted(set(problems))


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
    supp = (ROOT / "paper" / "supplementary.tex").read_text(encoding="utf-8")
    dangling = check_supplement_pointers(text, supp)
    if dangling:
        print(f"{len(dangling)} dangling supplement pointer(s):")
        for d in dangling:
            print(f"  {d}")
        return 1

    stale = check_bundle_docs()
    if stale:
        print(f"{len(stale)} possibly superseded number(s) in the bundle:")
        for d in stale[:10]:
            print(f"  {d}")
        return 1

    print("no hand-typed result numbers found in the manuscript source")
    print("all supplement pointers resolve")
    print("bundle documents agree with the current results")
    return 0

if __name__ == "__main__":
    sys.exit(main())
