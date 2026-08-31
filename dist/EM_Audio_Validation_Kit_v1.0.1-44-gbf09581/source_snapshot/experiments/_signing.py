from pathlib import Path
from _common import ROOT
from em_audio.c2pa_bridge import Signer

CERTS = ROOT / "tools" / "test_certs"


def signer() -> Signer:
    return Signer(cert_chain_pem=CERTS / "chain.pem",
                  private_key_pk8_pem=CERTS / "ee.pk8.pem",
                  trust_anchor_pem=CERTS / "ca.pem")
