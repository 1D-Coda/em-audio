"""Deterministic mixed-origin audio corpus.

Each clip has the form  captured | generated | captured  with sample-exact
ground truth, built from two independently licensed sources:

  captured   LibriSpeech dev-clean (CC BY 4.0; Panayotov et al., ICASSP 2015),
             fetched by script and used unmodified except for cropping.
  generated  eSpeak NG formant synthesis, produced locally.  No voice model of
             any real person is used and no third-party audio is embedded.

Concatenation is performed by stock ffmpeg through its command line; no project
code is in the signal path.
"""
from __future__ import annotations

import hashlib, json, random, shutil, subprocess, sys, time
from pathlib import Path
from typing import Dict, List, Tuple

from _common import ROOT, emit                                        # noqa: E402
from em_audio import ffmpeg_ops as F
from em_audio import fsutil as _fsutil
from em_audio import toolpath as _toolpath

SEED = 20260819
N_CLIPS = 600
FS = 16_000
CORPUS = ROOT / "corpus"
LIBRI = CORPUS / "LibriSpeech" / "dev-clean"
BUILD = CORPUS / "build"
CLIPS = CORPUS / "clips"
CAP_MIN_S, CAP_MAX_S = 0.60, 1.40      # captured segment duration bounds
GEN_MIN_S, GEN_MAX_S = 0.50, 1.20      # generated segment duration bounds
# Same resolution the self-test uses. PATH alone told a validator the tool was
# found and then failed the run: winget installs eSpeak NG outside PATH.
ESPEAK = _toolpath.locate("espeak-ng") or _toolpath.locate("espeak") or "espeak-ng"

PHRASES = [
    "the quarterly figures were revised on tuesday",
    "he denied any knowledge of the transfer",
    "the committee met behind closed doors",
    "she confirmed the shipment left on friday",
    "no decision has been taken at this stage",
    "the recording was made in the north wing",
    "they agreed to postpone the announcement",
    "the second witness declined to comment",
    "funding was approved without amendment",
    "the report will be published next month",
]


def espeak(text: str, dst: Path, speed: int, pitch: int) -> None:
    subprocess.run([ESPEAK, "-v", "en-us", "-s", str(speed), "-p", str(pitch),
                    "-a", "100", "-w", str(dst), text], check=True,
                   capture_output=True)
    # espeak-ng exits 0 when it could not write the file, and its -w path goes
    # through a fixed 200-byte buffer: past that it writes to a truncated name
    # and reports success. Without this check the run continues and dies two
    # steps later inside ffmpeg, complaining that an input does not exist, which
    # names neither the step that failed nor the reason. Deep extraction paths
    # are ordinary: a validator unpacked the archive into a folder of the same
    # name, and Windows still defaults to MAX_PATH 260.
    if not dst.exists():
        raise RuntimeError(
            f"espeak-ng reported success but wrote no file:\n  {dst}\n"
            f"  that path is {len(str(dst))} characters; espeak-ng truncates -w "
            f"beyond about 200.\n"
            f"  Move the package to a shorter path, for example C:\\em-audio "
            f"or ~/em-audio, and run again.")


def n_samples(path: Path) -> int:
    """Exact frame count of a PCM WAV file, read from its own header."""
    import wave
    with wave.open(str(path), "rb") as w:
        return w.getnframes()


def main() -> int:
    t0 = time.time()
    if not LIBRI.exists():
        print(f"missing corpus at {LIBRI}; run tools/fetch_corpus.sh", file=sys.stderr)
        return 2
    for d in (BUILD, CLIPS):
        if d.exists():
            _fsutil.rmtree(d)
        d.mkdir(parents=True)

    flacs = sorted(p for p in LIBRI.rglob("*.flac"))
    if len(flacs) < 2:
        # Without this the failure is rng.sample raising ValueError on an empty
        # population, which says nothing about a corpus. The cause is always
        # upstream: the fetch did not run, or ran and failed.
        print(f"no captured source audio under {LIBRI}: found {len(flacs)} flac "
              f"files.\nRun tools/fetch_corpus.sh and check that it succeeded; "
              f"every experiment\nthat needs audio depends on it.", file=sys.stderr)
        return 1
    rng = random.Random(SEED)
    index: List[Dict[str, object]] = []

    for i in range(N_CLIPS):
        src_a, src_b = rng.sample(flacs, 2)
        phrase = PHRASES[i % len(PHRASES)]
        speed = 130 + (i % 5) * 10
        pitch = 40 + (i % 3) * 10

        cap1 = BUILD / f"{i:04d}_cap1.wav"
        cap2 = BUILD / f"{i:04d}_cap2.wav"
        gen_raw = BUILD / f"{i:04d}_gen_raw.wav"
        gen = BUILD / f"{i:04d}_gen.wav"
        F.trim(src_a, cap1, round(rng.uniform(0.2, 1.0), 3), round(rng.uniform(CAP_MIN_S, CAP_MAX_S), 3))
        F.trim(src_b, cap2, round(rng.uniform(0.2, 1.0), 3), round(rng.uniform(CAP_MIN_S, CAP_MAX_S), 3))
        espeak(phrase, gen_raw, speed, pitch)
        gen_rs = BUILD / f"{i:04d}_gen_rs.wav"
        F.resample(gen_raw, gen_rs, FS)
        # trim the synthetic segment so the three segments are of comparable
        # length: the interesting case is a *small interior* generated region,
        # not a synthetic clip with captured fragments attached.
        F.trim(gen_rs, gen, 0.10, round(rng.uniform(GEN_MIN_S, GEN_MAX_S), 3))

        n1, ng, n2 = n_samples(cap1), n_samples(gen), n_samples(cap2)
        clip = CLIPS / f"clip_{i:04d}.wav"
        F.concat([cap1, gen, cap2], clip)
        total = n_samples(clip)

        index.append({
            "id": i, "path": str(clip.relative_to(ROOT)), "sample_rate": FS,
            "n_samples": total,
            "ground_truth": [
                {"kind": "C", "start": 0, "end": n1,
                 "lineage": f"urn:emaudio:librispeech:{src_a.stem}"},
                {"kind": "G", "start": n1, "end": n1 + ng,
                 "lineage": f"urn:emaudio:espeak-ng:1.52.0:{i:04d}"},
                {"kind": "C", "start": n1 + ng, "end": n1 + ng + n2,
                 "lineage": f"urn:emaudio:librispeech:{src_b.stem}"},
            ],
            "captured_sources": [src_a.stem, src_b.stem],
            "generated_phrase": phrase, "espeak_speed": speed, "espeak_pitch": pitch,
            "sha256": hashlib.sha256(clip.read_bytes()).hexdigest(),
        })
        if (i + 1) % 100 == 0:
            print(f"  built {i+1}/{N_CLIPS}")

    (CORPUS / "corpus_index.json").write_text(json.dumps(index, indent=1) + "\n")
    mism = sum(1 for r in index
               if r["ground_truth"][-1]["end"] != r["n_samples"])
    emit("C0_corpus_build", {
        "n_clips": N_CLIPS, "sample_rate": FS, "seed": SEED,
        "captured_source": "LibriSpeech dev-clean (CC BY 4.0)",
        "generated_source": "eSpeak NG 1.52.0 formant synthesis, generated locally",
        "concat_tool": "stock ffmpeg CLI (no project code in the signal path)",
        "boundary_mismatches": mism,
        "total_samples": sum(r["n_samples"] for r in index),
        "runtime_s": round(time.time() - t0, 3),
    })
    print(f"clips={N_CLIPS} boundary_mismatches={mism} ({time.time()-t0:.1f}s)")
    return 1 if mism else 0


if __name__ == "__main__":
    sys.exit(main())
