from __future__ import annotations
import json, os, platform, subprocess, sys, time
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "results" / "machine_readable"
RESULTS.mkdir(parents=True, exist_ok=True)

from em_audio.evidence import BOT, C, G, Evidence, claim_of          # noqa: E402
from em_audio.interval_map import SourceInterval, Timeline           # noqa: E402

CHANNEL = "capture-support"
SCOPE = frozenset({"digital-asset"})

# Declaration-derived support for the corpus and transport experiments. The
# exhaustive synthetic enumeration sweeps the domain positionally instead, in
# element() below, so that every value in S is exercised rather than two.
CAPTURE_SUPPORT = {"C": 0.90, "G": 0.10}


def element(kind: str, k: int, n: int, src: str = "s") -> Evidence:
    """Deterministic evidence element for symbol ``kind`` at position ``k``."""
    if kind == "B":                                   # ⊥ : unverified
        return Evidence(P=BOT, S={}, A={}, L=frozenset({f"urn:emaudio:{src}#el={k}"}))
    val = round((k + 1) / float(n + 1), 12)
    return Evidence(P=claim_of([kind]), S={CHANNEL: val}, A={CHANNEL: SCOPE},
                    L=frozenset({f"urn:emaudio:{src}#el={k}"}))


def timeline_from_word(word: Sequence[str], width: int = 1, src: str = "s") -> Timeline:
    n = len(word)
    ivs = [SourceInterval(src, k * width, (k + 1) * width, element(ch, k, n, src))
           for k, ch in enumerate(word)]
    return Timeline(src, ivs)


def _cpu_model() -> str:
    """The processor model, which platform.processor() reduces to 'arm'.

    A benchmark that reports only the architecture cannot be recreated: 'arm64'
    covers parts that differ several-fold in single-core throughput.
    """
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                 capture_output=True, text=True).stdout.strip()
            if out:
                return out
        else:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    # platform.processor() is empty on many Linuxes and verbose on Windows;
    # either is better than nothing, and os.cpu_count is always available.
    return platform.processor() or platform.machine() or "unavailable"


def _memory_bytes() -> str:
    """Physical memory in bytes, on the three platforms this runs on."""
    try:
        if sys.platform == "darwin":
            return subprocess.run(["sysctl", "-n", "hw.memsize"],
                                  capture_output=True, text=True).stdout.strip()
        if sys.platform.startswith("win"):
            # No /proc and no sysctl. wmic is deprecated but still present on
            # Windows Server 2025; PowerShell is the fallback.
            for cmd in (["wmic", "computersystem", "get", "TotalPhysicalMemory"],
                        ["powershell", "-NoProfile", "-Command",
                         "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"]):
                out = subprocess.run(cmd, capture_output=True, text=True).stdout
                digits = [w for w in out.split() if w.isdigit()]
                if digits:
                    return digits[0]
            return "unavailable"
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                return str(int(line.split()[1]) * 1024)
    except Exception:
        pass
    return "unavailable"


def env() -> Dict[str, str]:
    def _v(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()[0].strip()
        except Exception:
            return "unavailable"
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or platform.machine(),
        "cpu_model": _cpu_model(),
        "cpu_count_logical": str(os.cpu_count() or "unavailable"),
        "memory_bytes": _memory_bytes(),
        "ffmpeg": _v(["ffmpeg", "-version"]),
        "c2patool": _v(["c2patool", "--version"]),
        "node": _v(["node", "-v"]),
        "espeak_ng": _v(["espeak-ng", "--version"]),
    }


def emit(name: str, payload: Dict[str, object]) -> Path:
    payload = dict(payload)
    payload.setdefault("experiment", name)
    payload.setdefault("environment", env())
    p = RESULTS / f"{name}.json"
    p.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    print(f"[emit] {p.relative_to(ROOT)}")
    return p
