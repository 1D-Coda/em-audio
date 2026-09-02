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

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

# --returning writes the package for the reproducer whose run already failed.
RETURNING = "--returning" in sys.argv
# --mac ships the macOS letter and the double-clickable entry point.
MAC = "--mac" in sys.argv

# No paper/. A validator runs the experiments; the manuscript, its drafts and
# the reviews are not part of that, and shipping an unpublished manuscript to
# third parties is a decision that should be deliberate rather than incidental.
# The five tools that read paper/ skip and return 0 when it is absent.
INCLUDE = ["run_all.sh", "requirements.txt", "LICENSE", "DATA_LICENSES.md",
           "README.md", "CITATION.cff",
           "em_audio", "experiments", "tools", "tests", "oracle_js",
           "fixtures", "docs"]
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", "dist"}
EXCLUDE_SUFFIX = {".pyc", ".aux", ".out", ".fls", ".fdb_latexmk", ".blg",
                  ".spl", ".synctex.gz"}
EXCLUDE_NAMES = {".DS_Store"}

# Tooling for building releases and packages. A validator runs the experiments;
# none of this is part of that, and shipping it only invites the question of
# what it is for. explain_failure.py stays: it is what turns a traceback in
# their log into a cause. run_container/run_on_windows stay: the Docker path is
# documented and they are its entry points.
EXCLUDE_TOOLS = {"build_reproduction_package.py", "build_validation_kit.py",
                 "freeze_reference.py", "make_repro_docx.py"}

# Written by the pipeline on their machine. Shipping our copies adds bulk and,
# worse, leaves outputs lying in the tree that their run is supposed to produce.
EXCLUDE_RESULTS = {"figures", "tables"}

# Internal: how we cut a release, publish the repository and deposit the
# archive. Nothing a reproducer does.
EXCLUDE_DOCS = {"PUBLISH_REPO.md", "RELEASE_AND_DEPOSIT.md",
                "RELEASE_CHECKLIST.md", "reference_figures"}


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
        rel = p.relative_to(src)
        if src.name == "tools" and rel.name in EXCLUDE_TOOLS:
            continue
        if src.name == "docs" and rel.parts[0] in EXCLUDE_DOCS:
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
    elif MAC:
        if (kitdir / "LEEME_MAC.txt").exists():
            shutil.copy2(kitdir / "LEEME_MAC.txt", stage / "LEEME.txt")
        # At the top of the archive, where a double click finds it.
        cmd = ROOT / "tools" / "Reproducir_en_Mac.command"
        if cmd.exists():
            dst = stage / "Reproducir_en_Mac.command"
            shutil.copy2(cmd, dst)
            dst.chmod(0o755)
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
    # Narrowed to the manuscript's own documents. results/numbers.tex and
    # results/tables/*.tex are generated by the pipeline and belong here; the
    # first version of this check flagged them and refused to build.
    MANUSCRIPT = {"manuscript.tex", "supplementary.tex", "cover_letter.tex",
                  "refs.bib", "manuscript.pdf", "supplementary.pdf",
                  "cover_letter.pdf", "manuscript.bbl", "highlights.txt"}
    stray = [q.relative_to(inner).as_posix() for q in inner.rglob("*")
             if q.is_file() and q.name in MANUSCRIPT]
    if stray:
        print(f"REFUSING: manuscript documents reached the package: {stray[:5]}")
        return 1

    # Import every experiment and tool from the staged tree before shipping it.
    # A missing import once reached both a commit and a built archive: the
    # package looked complete, and C0 would have died with a NameError on every
    # validator's machine. Syntax is not enough; the module has to load.
    broken = []
    for q in sorted(list((inner / "experiments").glob("*.py"))
                    + list((inner / "em_audio").glob("*.py"))
                    + list((inner / "tools").glob("*.py"))):
        try:
            compile(q.read_text(), str(q), "exec")
        except SyntaxError as exc:
            broken.append(f"{q.relative_to(inner)}: {exc}")
    check = subprocess.run(
        [sys.executable, "-c",
         "import importlib.util, pathlib, sys\n"
         "sys.path[:0] = ['experiments', '.']\n"
         "for q in sorted(pathlib.Path('experiments').glob('*.py')):\n"
         "    if q.stem.startswith('_'): continue\n"
         "    spec = importlib.util.spec_from_file_location(q.stem, q)\n"
         "    m = importlib.util.module_from_spec(spec)\n"
         "    try: spec.loader.exec_module(m)\n"
         "    except SystemExit: pass\n"
         "    except Exception as e: print(f'{q}: {type(e).__name__}: {e}')\n"],
        cwd=inner, capture_output=True, text=True)
    if check.stdout.strip():
        broken += check.stdout.strip().splitlines()
    if broken:
        print("REFUSING: the staged package does not import cleanly:")
        for b in broken[:10]:
            print(f"  {b}")
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
