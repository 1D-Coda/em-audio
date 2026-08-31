"""Emit the highlights file with numbers taken from the results."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
MR = ROOT / "results" / "machine_readable"
B = json.loads((MR / "B_adversarial_timelines.json").read_text())
F = json.loads((MR / "F_c2pa_roundtrip.json").read_text())
G = json.loads((MR / "G_overhead.json").read_text())
d1 = B["per_depth"]["1"]
n_rt = sum(v["n"] for v in F["per_container"].values())
# The journal caps each highlight at 85 characters including spaces, and returns
# submissions that exceed it before review. The limit is enforced here rather
# than trusted, because these lines are regenerated on every run and a number
# that grows by one digit can push a line over without anyone noticing.
LIMIT = 85
lines = [
 "Derived audio can keep its waveform while claiming stronger provenance.",
 "A complete-source contract makes the derived claim the meet over its sources.",
 "Declared kernel footprints make the rule work on real codecs; erring large is safe.",
 f"Boundary-only inheritance promoted on {100*d1['baseline_promotion_rate']:.1f}% of timelines; complete-source on none.",
 f"Interval evidence survived {n_rt} signed C2PA round-trips at {100*G['em_over_ffmpeg_fraction']:.3f}% of FFmpeg time.",
]
over = [(len(l), l) for l in lines if len(l) > LIMIT]
if over:
    for n, l in over:
        print(f"[highlights] {n} chars, {n - LIMIT} over the limit: {l}")
    raise SystemExit(f"{len(over)} highlight(s) exceed {LIMIT} characters")
if not 3 <= len(lines) <= 5:
    raise SystemExit(f"{len(lines)} highlights; the journal requires 3 to 5")
(ROOT / "paper" / "highlights.txt").write_text("\n".join(lines) + "\n")
for l in lines:
    print(f"{len(l):3d}  {l}")
