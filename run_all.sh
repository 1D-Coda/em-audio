#!/usr/bin/env bash
# One-command reproduction.  Exits non-zero on any conformance failure.
set -uo pipefail

# Resolve the interpreter once, and resolve it by RUNNING it.
#
# An independent validator's Windows run produced nothing at all: every step
# printed "no se encontro Python; ejecutar sin argumentos para instalar desde
# el Microsoft Store" and did no work. Windows ships an App Execution Alias at
# that name which exists, sits on PATH, and is not an interpreter, so
# `command -v python3` finds it and shutil.which reports it. Only executing it
# tells you. On a normal Windows install the interpreter is `python` or `py -3`.
#
# CI did not catch this and structurally could not: the hosted runner installs
# a Python that does provide python3, so the green Windows job never exercised
# the case an ordinary validator has.
. "$(cd "$(dirname "$0")" && pwd)"/tools/resolve_python.sh
resolve_python || { python_not_found_message; exit 2; }
export PY

# Dependency preflight. Daniel's reproduction ran for twenty minutes before
# dying on a missing module, and the failure surfaced as a traceback in the
# middle of the log rather than as an instruction. Check first, say what is
# missing, and say how to fix it.
missing_tools=""
for t in ffmpeg ffprobe node c2patool espeak-ng; do
  command -v "$t" >/dev/null 2>&1 || missing_tools="$missing_tools $t"
done
missing_py=$($PY - <<'PYCHK'
import importlib.util
need = {"matplotlib": "matplotlib", "numpy": "numpy", "piper": "piper-tts"}
out = [pkg for mod, pkg in need.items() if importlib.util.find_spec(mod) is None]
print(" ".join(out))
PYCHK
)
if [ -n "$missing_tools" ] || [ -n "$missing_py" ]; then
  echo "MISSING DEPENDENCIES"
  [ -n "$missing_tools" ] && echo "  command-line tools:$missing_tools"
  if [ -n "$missing_py" ]; then
    echo "  python packages:$missing_py"
    echo "  install with: pip install -r requirements.txt"
  fi
  echo
  echo "Install these before running. Continuing would produce a partial result"
  echo "set in which the experiments that could not run leave the shipped files"
  echo "in place, so a comparison against them reports a match that never"
  echo "happened."
  exit 2
fi
# Resolve the repository root once and address everything from it. Relative
# paths made the run depend on the working directory it happened to be started
# from, and a clean-clone check found A3 failing to open a tool that was present
# and executable. A reproduction script is the wrong place for that class of
# fragility: it fails on someone else's machine and looks like a missing file.
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONHASHSEED=0
fail=0
failed_steps=""
current_step="startup"
step () { current_step="$*"; echo; echo "=== $* ==="; }
# `|| note` records that something failed but not what. A Windows run
# completed every experiment, printed a pass line for every check, and still
# ended in RUN FAILED with nothing in 1,300 lines of log naming the step.
# `note` is called instead, and deliberately does not change how any command is
# invoked: an earlier attempt re-wrapped each step in `bash -c` and broke every
# one of them on quoting.
note () {
  local rc=$?
  echo "  ** FAILED (exit $rc) in step: $current_step"
  failed_steps="$failed_steps
  - $current_step (exit $rc)"
  fail=1
}

step "environment"
$PY -V; ffmpeg -version | head -1; c2patool --version; node -v; espeak-ng --version

step "test credential"
# These two were the only steps whose failure was not recorded. A corpus fetch
# that fails leaves the pipeline running against no corpus, and the first thing
# to notice is an experiment several steps later complaining that a clip does
# not exist, which names neither the step that failed nor the reason.
[ -f "$ROOT"/tools/test_certs/chain.pem ] || "$ROOT"/tools/make_test_certs.sh || note

step "corpus"
[ -d "$ROOT"/corpus/LibriSpeech/dev-clean ] || "$ROOT"/tools/fetch_corpus.sh || {
  echo "the corpus could not be fetched; every experiment that needs audio will"
  echo "fail after this, so stop here rather than reporting those as results."
  exit 2
}

step "named regression tests"
$PY "$ROOT"/tests/test_contract.py || note

step "A  exhaustive finite-state conformance"
( cd "$ROOT"/experiments && $PY synthetic_state_space.py ) || note

step "A2 applicability scope battery"
( cd "$ROOT"/experiments && $PY scope_battery.py ) || note

step "A3 calibration tool self-test (must reject an under-declaration)"
$PY "$ROOT"/tools/calibrate_footprint.py --self-test || note

step "B  deterministic adversarial timelines"
( cd "$ROOT"/experiments && $PY adversarial_timelines.py ) || note

step "B2 policy ablation"
( cd "$ROOT"/experiments && $PY adversarial_timelines.py --ablation ) || note

step "H  two-language differential oracle"
( cd "$ROOT"/experiments && $PY oracle_differential.py ) || note

step "C0 build mixed-origin corpus"
( cd "$ROOT"/experiments && $PY build_corpus.py ) || note

step "C  ground-truth recovery"
( cd "$ROOT"/experiments && $PY public_audio_splice.py ) || note

step "C2 voice model"
"$ROOT"/tools/fetch_voice.sh || note

step "C2 robustness arm (neural TTS + noise overlay)"
( cd "$ROOT"/experiments && $PY robustness_corpus.py ) || note

step "D  transformation matrix (stock ffmpeg)"
( cd "$ROOT"/experiments && $PY transform_matrix.py ) || note

step "K  kernel-support containment (impulse probe)"
( cd "$ROOT"/experiments && $PY support_containment.py ) || note

step "E  provenance-loss behaviour"
( cd "$ROOT"/experiments && $PY manifest_stripping.py ) || note

step "F  signed round-trip and signal transparency"
( cd "$ROOT"/experiments && $PY c2pa_roundtrip.py ) || note

step "G  overhead"
( cd "$ROOT"/experiments && $PY overhead_benchmark.py ) || note

step "G2 overhead stability across repeated runs"
( cd "$ROOT"/experiments && $PY overhead_stability.py ) || note

step "J  C2PA-native componentOf composition"
( cd "$ROOT"/experiments && $PY c2pa_composition.py ) || note

step "I  claim dilution (cost of conservatism)"
( cd "$ROOT"/experiments && $PY claim_dilution.py ) || note

# Table S5 and the calibration rows are built from CALIBRATION.json, which was a
# tracked result file that no pipeline step regenerated. On a working tree the
# committed copy is present and the table builds, so the gap was invisible here;
# in the reproduction package, whose results/machine_readable/ ships empty so a
# comparison cannot pass vacuously, nothing recreated it and make_tables.py died
# on the missing file. That is what ended the independent reproduction of
# Section 7.11 in RUN FAILED. The self-test above proves the tool rejects an
# under-declaration; this pass is what writes the evidence of record.
# Optional second reader. Section 9 names single-validator transport as a gap;
# this narrows it without claiming to close it, and is skipped rather than failed
# when the library is absent, because it is not a required dependency.
step "N  second C2PA reader (optional, skipped if c2pa-python is absent)"
# Advisory, not a gate. The paper depends on nothing here, and an optional
# check that can end a third party's run in RUN FAILED is the exact defect this
# release is fixing. Its result file is what we read; a non-zero exit is printed
# and recorded rather than propagated.
( cd "$ROOT"/experiments && $PY second_reader.py ) \
  || echo "  (advisory: the second reader reported a problem; see N_second_reader.json)"

step "A3b footprint calibration (writes CALIBRATION.json)"
$PY "$ROOT"/tools/calibrate_footprint.py || note

step "tables and figures"
$PY "$ROOT"/tools/make_tables.py || note
$PY "$ROOT"/tools/make_macros.py || note
$PY "$ROOT"/tools/make_highlights.py || note
$PY "$ROOT"/tools/make_figures.py || note
$PY "$ROOT"/tools/make_figures_shared.py || note
$PY "$ROOT"/tools/figure_qa.py || note
$PY "$ROOT"/tools/make_figure_docs.py || note

step "preflight report"
$PY "$ROOT"/tools/make_checksums.py || note
$PY "$ROOT"/tools/preflight.py || note
$PY "$ROOT"/tools/check_numbers.py || note
$PY "$ROOT"/tools/prose_audit.py || note
$PY "$ROOT"/tools/check_journal_guide.py || note
$PY "$ROOT"/tools/check_interpreter_calls.py || note

echo
if [ "$fail" -ne 0 ]; then
  echo "RUN FAILED"
  echo "the step(s) that failed:$failed_steps"
  exit 1
fi
echo "RUN OK - all conformance checks passed"
