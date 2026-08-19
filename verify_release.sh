#!/usr/bin/env bash
# Verify a downloaded release against SHA256SUMS before reproducing.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f SHA256SUMS ]; then echo "SHA256SUMS missing" >&2; exit 1; fi
# SHA256SUMS deliberately does not list itself: the shell truncates the file
# before shasum can read it, so a self-entry can never match.
if command -v sha256sum >/dev/null; then sha256sum -c SHA256SUMS; else shasum -a 256 -c SHA256SUMS; fi
echo "checksums OK"
