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
echo "run_all.sh exit $run_rc, comparison exit $ver_rc"
echo "results are in $OUT"
# The pipeline's outcome is the container's outcome. Returning 0 regardless is
# how a run that never happened once reported success.
[ "$run_rc" -eq 0 ] && [ "$ver_rc" -eq 0 ]
