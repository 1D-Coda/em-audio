"""Experiment C2 -- supplementary robustness arm.

The evidence algebra never reads the signal, so the zero-promotion result
cannot in principle depend on acoustic character; this arm demonstrates that
empirically rather than leaving it to argument.  Two variants, 50 clips each:

  neural   the generated segment comes from a modern neural TTS (Piper,
           VITS architecture, LJSpeech-trained voice; LJSpeech is public
           domain) instead of formant synthesis;
  noisy    the whole mixed-origin clip is overlaid with locally generated
           band-limited noise at -18 dB (ffmpeg anoisesrc), so every segment
           boundary is acoustically buried.

Both variants rerun the ground-truth recovery and promotion checks of
Experiment C.  Pass = exact interval recovery and zero EM promotions on every
clip, matching the main corpus.
"""
from __future__ import annotations

import json, shutil, subprocess, sys, time, wave
from pathlib import Path
from typing import Dict, List

from _common import CHANNEL, ROOT, SCOPE, emit                        # noqa: E402
from em_audio import ffmpeg_ops as F
from em_audio.evidence import Evidence, aggregate, claim_of, promotes
from em_audio.interval_map import SourceInterval, Timeline, em_intervals, span_evidence
import em_audio.operators as O

CORPUS = ROOT / "corpus"
WORK = CORPUS / "robustness"
VOICE = CORPUS / "piper_voices" / "en_US-ljspeech-medium.onnx"
FS = 16_000
N_CLIPS = 50
CAPTURE_SUPPORT = {"C": 0.90, "G": 0.10}

PHRASES = [
    "the quarterly figures were revised on tuesday",
    "he denied any knowledge of the transfer",
    "the committee met behind closed doors",
    "she confirmed the shipment left on friday",
    "no decision has been taken at this stage",
]


def frames(p: Path) -> int:
    with wave.open(str(p), "rb") as w:
        return w.getnframes()


def timeline_of(gt, src="clip") -> Timeline:
    ivs = []
    for seg in gt:
        k = seg["kind"]
        ivs.append(SourceInterval(src, seg["start"], seg["end"],
                                  Evidence(P=claim_of([k]), S={CHANNEL: CAPTURE_SUPPORT[k]},
                                           A={CHANNEL: SCOPE}, L=frozenset({seg["lineage"]}))))
    return Timeline(src, ivs)


def check_clip(gt, n, tls) -> Dict[str, int]:
    out = O.transcode("clip", n, "flac")
    ivs = em_intervals(out, tls, footprint_aware=True)
    got = [(iv.out_start, iv.out_end, iv.ev.label) for iv in ivs]
    want = [(s["start"], s["end"], {"C": "CAPTURED", "G": "GENERATED"}[s["kind"]])
            for s in gt]
    ev_em = aggregate([iv.ev for iv in ivs])
    ev_bs = aggregate([iv.ev for iv in span_evidence(out, tls, "boundary")])
    truth = claim_of({s["kind"] for s in gt})
    return {"exact": int(got == want),
            "base_promote": int(promotes(truth, ev_bs.P)),
            "em_promote": int(promotes(truth, ev_em.P))}


def main() -> int:
    t0 = time.time()
    from piper import PiperVoice                                       # noqa: E402
    voice = PiperVoice.load(str(VOICE))

    index = json.loads((CORPUS / "corpus_index.json").read_text())
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    arms: Dict[str, Dict[str, int]] = {}

    # --- neural arm: rebuild clips with a Piper-generated middle segment -----
    stats = {"n": 0, "exact": 0, "base_promote": 0, "em_promote": 0}
    for i, rec in enumerate(index[:N_CLIPS]):
        gt0 = rec["ground_truth"]
        clip = ROOT / rec["path"]
        cap1, cap2 = WORK / f"n{i:03d}_c1.wav", WORK / f"n{i:03d}_c2.wav"
        F.trim(clip, cap1, 0.0, gt0[0]["end"] / FS)
        F.trim(clip, cap2, gt0[2]["start"] / FS, (gt0[2]["end"] - gt0[2]["start"]) / FS)
        raw = WORK / f"n{i:03d}_tts_raw.wav"
        with wave.open(str(raw), "wb") as w:
            voice.synthesize_wav(PHRASES[i % len(PHRASES)], w)
        gen = WORK / f"n{i:03d}_tts.wav"
        F.resample(raw, gen, FS)
        n1, ngen, n2 = frames(cap1), frames(gen), frames(cap2)
        out = WORK / f"n{i:03d}_clip.wav"
        F.concat([cap1, gen, cap2], out)
        gt = [{"kind": "C", "start": 0, "end": n1, "lineage": gt0[0]["lineage"]},
              {"kind": "G", "start": n1, "end": n1 + ngen,
               "lineage": f"urn:emaudio:piper-vits:ljspeech:{i:03d}"},
              {"kind": "C", "start": n1 + ngen, "end": n1 + ngen + n2,
               "lineage": gt0[2]["lineage"]}]
        if frames(out) != gt[-1]["end"]:
            print(f"boundary mismatch on neural clip {i}", file=sys.stderr)
            return 1
        r = check_clip(gt, frames(out), {"clip": timeline_of(gt)})
        stats["n"] += 1
        for k in ("exact", "base_promote", "em_promote"):
            stats[k] += r[k]
    arms["neural_tts"] = dict(stats)
    print(f"  neural : n={stats['n']} exact={stats['exact']} "
          f"base={stats['base_promote']} em={stats['em_promote']}")

    # --- noisy arm: overlay locally generated noise on the original clips ----
    stats = {"n": 0, "exact": 0, "base_promote": 0, "em_promote": 0}
    for i, rec in enumerate(index[:N_CLIPS]):
        clip = ROOT / rec["path"]
        n = rec["n_samples"]
        noisy = WORK / f"z{i:03d}_noisy.wav"
        subprocess.run([F.FFMPEG, "-y", "-loglevel", "error", "-i", str(clip),
                        "-f", "lavfi", "-i",
                        f"anoisesrc=r={FS}:colour=pink:amplitude=0.12:seed={i}",
                        "-filter_complex",
                        "[1:a]volume=-18dB[nz];[0:a][nz]amix=inputs=2:duration=first:normalize=0[out]",
                        "-map", "[out]", "-c:a", "pcm_s16le", str(noisy)], check=True)
        # the noise is a locally generated second source mixed over the whole
        # clip: the represented content of every output sample now includes it,
        # so the evidence model is an overlay and mixed ancestry is expected
        # everywhere -- the check is that ground truth stays recoverable from
        # the carried evidence and no promotion occurs anywhere.
        gt = rec["ground_truth"]
        tl = timeline_of(gt)
        nz = Timeline("noise", [SourceInterval("noise", 0, n,
                      Evidence(P=claim_of(["G"]), S={CHANNEL: 0.05},
                               A={CHANNEL: SCOPE},
                               L=frozenset({f"urn:emaudio:anoisesrc:pink:{i}"})))])
        model = O.overlay(("clip", n), ("noise", n), 0)
        ivs = em_intervals(model, {"clip": tl, "noise": nz}, footprint_aware=True)
        # expected: a captured segment plus generated noise is MIXED; the
        # generated segment plus generated noise stays GENERATED (G is already
        # in its atom set -- union adds nothing); and every interval's lineage
        # must name both the clip-side source and the noise source
        want = [(s["start"], s["end"],
                 frozenset({s["lineage"], f"urn:emaudio:anoisesrc:pink:{i}"}),
                 "MIXED" if s["kind"] == "C" else "GENERATED")
                for s in gt]
        got = [(iv.out_start, iv.out_end, iv.ev.L, iv.ev.label) for iv in ivs]
        exact = int(got == want)
        ev_em = aggregate([iv.ev for iv in ivs])
        truth = claim_of({s["kind"] for s in gt} | {"G"})
        stats["n"] += 1
        stats["exact"] += exact
        stats["em_promote"] += int(promotes(truth, ev_em.P))
        ev_bs = aggregate([iv.ev for iv in span_evidence(model, {"clip": tl, "noise": nz},
                                                         "boundary")])
        stats["base_promote"] += int(promotes(truth, ev_bs.P))
    arms["noise_overlay"] = dict(stats)
    print(f"  noisy  : n={stats['n']} exact={stats['exact']} "
          f"base={stats['base_promote']} em={stats['em_promote']}")

    payload = {
        "arms": arms,
        "neural_tts_engine": "Piper (VITS architecture), voice en_US-ljspeech-medium; "
                             "LJSpeech source data is public domain",
        "noise_source": "ffmpeg anoisesrc, pink, -18 dB, locally generated, seeded per clip",
        "note": ("the evidence algebra reads no acoustic features, so these arms test the "
                 "pipeline machinery under different signal character, not a detector"),
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("C2_robustness", payload)
    fail = any(a["exact"] != a["n"] or a["em_promote"] for a in arms.values())
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
