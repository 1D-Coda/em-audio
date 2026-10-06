"""Fetch a deterministic subset of PartialEdit v1.1, subset E1 (Zhang et al.,
Interspeech 2025; CC BY 4.0).

PartialEdit replaces one to three words inside genuine VCTK recordings with
neural speech editing (E1: VoiceCraft) and publishes the edited regions as
timestamps. It is a different generator generation from PartialSpoof's: a
codec language model editing words in place, the realistic threat to a genuine
recording, rather than concatenated segments from 2019 spoofing systems.

The E1 archive is 3.4 GB, so the stream is stopped as soon as the subset is
complete. The selection, fixed here before any result is seen: in archive
order, the first PER_SPEAKER labelled files of each speaker, until 600 are
taken, which spreads the subset over about thirty speakers while reading
roughly a third of the archive. Because the archive is not read to the end its
published MD5 cannot be checked; the label file's MD5 is, and every kept file
is recorded with its SHA-256 and archive member name.

Record: https://zenodo.org/records/18829689 (v1.1).
"""
from __future__ import annotations

import csv, hashlib, io, json, sys, tarfile, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "corpus" / "partialedit"
REC = "https://zenodo.org/records/18829689/files/"
MD5 = {"PartialEdit_E1E2.csv": "3ff74c4e5cab69013d1d9c4a30f59cae",
       "E1.tar.gz": "1f489d2ff488ddd6c9b655127725af2f"}
N_SELECT = 600
PER_SPEAKER = 20


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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wav").mkdir(exist_ok=True)
    data = _stream("PartialEdit_E1E2.csv").read()
    if hashlib.md5(data).hexdigest() != MD5["PartialEdit_E1E2.csv"]:
        sys.exit("label CSV md5 does not match the record")
    labels = {}
    for row in csv.reader(io.StringIO(data.decode())):
        if not row or not row[0].startswith("E1/"):
            continue
        vals = [float(x) for x in row[1:]]
        regions = [(vals[i], vals[i + 1]) for i in range(0, len(vals) - 1, 2)]
        labels[row[0]] = {"regions": regions, "total_s": vals[-1]}
    names = sorted(labels)

    buf = io.BufferedReader(_stream("E1.tar.gz"), buffer_size=1 << 20)
    got, per = {}, {}
    with tarfile.open(fileobj=buf, mode="r|gz") as t:
        for m in t:
            if not m.isfile() or "E1/" not in m.name:
                continue
            key = m.name[m.name.index("E1/"):]
            spk = key.split("/")[1]
            if key not in labels or per.get(spk, 0) >= PER_SPEAKER:
                continue
            blob = t.extractfile(m).read()
            uid = Path(key).stem
            (OUT / "wav" / f"{uid}.wav").write_bytes(blob)
            got[key] = (uid, hashlib.sha256(blob).hexdigest())
            per[spk] = per.get(spk, 0) + 1
            if len(got) >= N_SELECT:
                break
    meta = {got[k][0]: {"path_in_archive": k, "sha256": got[k][1], **labels[k]} for k in sorted(got)}
    (OUT / "partialedit_subset.json").write_text(json.dumps(
        {"source": REC, "version": "1.1", "license": "CC BY 4.0", "subset": "E1 (VoiceCraft)",
         "e1_files": len(names), "per_speaker": PER_SPEAKER, "speakers": len(per),
         "selection": "archive order, first files of each speaker, stream stopped when complete",
         "label_md5": MD5["PartialEdit_E1E2.csv"],
         "utterances": meta}, indent=1) + "\n", newline="\n")
    print(f"fetched {len(got)} of {len(names)} E1 files from {len(per)} speakers; label md5 verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
