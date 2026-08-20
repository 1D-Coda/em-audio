"""The v1 audio operator set and its declared kernel footprints.

Every operator returns a :class:`DerivedOutput` describing, for each contiguous
derived span, which source samples that span represents.  The ``footprint``
field is a *conservative over-approximation* of the kernel radius: Proposition 5
in the manuscript shows that enlarging the required source set can only weaken
the emitted claim, so an over-approximation is always safe while an
under-approximation is not.

Footprint constants are pinned to the exact processing configuration used in
``ffmpeg_ops.py``; they are not folklore values.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

from .interval_map import DerivedOutput, MapPiece

# --- declared footprint constants -------------------------------------------
#: taps per phase of the swresample polyphase FIR, pinned via
#: ``-af aresample=filter_size=32`` (see ffmpeg_ops.resample).
RESAMPLE_FILTER_SIZE = 32
#: MPEG-1 Layer III long-window length in samples (2 granules x 576).
MP3_WINDOW = 1152
#: LAME encoder delay in samples.
MP3_ENCODER_DELAY = 576
#: conservative MP3 footprint: one full window either side plus encoder delay.
MP3_FOOTPRINT = MP3_WINDOW + MP3_ENCODER_DELAY
#: FLAC is a lossless block codec; decoded essence is bit-exact, so an output
#: sample depends on exactly one source sample.
FLAC_FOOTPRINT = 0
#: ffmpeg ``atempo`` overlap-add analysis window, in seconds.
ATEMPO_WINDOW_S = 0.030
#: Declared guard bands, in source samples, absorbing the difference between an
#: exact integer interval model and the frame- or packet-granular behaviour of a
#: real implementation.  A guard band only *enlarges* D_y, which by Proposition 5
#: can only weaken the emitted claim, so an over-declared band is safe and an
#: under-declared one is a conformance failure.  ``transform_matrix.py`` measures
#: the model-versus-ffmpeg deviation on every corpus clip and fails if any
#: deviation exceeds the declared band.
GUARD_BAND = {
    "trim": 0,
    "concat": 0,
    "resample": 64,
    # One MPEG-1 Layer III granule. The guard absorbs frame-alignment slack
    # between the exact integer model and the encoder's granule boundaries; it
    # is added to the kernel radius, as for every other operator, rather than
    # being an independent floor.
    "transcode": MP3_ENCODER_DELAY,
    "normalize": 0,
    "time_stretch": 2048,
    # Raised from 2048 after the containment probe measured a frame-granular
    # reach of 3261 source samples past a retained run's start: a selector can
    # emit a frame that begins before the requested cut. The declared bound must
    # contain what was measured, so it is set above it with margin.
    "silence_removal": 4096,
    "overlay": 0,
}


def _fp_resample(fs_in: int, fs_out: int, filter_size: int = RESAMPLE_FILTER_SIZE) -> int:
    """Conservative source-domain kernel radius of a polyphase resampler."""
    ratio = max(1.0, fs_in / float(fs_out))
    return int(math.ceil(filter_size / 2.0 * ratio)) + 1


# --- operators ---------------------------------------------------------------

def trim(src: str, n_src: int, start: int, end: int) -> DerivedOutput:
    """Crop ``[start,end)`` of one source.  1:1 map, zero footprint."""
    start = max(0, int(start)); end = min(int(n_src), int(end))
    n = end - start
    return DerivedOutput(n, [MapPiece(0, n, src, start, end, 0, "trim")],
                         "trim", {"start": start, "end": end})


def concat(parts: Sequence[Tuple[str, int, int]]) -> DerivedOutput:
    """Append ``(src, start, end)`` parts.  1:1 map, zero footprint."""
    pieces: List[MapPiece] = []
    o = 0
    for i, (src, a, b) in enumerate(parts):
        n = int(b) - int(a)
        pieces.append(MapPiece(o, o + n, src, int(a), int(b), 0, f"concat[{i}]"))
        o += n
    return DerivedOutput(o, pieces, "concat", {"n_parts": len(parts)})


def resample(src: str, n_src: int, fs_in: int, fs_out: int,
             filter_size: int = RESAMPLE_FILTER_SIZE) -> DerivedOutput:
    n_out = int(math.floor(n_src * fs_out / float(fs_in)))
    fp = _fp_resample(fs_in, fs_out, filter_size) + GUARD_BAND["resample"]
    return DerivedOutput(n_out, [MapPiece(0, n_out, src, 0, n_src, fp, "resample")],
                         "resample", {"fs_in": fs_in, "fs_out": fs_out,
                                      "filter_size": filter_size, "footprint": fp})


def transcode(src: str, n_src: int, codec: str) -> DerivedOutput:
    fp = {"mp3": MP3_FOOTPRINT, "flac": FLAC_FOOTPRINT, "wav": 0}[codec]
    if codec == "mp3":
        fp += GUARD_BAND["transcode"]          # kernel + guard, as elsewhere
    return DerivedOutput(n_src, [MapPiece(0, n_src, src, 0, n_src, fp, f"transcode:{codec}")],
                         "transcode", {"codec": codec, "footprint": fp})


def normalize(src: str, n_src: int, *, strict_global: bool = False) -> DerivedOutput:
    """Amplitude normalisation by a single scalar gain.

    The gain is derived from the whole signal, but the *content* an output
    sample represents is one source sample.  EM aggregates over represented
    content, so the default footprint is 0.  ``strict_global=True`` selects the
    maximally conservative reading in which every output sample represents the
    whole signal; both readings are measured and reported (Section: Results).
    """
    fp = n_src if strict_global else 0
    return DerivedOutput(n_src, [MapPiece(0, n_src, src, 0, n_src, fp, "normalize")],
                         "normalize", {"strict_global": strict_global, "footprint": fp})


def time_stretch(src: str, n_src: int, tempo: float, fs: int,
                 window_s: float = ATEMPO_WINDOW_S) -> DerivedOutput:
    """Deterministic timestamp map ``t_src = tempo * t_out`` with OLA footprint."""
    n_out = int(math.floor(n_src / float(tempo)))
    fp = int(math.ceil(window_s * fs * max(1.0, tempo))) + 1 + GUARD_BAND["time_stretch"]
    return DerivedOutput(n_out, [MapPiece(0, n_out, src, 0, n_src, fp, "time_stretch")],
                         "time_stretch", {"tempo": tempo, "window_s": window_s, "footprint": fp})


def silence_removal(src: str, retained: Sequence[Tuple[int, int]]) -> DerivedOutput:
    """Explicit retained-interval map; one span per retained run.

    A real selector works at frame granularity, so the declared guard band
    covers the difference between the exact retained-sample model and the
    implementation's frame-aligned cut points.
    """
    pieces: List[MapPiece] = []
    o = 0
    g = GUARD_BAND["silence_removal"]
    for i, (a, b) in enumerate(retained):
        n = int(b) - int(a)
        if n <= 0:
            continue
        pieces.append(MapPiece(o, o + n, src, int(a), int(b), g, f"retained[{i}]"))
        o += n
    if not pieces:
        raise ValueError("silence removal retained nothing")
    return DerivedOutput(o, pieces, "silence_removal", {"n_runs": len(pieces)})


def overlay(a: Tuple[str, int], b: Tuple[str, int], offset: int = 0) -> DerivedOutput:
    """Mix two sources, ``b`` starting at output sample ``offset``.

    Output length is the envelope.  Over the overlap the output represents both
    sources, so two pieces cover the same output range and ``D_y`` is their
    union.
    """
    (sa, na), (sb, nb) = a, b
    n_out = max(na, offset + nb)
    pieces = [MapPiece(0, na, sa, 0, na, 0, "overlay:a"),
              MapPiece(offset, offset + nb, sb, 0, nb, 0, "overlay:b")]
    return DerivedOutput(n_out, pieces, "overlay", {"offset": offset})


OPERATORS = {
    "trim": trim, "concat": concat, "resample": resample, "transcode": transcode,
    "normalize": normalize, "time_stretch": time_stretch,
    "silence_removal": silence_removal, "overlay": overlay,
}
