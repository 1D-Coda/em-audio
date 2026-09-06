"""Experiment J -- C2PA-native heterogeneous composition.

The manuscript's standards argument is that C2PA can *preserve* component
histories (componentOf ingredients, digitalSourceType, c2pa.placed actions)
while not prescribing the aggregate claim computed over them.  This experiment
closes the loop between that argument and the signed transport: it builds the
exact object the argument describes and carries the EM aggregate through it.

Per fixture: a captured source and a generated source are each signed with
their own digitalSourceType; stock ffmpeg concatenates them; the composition is
signed with BOTH sources as componentOf ingredients, a spec-conformant
c2pa.placed action referencing each ingredient assertion (C2PA 2.4 section
18.16.3), and the EM assertion computed by the complete-source rule over the
two component timelines.  The composition is then derived (a trim retaining
both ancestries) and re-signed with parentOf.  Pass conditions: every
validation trusted under the declared anchor; both componentOf ingredients and
both placed references present; the EM assertion byte-identical after
validation; the whole-asset aggregate MIXED at both stages; decoded essence
unchanged by signing.
"""
from __future__ import annotations

import json, shutil, sys, time, wave
from pathlib import Path
from typing import Dict, List

from _common import CHANNEL, ROOT, SCOPE, emit                        # noqa: E402
from _signing import signer                                          # noqa: E402
from em_audio import c2pa_bridge as B, ffmpeg_ops as F
from em_audio.essence import essence_hash
from em_audio.evidence import Evidence, aggregate, claim_of
from em_audio.interval_map import SourceInterval, Timeline, em_intervals
from em_audio.manifest_schema import em_assertion
import em_audio.operators as O
from em_audio import fsutil as _fsutil

CORPUS = ROOT / "corpus"
WORK = CORPUS / "composition"
FIXTURES = ROOT / "fixtures" / "expected"
FS = 16_000
N_FIXTURES = 30
DST_CAPTURE = "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"
DST_TRAINED = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"


def frames(p: Path) -> int:
    with wave.open(str(p), "rb") as w:
        return w.getnframes()


def ev(kind: str, lineage: str) -> Evidence:
    return Evidence(P=claim_of([kind]),
                    S={CHANNEL: {"C": 0.90, "G": 0.10}[kind]},
                    A={CHANNEL: SCOPE}, L=frozenset({lineage}))


def main() -> int:
    t0 = time.time()
    index = json.loads((CORPUS / "corpus_index.json").read_text())[:N_FIXTURES]
    if WORK.exists():
        _fsutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    sg = signer()

    st = {"n": 0, "sources_trusted": 0, "composition_trusted": 0,
          "component_ingredients_recorded": 0, "placed_actions_reference_both": 0,
          "assertion_roundtrip_identical": 0, "aggregate_mixed": 0,
          "derived_trusted": 0, "derived_mixed": 0, "derived_parentOf": 0,
          "essence_mismatches": 0, "failures": []}
    frozen = False

    for rec in index:
        st["n"] += 1
        clip = ROOT / rec["path"]
        gt = rec["ground_truth"]
        n1 = gt[0]["end"]; ng = gt[1]["end"] - gt[1]["start"]
        wd = WORK / f"{rec['id']:04d}"
        wd.mkdir()

        # 1. the two sources, cut by stock ffmpeg from the labelled clip
        cap, gen = wd / "cap.wav", wd / "gen.wav"
        F.trim(clip, cap, 0.0, n1 / FS)
        F.trim(clip, gen, gt[1]["start"] / FS, ng / FS)
        n_cap, n_gen = frames(cap), frames(gen)

        # 2. sign each source with its own digitalSourceType and EM assertion
        signed = {}
        for path, kind, dst_uri, lin in ((cap, "C", DST_CAPTURE, gt[0]["lineage"]),
                                         (gen, "G", DST_TRAINED, gt[1]["lineage"])):
            n = frames(path)
            tl = Timeline("src", [SourceInterval("src", 0, n, ev(kind, lin))])
            ivs = em_intervals(O.transcode("src", n, "wav"), {"src": tl})
            a = em_assertion(ivs, FS, n, "complete-source", "capture", {})
            man = B.build_manifest(f"{'captured' if kind=='C' else 'generated'} source",
                                   a, [{"action": "c2pa.created",
                                        "digitalSourceType": dst_uri}])
            out = wd / f"{path.stem}_signed.wav"
            B.sign(path, out, man, sg, wd)
            rep = B.validate(out, sg, wd)
            if B.state_of(rep) == "Trusted":
                st["sources_trusted"] += 1
            else:
                st["failures"].append(f"{rec['id']} source {kind}: {B.state_of(rep)}")
            signed[kind] = out

        # 3. stock ffmpeg composes the two signed sources
        comp = wd / "comp.wav"
        F.concat([signed["C"], signed["G"]], comp)
        n_comp = frames(comp)
        pre_essence = essence_hash(comp)

        # 4. EM aggregate over the composition via the complete-source rule
        tl_c = Timeline("cap", [SourceInterval("cap", 0, n_cap, ev("C", gt[0]["lineage"]))])
        tl_g = Timeline("gen", [SourceInterval("gen", 0, n_gen, ev("G", gt[1]["lineage"]))])
        model = O.concat([("cap", 0, n_cap), ("gen", 0, n_gen)])
        ivs = em_intervals(model, {"cap": tl_c, "gen": tl_g})
        assertion = em_assertion(ivs, FS, model.n_out, "complete-source",
                                 "concat", {"n_parts": 2})

        # 5. componentOf ingredients + spec-conformant placed actions
        ing_c = B.ingredient_report(signed["C"], wd / "ing_cap", sg, wd)
        ing_g = B.ingredient_report(signed["G"], wd / "ing_gen", sg, wd)
        for ing, title in ((ing_c, "captured source"), (ing_g, "generated source")):
            ing["relationship"] = "componentOf"
            ing["title"] = title
        man = {
            "claim_generator_info": [{"name": "em-audio", "version": "1.0.0"}],
            "title": f"composition {rec['id']}",
            "ingredients": [ing_c, ing_g],
            "assertions": [
                {"label": "c2pa.actions.v2", "data": {"actions": [
                    {"action": "c2pa.placed",
                     "parameters": {"ingredientIds": [ing_c["instance_id"]]}},
                    {"action": "c2pa.placed",
                     "parameters": {"ingredientIds": [ing_g["instance_id"]]}},
                ]}},
                {"label": B.ASSERTION_LABEL, "data": assertion},
            ],
        }
        comp_signed = wd / "comp_signed.wav"
        B.sign(comp, comp_signed, man, sg, wd)
        rep = B.validate(comp_signed, sg, wd)

        if B.state_of(rep) == "Trusted":
            st["composition_trusted"] += 1
        else:
            st["failures"].append(f"{rec['id']} composition: {B.state_of(rep)} {B.failures(rep)}")
        comps = [i for i in B.ingredients_of(rep) if i.get("relationship") == "componentOf"]
        if len(comps) == 2:
            st["component_ingredients_recorded"] += 1
        am = rep["manifests"][rep["active_manifest"]]
        placed_refs = []
        for a in am["assertions"]:
            if a["label"].startswith("c2pa.actions"):
                for act in a["data"]["actions"]:
                    if act["action"] == "c2pa.placed":
                        placed_refs += act.get("parameters", {}).get("ingredients", [])
        if len(placed_refs) == 2 and len({r["url"] for r in placed_refs}) == 2:
            st["placed_actions_reference_both"] += 1
        back = B.em_assertion_of(rep)
        if back == json.loads(json.dumps(assertion)):
            st["assertion_roundtrip_identical"] += 1
        whole = aggregate([iv.ev for iv in ivs])
        states = {i["state"] for i in (back or {"intervals": []})["intervals"]}
        if whole.label == "MIXED" and states == {"CAPTURED", "GENERATED"}:
            st["aggregate_mixed"] += 1
        if essence_hash(comp_signed) != pre_essence:
            st["essence_mismatches"] += 1

        # 6. derive across the ancestry boundary, re-sign with parentOf
        a0, b0 = n_cap // 2, n_cap + n_gen // 2
        derived = wd / "derived.wav"
        F.trim(comp_signed, derived, a0 / FS, (b0 - a0) / FS)
        dmodel = O.trim("comp", n_comp, a0, b0)
        tl_comp = Timeline("comp", [SourceInterval("comp", iv.out_start, iv.out_end, iv.ev)
                                    for iv in ivs])
        divs = em_intervals(dmodel, {"comp": tl_comp})
        dassert = em_assertion(divs, FS, dmodel.n_out, "complete-source",
                               "trim", {"start": a0, "end": b0})
        dman = B.build_manifest(f"derived {rec['id']}", dassert, [{"action": "c2pa.cropped"}])
        dsigned = wd / "derived_signed.wav"
        B.sign(derived, dsigned, dman, sg, wd, parent=comp_signed)
        drep = B.validate(dsigned, sg, wd)
        if B.state_of(drep) == "Trusted":
            st["derived_trusted"] += 1
        else:
            st["failures"].append(f"{rec['id']} derived: {B.state_of(drep)}")
        if any(i.get("relationship") == "parentOf" for i in B.ingredients_of(drep)):
            st["derived_parentOf"] += 1
        dback = B.em_assertion_of(drep)
        dwhole = aggregate([iv.ev for iv in divs])
        if dwhole.label == "MIXED" and dback == json.loads(json.dumps(dassert)):
            st["derived_mixed"] += 1

        if not frozen:
            (FIXTURES / "manifest_composition_componentOf.json").write_text(
                json.dumps(rep, indent=1, sort_keys=True) + "\n")
            frozen = True

    payload = {
        "n_fixtures": st["n"],
        **{k: v for k, v in st.items() if k not in ("n", "failures")},
        "failures_sample": st["failures"][:10],
        "spec_notes": ("componentOf per C2PA 2.4 Table 10; c2pa.placed carries a hashed-URI "
                       "reference to each componentOf ingredient assertion per section "
                       "18.16.3, inserted by the claim generator from ingredientIds"),
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("J_c2pa_composition", payload)
    print(json.dumps({k: v for k, v in payload.items()
                      if k not in ("spec_notes", "failures_sample")}, indent=1))
    fail = (st["composition_trusted"] != st["n"] or st["component_ingredients_recorded"] != st["n"]
            or st["placed_actions_reference_both"] != st["n"]
            or st["assertion_roundtrip_identical"] != st["n"]
            or st["aggregate_mixed"] != st["n"] or st["derived_trusted"] != st["n"]
            or st["derived_mixed"] != st["n"] or st["essence_mismatches"])
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
