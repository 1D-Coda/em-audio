"""Experiment N -- can a second C2PA reader recover the evidence assertion?

Section 9 states the paper's own gap plainly: every signed round-trip is produced
and checked by the official ``c2patool``, so nothing establishes that another
conforming consumer reads the custom assertion the same way. This experiment
narrows that gap, and it is important to be exact about by how much.

``c2pa-python`` is a different reader, not an independent implementation. It
binds the same Rust core that ``c2patool`` wraps, at a different version and
through a different API, so agreement here rules out a CLI-specific artefact and
a version-specific serialisation change. It does not rule out a shared defect in
the core, and no claim of interoperability with an unrelated implementation
follows from it. A genuinely independent reader would be the stronger check and
this is not one.

Two things are measured:

1. **Recovery.** Does the second reader return the assertion under the exact
   label, with a payload equal to what the serialiser emitted?
2. **Graceful degradation.** If a consumer ignores the custom label entirely,
   is it still left with a valid standard C2PA manifest and its ingredient
   graph? Section 9 asserts this as a design intention. Here it is measured.

Skipped rather than failed when the library is absent, since it is not part of
the pipeline's required dependency set.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from _common import ROOT, emit                                     # noqa: E402
from em_audio import manifest_schema as ms                         # noqa: E402

WORK = ROOT / "corpus" / "roundtrip"
MAX_ASSETS = 30          # enough to cover all three containers several times


def _payload_of(manifest: dict) -> tuple[str | None, dict | None]:
    """The EM assertion's label and data, however the reader nests it."""
    for a in manifest.get("assertions", []) or []:
        if a.get("label") == ms.ASSERTION_LABEL:
            return a.get("label"), a.get("data")
    return None, None


def main() -> int:
    t0 = time.time()
    try:
        from c2pa import Reader
    except ImportError:
        emit("N_second_reader", {
            "experiment": "N_second_reader",
            "status": "skipped",
            "reason": ("c2pa-python is not installed; it is an optional reader "
                       "and not part of the pipeline's required dependencies"),
            "install": "pip install c2pa-python",
        })
        print("second reader: SKIPPED (c2pa-python not installed)")
        return 0

    # Media only. The signing step also writes a *_signed.manifest.json sidecar
    # next to each asset, and globbing on the stem swept those in as assets the
    # reader then refused, which reads as a failure of the reader rather than of
    # the glob.
    CONTAINERS = {".wav", ".flac", ".mp3"}
    assets = [p for p in sorted(WORK.glob("*_signed.*"))
              if p.suffix.lower() in CONTAINERS][:MAX_ASSETS]
    if not assets:
        print("second reader: no signed assets found; run experiment F first",
              file=sys.stderr)
        return 1

    rows = []
    for path in assets:
        row = {"asset": path.name, "container": path.suffix.lstrip(".")}
        try:
            with open(path, "rb") as fh:
                doc = json.loads(Reader(path.suffix.lstrip("."), fh).json())
        except Exception as exc:                       # noqa: BLE001
            row.update(read_ok=False, error=str(exc)[:200])
            rows.append(row)
            continue

        active = doc.get("manifests", {}).get(doc.get("active_manifest"), {})
        label, data = _payload_of(active)
        labels = [a.get("label") for a in active.get("assertions", []) or []]

        row.update(
            read_ok=True,
            em_assertion_present=label == ms.ASSERTION_LABEL,
            schema_matches=bool(data) and data.get("schema") == ms.SCHEMA,
            intervals=len(data.get("intervals", [])) if data else 0,
            # Degradation: what a consumer that ignores our label is left with.
            standard_assertions=[l for l in labels
                                 if l and l.startswith("c2pa.")],
            has_ingredients=bool(active.get("ingredients")),
            validation_state=doc.get("validation_state"),
        )
        rows.append(row)

    read = [r for r in rows if r.get("read_ok")]
    recovered = [r for r in read if r.get("em_assertion_present")
                 and r.get("schema_matches")]
    degrades = [r for r in read if r.get("standard_assertions")]

    from c2pa import __version__ as c2pa_py_version                # noqa: PLC0415
    result = {
        "experiment": "N_second_reader",
        "status": "run",
        "purpose": ("whether a reader other than c2patool recovers the evidence "
                    "assertion, and what a reader that ignores it is left with"),
        "independence_note": ("c2pa-python binds the same Rust core c2patool "
                              "wraps, at a different version and through a "
                              "different API. Agreement rules out a CLI-specific "
                              "or version-specific artefact. It is not an "
                              "independent implementation and no interoperability "
                              "claim follows from it."),
        "reader": f"c2pa-python {c2pa_py_version}",
        "assertion_label": ms.ASSERTION_LABEL,
        "assets_examined": len(rows),
        "assets_read": len(read),
        "assertion_recovered": len(recovered),
        "assertion_recovery_complete": len(recovered) == len(read) == len(rows),
        "degrades_to_standard_manifest": len(degrades),
        "degradation_complete": len(degrades) == len(read),
        "per_asset": rows,
        "runtime_s": round(time.time() - t0, 3),
    }
    emit("N_second_reader", result)

    print(f"second reader: c2pa-python {c2pa_py_version}")
    print(f"  read {len(read)}/{len(rows)} signed assets")
    print(f"  EM assertion recovered under the exact label: "
          f"{len(recovered)}/{len(read)}")
    print(f"  standard manifest still intact if the label is ignored: "
          f"{len(degrades)}/{len(read)}")
    bad = len(rows) - len(recovered)
    if bad:
        print(f"  {bad} asset(s) did not round-trip; see the result file")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
