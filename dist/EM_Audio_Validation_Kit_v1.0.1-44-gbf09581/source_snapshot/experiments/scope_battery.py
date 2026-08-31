"""Synthetic scope battery: the applicability cases the audio corpus cannot reach.

The v1 corpus carries one channel over one scope, so it never exhibits disjoint
or partially overlapping scopes, and never the inapplicable-to-applicable
transition that Proposition 4 turns on. This enumerates those cases directly.
"""
import itertools, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from em_audio.evidence import Evidence, aggregate, claim_of
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import emit

SCOPES = [frozenset(), frozenset({"a"}), frozenset({"b"}),
          frozenset({"a", "b"}), frozenset({"b", "c"})]
VALUES = [None, 0.0, 0.4, 0.9, 1.0]        # None: channel not applicable at all
MU = "ch"


def ev(scope, val, tag):
    if val is None:                         # not applicable to this source
        return Evidence(P=claim_of(["C"]), S={}, A={}, L=frozenset({tag}))
    if not scope:                           # applicable, empty scope: unconstructible
        return None
    return Evidence(P=claim_of(["C"]), S={MU: val}, A={MU: scope}, L=frozenset({tag}))


def aggregate_legacy(D):
    """The superseded form of requirement (iv), which withheld a channel only
    when an applicable source reported no value, and silently skipped a source
    to which the channel was not applicable at all. Kept here so the reason the
    rule changed is a measurement rather than an assertion."""
    D = list(D)
    channels = set()
    for e in D:
        channels |= set(e.A)
    S, A = {}, {}
    for mu in sorted(channels):
        applicable = [e for e in D if mu in e.A]
        if not applicable:
            continue
        scope = frozenset.intersection(*[e.A[mu] for e in applicable])
        if not scope or any(mu not in e.S for e in applicable):
            continue
        A[mu] = scope
        S[mu] = min(float(e.S[mu]) for e in applicable)
    return S


def run():
    cases = mono = skipped = legacy_bad = 0
    for (s1, v1), (s2, v2) in itertools.product(
            itertools.product(SCOPES, VALUES), repeat=2):
        e1, e2 = ev(s1, v1, "urn:1"), ev(s2, v2, "urn:2")
        if e1 is None or e2 is None:
            skipped += 1
            continue
        small, large = aggregate([e1]), aggregate([e1, e2])
        cases += 1
        # Proposition 4: enlarging D_y must not raise the channel in the lifted
        # domain. Unavailable is the bottom, so present-in-large/absent-in-small
        # is a rise, which is the case the original check skipped.
        sv, lv = small.S.get(MU), large.S.get(MU)
        if lv is None:
            mono += 1                                    # fell to bottom, or stayed
        elif sv is None:
            print(f"  VIOLATION: unavailable under {{x1}} but {lv} under {{x1,x2}}"
                  f"  (scopes {set(s1) or '-'} / {set(s2) or '-'}, values {v1} / {v2})")
        elif lv <= sv + 1e-12:
            mono += 1
        else:
            print(f"  VIOLATION: rose {sv} -> {lv}")
        # the same pair under the superseded rule
        lsv, llv = aggregate_legacy([e1]).get(MU), aggregate_legacy([e1, e2]).get(MU)
        if llv is not None and (lsv is None or llv > lsv + 1e-12):
            legacy_bad += 1

        # scope must never broaden
        ls = large.A.get(MU)
        if ls is not None and small.A.get(MU) is not None and not ls <= small.A[MU]:
            print(f"  VIOLATION: scope broadened {set(small.A[MU])} -> {set(ls)}")
    return cases, mono, skipped, legacy_bad


if __name__ == "__main__":
    c, m, sk, lb = run()
    emit("L_scope_battery", {
        "experiment": "L_scope_battery",
        "purpose": ("applicability cases the single-scope audio corpus cannot "
                    "reach: disjoint and overlapping scopes, and the "
                    "inapplicable-to-applicable transition that Proposition 4 "
                    "turns on"),
        "distinct_scopes": len(SCOPES),
        "enlargement_cases": c,
        "monotone": m,
        "violations": c - m,
        "unconstructible_skipped": sk,
        "violations_under_superseded_rule": lb,
    })
    print(f"scope battery: {c} enlargement cases, {m} monotone, "
          f"{c - m} violations ({sk} unconstructible skipped); "
          f"{lb} would violate under the superseded requirement (iv)")
    sys.exit(0 if c == m else 1)
