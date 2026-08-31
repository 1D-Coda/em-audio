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
# shasum is a Perl script that macOS ships and Git Bash on Windows does not;
# sha256sum is the coreutils name and is what Windows and most Linuxes have.
# With set -e a missing command aborts here, and the caller then continued with
# no corpus, so this is where a Windows run quietly lost its audio.
if command -v shasum >/dev/null 2>&1; then
  got=$(shasum -a 256 dev-clean.tar.gz | cut -d' ' -f1)
elif command -v sha256sum >/dev/null 2>&1; then
  got=$(sha256sum dev-clean.tar.gz | cut -d' ' -f1)
elif command -v certutil >/dev/null 2>&1; then
  got=$(certutil -hashfile dev-clean.tar.gz SHA256 | sed -n 2p | tr -d ' \r')
else
  echo "no SHA-256 tool found (tried shasum, sha256sum, certutil)" >&2; exit 1
fi
if [ "$got" != "$EXPECT" ]; then echo "checksum mismatch: $got != $EXPECT" >&2; exit 1; fi
[ -d LibriSpeech ] || tar xzf dev-clean.tar.gz
echo "corpus ready: $(find LibriSpeech -name '*.flac' | wc -l | tr -d ' ') flac files"
