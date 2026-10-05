"""Fetch a deterministic subset of PartialSpoof v1.2 (Zhang et al.; CC BY 4.0).

PartialSpoof embeds synthetic segments, from the ASVspoof 2019 LA spoofing
systems, inside bona fide utterances, and publishes where they are: per-utterance
timestamp files (``vad``) and 10 ms segment labels. That is third-party
mixed-origin speech with third-party ground truth, which this project's own
corpus cannot be.

The development archive is 2 GB. It is streamed once: its published MD5 is
checked over the whole stream while only the selected utterances are written,
so nothing of that size reaches the disk. The selection is every k-th spoofed
development utterance in sorted order, fixed here before any result is seen.

Record: https://zenodo.org/records/5766198 (v1.2).
"""
from __future__ import annotations

import hashlib, io, json, sys, tarfile, urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "corpus" / "partialspoof"
REC = "https://zenodo.org/records/5766198/files/"
MD5 = {"database_vad.tar.gz": "95e77e19a1bb4f2e79ed138fd35621ad",
       "database_segment_labels_v1.2.tar.gz": "c2bf6638e59ec7a5cf93c4a510fe4efe",
       "database_dev.tar.gz": "ddd4cd3221b7210ac879f67452fb209e"}
N_SELECT = 600


class _Hashing(io.RawIOBase):
    def __init__(self, raw):
        self.raw, self.md5 = raw, hashlib.md5()

    def readable(self):
        return True

    def readinto(self, b):
        chunk = self.raw.read(len(b))
        self.md5.update(chunk)
        b[:len(chunk)] = chunk
        return len(chunk)


def _stream(name):
    return urllib.request.urlopen(REC + name + "?download=1", timeout=120)


def _small(name) -> bytes:
    data = _stream(name).read()
    got = hashlib.md5(data).hexdigest()
    if got != MD5[name]:
        sys.exit(f"{name}: md5 {got} != published {MD5[name]}")
    return data


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wav").mkdir(exist_ok=True)
    vad = {}
    with tarfile.open(fileobj=io.BytesIO(_small("database_vad.tar.gz")), mode="r:gz") as t:
        for m in t:
            if m.isfile() and "/dev/" in m.name and m.name.endswith(".vad"):
                uid = Path(m.name).stem
                rows = [ln.split() for ln in t.extractfile(m).read().decode().splitlines() if ln.strip()]
                vad[uid] = [(float(a), float(b), int(c)) for a, b, c in rows]
    with tarfile.open(fileobj=io.BytesIO(_small("database_segment_labels_v1.2.tar.gz")), mode="r:gz") as t:
        m = t.getmember("database/segment_labels/dev_seglab_0.01.npy")
        seglab = np.load(io.BytesIO(t.extractfile(m).read()), allow_pickle=True).item()
    spoofed = sorted(u for u in vad if u.startswith("CON_") and any(c == 0 for _, _, c in vad[u]))
    step = max(1, len(spoofed) // N_SELECT)
    chosen = set(spoofed[::step][:N_SELECT])

    raw = _Hashing(_stream("database_dev.tar.gz"))
    buf = io.BufferedReader(raw, buffer_size=1 << 20)
    got = {}
    with tarfile.open(fileobj=buf, mode="r|gz") as t:
        for m in t:
            uid = Path(m.name).stem
            if m.isfile() and uid in chosen:
                data = t.extractfile(m).read()
                (OUT / "wav" / f"{uid}.wav").write_bytes(data)
                got[uid] = hashlib.sha256(data).hexdigest()
    while buf.read(1 << 20):
        pass                                   # hash the whole archive
    if raw.md5.hexdigest() != MD5["database_dev.tar.gz"]:
        sys.exit(f"dev archive md5 {raw.md5.hexdigest()} != published")
    missing = chosen - set(got)
    if missing:
        sys.exit(f"{len(missing)} selected utterances absent from the archive")
    meta = {uid: {"sha256": got[uid], "vad": vad[uid],
                  "seglab_0.01": [int(x) for x in seglab[uid]]} for uid in sorted(got)}
    (OUT / "partialspoof_subset.json").write_text(json.dumps(
        {"source": REC, "version": "1.2", "license": "CC BY 4.0",
         "split": "dev", "spoofed_dev_utterances": len(spoofed), "selection_step": step,
         "archive_md5": MD5, "utterances": meta}, indent=1) + "\n", newline="\n")
    print(f"fetched {len(got)} of {len(spoofed)} spoofed dev utterances (every {step}th); md5 verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
