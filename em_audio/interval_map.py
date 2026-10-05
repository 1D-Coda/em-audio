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
        # Indexed, not sliced: a slice copied the rest of the list on every
        # query, which made propagation quadratic in the number of intervals.
        ivs = self.intervals
        out = []
        for k in range(max(0, bisect_right(self._starts, a) - 1), len(ivs)):
            iv = ivs[k]
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

    def __post_init__(self) -> None:
        # SourceInterval refuses an empty span and this did not, so a zero-length
        # piece was constructible: trim with start == end, or concat given an
        # empty part. source_range then returns (0, 0) for it, which is not
        # distinguishable from a real range at the origin, and the containment
        # experiment's fallback path reads that as a sample outside every
        # declared range. The error is in the safe direction, a violation
        # reported where none exists, and no run has produced one; refusing the
        # object is cheaper than reasoning about it again.
        if self.out_end <= self.out_start:
            raise ValueError(
                f"empty or reversed output span [{self.out_start},{self.out_end})")

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

    # Two different things reach past the ends of a timeline and only one of
    # them is legitimate, so they are separated here rather than both being
    # absorbed by clamping.
    #
    # A footprint kernel may extend beyond the asset: there are no samples
    # there to depend on, so clipping it to the asset is correct.
    #
    # The nominal range a piece represents may not. If the piece claims source
    # samples the timeline carries no evidence for, that is missing evidence
    # inside the asset the caller declared, and clamping silently extended the
    # evidence that does exist over output the caller said came from elsewhere.
    # A timeline covering [0,10) passed to a model representing [0,20) produced
    # CAPTURED over the whole output.
    # Checked against the extent the piece itself declares, not against the
    # rounded range of each output sample. A rate-changing map rounds, so the
    # last output sample's nominal range can end a sample or two past the asset;
    # that is arithmetic at the boundary, not absent evidence, and an earlier
    # form of this check rejected three experiments over a one-sample overshoot.
    if piece.src_end > piece.src_start and (
            piece.src_start < tl.start or piece.src_end > tl.end):
        raise ValueError(
            f"timeline for {piece.src!r} covers [{tl.start},{tl.end}) but the "
            f"map draws from source [{piece.src_start},{piece.src_end}); "
            "evidence is missing inside the declared asset. Supply evidence for "
            "the whole asset, marking unknown spans as unverified, rather than "
            "leaving them absent."
        )
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


# ---------------------------------------------------------------------------
# Output coverage and the strict deployment profile
# ---------------------------------------------------------------------------

#: Map pieces whose footprint rests on measurement rather than on the algorithm.
#: The holdout challenge (Experiment K2) refutes both declarations on the
#: reference build, so the strict profile does not use them.
MEASURED_FOOTPRINT_LABELS = ("transcode:mp3", "time_stretch")


def _whole_asset_piece(oa: int, ob: int, src: str, n_src: int, label: str) -> MapPiece:
    """Output ``[oa,ob)`` depends on every sample of ``src``.

    The nominal range is the whole asset and the footprint is the asset length,
    so every output sample's widened range covers the asset whatever the rate.
    """
    return MapPiece(oa, ob, src, 0, n_src, n_src, label)


def check_coverage(out: DerivedOutput, n: int) -> None:
    """Raise unless the pieces cover ``[0, n)`` with no gap and nothing beyond.

    Pieces may overlap, as in a mix, where an output sample represents several
    sources; a gap is an output sample no declaration covers, and a piece past
    ``n`` declares output that does not exist.
    """
    if n < 0:
        raise ValueError(f"negative output length {n}")
    spans = sorted((p.out_start, p.out_end) for p in out.pieces)
    if n == 0:
        if spans:
            raise ValueError("pieces declared for an empty output")
        return
    if not spans or spans[0][0] != 0:
        raise ValueError("output coverage does not start at 0")
    reach = 0
    for a, b in spans:
        if b > n:
            raise ValueError(f"piece [{a},{b}) extends past the output length {n}")
        if a > reach:
            raise ValueError(f"output samples [{reach},{a}) are not covered")
        reach = max(reach, b)
    if reach != n:
        raise ValueError(f"output samples [{reach},{n}) are not covered")


def conform_to_decoded(out: DerivedOutput, n_decoded: int,
                       n_src: Dict[str, int]) -> DerivedOutput:
    """Fit a modelled map to the output length the processing actually produced.

    Pieces are clipped at ``n_decoded``. Output samples the model does not cover,
    a tail the operator emitted beyond the modelled extent, take whole-asset
    dependency on every source the output draws on: a declaration that is safe
    without any knowledge of where those samples came from. The result covers
    ``[0, n_decoded)`` exactly, which ``check_coverage`` verifies.
    """
    pieces: List[MapPiece] = []
    for p in out.pieces:
        if p.out_start >= n_decoded:
            continue
        if p.out_end <= n_decoded:
            pieces.append(p)
            continue
        # Clip, keeping the piece's own rate so the retained part maps as before.
        keep = n_decoded - p.out_start
        pieces.append(MapPiece(p.out_start, n_decoded, p.src, p.src_start,
                               p.src_start + keep * p.rate, p.footprint, p.label))
    srcs = sorted({p.src for p in out.pieces})
    covered = sorted((p.out_start, p.out_end) for p in pieces)
    gaps, reach = [], 0
    for a, b in covered:
        if a > reach:
            gaps.append((reach, a))
        reach = max(reach, b)
    if reach < n_decoded:
        gaps.append((reach, n_decoded))
    fallback = 0
    for a, b in gaps:
        fallback += b - a
        for s in srcs:
            pieces.append(_whole_asset_piece(a, b, s, n_src[s], "fallback:whole-asset"))
    res = DerivedOutput(n_decoded, pieces, out.operator,
                        dict(out.params, modelled_n_out=out.n_out,
                             decoded_n_out=n_decoded, fallback_samples=fallback))
    check_coverage(res, n_decoded)
    return res


def strict_profile(out: DerivedOutput, n_src: Dict[str, int]) -> DerivedOutput:
    """Replace every measured footprint by whole-asset dependency.

    Analytical footprints, those that follow from the algorithm and its pinned
    configuration, are kept. A measured footprint can be refuted by a probe and
    cannot be established by one, so the strict profile does not rely on it.
    """
    pieces = [(_whole_asset_piece(p.out_start, p.out_end, p.src, n_src[p.src],
                                  f"strict:{p.label}")
               if p.label.startswith(MEASURED_FOOTPRINT_LABELS) else p)
              for p in out.pieces]
    return DerivedOutput(out.n_out, pieces, out.operator, dict(out.params, profile="strict"))
