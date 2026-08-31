#!/usr/bin/env bash
# Fetch the neural-TTS voice model for the robustness arm (experiment C2).
# Voice: en_US-ljspeech-medium (Piper/VITS). LJSpeech source data is public
# domain; see DATA_LICENSES.md.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
d="$here/corpus/piper_voices"
mkdir -p "$d"
if [ -f "$d/en_US-ljspeech-medium.onnx" ]; then
  echo "voice already present"; exit 0
fi
# $PY when run_all.sh exported one, resolved here when this script is run on
# its own. Reported by an independent reproducer: this line invoked python3
# literally, so on a normal Windows install it hit the Microsoft Store alias and
# experiment C2 failed while every other step had already been fixed.
if [ -z "${PY:-}" ]; then
  . "$(cd "$(dirname "$0")" && pwd)"/resolve_python.sh
  resolve_python || { python_not_found_message; exit 2; }
fi
$PY -m piper.download_voices en_US-ljspeech-medium --data-dir "$d"

# Verify both files against the checksums recorded in DATA_LICENSES.md.
expect_model="6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22"
expect_cfg="141d612cc0a95ed7efc1ca936b845c2364967f2e9217c5dbfcf69fc4d6c65860"
. "$(cd "$(dirname "$0")" && pwd)"/sha256.sh
got_model=$(sha256_of "$d/en_US-ljspeech-medium.onnx")
got_cfg=$(sha256_of "$d/en_US-ljspeech-medium.onnx.json")
if [ "$got_model" != "$expect_model" ]; then
  echo "voice model checksum mismatch: $got_model != $expect_model" >&2; exit 1
fi
if [ "$got_cfg" != "$expect_cfg" ]; then
  echo "voice config checksum mismatch: $got_cfg != $expect_cfg" >&2; exit 1
fi
echo "voice ready (checksums verified)"
