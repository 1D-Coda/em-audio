"""Experiment H -- two-language differential on a frozen, language-neutral corpus.

The Python core (interval algebra with pulled-back boundaries) and the Node.js
oracle (brute-force per-sample evaluation, then run-length encoding) implement
the same specification by different algorithms.  Both are compared on a frozen
JSONL corpus written to ``fixtures/oracle_cases.jsonl`` and never regenerated
between runs.

Both implementations are author-written.  This is a differential test against
transcription and interval-arithmetic error, not evidence of independence from
the author; the manuscript states this explicitly.
"""
from __future__ import annotations

import itertools, json, subprocess, sys, time
from pathlib import Path
from typing import Dict, List

from _common import CHANNEL, ROOT, SCOPE, element, emit, timeline_from_word    # noqa: E402
from em_audio.evidence import _Bot, aggregate, label_of
from em_audio.interval_map import em_intervals, span_evidence
import em_audio.operators as O

FIXTURES = ROOT / "fixtures"
ORACLE = ROOT / "oracle_js" / "oracle.js"
WIDTH = 16
ALPHABET = ("C", "G", "B")
MAX_LEN = 6


def serialise_evidence(ev) -> Dict[str, object]:
    return {
        "P": None if isinstance(ev.P, _Bot) else sorted(ev.P),
        "S": {k: float(v) for k, v in sorted(ev.S.items())},
        "A": {k: sorted(v) for k, v in sorted(ev.A.items())},
        "L": sorted(ev.L),
    }


def build_cases() -> List[Dict[str, object]]:
    cases = []
    cid = 0
    for L in range(1, MAX_LEN + 1):
        for word in itertools.product(*[ALPHABET] * L):
            n = L * WIDTH
            tl = timeline_from_word(word, WIDTH)
            models = [
                ("trim_all", O.trim("s", n, 0, n)),
                ("resample_48_16", O.resample("s", n, 48000, 16000)),
                ("transcode_mp3", O.transcode("s", n, "mp3")),
                ("transcode_flac", O.transcode("s", n, "flac")),
                ("normalize", O.normalize("s", n)),
                ("time_stretch_1.25", O.time_stretch("s", n, 1.25, 48000)),
                ("concat_self", O.concat([("s", 0, n), ("s", 0, n)])),
            ]
            if n >= 3 * WIDTH:
                models.append(("trim_inner", O.trim("s", n, WIDTH, n - WIDTH)))
                models.append(("silence_removal",
                               O.silence_removal("s", [(0, WIDTH), (n - WIDTH, n)])))
            for name, m in models:
                cases.append({
                    "id": cid, "word": "".join(word), "operator": name,
                    "timelines": {"s": [{"src": i.src, "start": i.start, "end": i.end,
                                         "ev": serialise_evidence(i.ev)}
                                        for i in tl.intervals]},
                    "model": {"n_out": m.n_out,
                              "pieces": [{"out_start": p.out_start, "out_end": p.out_end,
                                          "src": p.src, "src_start": p.src_start,
                                          "src_end": p.src_end, "footprint": p.footprint}
                                         for p in m.pieces]},
                    "_py_model": m,
                })
                cid += 1
    return cases


def main() -> int:
    t0 = time.time()
    FIXTURES.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    path = FIXTURES / "oracle_cases.jsonl"
    with open(path, "w") as fh:
        for c in cases:
            d = {k: v for k, v in c.items() if k != "_py_model"}
            fh.write(json.dumps(d, sort_keys=True) + "\n")

    proc = subprocess.run(["node", str(ORACLE), str(path)], capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-3000:], file=sys.stderr)
        return 2
    js = {json.loads(l)["id"]: json.loads(l) for l in proc.stdout.splitlines() if l.strip()}

    compared = 0
    disagreements: List[str] = []
    max_support_delta = 0.0
    for c in cases:
        m = c["_py_model"]
        tl = timeline_from_word(c["word"], WIDTH)
        tls = {"s": tl}
        ivs = em_intervals(m, tls, footprint_aware=True)
        spans = span_evidence(m, tls, "boundary")
        nofp = span_evidence(m, tls, "em_nofp")
        py = {
            "em_intervals": [[i.out_start, i.out_end, i.ev.label,
                              {k: float(v) for k, v in sorted(i.ev.S.items())},
                              sorted(i.ev.L)] for i in ivs],
            "em_whole_state": aggregate([i.ev for i in ivs]).label,
            "em_nofp_state": aggregate([i.ev for i in nofp]).label,
            "baseline_whole_state": aggregate([i.ev for i in spans]).label,
            "em_whole_lineage": sorted(aggregate([i.ev for i in ivs]).L),
            "baseline_whole_lineage": sorted(aggregate([i.ev for i in spans]).L),
        }
        j = js[c["id"]]
        compared += 1
        for key in ("em_whole_state", "em_nofp_state", "baseline_whole_state",
                    "em_whole_lineage", "baseline_whole_lineage"):
            if py[key] != j[key]:
                if len(disagreements) < 20:
                    disagreements.append(f"case {c['id']} {c['word']}/{c['operator']} "
                                         f"{key}: py={py[key]} js={j[key]}")
        if [x[:3] for x in py["em_intervals"]] != [x[:3] for x in j["em_intervals"]]:
            if len(disagreements) < 20:
                disagreements.append(f"case {c['id']} {c['word']}/{c['operator']} interval structure")
        for a, b in zip(py["em_intervals"], j["em_intervals"]):
            for k in set(a[3]) | set(b[3]):
                if k in a[3] and k in b[3]:
                    max_support_delta = max(max_support_delta, abs(a[3][k] - b[3][k]))
                else:
                    disagreements.append(f"case {c['id']} channel availability {k}")

    payload = {
        "cases": len(cases), "compared": compared,
        "alphabet": list(ALPHABET), "max_word_length": MAX_LEN,
        "element_width_samples": WIDTH,
        "python_algorithm": "interval algebra with pulled-back source boundaries",
        "javascript_algorithm": "brute-force per-output-sample evaluation, run-length encoded",
        "disagreements": len(disagreements),
        "disagreement_sample": disagreements[:20],
        "max_support_abs_difference": max_support_delta,
        "independence_caveat": ("both implementations are author-written; this is a "
                                "differential test against transcription and interval-"
                                "arithmetic error, not author independence"),
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("H_oracle_differential", payload)
    print(f"cases={len(cases)} disagreements={len(disagreements)} "
          f"max_support_delta={max_support_delta}")
    return 1 if disagreements else 0


if __name__ == "__main__":
    sys.exit(main())
