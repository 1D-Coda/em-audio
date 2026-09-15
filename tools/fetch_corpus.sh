#!/usr/bin/env bash
# Fetch the public captured-speech corpus.  LibriSpeech dev-clean is licensed
# CC BY 4.0 (see corpus/LibriSpeech/LICENSE.TXT after extraction) and may be
# redistributed with attribution.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
# Resolved before the cd below: a relative invocation (./tools/fetch_corpus.sh)
# made "$(dirname "$0")" point nowhere once the working directory had changed.
. "$here/tools/sha256.sh"
# mkdir first: a source archive need not ship an empty corpus directory, and
# with set -e a missing one aborted the fetch before the first useful line.
mkdir -p "$here/corpus"
cd "$here/corpus"
URL="https://www.openslr.org/resources/12/dev-clean.tar.gz"
EXPECT="76f87d090650617fca0cac8f88b9416e0ebf80350acb97b343a85fa903728ab3"
# Windows curl (schannel) checks certificate revocation and fails outright
# when the CRL/OCSP server cannot be reached, which is the normal state behind
# a university or corporate proxy: "curl: (35) schannel ... CRYPT_E_REVOCATION
# _OFFLINE". An independent reproducer hit exactly that. --ssl-revoke-best-effort
# ignores only the offline case (a certificate known to be revoked still
# fails) and is passed only when this curl knows the option, so a curl older
# than 7.70 is not handed a flag it would reject.
revoke=""
if curl --help all 2>/dev/null | grep -q -- '--ssl-revoke-best-effort'; then
  revoke="--ssl-revoke-best-effort"
fi
# Download to a temporary name and rename on success: with -o straight to the
# final name, an interrupted transfer left a partial file that the next run
# took for a finished one and then reported as a checksum mismatch forever.
# A file that is present but does not verify is not a download to keep: the
# earlier "skip if the file exists" test let an empty or truncated archive left
# by a failed transfer block every later run with a checksum mismatch.
if [ -f dev-clean.tar.gz ] && [ "$(sha256_of dev-clean.tar.gz)" = "$EXPECT" ]; then
  echo "archive already present and verified"
else
  [ -f dev-clean.tar.gz ] && echo "existing archive does not verify; downloading again" >&2
  rm -f dev-clean.tar.gz dev-clean.tar.gz.part
  curl -L --fail --retry 3 --retry-delay 5 $revoke -o dev-clean.tar.gz.part "$URL" \
    && mv dev-clean.tar.gz.part dev-clean.tar.gz
  got=$(sha256_of dev-clean.tar.gz) || exit 1
  if [ "$got" != "$EXPECT" ]; then echo "checksum mismatch: $got != $EXPECT" >&2; exit 1; fi
fi
[ -d LibriSpeech ] || tar xzf dev-clean.tar.gz
echo "corpus ready: $(find LibriSpeech -name '*.flac' | wc -l | tr -d ' ') flac files"
