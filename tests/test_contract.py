"""Named regression tests for the evidence-monotone audio contract.

Every test named in the study protocol appears here by name.  ``run_all.sh``
fails the build if any of them fails.
"""
from __future__ import annotations

import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from em_audio.evidence import (BOT, C, G, Evidence, _Bot, aggregate, boundary_aggregate,
                               claim_of, label_of, leq_claim, meet_claim, promotes)
from em_audio.interval_map import (SourceInterval, Timeline, em_intervals, span_evidence)
from em_audio.conformance import compose_timeline, run_property_suite
from em_audio.manifest_schema import em_assertion, interval_from_json
import em_audio.operators as O

CH = "capture-support"
SC = frozenset({"digital-asset"})
W = 64
FAILURES = []


def ev(kind, v=0.9, tag="x"):
    if kind is None:
        return Evidence(P=BOT, L=frozenset({f"urn:{tag}"}))
    return Evidence(P=claim_of([kind]), S={CH: v}, A={CH: SC}, L=frozenset({f"urn:{tag}"}))


def tl_from(kinds, vals=None):
    vals = vals or [0.9] * len(kinds)
    return Timeline("s", [SourceInterval("s", i * W, (i + 1) * W, ev(k, vals[i], f"e{i}"))
                          for i, k in enumerate(kinds)])


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(name)


def whole(out, tls, policy):
    if policy == "em":
        return aggregate([i.ev for i in em_intervals(out, tls, footprint_aware=True)])
    return aggregate([i.ev for i in span_evidence(out, tls, "boundary")])


def main() -> int:
    # --- the minimal counterexample -------------------------------------
    tl = tl_from(["C", "C", "G", "C", "C"])
    tls = {"s": tl}; n = 5 * W
    out = O.transcode("s", n, "flac")
    check("C-C-G-C-C collapsed to CAPTURED by the baseline",
          whole(out, tls, "baseline").label == "CAPTURED")
    check("C-C-G-C-C is MIXED under EM",
          whole(out, tls, "em").label == "MIXED")

    tl2 = tl_from(["C", "C", None, "C"])
    tls2 = {"s": tl2}; n2 = 4 * W
    out2 = O.transcode("s", n2, "flac")
    check("C-C-BOT-C reported verified by the baseline",
          not isinstance(whole(out2, tls2, "baseline").P, _Bot))
    check("C-C-BOT-C is UNVERIFIED under EM",
          isinstance(whole(out2, tls2, "em").P, _Bot))

    # --- trim semantics --------------------------------------------------
    t3 = tl_from(["C", "G", "C"]); s3 = {"s": t3}
    check("trim removing all G may legitimately yield captured-only",
          whole(O.trim("s", 3 * W, 2 * W, 3 * W), s3, "em").label == "CAPTURED")
    check("trim retaining any G may not yield captured-only",
          whole(O.trim("s", 3 * W, W, 3 * W), s3, "em").label == "MIXED")

    # --- concat / overlay ------------------------------------------------
    tc = Timeline("a", [SourceInterval("a", 0, W, ev("C", 0.9, "a"))])
    tg = Timeline("b", [SourceInterval("b", 0, W, ev("G", 0.2, "b"))])
    cc = O.concat([("a", 0, W), ("b", 0, W)])
    check("concat C + G is MIXED",
          whole(cc, {"a": tc, "b": tg}, "em").label == "MIXED")
    ov = O.overlay(("a", 2 * W), ("b", W), W // 2)
    tc2 = Timeline("a", [SourceInterval("a", 0, 2 * W, ev("C", 0.9, "a"))])
    ivs = em_intervals(ov, {"a": tc2, "b": tg}, footprint_aware=True)
    overlap = [i for i in ivs if i.out_start >= W // 2 and i.out_end <= W // 2 + W]
    check("overlay C,G is MIXED over the overlap",
          any(i.ev.label == "MIXED" for i in overlap),
          str([(i.out_start, i.out_end, i.ev.label) for i in ivs]))

    # --- support and lineage --------------------------------------------
    tv = tl_from(["C", "C", "C"], [0.9, 0.1, 0.9]); sv = {"s": tv}
    o = O.transcode("s", 3 * W, "flac")
    check("same-channel support is the minimum over the complete source",
          abs(whole(o, sv, "em").S[CH] - 0.1) < 1e-12)
    check("boundary-only support promotes to the endpoint value",
          abs(whole(o, sv, "baseline").S[CH] - 0.9) < 1e-12)
    check("missing lineage contributor is a conformance failure",
          not frozenset({"urn:e1"}) <= whole(o, sv, "baseline").L)
    check("EM lineage is complete",
          frozenset({"urn:e0", "urn:e1", "urn:e2"}) <= whole(o, sv, "em").L)

    # --- applicable-but-unreported channel -------------------------------
    a = Evidence(P=claim_of([C]), S={CH: 0.5}, A={CH: SC}, L=frozenset({"u1"}))
    b = Evidence(P=claim_of([C]), S={}, A={CH: SC}, L=frozenset({"u2"}))
    check("channel applicable to a source but unreported makes the output unavailable",
          CH not in aggregate([a, b]).S)
    # A source to which the channel is not applicable at all used to be skipped,
    # leaving the channel computed from the rest. That is the same partial-subset
    # situation as the case above, and it is what broke Proposition 4 for
    # channels: enlarging D_y by a source that declares an otherwise
    # inapplicable channel raised it from unavailable to a value. Requirement
    # (iv) now covers both halves, so the channel is withheld.
    d = Evidence(P=claim_of([C]), S={}, A={}, L=frozenset({"u3"}))
    check("channel inapplicable to a required source is withheld, not computed "
          "from the rest", CH not in aggregate([a, d]).S)
    check("so enlarging D_y cannot raise a channel from unavailable to a value",
          CH not in aggregate([a, d]).S and aggregate([a]).S.get(CH) == 0.5)

    # --- scope ------------------------------------------------------------
    x = Evidence(P=claim_of([C]), S={CH: 0.5}, A={CH: frozenset({"p", "q"})}, L=frozenset({"u"}))
    y = Evidence(P=claim_of([C]), S={CH: 0.7}, A={CH: frozenset({"q", "r"})}, L=frozenset({"v"}))
    check("applicability scope is intersected, never broadened",
          aggregate([x, y]).A[CH] == frozenset({"q"}))
    z = Evidence(P=claim_of([C]), S={CH: 0.7}, A={CH: frozenset({"r"})}, L=frozenset({"v"}))
    check("empty scope intersection makes the channel unavailable",
          CH not in aggregate([x, z]).S)

    # --- kernel footprint --------------------------------------------------
    tk = tl_from(["C"] * 8 + ["G"] + ["C"] * 8); sk = {"s": tk}
    nk = 17 * W
    rs = O.resample("s", nk, 48000, 16000)
    fp = rs.pieces[0].footprint
    check("resample declares a non-zero kernel footprint", fp > 0, f"footprint={fp}")
    near = O.trim("s", nk, 0, 8 * W)                       # ends exactly at the G boundary
    narrow = span_evidence(near, sk, "em_nofp")
    wide = span_evidence(near, sk, "em")
    check("kernel-footprint completeness: widening D_y never strengthens the claim",
          leq_claim(aggregate([i.ev for i in wide]).P, aggregate([i.ev for i in narrow]).P))

    # --- pitch shift as a composite of in-scope operators --------------------
    tps = tl_from(["C", "G", "C", "C"]); sps = {"s": tps}; nps = 4 * W
    # rate-change reinterpretation (a resample map) followed by a compensating
    # time stretch: the common pitch-shift construction
    o_rs = O.resample("s", nps, 48000, 56000)          # up-shift reinterpretation
    t_mid = compose_timeline(o_rs, sps, "ps1")
    o_st = O.time_stretch("ps1", t_mid.end, 56000 / 48000.0, 56000)
    comp_ps = aggregate([i.ev for i in em_intervals(o_st, {"ps1": t_mid})])
    direct_ps = aggregate([i.ev for i in em_intervals(O.transcode("s", nps, "flac"), sps)])
    check("pitch shift (resample + stretch composite) does not promote",
          leq_claim(comp_ps.P, direct_ps.P) and comp_ps.L >= direct_ps.L,
          f"{comp_ps.label} vs {direct_ps.label}")

    # --- composition -------------------------------------------------------
    t7 = tl_from(["C", "G", "C", "C"]); s7 = {"s": t7}; n7 = 4 * W
    o1 = O.resample("s", n7, 48000, 16000)
    t8 = compose_timeline(o1, s7, "s2")
    o2 = O.transcode("s2", t8.end, "mp3")
    comp = aggregate([i.ev for i in em_intervals(o2, {"s2": t8})])
    direct = aggregate([i.ev for i in em_intervals(o1, s7)])
    check("composition of compliant transforms does not promote",
          leq_claim(comp.P, direct.P) and comp.L >= direct.L)

    # --- property suite over every operator ---------------------------------
    tp = tl_from(["C", "G", None, "C"]); sp = {"s": tp}; np_ = 4 * W
    for name, op in [("trim", O.trim("s", np_, 0, np_)),
                     ("resample", O.resample("s", np_, 48000, 16000)),
                     ("mp3", O.transcode("s", np_, "mp3")),
                     ("normalize", O.normalize("s", np_)),
                     ("stretch", O.time_stretch("s", np_, 1.25, 48000)),
                     ("silence", O.silence_removal("s", [(0, W), (2 * W, np_)]))]:
        res = run_property_suite(op, sp)
        check(f"property suite passes for {name}",
              all(c.passed for c in res),
              "; ".join(f"{c.name}:{c.detail}" for c in res if not c.passed))

    # --- serialisation round-trip -------------------------------------------
    ivs = em_intervals(O.transcode("s", 5 * W, "flac"), {"s": tl_from(["C", "C", "G", "C", "C"])})
    a = em_assertion(ivs, 48000, 5 * W, "complete-source", "transcode", {"codec": "flac"})
    back = [interval_from_json(i) for i in a["intervals"]]
    check("EM assertion round-trips through JSON",
          [b.P for b in back] == [i.ev.P for i in ivs]
          and [b.S for b in back] == [i.ev.S for i in ivs])
    bot_assert = json.loads(json.dumps(em_assertion(
        em_intervals(out2, tls2), 48000, n2, "complete-source", "t", {})))
    unver = [i for i in bot_assert["intervals"] if i["state"] == "UNVERIFIED"]
    check("unverified serialises as null provenance, never as an atom",
          len(unver) == 1 and unver[0]["provenance"] is None
          and all(i["provenance"] is not None for i in bot_assert["intervals"]
                  if i["state"] != "UNVERIFIED"),
          json.dumps([(i["state"], i["provenance"]) for i in bot_assert["intervals"]]))

    # Clause (ii)'s antecedent omitted a non-empty applicability condition, so a
    # channel narrowed to an empty scope under (iii) would still have been
    # required to carry a value. P4 iterates S and P5 iterates A, so neither
    # excluded the result on its own.
    try:
        Evidence(P=frozenset({"a"}), S={"c": 0.5}, A={"c": frozenset()},
                 L=frozenset({"a"}))
        nowhere_rejected = False
    except ValueError:
        nowhere_rejected = True
    check("a support value applicable nowhere is unconstructible", nowhere_rejected)

    print(f"\n{len(FAILURES)} failing test(s)" if FAILURES else "\nall tests passed")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
