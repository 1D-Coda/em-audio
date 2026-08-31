#!/usr/bin/env python3
"""Check the manuscript against the target journal's guide for authors.

The companion paper was returned before review by Computers and Geosciences for
missing line numbers and for length, which is a class of failure that costs a
submission cycle and is entirely mechanical to detect. These are the checks that
can be run rather than remembered, taken from the FSI: Digital Investigation
guide for authors. It exits non-zero so the pipeline fails on a violation.

What it cannot check is listed at the end of its own output, because a checklist
that silently omits its blind spots reads as coverage it does not have.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "paper" / "manuscript.tex"
HIGHLIGHTS = ROOT / "paper" / "highlights.txt"

ABSTRACT_MAX_WORDS = 250
HIGHLIGHT_MAX_CHARS = 85
HIGHLIGHT_RANGE = (3, 5)
KEYWORD_RANGE = (1, 7)

# The guide names this section exactly; a paraphrase is a returned submission.
AI_SECTION = ("Declaration of generative AI and AI-assisted technologies in "
              "the manuscript preparation process")


def words(tex: str) -> int:
    """Word count as the journal would see it, with each macro one number."""
    t = re.sub(r"\\[A-Za-z]+\{\}", "0", tex)
    t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", t)
    return len(re.sub(r"[{}$~\\]", " ", t).split())


def main() -> int:
    s = TEX.read_text()
    bad = []

    ab = s[s.index(r"\begin{abstract}") + 16:s.index(r"\end{abstract}")]
    n = words(ab)
    if n > ABSTRACT_MAX_WORDS:
        bad.append(f"abstract is {n} words, {n - ABSTRACT_MAX_WORDS} over the "
                   f"{ABSTRACT_MAX_WORDS}-word limit")

    kw = s[s.index(r"\begin{keyword}") + 15:s.index(r"\end{keyword}")]
    ks = [k.strip() for k in kw.split(r"\sep") if k.strip()]
    if not KEYWORD_RANGE[0] <= len(ks) <= KEYWORD_RANGE[1]:
        bad.append(f"{len(ks)} keywords; the guide allows "
                   f"{KEYWORD_RANGE[0]} to {KEYWORD_RANGE[1]}")

    if HIGHLIGHTS.exists():
        hl = [l for l in HIGHLIGHTS.read_text().splitlines() if l.strip()]
        if not HIGHLIGHT_RANGE[0] <= len(hl) <= HIGHLIGHT_RANGE[1]:
            bad.append(f"{len(hl)} highlights; the guide requires "
                       f"{HIGHLIGHT_RANGE[0]} to {HIGHLIGHT_RANGE[1]}")
        for i, l in enumerate(hl, 1):
            if len(l) > HIGHLIGHT_MAX_CHARS:
                bad.append(f"highlight {i} is {len(l)} characters, "
                           f"{len(l) - HIGHLIGHT_MAX_CHARS} over the limit")
    else:
        bad.append("highlights.txt is missing")

    if r"\linenumbers" not in s:
        bad.append("no line numbers; this is what the companion paper was "
                   "returned for")

    if f"\\section*{{{AI_SECTION}}}" not in s:
        bad.append("the generative-AI section title does not match the guide "
                   "word for word")

    # The guide requires the acknowledgements to sit directly before the
    # reference list, not merely somewhere near the end.
    order = re.findall(r"\\section\*\{([^}]+)\}|\\(bibliographystyle)", s)
    flat = [a or b for a, b in order]
    if "Acknowledgements" in flat:
        if flat.index("Acknowledgements") != flat.index("bibliographystyle") - 1:
            bad.append("acknowledgements are not directly before the reference "
                       "list")

    # The assertion label and schema URI appear inside a verbatim block in the
    # supplement, where LaTeX macros do not expand, so that one occurrence
    # cannot be generated like the rest and has to be checked instead.
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from em_audio import manifest_schema as _ms
    supp = (ROOT / "paper" / "supplementary.tex").read_text()
    if f'"schema": "{_ms.SCHEMA}"' not in supp:
        bad.append("the schema URI in the supplement's verbatim payload does "
                   "not match em_audio/manifest_schema.py")
    for f in ("paper/manuscript.tex", "paper/supplementary.tex", "CITATION.cff"):
        t = (ROOT / f).read_text()
        # the corresponding-author email is a contact, not a namespace
        t = t.replace("alex@aurtech.mx", "")
        if "aurtech" in t.lower():
            bad.append(f"{f} still names the retired namespace")

    if bad:
        print(f"[guide] {len(bad)} violation(s) of the guide for authors:")
        for b in bad:
            print(f"        {b}")
    else:
        print("[guide] abstract, keywords, highlights, line numbers, section "
              "titles and order all conform")

    # Stated rather than silently skipped: a checklist that hides its gaps
    # reads as coverage it does not have.
    print("[guide] not checked here, verify by hand before submitting:")
    for item in ("page count against what the journal actually publishes",
                 "reference style is settled: three recent FSI:DI articles have "
                 "alphabetical reference lists, so author-year; the manuscript "
                 "now uses elsarticle-harv with the authoryear class option",
                 "competing-interest declaration exported as .doc/.docx from "
                 "Elsevier's declarations tool",
                 "figures uploaded as separate files named Figure_1, Figure_2",
                 "first-author biography, 200 words maximum",
                 "research data deposited and cited: Option C is required, not "
                 "encouraged"):
        print(f"        {item}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
