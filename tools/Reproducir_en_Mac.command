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
else echo "no encuentro run_all.sh junto a este archivo"; read -r -p "Enter." _; exit 2
fi
ROOT="$(pwd)"

bold=$'\033[1m'; red=$'\033[31m'; green=$'\033[32m'; off=$'\033[0m'
say () { printf "\n%s== %s%s\n" "$bold" "$*" "$off"; }
bad () { printf "%s%s%s\n" "$red" "$*" "$off"; }
ok  () { printf "%s%s%s\n" "$green" "$*" "$off"; }

say "EM-Audio: reproduccion independiente"
echo "Carpeta: $ROOT"

# A long path silently truncates espeak-ng's output and the run dies later
# somewhere unrelated. Say it here rather than let it happen.
if [ ${#ROOT} -gt 120 ]; then
  bad "La ruta es larga (${#ROOT} caracteres)."
  echo "Mueve esta carpeta a ~/em-audio y vuelve a abrir este archivo."
  echo; read -r -p "Enter para cerrar." _; exit 2
fi

say "1/6  Herramientas externas"
missing=""
for t in ffmpeg ffprobe node espeak-ng c2patool; do
  if command -v "$t" >/dev/null 2>&1; then
    echo "  ok       $t"
  else
    echo "  falta    $t"; missing="$missing $t"
  fi
done
if [ -n "$missing" ]; then
  # espeak-ng and ffprobe are not separate formulae.
  formulae=$(echo "$missing" | sed 's/ffprobe//' | xargs || true)
  [ -z "$formulae" ] && formulae="ffmpeg"
  if ! command -v brew >/dev/null 2>&1; then
    bad "Falta Homebrew, que es como se instalan estas herramientas."
    echo "Instalalo desde https://brew.sh y vuelve a abrir este archivo."
    echo; read -r -p "Enter para cerrar." _; exit 2
  fi
  echo
  echo "Se pueden instalar con:  brew install $formulae"
  read -r -p "Instalarlas ahora? [s/N] " yn
  case "$yn" in
    s|S|y|Y) brew install $formulae || { bad "La instalacion fallo."; read -r -p "Enter." _; exit 2; } ;;
    *) echo "De acuerdo. Instalalas y vuelve a abrir este archivo."; read -r -p "Enter." _; exit 2 ;;
  esac
fi

say "2/6  Python y dependencias"
. "$ROOT/tools/resolve_python.sh"
resolve_python || { python_not_found_message; read -r -p "Enter." _; exit 2; }
echo "  interprete: $PY"
if [ ! -d "$ROOT/.venv" ]; then
  echo "  creando entorno virtual en .venv"
  $PY -m venv "$ROOT/.venv" || { bad "No se pudo crear el entorno."; read -r -p "Enter." _; exit 2; }
fi
# shellcheck disable=SC1091
. "$ROOT/.venv/bin/activate"
export PY="$ROOT/.venv/bin/python"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r "$ROOT/requirements.txt" \
  || { bad "pip fallo."; read -r -p "Enter." _; exit 2; }
ok "  dependencias listas"

say "3/6  Revision previa (no corre experimentos)"
"$PY" "$ROOT/tools/repro_selftest.py" || {
  bad "La revision previa encontro problemas. Resuelvelos y vuelve a abrir esto."
  read -r -p "Enter." _; exit 2; }

say "4/6  Corrida completa (unos 25 minutos, mas 322 MB la primera vez)"
echo "No cierres esta ventana."
bash "$ROOT/run_all.sh" 2>&1 | tee "$ROOT/run_all_output.txt"
run_rc=${PIPESTATUS[0]}
if [ "$run_rc" -eq 0 ]; then ok "  run_all.sh termino en RUN OK"
else bad "  run_all.sh salio $run_rc. Eso es un resultado: mandanoslo igual."; fi

say "5/6  Comparacion contra la version publicada"
"$PY" "$ROOT/tools/verify_reproduction.py" 2>&1 | tee "$ROOT/verify_output.txt"
ver_rc=${PIPESTATUS[0]}
echo
echo "  verify_reproduction.py salio $ver_rc"
echo "  Un valor distinto de cero NO es un fallo tuyo: significa que una salida"
echo "  difiere, que es justo lo que queremos saber."

say "6/6  Empaquetando lo que hay que mandar"
label="$(scutil --get ComputerName 2>/dev/null || hostname)"
label="$(echo "$label" | tr ' /' '__' | tr -cd 'A-Za-z0-9_-')"
arch="$(uname -m)"
# Next to this file, which is where a person who double-clicked it will look,
# rather than buried inside em-audio/.
outdir="$here"
out="$outdir/resultados_${label}_${arch}_$(date +%Y-%m-%d)"
rm -rf "$out"; mkdir -p "$out"
cp -R "$ROOT/results/machine_readable" "$out/" 2>/dev/null
for f in results/PREFLIGHT.txt run_all_output.txt verify_output.txt; do
  [ -f "$ROOT/$f" ] && cp "$ROOT/$f" "$out/"
done
{
  echo "maquina    : $label"
  echo "arquitectura: $arch"
  echo "macOS      : $(sw_vers -productVersion 2>/dev/null)"
  echo "run_all    : $run_rc"
  echo "verify     : $ver_rc"
  echo "fecha      : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$out/CORRIDA.txt"
( cd "$outdir" && zip -qr "$out.zip" "$(basename "$out")" ) && rm -rf "$out"
ok "Listo: $out.zip"
echo
echo "Manda ese archivo. Si corres en otra computadora, saldra con otro nombre"
echo "y queremos los dos."
echo
read -r -p "Enter para cerrar esta ventana." _
