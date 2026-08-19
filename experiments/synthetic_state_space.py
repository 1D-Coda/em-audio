"""Experiment A -- exhaustive finite-state conformance.

Every source word over {C, G, ⊥} up to a stated length is pushed through every
v1 operator and checked against the full property suite.  Deterministic: no
sampling, no seeds, exact counts.
"""
from __future__ import annotations

import itertools, sys, time
from typing import Dict, List

from _common import RESULTS, element, emit, timeline_from_word          # noqa: E402
from em_audio.conformance import (compose_timeline, p7_composition, run_property_suite)
from em_audio.evidence import BOT, _Bot, aggregate, claim_of, label_of, leq_claim


def expect_atoms(lbl):
    return {'CAPTURED': {'C'}, 'GENERATED': {'G'}, 'MIXED': {'C', 'G'}, 'UNVERIFIED': set()}[lbl]
from em_audio.interval_map import (SourceInterval, Timeline, em_intervals, span_evidence)
import em_audio.operators as O

ALPHABET = ("C", "G", "B")
MAX_LEN = 8
WIDTH = 64                     # samples per source element


def operators_for(word, n_src):
    """The battery of v1 operators exercised on one word."""
    ops = []
    ops.append(("trim_all", O.trim("s", n_src, 0, n_src)))
    if n_src >= 3 * WIDTH:
        ops.append(("trim_inner", O.trim("s", n_src, WIDTH, n_src - WIDTH)))
    ops.append(("resample_48_16", O.resample("s", n_src, 48000, 16000)))
    ops.append(("transcode_mp3", O.transcode("s", n_src, "mp3")))
    ops.append(("transcode_flac", O.transcode("s", n_src, "flac")))
    ops.append(("normalize", O.normalize("s", n_src)))
    ops.append(("normalize_strict", O.normalize("s", n_src, strict_global=True)))
    ops.append(("time_stretch_1.25", O.time_stretch("s", n_src, 1.25, 48000)))
    if n_src >= 2 * WIDTH:
        keep = [(0, WIDTH), (n_src - WIDTH, n_src)]
        ops.append(("silence_removal", O.silence_removal("s", keep)))
    ops.append(("concat_self", O.concat([("s", 0, n_src), ("s", 0, n_src)])))
    return ops


def main() -> int:
    t0 = time.time()
    checks_total = 0
    checks_failed = 0
    failures: List[str] = []
    per_check: Dict[str, Dict[str, int]] = {}
    words = 0
    cases = 0

    mixed_words = 0
    bot_words = 0
    label_counts: Dict[str, int] = {}
    composition_cases = 0

    for L in range(1, MAX_LEN + 1):
        for word in itertools.product(*[ALPHABET] * L):
            words += 1
            tl = timeline_from_word(word, WIDTH)
            tls = {"s": tl}
            n_src = L * WIDTH
            atoms = {c for c in word if c != "B"}
            has_bot = "B" in word
            if has_bot:
                bot_words += 1
            elif len(atoms) > 1:
                mixed_words += 1

            for name, out in operators_for(word, n_src):
                cases += 1
                for chk in run_property_suite(out, tls):
                    checks_total += 1
                    d = per_check.setdefault(chk.name, {"pass": 0, "fail": 0})
                    if chk.passed:
                        d["pass"] += 1
                    else:
                        d["fail"] += 1
                        checks_failed += 1
                        if len(failures) < 25:
                            failures.append(f"{''.join(word)}/{name}/{chk.name}: {chk.detail}")

                # Independent closed-form oracle over the *represented* source
                # elements: recompute the expected state directly from the
                # operator's nominal source ranges, without using the evidence
                # algebra.  For zero-footprint operators the output state must
                # equal it exactly; for kernel operators the output may only be
                # weaker (Proposition 5), never stronger.
                rep = set()
                for p_ in out.pieces:
                    a, b = int(p_.src_start), int(p_.src_end)
                    for k in range(L):
                        if k * WIDTH < b and (k + 1) * WIDTH > a:
                            rep.add(k)
                rep_syms = {word[k] for k in rep}
                if "B" in rep_syms:
                    expect = "UNVERIFIED"
                elif rep_syms:
                    expect = label_of(frozenset(rep_syms))
                else:
                    expect = "UNVERIFIED"
                spans = span_evidence(out, tls, "em")
                whole = aggregate([s.ev for s in spans])
                label_counts[expect] = label_counts.get(expect, 0) + 1
                zero_fp = all(p_.footprint == 0 for p_ in out.pieces)
                ok = (whole.label == expect) if zero_fp else \
                     leq_claim(whole.P, claim_of(None) if expect == "UNVERIFIED"
                               else claim_of([c for c in ("C", "G") if c in expect_atoms(expect)]))
                key = "closed_form_state_exact" if zero_fp else "closed_form_state_weaker"
                checks_total += 1
                d2 = per_check.setdefault(key, {"pass": 0, "fail": 0})
                if ok:
                    d2["pass"] += 1
                else:
                    d2["fail"] += 1; checks_failed += 1
                    if len(failures) < 25:
                        failures.append(f"{''.join(word)}/{name}: state {whole.label} vs expect {expect}")

            # P7: composition -- resample then trim, versus the direct meet
            if L <= 5:
                composition_cases += 1
                o1 = O.resample("s", n_src, 48000, 16000)
                tl2 = compose_timeline(o1, tls, "s2")
                o2 = O.trim("s2", tl2.end, 0, tl2.end)
                comp = em_intervals(o2, {"s2": tl2})
                direct = em_intervals(o1, tls)
                chk = p7_composition([(o1, tls), (o2, {"s2": tl2})], comp, direct)
                checks_total += 1
                d = per_check.setdefault(chk.name, {"pass": 0, "fail": 0})
                if chk.passed:
                    d["pass"] += 1
                else:
                    d["fail"] += 1; checks_failed += 1
                    if len(failures) < 25:
                        failures.append(f"{''.join(word)}/compose: {chk.detail}")

    payload = {
        "alphabet": list(ALPHABET),
        "max_word_length": MAX_LEN,
        "element_width_samples": WIDTH,
        "words_enumerated": words,
        "operator_cases": cases,
        "composition_cases": composition_cases,
        "checks_total": checks_total,
        "checks_failed": checks_failed,
        "per_check": per_check,
        "words_with_mixed_ancestry": mixed_words,
        "words_containing_unverified": bot_words,
        "expected_state_counts": label_counts,
        "failures_sample": failures,
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("A_synthetic_state_space", payload)
    print(f"words={words} cases={cases} checks={checks_total} failed={checks_failed} "
          f"({payload['runtime_s']}s)")
    return 1 if checks_failed else 0


if __name__ == "__main__":
    sys.exit(main())
