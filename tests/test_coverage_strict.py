"""Output coverage and the strict profile."""
import pytest
import em_audio.operators as O
from em_audio.evidence import Evidence, claim_of
from em_audio.interval_map import (SourceInterval, Timeline, check_coverage,
                                   conform_to_decoded, em_intervals, strict_profile)

N = 1000


def _tl(gen=(400, 410)):
    C = Evidence(P=claim_of(["C"]), S={"cap": 0.9}, A={"cap": frozenset({"s"})}, L=frozenset({"a"}))
    G = Evidence(P=claim_of(["G"]), S={"cap": 0.05}, A={"cap": frozenset({"s"})}, L=frozenset({"g"}))
    a, b = gen
    return {"s": Timeline("s", [SourceInterval("s", 0, a, C), SourceInterval("s", a, b, G),
                                SourceInterval("s", b, N, C)])}


def test_conform_adds_whole_asset_tail():
    m = O.time_stretch("s", N, 1.10, 16000)
    c = conform_to_decoded(m, m.n_out + 7, {"s": N})
    check_coverage(c, m.n_out + 7)
    assert c.params["fallback_samples"] == 7
    tail = [iv for iv in em_intervals(c, _tl()) if iv.out_start >= m.n_out]
    assert tail and all(iv.ev.P == claim_of(["C", "G"]) for iv in tail)


def test_conform_clips_short_output():
    m = O.trim("s", N, 100, 900)
    c = conform_to_decoded(m, 700, {"s": N})
    check_coverage(c, 700)
    assert c.params["fallback_samples"] == 0 and max(p.out_end for p in c.pieces) == 700


def test_check_coverage_rejects_gap_and_overrun():
    m = O.trim("s", N, 0, 500)
    with pytest.raises(ValueError):
        check_coverage(m, 600)
    with pytest.raises(ValueError):
        check_coverage(m, 400)


def test_strict_profile_whole_asset_for_measured_only():
    tl = _tl(gen=(5, 15))   # generated material far from the end of the asset
    mp3 = strict_profile(O.transcode("s", N, "mp3"), {"s": N})
    assert all(iv.ev.P == claim_of(["C", "G"]) for iv in em_intervals(mp3, tl))
    flac = strict_profile(O.transcode("s", N, "flac"), {"s": N})
    assert any(iv.ev.P == claim_of(["C"]) for iv in em_intervals(flac, tl))
