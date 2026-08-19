#!/usr/bin/env bash
# Fetch the public captured-speech corpus.  LibriSpeech dev-clean is licensed
# CC BY 4.0 (see corpus/LibriSpeech/LICENSE.TXT after extraction) and may be
# redistributed with attribution.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
cd "$here/corpus"
URL="https://www.openslr.org/resources/12/dev-clean.tar.gz"
EXPECT="76f87d090650617fca0cac8f88b9416e0ebf80350acb97b343a85fa903728ab3"
if [ ! -f dev-clean.tar.gz ]; then curl -L -o dev-clean.tar.gz "$URL"; fi
got=$(shasum -a 256 dev-clean.tar.gz | cut -d' ' -f1)
if [ "$got" != "$EXPECT" ]; then echo "checksum mismatch: $got != $EXPECT" >&2; exit 1; fi
[ -d LibriSpeech ] || tar xzf dev-clean.tar.gz
echo "corpus ready: $(find LibriSpeech -name '*.flac' | wc -l | tr -d ' ') flac files"
