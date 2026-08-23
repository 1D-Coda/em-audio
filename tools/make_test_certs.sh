#!/usr/bin/env bash
# Regenerate the local test signing credential used by the signed-transport
# experiments.  These are TEST credentials for a locally configured trust
# anchor; they are not on the C2PA Conformance Program trust list and the
# manuscript says so.
set -euo pipefail
d="$(cd "$(dirname "$0")" && pwd)/test_certs"
mkdir -p "$d"; cd "$d"
openssl ecparam -name prime256v1 -genkey -noout -out ca.key
openssl req -x509 -new -key ca.key -sha256 -days 3650 -out ca.pem \
  -subj "/C=MX/ST=Sonora/L=Hermosillo/O=EM-Audio Test CA/CN=EM-Audio Test Root CA" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"
openssl ecparam -name prime256v1 -genkey -noout -out ee.key
openssl req -new -key ee.key -out ee.csr \
  -subj "/C=MX/ST=Sonora/L=Hermosillo/O=EM-Audio Test Signer/CN=em-audio-test-signer"
printf 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature\nextendedKeyUsage=critical,emailProtection\n' > ee.ext
openssl x509 -req -in ee.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out ee.pem \
  -days 3650 -sha256 -extfile ee.ext
openssl pkcs8 -topk8 -nocrypt -in ee.key -out ee.pk8.pem
cat ee.pem ca.pem > chain.pem
echo "test credential written to $d"
