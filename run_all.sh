#!/usr/bin/env bash
# One-command reproduction.  Exits non-zero on any conformance failure.
set -uo pipefail
cd "$(dirname "$0")"
export PYTHONHASHSEED=0
fail=0
step () { echo; echo "=== $* ==="; }

step "environment"
python3 -V; ffmpeg -version | head -1; c2patool --version; node -v; espeak-ng --version

step "test credential"
[ -f tools/test_certs/chain.pem ] || ./tools/make_test_certs.sh

step "corpus"
[ -d corpus/LibriSpeech/dev-clean ] || ./tools/fetch_corpus.sh

step "named regression tests"
python3 tests/test_contract.py || fail=1

step "A  exhaustive finite-state conformance"
( cd experiments && python3 synthetic_state_space.py ) || fail=1

step "B  deterministic adversarial timelines"
( cd experiments && python3 adversarial_timelines.py ) || fail=1

step "B2 policy ablation"
( cd experiments && python3 adversarial_timelines.py --ablation ) || fail=1

step "H  two-language differential oracle"
( cd experiments && python3 oracle_differential.py ) || fail=1

step "C0 build mixed-origin corpus"
( cd experiments && python3 build_corpus.py ) || fail=1

step "C  ground-truth recovery"
( cd experiments && python3 public_audio_splice.py ) || fail=1

step "D  transformation matrix (stock ffmpeg)"
( cd experiments && python3 transform_matrix.py ) || fail=1

step "E  provenance-loss behaviour"
( cd experiments && python3 manifest_stripping.py ) || fail=1

step "F  signed round-trip and signal transparency"
( cd experiments && python3 c2pa_roundtrip.py ) || fail=1

step "G  overhead"
( cd experiments && python3 overhead_benchmark.py ) || fail=1

step "I  claim dilution (cost of conservatism)"
( cd experiments && python3 claim_dilution.py ) || fail=1

step "tables and figures"
python3 tools/make_tables.py || fail=1
python3 tools/make_macros.py || fail=1
python3 tools/make_highlights.py || fail=1
python3 tools/make_figures.py || fail=1

step "preflight report"
python3 tools/preflight.py || fail=1
python3 tools/check_numbers.py || fail=1

echo
if [ "$fail" -ne 0 ]; then echo "RUN FAILED"; exit 1; fi
echo "RUN OK - all conformance checks passed"
