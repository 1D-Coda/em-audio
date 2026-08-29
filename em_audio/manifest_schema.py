"""Serialisation of EM evidence as a namespaced C2PA assertion.

The assertion carries one entry per output evidence interval.  Temporal extent
is expressed with a C2PA region of interest using an ``npt`` temporal range
(C2PA 2.4, section 18.2.2.3), which is the specification's own mechanism for
making an assertion apply to part of an asset.  Sample-exact bounds are carried
alongside because npt strings are lossy at sample resolution.

Presentation labels (CAPTURED / GENERATED / MIXED / UNVERIFIED) are emitted for
convenience only.  The normative fields are ``provenance`` (null == unverified),
``support``, ``applicability`` and ``lineage``.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from .evidence import BOT, Evidence, _Bot, claim_of, label_of
from .interval_map import OutputInterval

# The C2PA convention for a vendor assertion is a reverse-DNS label under a
# namespace the author controls. It is chosen here under the repository host
# rather than a private domain, because the label is published in the paper and
# then cannot be changed, while a domain registration can lapse and leave the
# namespace to whoever registers it next.
NAMESPACE = "io.github.1d-coda"
ASSERTION_LABEL = f"{NAMESPACE}.emaudio.evidence"

# The schema identifier a reader may try to resolve. It is set to the archived
# deposit rather than to a web page, so that it keeps resolving after any
# repository is renamed or moved. Until the archive exists this is the
# repository itself, and the deposit DOI replaces it before submission.
SCHEMA = "https://github.com/1D-Coda/em-audio/blob/main/docs/em-audio-schema-1.0.md"
SCHEMA_VERSION = "1.0"


def _npt(samples: int, fs: int) -> str:
    return f"{samples / float(fs):.9f}"


def interval_to_json(iv: OutputInterval, fs: int) -> Dict[str, object]:
    ev = iv.ev
    prov: Optional[List[str]] = None if isinstance(ev.P, _Bot) else sorted(ev.P)
    return {
        "regionOfInterest": {
            "type": "temporal",
            "time": {"type": "npt",
                     "start": _npt(iv.out_start, fs),
                     "end": _npt(iv.out_end, fs)},
        },
        "samples": {"start": iv.out_start, "end": iv.out_end},
        "provenance": prov,
        "state": label_of(ev.P),
        "support": {k: round(float(v), 12) for k, v in sorted(ev.S.items())},
        "applicability": {k: sorted(v) for k, v in sorted(ev.A.items())},
        "lineage": sorted(ev.L),
    }


def em_assertion(intervals: Sequence[OutputInterval], fs: int, n_samples: int,
                 policy: str, operator: str, params: Dict[str, object]) -> Dict[str, object]:
    return {
        "schema": SCHEMA,
        "policy": policy,
        "operator": operator,
        "operatorParameters": params,
        "asset": {"sampleRate": fs, "sampleCount": n_samples},
        "intervals": [interval_to_json(iv, fs) for iv in intervals],
    }


def interval_from_json(d: Dict[str, object]) -> Evidence:
    prov = d.get("provenance")
    P = BOT if prov is None else claim_of(prov)
    return Evidence(P=P,
                    S={k: float(v) for k, v in (d.get("support") or {}).items()},
                    A={k: frozenset(v) for k, v in (d.get("applicability") or {}).items()},
                    L=frozenset(d.get("lineage") or []))


def assertion_states(assertion: Dict[str, object]) -> List[str]:
    return [i["state"] for i in assertion["intervals"]]
