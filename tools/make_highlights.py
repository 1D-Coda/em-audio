"""Emit the highlights file with numbers taken from the results."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MR = ROOT / "results" / "machine_readable"
F = json.loads((MR / "F_c2pa_roundtrip.json").read_text())
D = json.loads((MR / "D_transform_matrix.json").read_text())
pt = D["per_transformation"]
d_runs = sum(v["n"] for v in pt.values())
d_base = sum(v.get("baseline_either_promotions", v["baseline_promotions"]) for v in pt.values())
n_rt = sum(v["n"] for v in F["per_container"].values())
# Each highlight is capped at 85 characters including spaces. The limit is
# enforced here rather than trusted, because these lines are regenerated on
# every run and a number that grows by one digit can push a line over.
LIMIT = 85
lines = [
 "Derived audio can keep its waveform while claiming stronger provenance.",
 "A complete-source contract makes the derived claim the meet over its sources.",
 "Measured codec footprints failed a holdout test; whole-asset dependency stays safe.",
 f"Boundary-only promoted at interval level in {d_base:,} of {d_runs:,} FFmpeg runs; ours in none.",
 f"Decoded essence was unchanged across {n_rt:,} signed C2PA round-trips.",
]
over = [(len(l), l) for l in lines if len(l) > LIMIT]
if over:
    for n, l in over:
        print(f"[highlights] {n} chars, {n - LIMIT} over the limit: {l}")
    raise SystemExit(f"{len(over)} highlight(s) exceed {LIMIT} characters")
if not 3 <= len(lines) <= 5:
    raise SystemExit(f"{len(lines)} highlights; the journal requires 3 to 5")
out = ROOT / "paper" / "highlights.txt"
if not out.parent.is_dir():
    # No paper/ in the reproduction package: the highlights belong to the
    # manuscript, not to the experiments a validator is reproducing.
    print("[highlights] paper/ absent; skipped")
else:
    out.write_text("\n".join(lines) + "\n", newline="\n")
for l in lines:
    print(f"{len(l):3d}  {l}")
