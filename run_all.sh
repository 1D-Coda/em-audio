#!/usr/bin/env bash
# One-command reproduction.  Exits non-zero on any conformance failure.
set -uo pipefail

# Dependency preflight. Daniel's reproduction ran for twenty minutes before
# dying on a missing module, and the failure surfaced as a traceback in the
# middle of the log rather than as an instruction. Check first, say what is
# missing, and say how to fix it.
missing_tools=""
for t in ffmpeg ffprobe node c2patool espeak-ng; do
  command -v "$t" >/dev/null 2>&1 || missing_tools="$missing_tools $t"
done
missing_py=$(python3 - <<'PYCHK'
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
# Exported because the step runner starts each experiment in its own shell, and
# an unexported ROOT would expand to nothing there.
export ROOT
cd "$ROOT"
export PYTHONHASHSEED=0
fail=0
failed_steps=""
current_step="startup"
step () { current_step="$*"; echo; echo "=== $* ==="; }
# `|| fail=1` records that something failed but not what. A Windows run
# completed every experiment, printed a pass line for every check, and still
# ended in RUN FAILED with nothing naming the step: finding it meant reading
# 1,300 lines of CI log. Record the name at the point of failure instead.
run () {
  # Captured on the failure branch itself. An `if cmd; then return 0; fi`
  # leaves $? at 0 when the command fails, because the `if` statement succeeded,
  # and every failure was reported as exit 0.
  local rc=0
  "$@" || rc=$?
  [ "$rc" -eq 0 ] && return 0
  echo "  ** FAILED (exit $rc) in step '$current_step': $*"
  failed_steps="$failed_steps
  - $current_step: $* (exit $rc)"
  fail=1
  return 0
}

step "environment"
python3 -V; ffmpeg -version | head -1; c2patool --version; node -v; espeak-ng --version

step "test credential"
# These two were the only steps whose failure was not recorded. A corpus fetch
# that fails leaves the pipeline running against no corpus, and the first thing
# to notice is an experiment several steps later complaining that a clip does
# not exist, which names neither the step that failed nor the reason.
[ -f "$ROOT"/tools/test_certs/chain.pem ] || "$ROOT"/tools/make_test_certs.sh || fail=1  # a missing credential is caught by the next step

step "corpus"
[ -d "$ROOT"/corpus/LibriSpeech/dev-clean ] || "$ROOT"/tools/fetch_corpus.sh || {
  echo "the corpus could not be fetched; every experiment that needs audio will"
  echo "fail after this, so stop here rather than reporting those as results."
  exit 2
}

step "named regression tests"
run python3 "$ROOT"/tests/test_contract.py

step "A  exhaustive finite-state conformance"
run bash -c \'cd "$ROOT"/experiments && python3 synthetic_state_space.py\'

step "A2 applicability scope battery"
run bash -c \'cd "$ROOT"/experiments && python3 scope_battery.py\'

step "A3 calibration tool self-test (must reject an under-declaration)"
run python3 "$ROOT"/tools/calibrate_footprint.py --self-test

step "B  deterministic adversarial timelines"
run bash -c \'cd "$ROOT"/experiments && python3 adversarial_timelines.py\'

step "B2 policy ablation"
run bash -c \'cd "$ROOT"/experiments && python3 adversarial_timelines.py --ablation\'

step "H  two-language differential oracle"
run bash -c \'cd "$ROOT"/experiments && python3 oracle_differential.py\'

step "C0 build mixed-origin corpus"
run bash -c \'cd "$ROOT"/experiments && python3 build_corpus.py\'

step "C  ground-truth recovery"
run bash -c \'cd "$ROOT"/experiments && python3 public_audio_splice.py\'

step "C2 voice model"
run "$ROOT"/tools/fetch_voice.sh

step "C2 robustness arm (neural TTS + noise overlay)"
run bash -c \'cd "$ROOT"/experiments && python3 robustness_corpus.py\'

step "D  transformation matrix (stock ffmpeg)"
run bash -c \'cd "$ROOT"/experiments && python3 transform_matrix.py\'

step "K  kernel-support containment (impulse probe)"
run bash -c \'cd "$ROOT"/experiments && python3 support_containment.py\'

step "E  provenance-loss behaviour"
run bash -c \'cd "$ROOT"/experiments && python3 manifest_stripping.py\'

step "F  signed round-trip and signal transparency"
run bash -c \'cd "$ROOT"/experiments && python3 c2pa_roundtrip.py\'

step "G  overhead"
run bash -c \'cd "$ROOT"/experiments && python3 overhead_benchmark.py\'

step "G2 overhead stability across repeated runs"
run bash -c \'cd "$ROOT"/experiments && python3 overhead_stability.py\'

step "J  C2PA-native componentOf composition"
run bash -c \'cd "$ROOT"/experiments && python3 c2pa_composition.py\'

step "I  claim dilution (cost of conservatism)"
run bash -c \'cd "$ROOT"/experiments && python3 claim_dilution.py\'

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
( cd "$ROOT"/experiments && python3 second_reader.py ) \
  || echo "  (advisory: the second reader reported a problem; see N_second_reader.json)"

step "A3b footprint calibration (writes CALIBRATION.json)"
run python3 "$ROOT"/tools/calibrate_footprint.py

step "tables and figures"
run python3 "$ROOT"/tools/make_tables.py
run python3 "$ROOT"/tools/make_macros.py
run python3 "$ROOT"/tools/make_highlights.py
run python3 "$ROOT"/tools/make_figures.py
run python3 "$ROOT"/tools/make_figures_shared.py
run python3 "$ROOT"/tools/figure_qa.py
run python3 "$ROOT"/tools/make_figure_docs.py

step "preflight report"
run python3 "$ROOT"/tools/make_checksums.py
run python3 "$ROOT"/tools/preflight.py
run python3 "$ROOT"/tools/check_numbers.py
run python3 "$ROOT"/tools/prose_audit.py
run python3 "$ROOT"/tools/check_journal_guide.py

echo
if [ "$fail" -ne 0 ]; then
  echo "RUN FAILED"
  echo "the step(s) that failed:$failed_steps"
  exit 1
fi
echo "RUN OK - all conformance checks passed"
