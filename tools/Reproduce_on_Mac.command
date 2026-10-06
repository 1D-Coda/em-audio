#!/bin/bash
# Double-clickable on macOS: Finder opens it in Terminal.
#
# Does the whole reproduction: checks the tools, builds a virtual environment,
# runs the pipeline, compares against the release, and leaves one zip to send
# back. Nothing is installed without asking first.
set -uo pipefail

# Works both from tools/ inside a checkout and from the top of the archive,
# where the file sits next to em-audio/ so a double click finds it in Finder.
here="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$here/run_all.sh" ]; then cd "$here"
elif [ -f "$here/em-audio/run_all.sh" ]; then cd "$here/em-audio"
elif [ -f "$here/../run_all.sh" ]; then cd "$here/.."
else echo "cannot find run_all.sh next to this file"; read -r -p "Press Enter." _; exit 2
fi
ROOT="$(pwd)"

bold=$'\033[1m'; red=$'\033[31m'; green=$'\033[32m'; off=$'\033[0m'
say () { printf "\n%s== %s%s\n" "$bold" "$*" "$off"; }
bad () { printf "%s%s%s\n" "$red" "$*" "$off"; }
ok  () { printf "%s%s%s\n" "$green" "$*" "$off"; }

say "EM-Audio: independent reproduction"
echo "Folder: $ROOT"

# A long path silently truncates espeak-ng's output and the run dies later
# somewhere unrelated. Say it here rather than let it happen.
if [ ${#ROOT} -gt 120 ]; then
  bad "The path is long (${#ROOT} characters)."
  echo "Move this folder to ~/em-audio and open this file again."
  echo; read -r -p "Press Enter to close." _; exit 2
fi

say "1/6  External tools"
missing=""
for t in ffmpeg ffprobe node espeak-ng c2patool; do
  if command -v "$t" >/dev/null 2>&1; then
    echo "  ok       $t"
  else
    echo "  missing  $t"; missing="$missing $t"
  fi
done
if [ -n "$missing" ]; then
  # ffprobe ships inside the ffmpeg formula; the rest are formulae by name.
  formulae=$(echo "$missing" | sed 's/ffprobe//' | xargs || true)
  [ -z "$formulae" ] && formulae="ffmpeg"
  if ! command -v brew >/dev/null 2>&1; then
    bad "Homebrew is missing. It is how these tools get installed."
    echo "Install it from https://brew.sh and open this file again."
    echo; read -r -p "Press Enter to close." _; exit 2
  fi
  echo
  echo "They can be installed with:  brew install $formulae"
  read -r -p "Install them now? [y/N] " yn
  case "$yn" in
    s|S|y|Y) brew install $formulae || { bad "The install failed."; read -r -p "Press Enter." _; exit 2; } ;;
    *) echo "OK. Install them and open this file again."; read -r -p "Press Enter." _; exit 2 ;;
  esac
fi

say "2/6  Python and dependencies"
. "$ROOT/tools/resolve_python.sh"
resolve_python || { python_not_found_message; read -r -p "Press Enter." _; exit 2; }
echo "  interpreter: $PY"
if [ ! -d "$ROOT/.venv" ]; then
  echo "  creating virtual environment in .venv"
  $PY -m venv "$ROOT/.venv" || { bad "Could not create the environment."; read -r -p "Press Enter." _; exit 2; }
fi
# shellcheck disable=SC1091
. "$ROOT/.venv/bin/activate"
export PY="$ROOT/.venv/bin/python"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r "$ROOT/requirements.txt" \
  || { bad "pip failed."; read -r -p "Press Enter." _; exit 2; }
ok "  dependencies ready"

say "3/6  Pre-check (runs no experiments)"
"$PY" "$ROOT/tools/repro_selftest.py" || {
  bad "The pre-check found problems. Fix them and open this again."
  read -r -p "Press Enter." _; exit 2; }

say "4/6  Full run (about 25 minutes, plus 322 MB the first time)"
echo "Do not close this window."
bash "$ROOT/run_all.sh" 2>&1 | tee "$ROOT/run_all_output.txt"
run_rc=${PIPESTATUS[0]}
if [ "$run_rc" -eq 0 ]; then ok "  run_all.sh finished with RUN OK"
else bad "  run_all.sh exited $run_rc. That is a result: send it to us anyway."; fi

say "5/6  Comparison against the published release"
"$PY" "$ROOT/tools/verify_reproduction.py" 2>&1 | tee "$ROOT/verify_output.txt"
ver_rc=${PIPESTATUS[0]}
echo
echo "  verify_reproduction.py exited $ver_rc"
echo "  A non-zero value is NOT your fault. It means an output"
echo "  differs, which is exactly what we want to know."

say "6/6  Packing what to send back"
label="$(scutil --get ComputerName 2>/dev/null || hostname)"
label="$(echo "$label" | tr ' /' '__' | tr -cd 'A-Za-z0-9_-')"
arch="$(uname -m)"
# Next to this file, which is where a person who double-clicked it will look,
# rather than buried inside em-audio/.
outdir="$here"
out="$outdir/results_${label}_${arch}_$(date +%Y-%m-%d)"
rm -rf "$out"; mkdir -p "$out"
cp -R "$ROOT/results/machine_readable" "$out/" 2>/dev/null
for f in results/PREFLIGHT.txt run_all_output.txt verify_output.txt; do
  [ -f "$ROOT/$f" ] && cp "$ROOT/$f" "$out/"
done
{
  echo "machine     : $label"
  echo "architecture: $arch"
  echo "macOS       : $(sw_vers -productVersion 2>/dev/null)"
  echo "run_all     : $run_rc"
  echo "verify      : $ver_rc"
  echo "date        : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/RUN_INFO.txt"
( cd "$outdir" && zip -qr "$out.zip" "$(basename "$out")" ) && rm -rf "$out"
ok "Done: $out.zip"
echo
echo "Send that file. If you run on another computer, it gets a different name,"
echo "and we want both."
echo
read -r -p "Press Enter to close this window." _
