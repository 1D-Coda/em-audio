"""Experiment B -- deterministic adversarial timeline benchmark.

10 000 frozen source timelines of 64 intervals, majority captured, with one to
four *non-boundary* intervals replaced by generated-derived (G) or unverified
(⊥) evidence.  Two evidence policies are evaluated on identical derived audio:

  BASELINE  boundary-only / primary-parent inheritance (a constructed reference
            policy, motivated by C2PA 2.4 Table 10 ``parentOf``; it is not a
            claim about the behaviour of any shipping product)
  EM        complete-source aggregation

Rates below are a MECHANISM STRESS RATE for this frozen fixture family.  They
are not an estimate of how often any deployed system promotes provenance.
"""
from __future__ import annotations

import json, random, sys, time
from typing import Dict, List, Tuple

from _common import CHANNEL, ROOT, SCOPE, element, emit, timeline_from_word   # noqa: E402
from em_audio.evidence import (BOT, Evidence, _Bot, aggregate, claim_of, label_of,
                               leq_claim, promotes)
from em_audio.interval_map import (SourceInterval, Timeline, em_intervals, span_evidence)
import em_audio.operators as O

SEED = 20260819
N_TIMELINES = 10_000
N_INTERVALS = 64
WIDTH = 64                      # samples per source interval
FS = 48_000
MAX_DEPTH = 5
FIXTURES = ROOT / "fixtures"


def make_word(rng: random.Random):
    w = ["C"] * N_INTERVALS
    k = rng.randint(1, 4)
    positions = rng.sample(range(1, N_INTERVALS - 1), k)     # never a boundary
    for p in positions:
        w[p] = rng.choice(["G", "B"])
    return "".join(w), k


def chain(depth: int, n_src: int):
    """A fixed composition chain of representation-only operators."""
    steps = [
        ("trim_inner", lambda src, n: O.trim(src, n, WIDTH, n - WIDTH)),
        ("resample_48_16", lambda src, n: O.resample(src, n, 48000, 16000)),
        ("transcode_mp3", lambda src, n: O.transcode(src, n, "mp3")),
        ("normalize", lambda src, n: O.normalize(src, n)),
        ("time_stretch_1.25", lambda src, n: O.time_stretch(src, n, 1.25, 16000)),
    ]
    return steps[:depth]


_ELEM_CACHE: Dict[Tuple[str, int], Evidence] = {}


def _elem(kind: str, k: int) -> Evidence:
    key = (kind, k)
    e = _ELEM_CACHE.get(key)
    if e is None:
        e = element(kind, k, N_INTERVALS)
        _ELEM_CACHE[key] = e
    return e


def source_timeline(word: str) -> Timeline:
    ivs = [SourceInterval("s", k * WIDTH, (k + 1) * WIDTH, _elem(ch, k))
           for k, ch in enumerate(word)]
    return Timeline("s", ivs, check=False)


def run_chain(word: str, policy: str, max_depth: int):
    """Push a word through the chain once, yielding the state after each depth."""
    tl = source_timeline(word)
    tls = {"s": tl}
    src, n = "s", len(word) * WIDTH
    out_states = []
    for i, (name, mk) in enumerate(chain(max_depth, n)):
        out = mk(src, n)
        if policy == "em":
            ivs = em_intervals(out, tls, footprint_aware=True)
        else:
            ivs = span_evidence(out, tls, "boundary")
        nxt = f"s{i+1}"
        tl = Timeline(nxt, [SourceInterval(nxt, iv.out_start, iv.out_end, iv.ev) for iv in ivs],
                      check=False)
        tls = {nxt: tl}
        src, n = nxt, tl.end
        out_states.append(tl)
    return out_states


def main() -> int:
    t0 = time.time()
    rng = random.Random(SEED)
    made = [make_word(rng) for _ in range(N_TIMELINES)]
    words = [w for w, _ in made]
    kvals = [k for _, k in made]

    FIXTURES.mkdir(parents=True, exist_ok=True)
    with open(FIXTURES / "frozen_timelines.jsonl", "w") as fh:
        for i, w in enumerate(words):
            fh.write(json.dumps({"id": i, "word": w, "k_anomalies": kvals[i]}) + "\n")

    per_depth: Dict[str, Dict[str, object]] = {}
    acc = {d: dict(prom_base=0, prom_em=0, unver_base=0, unver_em=0,
                   lin_base=0, lin_em=0, sup_base=0, sup_em=0,
                   ivs_base=0, ivs_em=0) for d in range(1, MAX_DEPTH + 1)}

    per_k = {k: dict(n=0, base=0, em=0) for k in range(1, 5)}
    for wi, w in enumerate(words):
        em_states = run_chain(w, "em", MAX_DEPTH)
        bs_states = run_chain(w, "boundary", MAX_DEPTH)
        rep = w[1:-1]
        truth_bot = "B" in rep
        truth_atoms = {c for c in rep if c != "B"}
        truth = BOT if truth_bot else claim_of(truth_atoms)
        need = {f"urn:emaudio:s#el={k}" for k in range(1, len(w) - 1)}
        tl0 = source_timeline(w)
        vals = [i.ev.S[CHANNEL] for i in tl0.intervals[1:-1] if CHANNEL in i.ev.S]
        floor = min(vals) if vals else None

        for d in range(1, MAX_DEPTH + 1):
            a = acc[d]
            if d == 1:
                pk = per_k[kvals[wi]]; pk["n"] += 1
            tl_em, tl_bs = em_states[d - 1], bs_states[d - 1]
            ev_em = aggregate([i.ev for i in tl_em.intervals])
            ev_bs = aggregate([i.ev for i in tl_bs.intervals])
            a["ivs_em"] += len(tl_em.intervals)
            a["ivs_base"] += len(tl_bs.intervals)
            if promotes(truth, ev_bs.P):
                a["prom_base"] += 1
                if d == 1:
                    pk["base"] += 1
            if promotes(truth, ev_em.P):
                a["prom_em"] += 1
                if d == 1:
                    pk["em"] += 1
            if truth_bot and not isinstance(ev_bs.P, _Bot):
                a["unver_base"] += 1
            if truth_bot and not isinstance(ev_em.P, _Bot):
                a["unver_em"] += 1
            if not need <= ev_em.L:
                a["lin_em"] += 1
            if not need <= ev_bs.L:
                a["lin_base"] += 1
            if floor is not None:
                if CHANNEL in ev_bs.S and ev_bs.S[CHANNEL] > floor + 1e-12:
                    a["sup_base"] += 1
                if CHANNEL in ev_em.S and ev_em.S[CHANNEL] > floor + 1e-12:
                    a["sup_em"] += 1

    for depth in range(1, MAX_DEPTH + 1):
        a = acc[depth]
        per_depth[str(depth)] = {
            "operators": [n for n, _ in chain(depth, 0)],
            "timelines": N_TIMELINES,
            "baseline_provenance_promotions": a["prom_base"],
            "em_provenance_promotions": a["prom_em"],
            "baseline_promotion_rate": round(a["prom_base"] / N_TIMELINES, 6),
            "em_promotion_rate": round(a["prom_em"] / N_TIMELINES, 6),
            "baseline_unverified_to_verified": a["unver_base"],
            "em_unverified_to_verified": a["unver_em"],
            "baseline_lineage_omissions": a["lin_base"],
            "em_lineage_omissions": a["lin_em"],
            "baseline_support_promotions": a["sup_base"],
            "em_support_promotions": a["sup_em"],
            "baseline_output_intervals": a["ivs_base"],
            "em_output_intervals": a["ivs_em"],
        }
        print(f"depth {depth}: baseline promotions {a['prom_base']}/{N_TIMELINES} "
              f"({100*a['prom_base']/N_TIMELINES:.1f}%)  EM {a['prom_em']}")

    # --- single-operator sweep: each v1 operator applied alone -------------
    single_ops = [
        ("trim_inner", lambda src, n: O.trim(src, n, WIDTH, n - WIDTH)),
        ("trim_head", lambda src, n: O.trim(src, n, 0, n - WIDTH)),
        ("concat_self", lambda src, n: O.concat([(src, 0, n), (src, 0, n)])),
        ("resample_48_16", lambda src, n: O.resample(src, n, 48000, 16000)),
        ("transcode_mp3", lambda src, n: O.transcode(src, n, "mp3")),
        ("transcode_flac", lambda src, n: O.transcode(src, n, "flac")),
        ("normalize", lambda src, n: O.normalize(src, n)),
        ("time_stretch_1.25", lambda src, n: O.time_stretch(src, n, 1.25, FS)),
        ("silence_removal", lambda src, n: O.silence_removal(src, [(0, n // 2), (n // 2 + WIDTH, n)])),
    ]
    per_operator = {}
    for name, mk in single_ops:
        b = e = 0
        for w in words:
            tl = source_timeline(w); tls = {"s": tl}
            n = len(w) * WIDTH
            out = mk("s", n)
            rep = set()
            for pc in out.pieces:
                for k in range(len(w)):
                    if k * WIDTH < pc.src_end and (k + 1) * WIDTH > pc.src_start:
                        rep.add(k)
            syms = {w[k] for k in rep}
            truth = BOT if "B" in syms else claim_of(syms)
            ev_b = aggregate([i.ev for i in span_evidence(out, tls, "boundary")])
            ev_e = aggregate([i.ev for i in em_intervals(out, tls, footprint_aware=True)])
            if promotes(truth, ev_b.P):
                b += 1
            if promotes(truth, ev_e.P):
                e += 1
        per_operator[name] = {"baseline_promotions": b, "em_promotions": e,
                              "baseline_rate": round(b / N_TIMELINES, 6),
                              "em_rate": round(e / N_TIMELINES, 6)}
        print(f"  op {name:20s} baseline {b:5d} ({100*b/N_TIMELINES:5.1f}%)  EM {e}")

    # --- control arm: anomaly positions uniform over ALL positions ---------
    # Boundary-only inheritance can only notice an anomaly that lands on a
    # represented boundary.  With k anomalies of a single type placed uniformly
    # over the n positions of a whole-source, zero-footprint operator, the
    # probability that no anomaly lands on either boundary -- and therefore the
    # probability of promotion -- is exactly C(n-2,k)/C(n,k).  Agreement between
    # the measured rate and that closed form is an analytic check on the
    # harness, and it shows that the adversarial arm's near-unity rate is a
    # property of the deliberate construction rather than an empirical discovery
    # about deployed software.
    from math import comb
    control = {}
    for kind in ("G", "B"):
        rng2 = random.Random(SEED + (1 if kind == "G" else 2))
        arm = {k: dict(n=0, base=0, em=0) for k in range(1, 5)}
        for _ in range(N_TIMELINES):
            w = ["C"] * N_INTERVALS
            k = rng2.randint(1, 4)
            for pos in rng2.sample(range(N_INTERVALS), k):
                w[pos] = kind
            w = "".join(w)
            tl = source_timeline(w); tls = {"s": tl}
            n = len(w) * WIDTH
            out = O.transcode("s", n, "flac")        # whole-source, zero footprint
            syms = set(w)
            truth = BOT if "B" in syms else claim_of(syms)
            ev_b = aggregate([i.ev for i in span_evidence(out, tls, "boundary")])
            ev_e = aggregate([i.ev for i in em_intervals(out, tls, footprint_aware=True)])
            c = arm[k]; c["n"] += 1
            if promotes(truth, ev_b.P):
                c["base"] += 1
            if promotes(truth, ev_e.P):
                c["em"] += 1
        control[kind] = {}
        for k, v in arm.items():
            pred = comb(N_INTERVALS - 2, k) / comb(N_INTERVALS, k)
            meas = v["base"] / max(1, v["n"])
            control[kind][str(k)] = {**v, "measured_baseline_rate": round(meas, 6),
                                     "closed_form_baseline_rate": round(pred, 6),
                                     "abs_deviation": round(abs(meas - pred), 6)}
            print(f"  control {kind} k={k}: measured {meas:.4f}  closed form {pred:.4f}  "
                  f"dev {abs(meas-pred):.4f}  EM {v['em']}")

    payload = {
        "control_uniform_positions": control,
        "per_operator_single_step": per_operator,
        "per_k_anomalies_depth1": {str(k): {**v, "baseline_rate": round(v["base"] / max(1, v["n"]), 6)}
                                   for k, v in per_k.items()},
        "irreversibility_note": ("the baseline promotion established at depth 1 persists at every "
                                 "later depth: once the interior evidence is discarded it cannot be "
                                 "recovered by a downstream operator"),
        "seed": SEED, "n_timelines": N_TIMELINES, "n_intervals": N_INTERVALS,
        "interval_width_samples": WIDTH, "sample_rate": FS, "max_depth": MAX_DEPTH,
        "baseline_definition": ("boundary-only / primary-parent inheritance; a constructed "
                                "reference policy motivated by C2PA 2.4 Table 10 parentOf, "
                                "not a claim about any shipping product"),
        "interpretation": ("mechanism stress rate over a frozen adversarial fixture family; "
                           "NOT a population prevalence estimate"),
        "per_depth": per_depth,
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("B_adversarial_timelines", payload)
    fail = any(v["em_provenance_promotions"] or v["em_unverified_to_verified"]
               or v["em_lineage_omissions"] or v["em_support_promotions"]
               for v in per_depth.values())
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
