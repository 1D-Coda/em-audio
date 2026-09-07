"""Regressions from the 2026-09-06 external review.

Each test encodes a defect the review reproduced against the shipped code.
They are written to FAIL on the code as reviewed and to pass once fixed, so
that a validator which accepts a violation is itself caught by a test rather
than trusted because the canonical aggregator happens to be correct.

Run: python3 tests/test_review_regressions.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from em_audio.evidence import Evidence, BOT, claim_of, aggregate                     # noqa: E402
from em_audio.interval_map import (Timeline, SourceInterval, OutputInterval,  # noqa: E402
                                   em_intervals)
from em_audio.manifest_schema import em_assertion                          # noqa: E402
from em_audio import conformance as c                                      # noqa: E402
import em_audio.operators as O                                             # noqa: E402

SCOPE = frozenset({"audio"})
CAP = Evidence(claim_of(["C"]), {"mu": 0.9}, {"mu": SCOPE}, frozenset({"a"}))
CHECKS = [c.p1_exact_union, c.p2_no_promotion, c.p3_unverified_non_promotion,
          c.p4_support_non_promotion, c.p5_applicability_non_broadening,
          c.p6_complete_lineage, c.p9_channel_scope_agreement]

# Every check the suite runs, structural first: a candidate has to be a
# well-formed annotation of the map before any semantic question about it means
# anything.
ALL_CHECKS = [c.p0_structural] + CHECKS


def _forged(other: Evidence, provenance) -> bool:
    """True if every validator accepts an output that keeps a channel it must
    withhold under requirement (iv) or (iv')."""
    tl = Timeline("s", [SourceInterval("s", 0, 10, CAP), SourceInterval("s", 10, 20, other)])
    out = O.trim("s", 20, 0, 20)
    bad = [OutputInterval(0, 20, Evidence(provenance, {"mu": 0.9}, {"mu": SCOPE},
                                          frozenset({"a", "b"})), (0,))]
    return all(f(out, {"s": tl}, bad).passed for f in CHECKS)


def test_validators_reject_channel_with_inapplicable_source():
    # (iv): a channel not applicable to every required source is withheld.
    other = Evidence(claim_of(["C"]), L=frozenset({"b"}))
    assert not _forged(other, claim_of(["C"])), \
        "validators accepted a numeric channel although a required source lacks it"


def test_validators_reject_channel_with_unverified_source():
    # (iv'): a bottom source withholds every numeric channel.
    other = Evidence(BOT, L=frozenset({"b"}))
    assert not _forged(other, BOT), \
        "validators accepted a numeric channel although a required source is unverified"


def test_p6_requires_exact_lineage():
    tl = Timeline("s", [SourceInterval("s", 0, 20, CAP)])
    out = O.trim("s", 20, 0, 20)
    invented = [OutputInterval(0, 20, Evidence(claim_of(["C"]), {"mu": 0.9}, {"mu": SCOPE},
                                               frozenset({"a", "z"})), (0,))]
    assert not c.p6_complete_lineage(out, {"s": tl}, invented).passed, \
        "P6 accepted lineage carrying a member no required source has"


def test_p7_rejects_strengthened_composition():
    final = [OutputInterval(0, 20, CAP)]
    direct = [OutputInterval(0, 10, CAP), OutputInterval(10, 20, Evidence(claim_of(["G"])))]
    assert not c.p7_composition([], final, direct).passed, \
        "P7 accepted an all-captured composition against a direct meet that is generated on [10,20)"


def test_p7_accepts_equivalent_partitions():
    # The same evidence split at a different point is the same claim.
    final = [OutputInterval(0, 5, CAP), OutputInterval(5, 20, CAP)]
    direct = [OutputInterval(0, 20, CAP)]
    assert c.p7_composition([], final, direct).passed


def test_partial_evidence_is_not_extrapolated():
    tl = Timeline("s", [SourceInterval("s", 0, 10, CAP)])
    try:
        ivs = em_intervals(O.trim("s", 20, 0, 20), {"s": tl})
    except ValueError:
        return  # rejection is an acceptable outcome
    labels = {(i.out_start, i.out_end, i.ev.label) for i in ivs}
    assert (0, 20, "CAPTURED") not in labels, \
        "evidence on [0,10) was extended to [0,20) as CAPTURED"
    assert any(l == "UNVERIFIED" for _, _, l in labels), \
        "the uncovered half of the output carries no unverified evidence"


def test_resampled_assertion_is_in_output_units():
    tl = Timeline("s", [SourceInterval("s", 0, 16000, CAP)])
    m = O.resample("s", 16000, 16000, 8000)
    ivs = em_intervals(m, {"s": tl})
    from em_audio.manifest_schema import output_sample_rate
    fs_out = output_sample_rate(m.operator, m.params, 16000)
    a = em_assertion(ivs, fs_out, m.n_out, "complete-source", m.operator, m.params)
    end = float(a["intervals"][-1]["regionOfInterest"]["time"]["end"])
    assert abs(end - 1.0) < 1e-6, f"one second of 8 kHz output asserted as ending at {end} s"
    assert a["asset"]["sampleRate"] == 8000, "assertion does not carry the output rate"
    assert abs(float(a["asset"]["durationSeconds"]) - 1.0) < 1e-9, \
        "assertion does not carry the true output extent"


# --- v6 review: validators trusted the candidate's own contributor list ------

def test_structural_rejects_omitted_contributor():
    """A fully overlaid captured/generated pair, claimed captured with only the
    captured piece named, passed all seven semantic checks. Each one rebuilt the
    required-source set from the candidate's own piece_indices, so omitting a
    contributor made the comparison vacuous: a promotion cleared by the
    validators written to prevent promotion."""
    cap = Evidence(claim_of(["C"]), L=frozenset({"a"}))
    gen = Evidence(claim_of(["G"]), L=frozenset({"b"}))
    tls = {"a": Timeline("a", [SourceInterval("a", 0, 10, cap)]),
           "b": Timeline("b", [SourceInterval("b", 0, 10, gen)])}
    out = O.overlay(("a", 10), ("b", 10), 0)
    forged = [OutputInterval(0, 10, Evidence(claim_of(["C"]), L=frozenset({"a"})), (0,))]
    rejected = [f.__name__ for f in ALL_CHECKS if not f(out, tls, forged).passed]
    assert "p0_structural" in rejected, "structural check accepted an omitted contributor"
    assert "p2_no_promotion" in rejected, "promotion check did not see the promotion"


def test_structural_rejects_empty_and_truncated_annotation():
    """Every semantic check quantifies over the intervals it is given, so an
    empty list satisfied all of them vacuously, and a truncated one satisfied
    them over the part it chose to describe."""
    cap = Evidence(claim_of(["C"]), L=frozenset({"a"}))
    tls = {"a": Timeline("a", [SourceInterval("a", 0, 10, cap)])}
    out = O.trim("a", 10, 0, 10)
    assert not c.p0_structural(out, tls, []).passed, "empty annotation accepted"
    half = [OutputInterval(0, 5, cap, (0,))]
    assert not c.p0_structural(out, tls, half).passed, "truncated annotation accepted"
    gap = [OutputInterval(0, 3, cap, (0,)), OutputInterval(7, 10, cap, (0,))]
    assert not c.p0_structural(out, tls, gap).passed, "gap in coverage accepted"
    overlap = [OutputInterval(0, 6, cap, (0,)), OutputInterval(4, 10, cap, (0,))]
    assert not c.p0_structural(out, tls, overlap).passed, "overlapping claim accepted"


def test_structural_accepts_the_canonical_output():
    """The point is to reject malformed candidates, not to reject correct ones."""
    cap = Evidence(claim_of(["C"]), L=frozenset({"a"}))
    gen = Evidence(claim_of(["G"]), L=frozenset({"b"}))
    tls = {"a": Timeline("a", [SourceInterval("a", 0, 10, cap)]),
           "b": Timeline("b", [SourceInterval("b", 0, 10, gen)])}
    out = O.overlay(("a", 10), ("b", 10), 0)
    canon = em_intervals(out, tls, footprint_aware=True)
    for f in ALL_CHECKS:
        assert f(out, tls, canon).passed, f"{f.__name__} rejected the canonical output"


def test_derived_child_inherits_the_parent_propagated_evidence():
    """A child derived from a signed parent must read the parent's propagated
    evidence, not the original source timeline.

    The signed-transport experiment built each child from the original timeline,
    so a trim of an MP3-transcoded asset re-read the sharp source labels and
    asserted CAPTURED and GENERATED over regions its own parent had already
    marked MIXED by the codec footprint. That is a promotion, produced inside
    the experiment meant to demonstrate the contract, and none of that
    experiment's metrics could see it: they measure validation state and decoded
    essence, never interval structure.
    """
    C = Evidence(claim_of(["C"]), L=frozenset({"cap"}))
    G = Evidence(claim_of(["G"]), L=frozenset({"gen"}))
    tl = Timeline("clip", [SourceInterval("clip", 0, 4000, C),
                           SourceInterval("clip", 4000, 6000, G),
                           SourceInterval("clip", 6000, 10000, C)])
    parent = O.transcode("clip", 10000, "mp3")
    pivs = em_intervals(parent, {"clip": tl}, footprint_aware=True)
    assert any(i.ev.label == "MIXED" for i in pivs), "parent should carry mixed boundaries"

    a, b = 1000, 9000
    reset = em_intervals(O.trim("clip", 10000, a, b), {"clip": tl}, footprint_aware=True)
    assert not any(i.ev.label == "MIXED" for i in reset), "fixture no longer shows the defect"

    ptl = Timeline("signed", [SourceInterval("signed", i.out_start, i.out_end, i.ev)
                              for i in pivs], check=False)
    tmodel = O.trim("signed", parent.n_out, a, b)
    tivs = em_intervals(tmodel, {"signed": ptl}, footprint_aware=True)
    assert any(i.ev.label == "MIXED" for i in tivs), \
        "child derived from the parent lost the parent's mixed boundaries"

    # Compared interval by interval on the common refinement of the parent's
    # boundaries mapped into child coordinates, not by counting labels. An
    # earlier version of this test ended in `assert x or True`, which is
    # satisfied by anything: a test that cannot fail is worse than no test,
    # because it reports as evidence.
    for child in tivs:
        src_lo, src_hi = tmodel.pieces[0].source_range(child.out_start, child.out_end)
        overlapping = [q for q in pivs if q.out_start < src_hi and q.out_end > src_lo]
        assert overlapping, f"child [{child.out_start},{child.out_end}) maps to no parent evidence"
        expected = aggregate([q.ev for q in overlapping])
        assert child.ev.P == expected.P, (
            f"child [{child.out_start},{child.out_end}) claims {child.ev.label}; "
            f"its parent sources over [{src_lo},{src_hi}) give {expected.label}")
        assert expected.L <= child.ev.L, (
            f"child [{child.out_start},{child.out_end}) drops lineage "
            f"{sorted(expected.L - child.ev.L)}")

    # And the production path must reject a source reset. Rebuilding the child
    # from the original timeline is what the signing experiment used to do.
    reset_ivs = em_intervals(O.trim("clip", 10000, a, b), {"clip": tl},
                             footprint_aware=True)
    reset_labels = [i.ev.label for i in reset_ivs]
    inherited_labels = [i.ev.label for i in tivs]
    assert reset_labels != inherited_labels, (
        "the source-reset path and the inherited path agree, so this test no "
        "longer distinguishes them")
    assert "GENERATED" in reset_labels and "GENERATED" not in inherited_labels, (
        "the reset path should assert sharp GENERATED where the inherited path "
        "carries MIXED")


def test_validators_reject_an_invented_contributor():
    """Naming a contributor that contributes nothing must fail too.

    _required once took the union of the claimed indices with the geometrically
    active ones, reasoning that inventing a contributor only widens the required
    set and so cannot promote. True of promotion, wrong as validation: P1 is
    named exact union and says nothing dropped, nothing invented, and the union
    made invention undetectable. Claiming generated material where there is none
    is a false provenance statement in the direction that discredits real
    captured evidence.
    """
    A = Evidence(claim_of(["C"]), L=frozenset({"a"}))
    B = Evidence(claim_of(["G"]), L=frozenset({"b"}))
    tls = {"a": Timeline("a", [SourceInterval("a", 0, 10, A)]),
           "b": Timeline("b", [SourceInterval("b", 0, 10, B)])}
    out = O.concat([("a", 0, 10), ("b", 0, 10)])

    forged = [OutputInterval(0, 10, Evidence(claim_of(["C", "G"]),
                                             L=frozenset({"a", "b"})), (0, 1)),
              OutputInterval(10, 20, Evidence(claim_of(["G"]), L=frozenset({"b"})), (1,))]
    rejected = [f.__name__ for f in ALL_CHECKS if not f(out, tls, forged).passed]
    assert "p0_structural" in rejected, "invented contributor accepted"

    out_of_range = [OutputInterval(0, 10, A, (0, 7)),
                    OutputInterval(10, 20, B, (1,))]
    assert not c.p0_structural(out, tls, out_of_range).passed, "out-of-range index accepted"

    malformed = [OutputInterval(0, 10, A, None), OutputInterval(10, 20, B, (1,))]
    assert not c.p0_structural(out, tls, malformed).passed, "malformed indices accepted"

    canon = em_intervals(out, tls, footprint_aware=True)
    for f in ALL_CHECKS:
        assert f(out, tls, canon).passed, f"{f.__name__} rejected the canonical concat"


def test_overlay_source_map_overlap_stays_legitimate():
    """Two sources genuinely covering the same output range is what overlay is.
    Rejecting invented participation must not reject that."""
    A = Evidence(claim_of(["C"]), L=frozenset({"a"}))
    B = Evidence(claim_of(["G"]), L=frozenset({"b"}))
    tls = {"a": Timeline("a", [SourceInterval("a", 0, 10, A)]),
           "b": Timeline("b", [SourceInterval("b", 0, 10, B)])}
    out = O.overlay(("a", 10), ("b", 10), 0)
    canon = em_intervals(out, tls, footprint_aware=True)
    assert canon and canon[0].ev.label == "MIXED"
    for f in ALL_CHECKS:
        assert f(out, tls, canon).passed, f"{f.__name__} rejected a legitimate overlay"


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1; print(f"  FAIL  {t.__name__}: {e}")
        except Exception:
            failed += 1; print(f"  ERROR {t.__name__}"); traceback.print_exc(limit=1)
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
