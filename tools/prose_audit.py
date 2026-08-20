"""Audit manuscript prose for machine-writing tells.

A hit is a defect to triage, not automatically to fix: a flagged word is
sometimes the correct technical term (a test *harness*, a *robustness* arm).
Exits non-zero only on em dashes, which are never wanted in prose.
"""
from __future__ import annotations

import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / "paper" / "manuscript.tex", ROOT / "paper" / "cover_letter.tex"]

VOCAB = ("delve|landscape|realm|paradigm|seamless|meticulous|pivotal|underscores|"
         "cutting-edge|holistic|actionable|impactful|nuanced|myriad|plethora|"
         "facilitate|foster|empower|streamline|leverage|utilize|testament to|"
         "game-chang|deep dive|unpack|ever-evolving|at its core|best practices")
FILLER = ("it is worth noting|it is important to note|it is worth being explicit|"
          "\\bnotably\\b|\\binterestingly\\b|\\bmoreover\\b|\\bfurthermore\\b|"
          "\\badditionally\\b|in conclusion|to summari[sz]e|that being said|"
          "at the end of the day|in order to|due to the fact that|when it comes to|"
          "the reality is|\\blet's\\b|serves as|\\bboasts\\b")


def check_rendered_periods(pdf_path):
    """elsarticle's \\paragraph appends its own period, so a heading that already
    ends in one renders as two. The source reads correctly either way, so this
    is only visible in the built PDF and only worth checking there."""
    import subprocess
    try:
        txt = subprocess.run(["pdftotext", str(pdf_path), "-"],
                             capture_output=True, text=True).stdout
    except FileNotFoundError:
        return []
    return sorted(set(re.findall(r"[A-Za-z][a-z]+\.\.", txt)))


def main() -> int:
    fail = 0
    for path in TARGETS:
        if not path.exists():
            continue
        text = path.read_text()
        prose = "\n".join(l for l in text.splitlines()
                          if "&" not in l and not l.strip().startswith("%"))
        dashes = len(re.findall(r"---", prose)) + prose.count("—")
        vocab = re.findall(VOCAB, prose, re.I)
        filler = re.findall(FILLER, prose, re.I)
        print(f"{path.name}: em-dashes {dashes}, vocabulary hits {len(vocab)}, "
              f"filler hits {len(filler)}")
        for label, hits in (("vocabulary", vocab), ("filler", filler)):
            if hits:
                print(f"   {label}: {sorted(set(h.lower() for h in hits))}")
        if dashes:
            fail = 1

        pdf = path.with_suffix(".pdf")
        if pdf.exists():
            doubled = check_rendered_periods(pdf)
            if doubled:
                print(f"   {len(doubled)} doubled period(s) in the rendered PDF: "
                      f"{doubled[:6]}")
                fail = 1
    return fail


if __name__ == "__main__":
    sys.exit(main())
