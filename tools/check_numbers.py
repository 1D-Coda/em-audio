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


# Counts written as words are still hand-typed counts. The cover letter drifted
# from the manuscript by claiming "eight of the ten" result files reproduced
# where the macros said otherwise, and a digit scanner would never have seen it.
WORD_COUNTS = ("one two three four five six seven eight nine ten eleven twelve "
               "thirteen fourteen fifteen twenty thirty forty fifty hundred").split()
WORD_COUNT_RE = re.compile(
    r"\b(" + "|".join(WORD_COUNTS) + r")\b(?=\s+(?:of|out\s+of)\s+(?:the\s+)?"
    r"(?:\b(?:" + "|".join(WORD_COUNTS) + r")\b|\d))", re.I)


def check_cover_letter() -> list[tuple[str, str]]:
    """The cover letter is the first document an editor reads, and it sat
    outside this check while every other document was inside it. It therefore
    carried its own reproduction counts and contradicted Section 7.11. Same
    rule, same enforcement: results reach the letter through macros only."""
    path = ROOT / "paper" / "cover_letter.tex"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    text = text[text.index(r"\begin{document}"):]
    text = re.sub(r"(?m)%.*$", "", text)
    # Structural and identifying material: class options, margins, the author's
    # postal address, and cross-references to manuscript sections, which a
    # separate document cannot resolve with \ref.
    text = re.sub(r"\\(documentclass|usepackage|input|signature|address|opening|closing)"
                  r"\s*(\[[^\]]*\])?(\{[^}]*\})?", " ", text)
    text = re.sub(r"\\(begin|end)\{[^}]*\}", " ", text)
    text = re.sub(r"(Section|Table|Figure)~?\d+(\.\d+)*", " ", text)
    out = []
    for m in NUM.finditer(text):
        tok = m.group(1).rstrip(".,")
        if tok in ALLOWED:
            continue
        out.append((tok, text[max(0, m.start() - 60):m.start() + 40]
                    .replace("\n", " ").strip()))
    for m in WORD_COUNT_RE.finditer(text):
        out.append((m.group(1), text[max(0, m.start() - 60):m.start() + 60]
                    .replace("\n", " ").strip()))
    return out


def check_supplement_pointers(manuscript: str, supplement: str) -> list[str]:
    """Every 'Supplementary Note/Table SN' must resolve to something the
    supplement actually numbers. A pointer at a table is only valid if the
    supplement captions that many tables, which it will not do while its
    longtables carry no caption."""
    import re
    problems = []
    # Existence is not enough. Every pointer was reported as resolving while
    # three of them named the wrong note, because inserting a supplement section
    # ahead of the one they meant renumbered it and a pointer to "some note S8"
    # is satisfied by whatever now sits at position 8. Pointers must therefore be
    # written as generated macros, which are tied to a section title rather than
    # to a position, and a literal SN in the source is itself the defect.
    # Typed structural cross-references. Two of these went stale without anyone
    # noticing: the supplement pointed at "Proposition~5", which does not exist,
    # and at "Table~1 of the manuscript" for a footprint table that is Table 3.
    # Both survived every check because a hard-coded numeral is not a \ref and
    # is not a result number either, so neither existing rule looked at them.
    # A cross-reference must be a \ref, which LaTeX keeps correct, or it is a
    # number that will eventually be wrong.
    for doc, name in ((manuscript, "manuscript.tex"), (supplement, "supplementary.tex")):
        for kind, num in re.findall(r"\b(Proposition|Theorem|Lemma|Corollary)~?(\d+)", doc):
            problems.append(
                f"{name} hard-codes {kind}~{num}; use \\ref so it cannot go stale")
        for num in re.findall(r"\bTable~?(\d+) of the manuscript", doc):
            problems.append(
                f"{name} hard-codes Table~{num} of the manuscript; use \\ref")

    literal = re.findall(r"Supplementary (?:Note|Table)~?S(\d+)", manuscript)
    if literal:
        problems.append(
            f"{len(literal)} supplement pointer(s) written as a literal number "
            f"(S{', S'.join(sorted(set(literal)))}); use the generated \\Note* "
            f"macros so the pointer follows the section it names")
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
    # The newest bundle, not a hardcoded date: pinning the date meant that
    # exporting a fresh bundle silently moved it outside this guard, which is
    # exactly the bundle most likely to disagree with the current results.
    subs = sorted(ROOT.parent.glob("EM_Audio_Submission_*"))
    if not subs:
        return []
    sub = subs[-1]
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
    # The reproduction package for validators ships without paper/: they run
    # the experiments, not the manuscript. A missing manuscript is that case,
    # not a defect, so say so and succeed rather than ending their run.
    if not TEX.exists():
        print(f"[check_numbers] paper/ absent, so there is no manuscript to check; "
              "skipped. This is expected in the reproduction package.")
        return 0
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
    # An ORCID is a person's identifier wherever it appears, including the
    # acknowledgement of the independent reproducer, and is not a result.
    text = re.sub(r"ORCID\s+[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9X]{4}", " ", text)
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

    letter_bad = check_cover_letter()
    if letter_bad:
        print(f"{len(letter_bad)} possible hand-typed result number(s) in the cover letter:")
        for tok, ctx in letter_bad[:25]:
            print(f"  {tok!r}  ...{ctx}...")
        return 1

    print("no hand-typed result numbers found in the manuscript source")
    print("no hand-typed result numbers found in the cover letter")
    print("all supplement pointers resolve")
    print("bundle documents agree with the current results")
    return 0

if __name__ == "__main__":
    sys.exit(main())
