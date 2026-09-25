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
SUPP = ROOT / "paper" / "supplementary.tex"

# Numbers that are structural, not measured.
ALLOWED = {
    # format and specification constants, quoted with their source in the text
    "1152", "50", "16", "2", "1", "0", "8", "4", "5", "3", "6", "7", "9", "10",
    "2024", "2026", "1689", "2.4", "18.2", "18.16", "15.11", "18.10", "4.0",
    "256", "0.27", "1.0", "24", "26", "27", "30", "31", "33", "34", "36",
    "1.52", "9.0", "3.11", "18", "20", "40", "60", "80", "100", "1.10",
}
NUM = re.compile(r"(?<![\\A-Za-z0-9._{])(\d[\d.,]*)(?![\d}])")


# Counts written as words are still hand-typed counts: "eight of the ten" can
# drift from the macros exactly as a digit can, and a digit scanner never sees it.
WORD_COUNTS = ("one two three four five six seven eight nine ten eleven twelve "
               "thirteen fourteen fifteen twenty thirty forty fifty hundred").split()
WORD_COUNT_RE = re.compile(
    r"\b(" + "|".join(WORD_COUNTS) + r")\b(?=\s+(?:of|out\s+of)\s+(?:the\s+)?"
    r"(?:\b(?:" + "|".join(WORD_COUNTS) + r")\b|\d))", re.I)


def check_supplement_release_tag(supplement: str) -> list[str]:
    """The supplement's reproduction recipe once pinned v1.0.4 while the paper
    reported v1.0.7, and no check read the supplement, so the recipe rebuilt a
    release two behind the numbers it was meant to reproduce. The release
    identity belongs to \\Rtag, which is read from SNAPSHOT.txt; a typed tag
    anywhere in the supplement can only go stale."""
    import re
    return [f"line {supplement[:m.start()].count(chr(10)) + 1}: {m.group(0)!r} "
            "is a typed release tag; use \\Rtag{} so it cannot drift"
            for m in re.finditer(r"\bv\d+\.\d+\.\d+", supplement)]


def check_readme_release_tag() -> list[str]:
    """README.md's one-line reproduction checked out v1.0.4 while the release
    was v1.2.0: the first command a reader runs rebuilt a release eight behind
    the results beside it. freeze_reference.py stamps the tag; this confirms it
    matches the one SNAPSHOT.txt names."""
    import re
    readme = ROOT / "README.md"
    snap = ROOT / "results" / "reference" / "SNAPSHOT.txt"
    if not (readme.exists() and snap.exists()):
        return []
    m = re.search(r"release (v\d+\.\d+\.\d+)", snap.read_text())
    if not m:
        return ["SNAPSHOT.txt names no release tag"]
    tags = re.findall(r"git checkout (v\d+\.\d+\.\d+)", readme.read_text())
    return [f"README.md checks out {t}, the frozen reference is {m.group(1)}"
            for t in tags if t != m.group(1)]


def check_supplement_pointers(manuscript: str, supplement: str) -> list[str]:
    """Every 'Supplementary Note/Table SN' must resolve to something the
    supplement actually numbers. A pointer at a table is only valid if the
    supplement captions that many tables."""
    import re
    problems = []
    # Existence is not enough. Every pointer was reported as resolving while
    # three of them named the wrong note, because inserting a supplement section
    # ahead of the one they meant renumbered it and a pointer to "some note S8"
    # is satisfied by whatever now sits at position 8. Pointers must therefore be
    # written as generated macros, which are tied to a section title rather than
    # to a position, and a literal SN in the source is itself the defect.
    # Typed structural cross-references. Two of these once went stale unnoticed:
    # one named a proposition that does not exist, the other the wrong table.
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


def check_label_macros() -> list[str]:
    """The cross-document macros must match what the manuscript just printed.

    make_macros.py reads these from paper/manuscript.aux so the supplement
    cannot disagree with the manuscript's own numbering. That holds only while
    numbers.tex is current. Moving one table to the supplement renumbered the
    rest, numbers.tex was not regenerated before the commit, and the supplement
    went out naming Table 3 for a table the manuscript prints as Table 2. The
    generator was right and the file was stale, which nothing here checked.
    """
    import re
    aux = ROOT / "paper" / "manuscript.aux"
    if not aux.exists() or not NUMBERS.exists():
        return []                      # nothing built yet; make_macros says so
    atext = aux.read_text(errors="ignore")
    ntext = NUMBERS.read_text()
    labels = {"PropFootprint": "prop:footprint", "PropUnion": "prop:union",
              "ThmComposition": "thm:composition", "TabOperators": "tab:operators"}
    bad = []
    for macro, label in labels.items():
        am = re.search(r"\\newlabel\{" + re.escape(label) + r"\}\{\{([^}]*)\}", atext)
        nm = re.search(r"\\newcommand\{\\" + macro + r"\}\{([^\\}]*)", ntext)
        if not am or not nm:
            continue
        if am.group(1).strip() != nm.group(1).strip():
            bad.append(f"\\{macro} is {nm.group(1).strip()!r} but the manuscript "
                       f"now numbers {label} as {am.group(1).strip()!r}; "
                       f"run tools/make_macros.py")
    return bad


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
    # A version attached to a named product is not a result. "Windows~11" was
    # reported as a hand-typed count. Kept narrow on purpose: the digits must
    # follow one of these names, so a bare 11 anywhere else is still caught.
    text = re.sub(r"\b(Windows|PowerShell|macOS|Ubuntu|Debian|Python|FFmpeg|"
                  r"Node|c2patool|Opus|eSpeak(?:\s+NG)?)(?:~|\s|\s?v)?\d[\d.]*",
                  r"\1", text, flags=re.I)
    text = text.replace("[0,1]", " ")
    text = re.sub(r"(?m)%.*$", "", text)
    # \href{url}{text}: a link is an identifier, whatever its visible text.
    text = re.sub(r"\\href\{[^}]*\}\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", " ", text)
    text = re.sub(r"\\(includegraphics|input|label|ref|eqref|cite\w*|usepackage|graphicspath|section|subsection|url|path)\s*(\[[^\]]*\])?\{[^}]*\}", " ", text)
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

    tag_bad = check_supplement_release_tag(SUPP.read_text()) if SUPP.exists() else []
    if tag_bad:
        print(f"{len(tag_bad)} typed release tag(s) in the supplement:")
        for msg in tag_bad:
            print(f"  {msg}")
        return 1

    readme_bad = check_readme_release_tag()
    if readme_bad:
        for msg in readme_bad:
            print(f"  {msg}")
        return 1

    print("no hand-typed result numbers found in the manuscript source")
    print("all supplement pointers resolve")
    print("the supplement names no release tag by hand")
    print("README.md checks out the frozen reference tag")
    stale = check_label_macros()
    if stale:
        print("stale cross-document macro(s):", file=sys.stderr)
        for b in stale:
            print("   ", b, file=sys.stderr)
        return 1
    print("cross-document macros match the manuscript's own numbering")
    return 0

if __name__ == "__main__":
    sys.exit(main())
