"""Experiment F -- signed round-trip and signal transparency under signing.

For each container the chain is: sign the source, read it back, validate,
derive with stock ffmpeg, attach the parent ingredient and an editorial action,
re-sign, validate again.  The EM assertion must survive both signatures
byte-equivalently, and -- the signal-transparency test (P8) -- the *decoded
essence* of the derived asset must be identical before signing, after signing
with the EM assertion, and after signing with the baseline assertion.  Whole-file
hashes are deliberately not used: embedding a manifest changes the file.
"""
from __future__ import annotations

import json, shutil, statistics, sys, time
from pathlib import Path
from typing import Dict, List

from _common import CAPTURE_SUPPORT, CHANNEL, ROOT, SCOPE, emit  # noqa: E402
from _signing import signer                                          # noqa: E402
from em_audio import c2pa_bridge as B, ffmpeg_ops as F
from em_audio.essence import essence_hash, file_hash
from em_audio.evidence import Evidence, aggregate, claim_of
from em_audio.interval_map import SourceInterval, Timeline, em_intervals, span_evidence
from em_audio.manifest_schema import ASSERTION_LABEL, em_assertion
import em_audio.operators as O

CORPUS = ROOT / "corpus"
WORK = CORPUS / "roundtrip"
FIXTURES = ROOT / "fixtures" / "expected"
FS = 16_000
N_CLIPS = 40
CONTAINERS = ["wav", "flac", "mp3"]


def timeline_of(rec) -> Timeline:
    ivs = []
    for seg in rec["ground_truth"]:
        k = seg["kind"]
        ivs.append(SourceInterval("clip", seg["start"], seg["end"],
                                  Evidence(P=claim_of([k]), S={CHANNEL: CAPTURE_SUPPORT[k]},
                                           A={CHANNEL: SCOPE}, L=frozenset({seg["lineage"]}))))
    return Timeline("clip", ivs)


def main() -> int:
    t0 = time.time()
    index = json.loads((CORPUS / "corpus_index.json").read_text())[:N_CLIPS]
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    sg = signer()

    per_container: Dict[str, Dict[str, object]] = {}
    essence_rows: List[Dict[str, object]] = []
    frozen_saved = set()

    for ext in CONTAINERS:
        st = {"n": 0, "sign_ok": 0, "validate_trusted": 0, "validate_valid_or_better": 0,
              "assertion_roundtrip_identical": 0, "derive_sign_ok": 0,
              "derived_validate_trusted": 0, "parentOf_recorded": 0,
              "derived_assertion_roundtrip_identical": 0,
              "essence_identical_pre_vs_em": 0, "essence_identical_pre_vs_baseline": 0,
              "essence_identical_em_vs_baseline": 0, "file_hash_changed_by_signing": 0,
              "manifest_bytes": [], "em_assertion_bytes": [],
              "sign_ms": [], "validate_ms": [], "failures": []}
        for rec in index:
            st["n"] += 1
            src_wav = ROOT / rec["path"]
            n = rec["n_samples"]
            tl = timeline_of(rec)
            base = WORK / f"{rec['id']:04d}_src.{ext}"
            F.transcode(src_wav, base, ext)

            model = O.transcode("clip", n, ext)
            ivs = em_intervals(model, {"clip": tl}, footprint_aware=True)
            assertion = em_assertion(ivs, FS, model.n_out, "complete-source",
                                     model.operator, model.params)
            man = B.build_manifest(f"clip {rec['id']} {ext}", assertion,
                                   [{"action": "c2pa.transcoded"}])
            signed = WORK / f"{rec['id']:04d}_signed.{ext}"
            t1 = time.perf_counter()
            B.sign(base, signed, man, sg, WORK)
            st["sign_ms"].append((time.perf_counter() - t1) * 1000)
            st["sign_ok"] += 1
            st["manifest_bytes"].append(signed.stat().st_size - base.stat().st_size)
            st["em_assertion_bytes"].append(len(json.dumps(assertion).encode()))

            t1 = time.perf_counter()
            rep = B.validate(signed, sg, WORK)
            st["validate_ms"].append((time.perf_counter() - t1) * 1000)
            state = B.state_of(rep)
            if state == "Trusted":
                st["validate_trusted"] += 1
            if state in ("Trusted", "Valid"):
                st["validate_valid_or_better"] += 1
            else:
                st["failures"].append(f"{rec['id']}/{ext}: state={state} {B.failures(rep)}")
            back = B.em_assertion_of(rep)
            if back == json.loads(json.dumps(assertion)):
                st["assertion_roundtrip_identical"] += 1

            # ---- derive -----------------------------------------------------
            derived = WORK / f"{rec['id']:04d}_derived.{ext}"
            dur = n / float(FS)
            F.trim(signed, derived, 0.1 * dur, 0.8 * dur, codec=ext)
            a = int(0.1 * n); b = a + int(0.8 * n)
            dmodel = O.trim("clip", n, a, b)
            divs = em_intervals(dmodel, {"clip": tl}, footprint_aware=True)
            dassert = em_assertion(divs, FS, dmodel.n_out, "complete-source",
                                   dmodel.operator, dmodel.params)
            bspans = span_evidence(dmodel, {"clip": tl}, "boundary")
            bassert = em_assertion(bspans, FS, dmodel.n_out, "boundary-only",
                                   dmodel.operator, dmodel.params)

            pre_essence = essence_hash(derived)
            pre_file = file_hash(derived)

            dman = B.build_manifest(f"clip {rec['id']} derived {ext}", dassert,
                                    [{"action": "c2pa.cropped"}])
            dsigned = WORK / f"{rec['id']:04d}_derived_em.{ext}"
            B.sign(derived, dsigned, dman, sg, WORK, parent=signed)
            st["derive_sign_ok"] += 1

            bman = B.build_manifest(f"clip {rec['id']} derived {ext}", bassert,
                                    [{"action": "c2pa.cropped"}])
            bsigned = WORK / f"{rec['id']:04d}_derived_base.{ext}"
            B.sign(derived, bsigned, bman, sg, WORK, parent=signed)

            drep = B.validate(dsigned, sg, WORK)
            if B.state_of(drep) == "Trusted":
                st["derived_validate_trusted"] += 1
            else:
                st["failures"].append(f"{rec['id']}/{ext} derived: state={B.state_of(drep)} "
                                      f"{B.failures(drep)}")
            if any(i.get("relationship") == "parentOf" for i in B.ingredients_of(drep)):
                st["parentOf_recorded"] += 1
            if B.em_assertion_of(drep) == json.loads(json.dumps(dassert)):
                st["derived_assertion_roundtrip_identical"] += 1

            h_em, h_bs = essence_hash(dsigned), essence_hash(bsigned)
            if h_em == pre_essence:
                st["essence_identical_pre_vs_em"] += 1
            if h_bs == pre_essence:
                st["essence_identical_pre_vs_baseline"] += 1
            if h_em == h_bs:
                st["essence_identical_em_vs_baseline"] += 1
            if file_hash(dsigned) != pre_file:
                st["file_hash_changed_by_signing"] += 1
            essence_rows.append({"clip": rec["id"], "container": ext,
                                 "essence_pre": pre_essence, "essence_em": h_em,
                                 "essence_baseline": h_bs,
                                 "file_pre": pre_file, "file_em": file_hash(dsigned)})

            if ext not in frozen_saved:
                (FIXTURES / f"manifest_{ext}_signed.json").write_text(
                    json.dumps(rep, indent=1, sort_keys=True) + "\n")
                (FIXTURES / f"manifest_{ext}_derived.json").write_text(
                    json.dumps(drep, indent=1, sort_keys=True) + "\n")
                frozen_saved.add(ext)

        per_container[ext] = {
            **{k: v for k, v in st.items()
               if k not in ("manifest_bytes", "em_assertion_bytes", "sign_ms", "validate_ms", "failures")},
            "median_manifest_overhead_bytes": int(statistics.median(st["manifest_bytes"])),
            "median_em_assertion_bytes": int(statistics.median(st["em_assertion_bytes"])),
            "median_sign_ms": round(statistics.median(st["sign_ms"]), 2),
            "median_validate_ms": round(statistics.median(st["validate_ms"]), 2),
            "failures": st["failures"][:10],
        }
        print(f"  {ext}: trusted {st['validate_trusted']}/{st['n']} derived-trusted "
              f"{st['derived_validate_trusted']}/{st['n']} essence-identical "
              f"{st['essence_identical_pre_vs_em']}/{st['n']}")

    payload = {
        "n_clips": len(index), "containers": CONTAINERS,
        "c2patool": B.version(),
        "signal_transparency_method": ("SHA-256 of decoded PCM (s16le at the asset's own rate); "
                                       "whole-file hashes are not used because embedding a "
                                       "manifest changes the file"),
        "trust_note": ("signed with a locally generated test credential and a locally configured "
                       "trust anchor; the credential is not on the C2PA Conformance Program "
                       "trust list, so 'Trusted' here means trusted under the declared local "
                       "anchor, not conformance-program trust"),
        "per_container": per_container,
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("F_c2pa_roundtrip", payload)
    (ROOT / "results" / "machine_readable" / "F_essence_rows.json").write_text(
        json.dumps(essence_rows, indent=1) + "\n")
    fail = any(v["validate_valid_or_better"] != v["n"]
               or v["derived_validate_trusted"] != v["n"]
               or v["essence_identical_pre_vs_em"] != v["n"]
               or v["essence_identical_em_vs_baseline"] != v["n"]
               or v["assertion_roundtrip_identical"] != v["n"]
               for v in per_container.values())
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
