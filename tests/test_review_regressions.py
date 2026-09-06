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

from em_audio.evidence import Evidence, BOT, claim_of                     # noqa: E402
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
