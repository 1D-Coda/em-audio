"""Canonical decoded-essence identity.

Signal transparency (P8) is verified by comparing *decoded PCM*, never whole-file
hashes: a file hash changes as soon as a manifest is embedded, so a file-level
comparison would be meaningless.  The canonical essence of an asset is defined
as the SHA-256 of its decoded stream rendered to signed 16-bit little-endian PCM
at the asset's own sample rate and channel count, produced by stock ffmpeg.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Dict

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def decoded_pcm(path: str | Path) -> bytes:
    p = subprocess.run([FFMPEG, "-v", "error", "-i", str(path),
                        "-f", "s16le", "-acodec", "pcm_s16le", "-"],
                       capture_output=True, check=True)
    return p.stdout


def essence_hash(path: str | Path) -> str:
    return hashlib.sha256(decoded_pcm(path)).hexdigest()


def essence_identical(a: str | Path, b: str | Path) -> bool:
    return essence_hash(a) == essence_hash(b)


def file_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def essence_report(a: str | Path, b: str | Path) -> Dict[str, object]:
    ha, hb = essence_hash(a), essence_hash(b)
    return {"a": str(a), "b": str(b), "essence_a": ha, "essence_b": hb,
            "essence_identical": ha == hb,
            "file_a": file_hash(a), "file_b": file_hash(b),
            "file_identical": file_hash(a) == file_hash(b)}
