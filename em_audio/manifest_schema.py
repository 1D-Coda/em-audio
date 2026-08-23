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

SCHEMA = "https://aurtech.mx/ns/em-audio/1.0"
ASSERTION_LABEL = "mx.aurtech.emaudio.evidence"


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
