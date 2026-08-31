#!/usr/bin/env python3
"""Build the independent-reproduction package sent to a validator.

Distinct from build_validation_kit.py, which builds the Docker/Windows kit.
This one ships the source, the paper and the frozen reference results so a
reproducer can run the pipeline natively and compare.

results/machine_readable/ ships EMPTY on purpose: a comparison that finds the
author's own results already in place reports a match that never happened.
This build asserts that rather than trusting it.

    python3 tools/build_reproduction_package.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

# --returning writes the package for the reproducer whose run already failed.
RETURNING = "--returning" in sys.argv

# No paper/. A validator runs the experiments; the manuscript, its drafts and
# the reviews are not part of that, and shipping an unpublished manuscript to
# third parties is a decision that should be deliberate rather than incidental.
# The five tools that read paper/ skip and return 0 when it is absent.
INCLUDE = ["run_all.sh", "requirements.txt", "LICENSE", "DATA_LICENSES.md",
           "README.md", "CITATION.cff", "verify_release.sh", ".gitignore",
           "em_audio", "experiments", "tools", "tests", "oracle_js",
           "fixtures", "docs"]
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", "dist"}
EXCLUDE_SUFFIX = {".pyc", ".aux", ".out", ".fls", ".fdb_latexmk", ".blg",
                  ".spl", ".synctex.gz"}
EXCLUDE_NAMES = {".DS_Store"}


def copy_into(src: Path, dst: Path) -> None:
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    for p in sorted(src.rglob("*")):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.name in EXCLUDE_NAMES or p.suffix in EXCLUDE_SUFFIX:
            continue
        if p.is_file():
            t = dst / p.relative_to(src)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, t)


def main() -> int:
    tag = subprocess.run(["git", "describe", "--tags", "--always"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip() or "untagged"
    name = f"EM_Audio_reproduction_{tag}"
    stage = DIST / name
    if stage.exists():
        shutil.rmtree(stage)
    inner = stage / "em-audio"
    inner.mkdir(parents=True)

    for rel in INCLUDE:
        src = ROOT / rel
        if src.exists():
            copy_into(src, inner / rel)
        else:
            print(f"  note: {rel} absent, skipped")

    # The frozen reference is what the reproducer compares against.
    copy_into(ROOT / "results" / "reference", inner / "results" / "reference")
    for extra in ("PREFLIGHT.txt", "numbers.tex", "13_Figure_Data_Sources.md",
                  "14_Figure_QA.md"):
        f = ROOT / "results" / extra
        if f.exists():
            copy_into(f, inner / "results" / extra)
    for d in ("figures", "tables"):
        if (ROOT / "results" / d).is_dir():
            copy_into(ROOT / "results" / d, inner / "results" / d)

    # Empty by design, and asserted below. A zip does not carry empty
    # directories, so the reproducer would unpack a tree with no
    # results/machine_readable at all; ship a note that explains why it is bare
    # and that also makes the directory exist.
    mr = inner / "results" / "machine_readable"
    mr.mkdir(parents=True, exist_ok=True)
    (mr / "README.txt").write_text(
        "Empty on purpose.\n\n"
        "run_all.sh writes this directory. It ships bare so that\n"
        "verify_reproduction.py cannot compare the author's own results\n"
        "against themselves and report a match that never happened.\n\n"
        "After your run this holds the result files to send back.\n",
        encoding="utf-8")
    (inner / "corpus").mkdir(parents=True, exist_ok=True)
    ci = ROOT / "corpus" / "corpus_index.json"
    if ci.exists():
        shutil.copy2(ci, inner / "corpus" / "corpus_index.json")
    (inner / ".reproduction_package").write_text(
        f"built from {tag}\n", encoding="utf-8")

    # The two documents the reader opens first, at the top of the archive.
    # Two audiences. LEEME.txt apologises for a specific failed run and is for
    # the reproducer who hit it; LEEME_NUEVO/README_FIRST are for someone
    # starting fresh, to whom that apology would only be confusing.
    kitdir = ROOT / "release_kits" / "reproduction_es"
    if RETURNING:
        for src, dst in ((kitdir / "LEEME.txt", "LEEME.txt"),):
            if src.exists():
                shutil.copy2(src, stage / dst)
    else:
        for src, dst in ((kitdir / "LEEME_NUEVO.txt", "LEEME.txt"),
                         (kitdir / "README_FIRST.txt", "README_FIRST.txt")):
            if src.exists():
                shutil.copy2(src, stage / dst)
    guide = ROOT / "docs" / "REPRODUCTION_GUIDE.md"
    if guide.exists():
        shutil.copy2(guide, stage / "REPRODUCTION_GUIDE.md")

    # Assert the two properties the package's own honesty depends on.
    leftovers = list((inner / "results" / "machine_readable").glob("*.json"))
    if leftovers:
        print(f"REFUSING: results/machine_readable/ ships {len(leftovers)} result "
              "file(s). A comparison would match the author's results against "
              "themselves.")
        return 1
    if not list((inner / "results" / "reference").glob("*.json")):
        print("REFUSING: results/reference/ is empty, so there is nothing to "
              "compare against. Run tools/freeze_reference.py first.")
        return 1

    # The package must not carry the manuscript, and the pipeline must not need
    # it. Asserted, because "I removed the directory" and "the run still
    # succeeds without it" are different claims.
    if (inner / "paper").exists():
        print("REFUSING: the package contains paper/. The manuscript is not "
              "part of what a validator reproduces.")
        return 1
    stray = [q.relative_to(inner).as_posix() for q in inner.rglob("*")
             if q.is_file() and q.suffix in {".tex", ".bbl"}]
    if stray:
        print(f"REFUSING: manuscript sources reached the package: {stray[:5]}")
        return 1

    zpath = DIST / f"{name}.zip"
    if zpath.exists():
        zpath.unlink()
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                z.write(p, str(Path(name) / p.relative_to(stage)))
    mb = zpath.stat().st_size / 1e6
    print(f"[kit] {zpath}  ({mb:.1f} MB, tag {tag})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
