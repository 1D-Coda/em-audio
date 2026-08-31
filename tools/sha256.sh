# Sourced, not executed. One SHA-256 helper for every script that verifies a
# download, because the same defect was fixed twice in two copies: shasum is a
# Perl script macOS ships and Git Bash on Windows does not, and under `set -e` a
# missing command aborts the script. In fetch_corpus.sh that silently left the
# run with no corpus; in fetch_voice.sh it stopped the run outright.
sha256_of () {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | cut -d' ' -f1
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | cut -d' ' -f1
  elif command -v certutil >/dev/null 2>&1; then
    certutil -hashfile "$1" SHA256 | sed -n 2p | tr -d ' \r'
  else
    echo "no SHA-256 tool found (tried shasum, sha256sum, certutil)" >&2
    return 1
  fi
}
