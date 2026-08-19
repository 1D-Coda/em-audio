"""Audio processing through *stock FFmpeg via its command line*.

No project code is in the signal path.  This is the audio counterpart of the
third-party-generator audit in the prior spatial work: the artefact that either
does or does not exhibit provenance promotion is produced by software the
authors do not control, and only the *evidence policies* are evaluated here.

Every function returns the exact argv it ran so the manuscript can quote it.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .operators import ATEMPO_WINDOW_S, RESAMPLE_FILTER_SIZE

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"


@dataclass
class Run:
    argv: List[str]
    returncode: int
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _run(argv: Sequence[str]) -> Run:
    p = subprocess.run(list(argv), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(argv)}\n{p.stderr[-2000:]}")
    return Run(list(argv), p.returncode, p.stderr)


def versions() -> Dict[str, str]:
    fv = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True).stdout.splitlines()[0]
    return {"ffmpeg": fv.strip()}


def probe(path: str | Path) -> Dict[str, object]:
    p = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "a:0",
                        "-show_entries", "stream=sample_rate,channels,codec_name,duration_ts",
                        "-show_entries", "format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    d = json.loads(p.stdout)
    st = d["stream" + "s"][0]
    return {"sample_rate": int(st["sample_rate"]), "channels": int(st["channels"]),
            "codec": st["codec_name"], "duration": float(d["format"]["duration"])}


# --- generation --------------------------------------------------------------

def sine(path: Path, seconds: float, fs: int = 48000, freq: float = 440.0) -> Run:
    return _run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi",
                 "-i", f"sine=frequency={freq}:duration={seconds}:sample_rate={fs}",
                 "-ac", "1", "-c:a", "pcm_s16le", str(path)])


def silence(path: Path, seconds: float, fs: int = 48000) -> Run:
    return _run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi",
                 "-i", f"anullsrc=r={fs}:cl=mono", "-t", str(seconds),
                 "-c:a", "pcm_s16le", str(path)])


# --- v1 operator set ---------------------------------------------------------

def _codec_args(codec: str, bitrate: str = "128k") -> List[str]:
    if codec in ("wav", "pcm_s16le"):
        return ["-c:a", "pcm_s16le"]
    if codec == "flac":
        # pin the block size so the encoder does not inherit an incompatible
        # frame size from a FLAC input stream
        return ["-c:a", "flac", "-frame_size", "4096"]
    if codec == "mp3":
        return ["-c:a", "libmp3lame", "-b:a", bitrate]
    raise ValueError(codec)


def trim(src: Path, dst: Path, start_s: float, dur_s: float, codec: str = "wav") -> Run:
    return _run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                 "-ss", f"{start_s:.9f}", "-t", f"{dur_s:.9f}",
                 *_codec_args(codec), str(dst)])


def concat(srcs: Sequence[Path], dst: Path) -> Run:
    argv = [FFMPEG, "-y", "-loglevel", "error"]
    for s in srcs:
        argv += ["-i", str(s)]
    n = len(srcs)
    inputs = "".join(f"[{i}:a]" for i in range(n))
    argv += ["-filter_complex", f"{inputs}concat=n={n}:v=0:a=1[out]",
             "-map", "[out]", "-c:a", "pcm_s16le", str(dst)]
    return _run(argv)


def resample(src: Path, dst: Path, fs_out: int,
             filter_size: int = RESAMPLE_FILTER_SIZE) -> Run:
    return _run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                 "-af", f"aresample={fs_out}:filter_size={filter_size}:resampler=swr",
                 "-c:a", "pcm_s16le", str(dst)])


def transcode(src: Path, dst: Path, codec: str, bitrate: str = "128k") -> Run:
    return _run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                 *_codec_args(codec, bitrate), str(dst)])


def normalize(src: Path, dst: Path, gain_db: float) -> Run:
    """Single scalar gain (peak normalisation applied as one volume factor)."""
    return _run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                 "-af", f"volume={gain_db:.6f}dB", "-c:a", "pcm_s16le", str(dst)])


def peak_gain_db(src: Path, target_db: float = -1.0) -> float:
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", str(src), "-af", "volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    peak = 0.0
    for line in p.stderr.splitlines():
        if "max_volume:" in line:
            peak = float(line.split("max_volume:")[1].strip().split()[0])
    return target_db - peak


def time_stretch(src: Path, dst: Path, tempo: float) -> Run:
    return _run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                 "-af", f"atempo={tempo:.6f}", "-c:a", "pcm_s16le", str(dst)])


def cut_runs(src: Path, dst: Path, runs: Sequence[Tuple[float, float]], fs: int) -> Run:
    """Silence removal expressed as an explicit retained-interval map."""
    sel = "+".join(f"between(t,{a:.9f},{b:.9f})" for a, b in runs)
    return _run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
                 "-af", f"aselect='{sel}',asetpts=N/SR/TB", "-c:a", "pcm_s16le", str(dst)])


def overlay(a: Path, b: Path, dst: Path, offset_s: float) -> Run:
    delay_ms = int(round(offset_s * 1000))
    return _run([FFMPEG, "-y", "-loglevel", "error", "-i", str(a), "-i", str(b),
                 "-filter_complex",
                 f"[1:a]adelay={delay_ms}:all=1[d];[0:a][d]amix=inputs=2:duration=longest:normalize=0[out]",
                 "-map", "[out]", "-c:a", "pcm_s16le", str(dst)])
