#!/usr/bin/env bash
# Fetch the public captured-speech corpus.  LibriSpeech dev-clean is licensed
# CC BY 4.0 (see corpus/LibriSpeech/LICENSE.TXT after extraction) and may be
# redistributed with attribution.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
# mkdir first: a source archive need not ship an empty corpus directory, and
# with set -e a missing one aborted the fetch before the first useful line.
mkdir -p "$here/corpus"
cd "$here/corpus"
URL="https://www.openslr.org/resources/12/dev-clean.tar.gz"
EXPECT="76f87d090650617fca0cac8f88b9416e0ebf80350acb97b343a85fa903728ab3"
if [ ! -f dev-clean.tar.gz ]; then curl -L -o dev-clean.tar.gz "$URL"; fi
. "$(cd "$(dirname "$0")" && pwd)"/sha256.sh
got=$(sha256_of dev-clean.tar.gz) || exit 1
if [ "$got" != "$EXPECT" ]; then echo "checksum mismatch: $got != $EXPECT" >&2; exit 1; fi
[ -d LibriSpeech ] || tar xzf dev-clean.tar.gz
echo "corpus ready: $(find LibriSpeech -name '*.flac' | wc -l | tr -d ' ') flac files"
