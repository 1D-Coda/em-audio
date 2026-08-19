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
lines = [
 "Derived audio can keep its exact waveform while claiming stronger provenance than its sources.",
 "A complete-source operator contract makes the derived claim the meet over every represented interval.",
 "Declared kernel footprints make the rule implementable against real codecs; over-approximation is safe.",
 f"Boundary-only inheritance promoted on {100*d1['baseline_promotion_rate']:.1f}% of frozen timelines; complete-source on none.",
 f"Interval evidence survived {n_rt} signed C2PA round-trips at {100*G['em_over_ffmpeg_fraction']:.3f}% of FFmpeg time.",
]
(ROOT / "paper" / "highlights.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
