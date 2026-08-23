"""Temporal interval maps: the audio instantiation of the complete-source rule.

All positions are in *samples* on a named source asset and all intervals are
half-open ``[start, end)``, matching the C2PA temporal-range convention in which
"All start times are inclusive of that moment in time, and all end times are, by
default, exclusive of it" (C2PA 2.4, section 18.2.2.3).
"""
from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from .evidence import BOT, Evidence, aggregate, boundary_aggregate


@dataclass(frozen=True)
class SourceInterval:
    """One evidence-homogeneous interval of a source asset."""
    src: str
    start: int
    end: int
    ev: Evidence

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError(f"empty or reversed interval [{self.start},{self.end})")


class Timeline:
    """An ordered, gapless partition of one source asset into evidence intervals."""

    def __init__(self, src: str, intervals: Sequence[SourceInterval], *, check: bool = True):
        if not intervals:
            raise ValueError("timeline must have at least one interval")
        if check:
            iv = sorted(intervals, key=lambda i: i.start)
            for a, b in zip(iv, iv[1:]):
                if a.end != b.start:
                    raise ValueError(f"timeline is not gapless at {a.end} != {b.start}")
                if a.src != b.src:
                    raise ValueError("timeline mixes source assets")
        else:
            iv = intervals
        self.src = src
        self.intervals: List[SourceInterval] = list(iv)
        self._starts = [i.start for i in self.intervals]

    # -- geometry --------------------------------------------------------
    @property
    def start(self) -> int:
        return self.intervals[0].start

    @property
    def end(self) -> int:
        return self.intervals[-1].end

    @property
    def n_samples(self) -> int:
        return self.end - self.start

    def boundaries(self) -> List[int]:
        return [self.start] + [i.end for i in self.intervals]

    # -- lookup ----------------------------------------------------------
    def at(self, pos: int) -> SourceInterval:
        """The interval containing sample ``pos`` (clamped into range)."""
        pos = max(self.start, min(self.end - 1, int(pos)))
        k = bisect_right(self._starts, pos) - 1
        return self.intervals[k]

    def covering(self, a: int, b: int) -> List[SourceInterval]:
        """Every interval intersecting ``[a, b)`` -- the complete required set.

        The range is clamped to the timeline; an empty request yields the single
        interval containing ``a`` so that a zero-width footprint still names a
        source rather than silently naming nothing.
        """
        a = max(self.start, min(self.end, int(a)))
        b = max(self.start, min(self.end, int(b)))
        if b <= a:
            return [self.at(a)]
        lo = bisect_right(self._starts, a) - 1
        out = []
        for iv in self.intervals[max(0, lo):]:
            if iv.start >= b:
                break
            if iv.end > a:
                out.append(iv)
        return out


@dataclass(frozen=True)
class MapPiece:
    """One contiguous derived span: output ``[out_start,out_end)`` represents
    source ``[src_start, src_end)`` on asset ``src``.

    ``footprint`` is the *conservative kernel radius in source samples*: the
    number of extra source samples on each side that any output sample in this
    piece may depend on.  It is declared per operator and is 0 only for
    operators whose output samples depend on exactly one source sample.
    """
    out_start: int
    out_end: int
    src: str
    src_start: float
    src_end: float
    footprint: int = 0
    label: str = ""

    @property
    def n_out(self) -> int:
        return self.out_end - self.out_start

    @property
    def rate(self) -> float:
        """Source samples consumed per output sample."""
        if self.n_out <= 0:
            return 1.0
        return (self.src_end - self.src_start) / self.n_out

    def to_source(self, out_pos: float) -> float:
        return self.src_start + (out_pos - self.out_start) * self.rate

    def source_range(self, oa: int, ob: int, *, with_footprint: bool = True) -> Tuple[int, int]:
        """Required source sample range for output range ``[oa, ob)``."""
        oa = max(self.out_start, oa)
        ob = min(self.out_end, ob)
        if ob <= oa:
            return (0, 0)
        s0 = self.to_source(oa)
        s1 = self.to_source(ob)
        lo = int(math.floor(min(s0, s1)))
        hi = int(math.ceil(max(s0, s1)))
        if with_footprint:
            lo -= self.footprint
            hi += self.footprint
        if hi <= lo:
            hi = lo + 1
        return (lo, hi)


@dataclass
class DerivedOutput:
    """The result of applying an operator: output length plus its span map."""
    n_out: int
    pieces: List[MapPiece]
    operator: str
    params: Dict[str, object]


# ---------------------------------------------------------------------------
# Evidence policies
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OutputInterval:
    out_start: int
    out_end: int
    ev: Evidence
    piece_indices: Tuple[int, ...] = ()

    @property
    def piece_index(self) -> int:
        return self.piece_indices[0] if self.piece_indices else 0


def _sources_for(piece: MapPiece, timelines: Dict[str, Timeline], oa: int, ob: int,
                 *, footprint_aware: bool) -> List[SourceInterval]:
    lo, hi = piece.source_range(oa, ob, with_footprint=footprint_aware)
    tl = timelines[piece.src]
    return tl.covering(lo, hi)


def em_intervals(out: DerivedOutput, timelines: Dict[str, Timeline],
                 *, footprint_aware: bool = True) -> List[OutputInterval]:
    """Complete-source evidence, refined to the finest well-defined partition.

    The output partition is the pull-back of every source evidence boundary that
    falls inside a piece, taken across *all* pieces.  Where pieces overlap -- a
    mix or overlay -- the required source set of an output interval is the union
    over every piece covering it, so an overlapped region represents both
    sources.  Adjacent intervals with identical evidence are merged.
    """
    if not out.pieces:
        return []
    cuts = set()
    for p in out.pieces:
        cuts.add(p.out_start); cuts.add(p.out_end)
        tl = timelines[p.src]
        rate = p.rate
        if rate:
            # Pull every source evidence boundary back into output coordinates.
            # When the piece declares a kernel footprint, the *widened* source
            # range of an output sample starts or stops covering a neighbouring
            # interval at the pull-backs of b -/+ footprint, not of b itself, so
            # those shifted positions are cut as well.  Without them the whole
            # emitted interval inherits the widened source set -- safe under
            # footprint monotonicity, but needlessly coarse; the claim-dilution
            # experiment measures exactly this and caught the earlier
            # interval-granularity behaviour.
            offsets = (0,) if not (footprint_aware and p.footprint) else \
                (-p.footprint, 0, p.footprint)
            for b in tl.boundaries():
                for off in offsets:
                    o = p.out_start + (b + off - p.src_start) / rate
                    for oi in (int(math.floor(o)), int(math.floor(o)) + 1):
                        if p.out_start < oi < p.out_end:
                            cuts.add(oi)
    edges = sorted(cuts)
    res: List[OutputInterval] = []
    for oa, ob in zip(edges, edges[1:]):
        covering = [(i, p) for i, p in enumerate(out.pieces)
                    if p.out_start <= oa and p.out_end >= ob]
        if not covering:
            continue
        srcs: List[SourceInterval] = []
        for _, p in covering:
            srcs.extend(_sources_for(p, timelines, oa, ob, footprint_aware=footprint_aware))
        res.append(OutputInterval(oa, ob, aggregate([s.ev for s in srcs]),
                                  tuple(i for i, _ in covering)))
    merged: List[OutputInterval] = []
    for iv in res:
        if merged and merged[-1].out_end == iv.out_start and merged[-1].ev == iv.ev \
                and merged[-1].piece_indices == iv.piece_indices:
            prev = merged.pop()
            merged.append(OutputInterval(prev.out_start, iv.out_end, iv.ev, iv.piece_indices))
        else:
            merged.append(iv)
    return merged


def span_evidence(out: DerivedOutput, timelines: Dict[str, Timeline], policy: str) -> List[OutputInterval]:
    """One evidence record per derived span, under the named policy.

    Policies
    --------
    ``em``            complete-source aggregation, kernel-footprint aware
    ``em_nofp``       complete-source aggregation, footprint-blind
    ``boundary``      boundary-only inheritance, footprint-blind  (BASELINE)
    ``boundary_fp``   boundary-only inheritance, footprint aware
    """
    fp = policy in ("em", "boundary_fp")
    boundary = policy in ("boundary", "boundary_fp")
    res: List[OutputInterval] = []
    for pi, p in enumerate(out.pieces):
        srcs = _sources_for(p, timelines, p.out_start, p.out_end, footprint_aware=fp)
        evs = [x.ev for x in srcs]
        ev = boundary_aggregate(evs) if boundary else aggregate(evs)
        res.append(OutputInterval(p.out_start, p.out_end, ev, (pi,)))
    return res
