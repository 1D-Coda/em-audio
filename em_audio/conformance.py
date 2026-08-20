"""Executable operator-contract checks (properties P1-P7).

P8 (signal transparency) is file-level and lives in ``essence.py`` plus the
transformation-matrix experiment.

Each check returns ``(passed, detail)``.  A conformance run aggregates them and
``run_all.sh`` exits non-zero on any failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .evidence import BOT, Evidence, _Bot, aggregate, leq_claim, promotes
from .interval_map import (DerivedOutput, OutputInterval, SourceInterval, Timeline,
                           em_intervals, span_evidence, _sources_for)


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


def _required(out: DerivedOutput, timelines: Dict[str, Timeline], pis, oa: int, ob: int,
              footprint_aware: bool = True) -> List[SourceInterval]:
    if isinstance(pis, int):
        pis = (pis,)
    srcs: List[SourceInterval] = []
    for pi in pis:
        srcs.extend(_sources_for(out.pieces[pi], timelines, oa, ob,
                                 footprint_aware=footprint_aware))
    return srcs


# --- P1 ---------------------------------------------------------------------

def p1_exact_union(out: DerivedOutput, timelines: Dict[str, Timeline],
                   intervals: Sequence[OutputInterval]) -> Check:
    """Output provenance is exactly the union of required-source provenance:
    nothing dropped, nothing invented."""
    for iv in intervals:
        srcs = _required(out, timelines, iv.piece_indices, iv.out_start, iv.out_end)
        atoms = set()
        bot = False
        for s in srcs:
            if isinstance(s.ev.P, _Bot):
                bot = True
            else:
                atoms |= set(s.ev.P)
        if bot:
            if not isinstance(iv.ev.P, _Bot):
                return Check("P1_exact_union", False,
                             f"[{iv.out_start},{iv.out_end}) required source in ⊥ but output is {iv.ev.label}")
            continue
        if isinstance(iv.ev.P, _Bot) or set(iv.ev.P) != atoms:
            return Check("P1_exact_union", False,
                         f"[{iv.out_start},{iv.out_end}) union {sorted(atoms)} != output {iv.ev.P}")
    return Check("P1_exact_union", True, f"{len(intervals)} intervals")


# --- P2 ---------------------------------------------------------------------

def p2_no_promotion(out: DerivedOutput, timelines: Dict[str, Timeline],
                    intervals: Sequence[OutputInterval]) -> Check:
    """The emitted claim is no stronger than the meet of every required source."""
    for iv in intervals:
        srcs = _required(out, timelines, iv.piece_indices, iv.out_start, iv.out_end)
        ref = aggregate([s.ev for s in srcs])
        if promotes(ref.P, iv.ev.P):
            return Check("P2_no_promotion", False,
                         f"[{iv.out_start},{iv.out_end}) output {iv.ev.label} > source meet {ref.label}")
    return Check("P2_no_promotion", True, f"{len(intervals)} intervals")


# --- P3 ---------------------------------------------------------------------

def p3_unverified_non_promotion(out: DerivedOutput, timelines: Dict[str, Timeline],
                                intervals: Sequence[OutputInterval]) -> Check:
    """A span containing any unverified required source stays unverified."""
    for iv in intervals:
        srcs = _required(out, timelines, iv.piece_indices, iv.out_start, iv.out_end)
        if any(isinstance(s.ev.P, _Bot) for s in srcs) and not isinstance(iv.ev.P, _Bot):
            return Check("P3_unverified_non_promotion", False,
                         f"[{iv.out_start},{iv.out_end}) became {iv.ev.label} despite ⊥ source")
    return Check("P3_unverified_non_promotion", True, f"{len(intervals)} intervals")


# --- P4 ---------------------------------------------------------------------

def p4_support_non_promotion(out: DerivedOutput, timelines: Dict[str, Timeline],
                             intervals: Sequence[OutputInterval]) -> Check:
    for iv in intervals:
        srcs = _required(out, timelines, iv.piece_indices, iv.out_start, iv.out_end)
        for mu, val in iv.ev.S.items():
            applicable = [s.ev for s in srcs if mu in s.ev.A]
            if not applicable:
                return Check("P4_support_non_promotion", False,
                             f"channel {mu} emitted with no applicable source")
            if any(mu not in e.S for e in applicable):
                return Check("P4_support_non_promotion", False,
                             f"channel {mu} emitted although an applicable source reports no value")
            for e in applicable:
                if val > e.S[mu] + 1e-12:
                    return Check("P4_support_non_promotion", False,
                                 f"[{iv.out_start},{iv.out_end}) {mu}={val} > source {e.S[mu]}")
    return Check("P4_support_non_promotion", True, f"{len(intervals)} intervals")


# --- P8 ---------------------------------------------------------------------

def p8_channel_scope_agreement(out: "DerivedOutput", timelines: Dict[str, Timeline],
                               intervals: Sequence[OutputInterval]) -> Check:
    """Every valued channel carries a non-empty scope, and every scoped channel
    carries a value. P4 iterates S and P5 iterates A, so neither on its own
    excludes a value declared applicable nowhere."""
    for iv in intervals:
        valued, scoped = set(iv.ev.S), set(iv.ev.A)
        if valued != scoped:
            return Check("P8_channel_scope_agreement", False,
                         f"[{iv.out_start},{iv.out_end}) valued {sorted(valued)} "
                         f"but scoped {sorted(scoped)}")
        for mu, scope in iv.ev.A.items():
            if not scope:
                return Check("P8_channel_scope_agreement", False,
                             f"[{iv.out_start},{iv.out_end}) channel {mu} scoped to nothing")
    return Check("P8_channel_scope_agreement", True, f"{len(intervals)} intervals")


# --- P5 ---------------------------------------------------------------------

def p5_applicability_non_broadening(out: DerivedOutput, timelines: Dict[str, Timeline],
                                    intervals: Sequence[OutputInterval]) -> Check:
    for iv in intervals:
        srcs = _required(out, timelines, iv.piece_indices, iv.out_start, iv.out_end)
        for mu, scope in iv.ev.A.items():
            applicable = [s.ev for s in srcs if mu in s.ev.A]
            if not applicable:
                return Check("P5_applicability_non_broadening", False, f"channel {mu} invented")
            inter = frozenset.intersection(*[e.A[mu] for e in applicable])
            if not scope <= inter:
                return Check("P5_applicability_non_broadening", False,
                             f"[{iv.out_start},{iv.out_end}) scope {sorted(scope)} broader than {sorted(inter)}")
    return Check("P5_applicability_non_broadening", True, f"{len(intervals)} intervals")


# --- P6 ---------------------------------------------------------------------

def p6_complete_lineage(out: DerivedOutput, timelines: Dict[str, Timeline],
                        intervals: Sequence[OutputInterval]) -> Check:
    for iv in intervals:
        srcs = _required(out, timelines, iv.piece_indices, iv.out_start, iv.out_end)
        need = frozenset().union(*[s.ev.L for s in srcs]) if srcs else frozenset()
        if not need <= iv.ev.L:
            missing = sorted(need - iv.ev.L)
            return Check("P6_complete_lineage", False,
                         f"[{iv.out_start},{iv.out_end}) missing lineage {missing[:4]}")
    return Check("P6_complete_lineage", True, f"{len(intervals)} intervals")


# --- footprint monotonicity -------------------------------------------------

def p_footprint_monotone(out: DerivedOutput, timelines: Dict[str, Timeline]) -> Check:
    """Enlarging D_y can only weaken the emitted claim (Proposition 5).

    Compared here as footprint-aware (larger D_y) versus footprint-blind.
    """
    wide = span_evidence(out, timelines, "em")
    narrow = span_evidence(out, timelines, "em_nofp")
    for w, n in zip(wide, narrow):
        if not leq_claim(w.ev.P, n.ev.P):
            return Check("P_footprint_monotone", False,
                         f"[{w.out_start},{w.out_end}) wider D_y gave stronger claim")
        for mu, v in w.ev.S.items():
            if mu in n.ev.S and v > n.ev.S[mu] + 1e-12:
                return Check("P_footprint_monotone", False, f"channel {mu} rose with wider D_y")
    return Check("P_footprint_monotone", True, f"{len(wide)} spans")


# --- P7 composition ---------------------------------------------------------

def compose_timeline(out: DerivedOutput, timelines: Dict[str, Timeline],
                     new_src: str) -> Timeline:
    """Turn an EM output into the source timeline of the next operator."""
    ivs = em_intervals(out, timelines, footprint_aware=True)
    return Timeline(new_src, [SourceInterval(new_src, iv.out_start, iv.out_end, iv.ev)
                              for iv in ivs])


def p7_composition(chain: Sequence[Tuple[DerivedOutput, Dict[str, Timeline]]],
                   final: Sequence[OutputInterval],
                   direct: Sequence[OutputInterval]) -> Check:
    """A composed chain refuses at least as much as the equivalent direct meet."""
    if len(final) != len(direct):
        return Check("P7_composition", True, "different partitions; compared pointwise below")
    for a, b in zip(final, direct):
        if not leq_claim(a.ev.P, b.ev.P):
            return Check("P7_composition", False, "composed chain stronger than direct meet")
    return Check("P7_composition", True, f"{len(final)} intervals")


def run_property_suite(out: DerivedOutput, timelines: Dict[str, Timeline]) -> List[Check]:
    ivs = em_intervals(out, timelines, footprint_aware=True)
    return [
        p1_exact_union(out, timelines, ivs),
        p2_no_promotion(out, timelines, ivs),
        p3_unverified_non_promotion(out, timelines, ivs),
        p4_support_non_promotion(out, timelines, ivs),
        p5_applicability_non_broadening(out, timelines, ivs),
        p6_complete_lineage(out, timelines, ivs),
        p8_channel_scope_agreement(out, timelines, ivs),
        p_footprint_monotone(out, timelines),
    ]
