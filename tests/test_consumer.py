"""The consumer recomputes claims from the declared map and flags disagreement."""
import json
import em_audio.operators as O
from em_audio.consumer import verify
from em_audio.evidence import Evidence, claim_of
from em_audio.interval_map import OutputInterval, SourceInterval, Timeline, em_intervals
from em_audio.manifest_schema import dependency_declaration, em_assertion, with_declaration

N = 1000
C = Evidence(P=claim_of(["C"]), S={"cap": 0.9}, A={"cap": frozenset({"s"})}, L=frozenset({"a"}))
G = Evidence(P=claim_of(["G"]), S={"cap": 0.05}, A={"cap": frozenset({"s"})}, L=frozenset({"g"}))
TL = Timeline("s", [SourceInterval("s", 0, 400, C), SourceInterval("s", 400, 600, G),
                    SourceInterval("s", 600, N, C)])
SRC = {"s": json.loads(json.dumps(em_assertion(
    [OutputInterval(i.start, i.end, i.ev) for i in TL.intervals], 16000, N, "source", "capture", {})))}


def _assertion(model, ivs):
    a = em_assertion(ivs, 16000, model.n_out, "complete-source", model.operator, model.params)
    return json.loads(json.dumps(with_declaration(a, dependency_declaration(model, "declared", {"s": N}))))


def test_honest_assertion_verifies():
    m = O.resample("s", N, 16000, 8000)
    assert verify(_assertion(m, em_intervals(m, {"s": TL})), SRC)["verdict"] == "CONSISTENT"


def test_promoted_interval_is_flagged():
    m = O.trim("s", N, 100, 900)
    a = _assertion(m, em_intervals(m, {"s": TL}))
    g = next(i for i in a["intervals"] if i["provenance"] == ["G"])
    g["provenance"], g["state"] = ["C"], "CAPTURED"
    assert verify(a, SRC)["verdict"] == "PROMOTION"


def test_gap_in_declaration_is_a_coverage_failure():
    m = O.silence_removal("s", [(0, 300), (700, N)])
    a = _assertion(m, em_intervals(m, {"s": TL}))
    a["dependencyDeclaration"]["pieces"].pop()
    assert verify(a, SRC)["verdict"] == "COVERAGE_FAILURE"


def test_missing_declaration_is_reported():
    m = O.trim("s", N, 0, N)
    a = _assertion(m, em_intervals(m, {"s": TL}))
    del a["dependencyDeclaration"]
    assert verify(a, SRC)["verdict"] == "NO_DECLARATION"
