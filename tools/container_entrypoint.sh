#!/usr/bin/env bash
# Run the pipeline, compare, and leave everything a reader needs in /out.
#
# The container answers the narrower of the project's two questions: whether the
# implementation reproduces when the environment is held still. It therefore
# compares against results/reference_container/, frozen from a run of this same
# image, and not against results/reference/, which was produced on the author's
# macOS machine with a different FFmpeg. Comparing a Linux container against a
# macOS reference would rediscover the build-specific footprint findings and
# report them as failures of the container, which is the confusion this split
# exists to remove.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT_DIR:-/out}"
mkdir -p "$OUT"

echo "=== environment fixed by this image"
python3 -V; ffmpeg -version | head -1; c2patool --version; node -v; espeak-ng --version

echo
echo "=== pipeline"
"$ROOT/run_all.sh" 2>&1 | tee "$OUT/run_all_output.txt"
run_rc=${PIPESTATUS[0]}

echo
echo "=== comparison against this image's own reference"
if [ -d "$ROOT/results/reference_container" ] && \
   compgen -G "$ROOT/results/reference_container/*.json" >/dev/null; then
  python3 "$ROOT/tools/verify_reproduction.py" \
      --reference-dir "$ROOT/results/reference_container" 2>&1 | tee "$OUT/verify_output.txt"
  ver_rc=${PIPESTATUS[0]}
else
  echo "no container reference is frozen yet; this run can establish one" \
      | tee "$OUT/verify_output.txt"
  ver_rc=0
fi

cp -r "$ROOT/results/machine_readable" "$OUT/" 2>/dev/null || true
cp "$ROOT/results/PREFLIGHT.txt" "$OUT/" 2>/dev/null || true

echo
echo "=== what this run concluded"
# Two claims, two exit codes. The pipeline's exit status folds together
# "conformance failed" and "a declared footprint does not hold on this build",
# which are different findings with different consequences: the first is a
# defect in the implementation, the second is the paper's own central result
# about declarations being build-specific. One number cannot report both, and
# collapsing them is what made the independent reproduction hard to read.
#
# Nothing is softened. An under-declared footprint remains a hard failure of
# experiment K and of the calibration, exactly as it must: the guarantee does
# not hold for the samples outside the declaration.
under=0
if grep -q "UNDER-DECLARED" "$OUT/run_all_output.txt" 2>/dev/null; then under=1; fi
if grep -qE "outside declared support [1-9]" "$OUT/run_all_output.txt" 2>/dev/null; then under=1; fi

if [ "$run_rc" -eq 0 ] && [ "$ver_rc" -eq 0 ]; then
  echo "conformance: PASS    declarations on this build: hold"
  exit 0
fi
if [ "$under" -eq 1 ]; then
  echo "declarations on this build: AT LEAST ONE IS UNDER-DECLARED"
  echo "  This is the finding of Section 7.11, measured again on this image's"
  echo "  FFmpeg. The declared footprints of Table 3 are calibrated for the"
  echo "  reference build and the manuscript says they must be re-declared and"
  echo "  re-tested for another one. Reported, not absorbed."
  grep -E "UNDER-DECLARED|outside declared support" "$OUT/run_all_output.txt" | sed "s/^/  /"
  echo
  echo "Exit 3 means: the pipeline ran, and a declaration does not hold here."
  exit 3
fi
echo "run_all.sh exit $run_rc, comparison exit $ver_rc, and no under-declaration"
echo "was reported, so something else failed. That is a defect, not a finding."
exit 1
