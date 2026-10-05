"""Consumer-side verification of an EM assertion against its declared map.

A consumer holds the derived asset's assertion and, from the ingredient graph,
each source's own interval evidence. If the assertion carries a dependency
declaration, the consumer rebuilds the map, checks that it covers the output
exactly, recomputes every interval's record under the complete-source rule and
compares it with what the producer emitted.

What a pass establishes is consistency with the signed declaration. A producer
that declares a map narrower than its processing, or misstates its operation,
passes; the declaration is the producer's claim, and only calibration of the
processing itself (Experiments K and K2) can test it.
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from .evidence import leq_claim, label_of
from .interval_map import (DerivedOutput, MapPiece, SourceInterval, Timeline,
                           check_coverage, em_intervals)
from .manifest_schema import interval_from_json


def source_timeline(src: str, source_assertion: Dict[str, object]) -> Timeline:
    """A source's evidence timeline, read from that source's own assertion."""
    ivs = [SourceInterval(src, int(i["samples"]["start"]), int(i["samples"]["end"]),
                          interval_from_json(i))
           for i in source_assertion["intervals"]]
    return Timeline(src, ivs)


def rebuild(declaration: Dict[str, object]) -> DerivedOutput:
    pieces = [MapPiece(int(p["output"]["start"]), int(p["output"]["end"]), p["source"],
                       float(p["sourceRange"]["start"]), float(p["sourceRange"]["end"]),
                       int(p["footprint"]), p.get("label", ""))
              for p in declaration["pieces"]]
    return DerivedOutput(int(declaration["outputSampleCount"]), pieces, "declared", {})


def verify(assertion: Dict[str, object],
           source_assertions: Dict[str, Dict[str, object]],
           decoded_samples: int = None) -> Dict[str, object]:
    """Recompute the assertion's claims from its declaration and the sources.

    Returns the verdict and, per disagreement, the output span, the emitted and
    recomputed records, and whether the emitted claim is stronger (a promotion
    relative to the declaration) or merely different.
    """
    decl = assertion.get("dependencyDeclaration")
    if decl is None:
        return {"verdict": "NO_DECLARATION", "consistent": False, "findings": []}
    model = rebuild(decl)
    findings: List[Dict[str, object]] = []
    # The declaration states its own output length. A consumer that decodes the
    # asset itself passes the decoded count, and a declaration that stops short
    # of the audio, or runs past it, fails here whatever its map says.
    if decoded_samples is not None and decoded_samples != model.n_out:
        return {"verdict": "LENGTH_MISMATCH", "consistent": False,
                "findings": [{"kind": "length", "declared": model.n_out,
                              "decoded": decoded_samples}]}
    try:
        check_coverage(model, model.n_out)
    except ValueError as e:
        return {"verdict": "COVERAGE_FAILURE", "consistent": False,
                "findings": [{"kind": "coverage", "detail": str(e)}]}
    if int(assertion["asset"]["sampleCount"]) != model.n_out:
        findings.append({"kind": "length", "detail": "asset sampleCount differs from the declaration"})
    tls = {s: source_timeline(s, source_assertions[s]) for s in decl["sources"]}
    recomputed = em_intervals(model, tls, footprint_aware=True)
    emitted = [(int(i["samples"]["start"]), int(i["samples"]["end"]), interval_from_json(i))
               for i in assertion["intervals"]]
    # Compare on the common refinement of both partitions.
    edges = sorted({a for a, _, _ in emitted} | {b for _, b, _ in emitted}
                   | {iv.out_start for iv in recomputed} | {iv.out_end for iv in recomputed})

    def at_emitted(x):
        return next((e for a, b, e in emitted if a <= x < b), None)

    def at_recomputed(x):
        return next((iv.ev for iv in recomputed if iv.out_start <= x < iv.out_end), None)

    for a, b in zip(edges, edges[1:]):
        e, r = at_emitted(a), at_recomputed(a)
        if e is None:
            findings.append({"kind": "unclaimed", "span": [a, b]})
            continue
        if r is None:
            findings.append({"kind": "claim_without_declaration", "span": [a, b]})
            continue
        if e == r:
            continue
        stronger = (not leq_claim(e.P, r.P)
                    or any(m not in r.S or e.S[m] > r.S[m] for m in e.S)
                    or any(m in r.A and not e.A[m] <= r.A[m] for m in e.A)
                    or not r.L <= e.L)
        findings.append({"kind": "promotion" if stronger else "mismatch", "span": [a, b],
                         "emitted": label_of(e.P), "recomputed": label_of(r.P)})
    promotions = sum(1 for f in findings if f["kind"] == "promotion")
    verdict = ("CONSISTENT" if not findings else
               "PROMOTION" if promotions else "INCONSISTENT")
    return {"verdict": verdict, "consistent": not findings, "findings": findings}
