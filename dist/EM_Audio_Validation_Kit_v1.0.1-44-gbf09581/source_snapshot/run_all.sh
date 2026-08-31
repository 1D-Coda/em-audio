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
cd "$ROOT"
export PYTHONHASHSEED=0
fail=0
step () { echo; echo "=== $* ==="; }

step "environment"
python3 -V; ffmpeg -version | head -1; c2patool --version; node -v; espeak-ng --version

step "test credential"
# These two were the only steps whose failure was not recorded. A corpus fetch
# that fails leaves the pipeline running against no corpus, and the first thing
# to notice is an experiment several steps later complaining that a clip does
# not exist, which names neither the step that failed nor the reason.
[ -f "$ROOT"/tools/test_certs/chain.pem ] || "$ROOT"/tools/make_test_certs.sh || fail=1

step "corpus"
[ -d "$ROOT"/corpus/LibriSpeech/dev-clean ] || "$ROOT"/tools/fetch_corpus.sh || {
  echo "the corpus could not be fetched; every experiment that needs audio will"
  echo "fail after this, so stop here rather than reporting those as results."
  exit 2
}

step "named regression tests"
python3 "$ROOT"/tests/test_contract.py || fail=1

step "A  exhaustive finite-state conformance"
( cd "$ROOT"/experiments && python3 synthetic_state_space.py ) || fail=1

step "A2 applicability scope battery"
( cd "$ROOT"/experiments && python3 scope_battery.py ) || fail=1

step "A3 calibration tool self-test (must reject an under-declaration)"
python3 "$ROOT"/tools/calibrate_footprint.py --self-test || fail=1

step "B  deterministic adversarial timelines"
( cd "$ROOT"/experiments && python3 adversarial_timelines.py ) || fail=1

step "B2 policy ablation"
( cd "$ROOT"/experiments && python3 adversarial_timelines.py --ablation ) || fail=1

step "H  two-language differential oracle"
( cd "$ROOT"/experiments && python3 oracle_differential.py ) || fail=1

step "C0 build mixed-origin corpus"
( cd "$ROOT"/experiments && python3 build_corpus.py ) || fail=1

step "C  ground-truth recovery"
( cd "$ROOT"/experiments && python3 public_audio_splice.py ) || fail=1

step "C2 voice model"
"$ROOT"/tools/fetch_voice.sh || fail=1

step "C2 robustness arm (neural TTS + noise overlay)"
( cd "$ROOT"/experiments && python3 robustness_corpus.py ) || fail=1

step "D  transformation matrix (stock ffmpeg)"
( cd "$ROOT"/experiments && python3 transform_matrix.py ) || fail=1

step "K  kernel-support containment (impulse probe)"
( cd "$ROOT"/experiments && python3 support_containment.py ) || fail=1

step "E  provenance-loss behaviour"
( cd "$ROOT"/experiments && python3 manifest_stripping.py ) || fail=1

step "F  signed round-trip and signal transparency"
( cd "$ROOT"/experiments && python3 c2pa_roundtrip.py ) || fail=1

step "G  overhead"
( cd "$ROOT"/experiments && python3 overhead_benchmark.py ) || fail=1

step "G2 overhead stability across repeated runs"
( cd "$ROOT"/experiments && python3 overhead_stability.py ) || fail=1

step "J  C2PA-native componentOf composition"
( cd "$ROOT"/experiments && python3 c2pa_composition.py ) || fail=1

step "I  claim dilution (cost of conservatism)"
( cd "$ROOT"/experiments && python3 claim_dilution.py ) || fail=1

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
python3 "$ROOT"/tools/calibrate_footprint.py || fail=1

step "tables and figures"
python3 "$ROOT"/tools/make_tables.py || fail=1
python3 "$ROOT"/tools/make_macros.py || fail=1
python3 "$ROOT"/tools/make_highlights.py || fail=1
python3 "$ROOT"/tools/make_figures.py || fail=1
python3 "$ROOT"/tools/make_figures_shared.py || fail=1
python3 "$ROOT"/tools/figure_qa.py || fail=1
python3 "$ROOT"/tools/make_figure_docs.py || fail=1

step "preflight report"
python3 "$ROOT"/tools/make_checksums.py || fail=1
python3 "$ROOT"/tools/preflight.py || fail=1
python3 "$ROOT"/tools/check_numbers.py || fail=1
python3 "$ROOT"/tools/prose_audit.py || fail=1
python3 "$ROOT"/tools/check_journal_guide.py || fail=1

echo
if [ "$fail" -ne 0 ]; then echo "RUN FAILED"; exit 1; fi
echo "RUN OK - all conformance checks passed"
