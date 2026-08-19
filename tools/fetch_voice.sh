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
python3 -m piper.download_voices en_US-ljspeech-medium --data-dir "$d"
echo "voice ready"
