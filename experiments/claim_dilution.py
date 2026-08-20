"""Experiment I -- the cost of conservatism (claim dilution).

Proposition 4 (footprint monotonicity) makes over-approximating the required
source set *safe*: it can never promote.  Safety alone is cheap -- declaring the
whole asset as every sample's dependency is perfectly safe and perfectly useless,
because every output interval near an ancestry change collapses to the weaker
claim.  This experiment measures what the declared footprints actually cost:

  dilution fraction = (output samples whose footprint-aware claim is strictly
                       weaker than the claim over the nominal represented
                       content) / (total output samples)

computed per transformation over the whole mixed-origin corpus, and separately
along a five-operator composition chain to test whether conservatism compounds.

The footprint-blind evaluation is the reference here because the corpus ground
truth is constructed: the nominal source range of each output sample *is* the
content it represents, exactly, by construction.  On real signals the exact
dependency is unknowable inside a third-party codec -- which is why the
footprint exists -- so this is an upper bound on the information the footprint
gives away when the nominal map happens to be exact.
"""
from __future__ import annotations

import json, statistics, sys, time
from typing import Dict, List, Tuple

from _common import CHANNEL, ROOT, SCOPE, emit                        # noqa: E402
from em_audio.evidence import Evidence, _Bot, claim_of, leq_claim
from em_audio.interval_map import SourceInterval, Timeline, em_intervals
import em_audio.operators as O

CORPUS = ROOT / "corpus"
FS = 16_000
CAPTURE_SUPPORT = {"C": 0.90, "G": 0.10}


def timeline_of(rec) -> Timeline:
    ivs = []
    for seg in rec["ground_truth"]:
        k = seg["kind"]
        ivs.append(SourceInterval("clip", seg["start"], seg["end"],
                                  Evidence(P=claim_of([k]), S={CHANNEL: CAPTURE_SUPPORT[k]},
                                           A={CHANNEL: SCOPE}, L=frozenset({seg["lineage"]}))))
    return Timeline("clip", ivs)


def strictly_weaker(fp_ev: Evidence, ref_ev: Evidence) -> bool:
    """True iff the footprint-aware record asserts strictly less than the
    reference: a weaker provenance claim, a lost channel, or a lower value."""
    if fp_ev.P != ref_ev.P:
        return True                      # leq is guaranteed; inequality = weaker
    for mu, v in ref_ev.S.items():
        if mu not in fp_ev.S or fp_ev.S[mu] < v - 1e-12:
            return True
    return False


def diluted_samples(model, tls) -> Tuple[int, int]:
    """(weakened output samples, total output samples) for one derived output."""
    fp = em_intervals(model, tls, footprint_aware=True)
    ref = em_intervals(model, tls, footprint_aware=False)
    edges = sorted({iv.out_start for iv in fp} | {iv.out_end for iv in fp}
                   | {iv.out_start for iv in ref} | {iv.out_end for iv in ref})

    def at(ivs, pos):
        for iv in ivs:
            if iv.out_start <= pos < iv.out_end:
                return iv.ev
        return None

    weak = 0
    total = 0
    for a, b in zip(edges, edges[1:]):
        e_fp, e_ref = at(fp, a), at(ref, a)
        if e_fp is None or e_ref is None:
            continue
        total += b - a
        if strictly_weaker(e_fp, e_ref):
            weak += b - a
    return weak, total


def main() -> int:
    t0 = time.time()
    index = json.loads((CORPUS / "corpus_index.json").read_text())

    jobs = {
        "trim_10_90": lambda n: O.trim("clip", n, n // 10, n - n // 10),
        "resample_16_8": lambda n: O.resample("clip", n, 16000, 8000),
        "transcode_mp3": lambda n: O.transcode("clip", n, "mp3"),
        "transcode_flac": lambda n: O.transcode("clip", n, "flac"),
        "normalize": lambda n: O.normalize("clip", n),
        "time_stretch_1.10": lambda n: O.time_stretch("clip", n, 1.10, FS),
        "silence_removal": lambda n: O.silence_removal(
            "clip", [(0, int(0.4 * n)), (int(0.6 * n), n)]),
        # overlay's nominal required-source set already contains every covering
        # source and both pieces declare zero footprint, so its expected
        # dilution is exactly zero; it is included so the table covers all
        # eight transformations of the main experiment rather than leaving the
        # reader to infer the omission.
        "overlay_generated": "OVERLAY",
    }

    tone_ev = Evidence(P=claim_of(["G"]), S={CHANNEL: 0.05}, A={CHANNEL: SCOPE},
                       L=frozenset({"urn:emaudio:ffmpeg-lavfi-sine:660Hz"}))
    n_tone = FS // 2
    tone_tl = Timeline("tone", [SourceInterval("tone", 0, n_tone, tone_ev)])

    per_tf: Dict[str, Dict[str, object]] = {}
    for name, mk in jobs.items():
        fracs = []
        for rec in index:
            n = rec["n_samples"]
            tls = {"clip": timeline_of(rec), "tone": tone_tl}
            model = O.overlay(("clip", n), ("tone", n_tone), n // 2) \
                if mk == "OVERLAY" else mk(n)
            weak, total = diluted_samples(model, tls)
            fracs.append(weak / total if total else 0.0)
        per_tf[name] = {
            "clips": len(fracs),
            "median_dilution_fraction": round(statistics.median(fracs), 6),
            "mean_dilution_fraction": round(statistics.fmean(fracs), 6),
            "max_dilution_fraction": round(max(fracs), 6),
            "clips_with_any_dilution": sum(1 for f in fracs if f > 0),
        }
        print(f"  {name:20s} median {per_tf[name]['median_dilution_fraction']*100:6.3f}%  "
              f"max {per_tf[name]['max_dilution_fraction']*100:6.3f}%")

    # --- composition: does conservatism compound along a chain? ------------
    chain_ops = [
        ("trim_inner", lambda src, n: O.trim(src, n, n // 10, n - n // 10)),
        ("resample_16_8", lambda src, n: O.resample(src, n, 16000, 8000)),
        ("transcode_mp3", lambda src, n: O.transcode(src, n, "mp3")),
        ("normalize", lambda src, n: O.normalize(src, n)),
        ("time_stretch_1.10", lambda src, n: O.time_stretch(src, n, 1.10, 8000)),
    ]
    depth_rows = []
    for depth in range(1, len(chain_ops) + 1):
        fracs = []
        for rec in index[:200]:
            tl = timeline_of(rec)
            tls = {"clip": tl}
            src, n = "clip", rec["n_samples"]
            # propagate footprint-aware evidence through the chain,
            # and separately the footprint-blind reference
            state = {"fp": tl, "ref": tl}
            for i, (_, mk) in enumerate(chain_ops[:depth]):
                nxt = f"s{i+1}"
                new_state = {}
                for key, cur in state.items():
                    model = mk(cur.src, cur.end)
                    ivs = em_intervals(model, {cur.src: cur},
                                       footprint_aware=(key == "fp"))
                    new_state[key] = Timeline(nxt, [
                        SourceInterval(nxt, iv.out_start, iv.out_end, iv.ev)
                        for iv in ivs], check=False)
                state = new_state
            fp_tl, ref_tl = state["fp"], state["ref"]
            edges = sorted({i.start for i in fp_tl.intervals} | {fp_tl.end}
                           | {i.start for i in ref_tl.intervals} | {ref_tl.end})
            weak = total = 0
            for a, b in zip(edges, edges[1:]):
                if a >= min(fp_tl.end, ref_tl.end):
                    break
                e_fp, e_ref = fp_tl.at(a).ev, ref_tl.at(a).ev
                total += b - a
                if strictly_weaker(e_fp, e_ref):
                    weak += b - a
            fracs.append(weak / total if total else 0.0)
        depth_rows.append({"depth": depth,
                           "operators": [nm for nm, _ in chain_ops[:depth]],
                           "clips": len(fracs),
                           "median_dilution_fraction": round(statistics.median(fracs), 6),
                           "max_dilution_fraction": round(max(fracs), 6)})
        print(f"  chain depth {depth}: median "
              f"{depth_rows[-1]['median_dilution_fraction']*100:.3f}%  "
              f"max {depth_rows[-1]['max_dilution_fraction']*100:.3f}%")

    # --- long-asset arm: the same fixed-radius bands on broadcast-length ----
    # material.  A 30 s asset with one interior generated segment, through a
    # three-operator chain (trim to the middle 80% -> normalize -> MP3), is the
    # shape of a routine broadcast edit; the bands are the same absolute widths
    # as on the corpus clips, so the fraction shrinks with duration.
    long_rows = []
    # 2.85 s is the corpus median clip duration: including it holds the operator
    # sequence fixed and varies only duration, so the comparison isolates asset
    # length rather than confounding it with a different chain.
    for dur_s in (2.85, 30, 300):
        n = int(dur_s * FS)
        g0, g1 = int(0.45 * n), int(0.55 * n)
        tl = Timeline("clip", [
            SourceInterval("clip", 0, g0, Evidence(P=claim_of(["C"]),
                           S={CHANNEL: 0.9}, A={CHANNEL: SCOPE}, L=frozenset({"urn:a"}))),
            SourceInterval("clip", g0, g1, Evidence(P=claim_of(["G"]),
                           S={CHANNEL: 0.1}, A={CHANNEL: SCOPE}, L=frozenset({"urn:b"}))),
            SourceInterval("clip", g1, n, Evidence(P=claim_of(["C"]),
                           S={CHANNEL: 0.9}, A={CHANNEL: SCOPE}, L=frozenset({"urn:c"}))),
        ])
        state = {"fp": tl, "ref": tl}
        chain3 = [lambda src, m: O.trim(src, m, m // 10, m - m // 10),
                  lambda src, m: O.normalize(src, m),
                  lambda src, m: O.transcode(src, m, "mp3")]
        for i, mk3 in enumerate(chain3):
            nxt = f"L{i+1}"
            state = {key: Timeline(nxt, [SourceInterval(nxt, iv.out_start, iv.out_end, iv.ev)
                                         for iv in em_intervals(mk3(cur.src, cur.end),
                                                                {cur.src: cur},
                                                                footprint_aware=(key == "fp"))],
                                   check=False)
                     for key, cur in state.items()}
        fp_tl, ref_tl = state["fp"], state["ref"]
        edges = sorted({i.start for i in fp_tl.intervals} | {fp_tl.end}
                       | {i.start for i in ref_tl.intervals} | {ref_tl.end})
        weak = total = 0
        for a, b in zip(edges, edges[1:]):
            if a >= min(fp_tl.end, ref_tl.end):
                break
            total += b - a
            if strictly_weaker(fp_tl.at(a).ev, ref_tl.at(a).ev):
                weak += b - a
        long_rows.append({"asset_seconds": dur_s,
                          "chain": ["trim_middle_80", "normalize", "transcode_mp3"],
                          "dilution_fraction": round(weak / total, 6)})
        print(f"  long asset {dur_s}s, depth-3 chain: dilution "
              f"{100*weak/total:.3f}%")

    payload = {
        "long_asset_chain": long_rows,
        "definition": ("fraction of output samples whose footprint-aware evidence record is "
                       "strictly weaker (weaker provenance claim, lost channel, or lower "
                       "support value) than the record computed over the nominal represented "
                       "content; an upper bound on what the declared footprints cost when the "
                       "nominal map is exact"),
        "per_transformation": per_tf,
        "composition_chain": depth_rows,
        "n_clips": len(index),
        "chain_subset_clips": 200,
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("I_claim_dilution", payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
