"""Batch runner for a duration-only infrastructure smoke test."""
import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path
import subprocess
import tempfile
import wave

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/experimental_v1.json"
SCRIPT = ROOT / "praat/smoke_test.praat"
MAX_BYTES = 10 * 1024 * 1024

class AnalysisError(RuntimeError):
    pass

def _run(args):
    try:
        return subprocess.run(args, shell=False, capture_output=True, text=True,
                              timeout=15, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise AnalysisError("Praat execution failed or timed out") from exc

def analyze_wav(data: bytes, executable: str | None = None) -> dict:
    if not data or len(data) > MAX_BYTES:
        raise ValueError("WAV must contain 1 byte to 10 MiB")
    config_bytes = CONFIG_PATH.read_bytes()
    config = json.loads(config_bytes)
    executable = executable or os.environ.get("PRAAT_EXECUTABLE", "praat")
    with tempfile.TemporaryDirectory(prefix="habla-motora-") as temp:
        path = Path(temp) / "input.wav"
        path.write_bytes(data)
        try:
            with wave.open(str(path), "rb") as wav:
                frames, rate = wav.getnframes(), wav.getframerate()
                if (wav.getnchannels() != 1 or wav.getsampwidth() not in (2, 3, 4)
                    or rate not in (44100, 48000) or frames == 0
                    or wav.getcomptype() != "NONE"):
                    raise ValueError("Expected nonempty mono PCM WAV, 16/24/32-bit, 44100/48000 Hz")
        except (wave.Error, EOFError) as exc:
            raise ValueError("Invalid PCM WAV") from exc
        version = _run([executable, "--version"])
        expected = config["engine"]["praat_version"]
        match = re.fullmatch(r"Praat (\d+\.\d+\.\d+)(?: \([^\n]*\))?", version)
        if match is None or match.group(1) != expected:
            raise AnalysisError(f"Expected Praat {expected}; received {version!r}")
        raw = _run([executable, "--run", str(SCRIPT), str(path)])
        try:
            duration = float(raw)
        except ValueError as exc:
            raise AnalysisError("Invalid duration returned by Praat") from exc
        if not math.isfinite(duration) or duration <= 0 or abs(duration - frames/rate) > 1/rate:
            raise AnalysisError("Praat duration disagrees with WAV sample count")
    return {
        "status": "infrastructure_smoke_test_only",
        "provenance": {
            "praat_version": expected,
            "praat_version_output": version,
            "protocol_version": config["protocol_version"],
            "configuration_version": config["configuration_version"],
            "configuration_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "file_sha256": hashlib.sha256(data).hexdigest(),
            "script_sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        },
        "temporal": {"file_duration_s": duration},
        "quality": {
            "f0_coverage": {"value": None, "reason": "not_implemented"},
            "accepted_cycles": {"value": None, "reason": "not_implemented"},
            "technical_warnings": ["Duration refers to the entire WAV, not a selected phonation segment.",
                                   "Acoustic measures and quality assessment are not implemented."],
        },
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("wav", type=Path)
    args = parser.parse_args()
    if args.wav.stat().st_size > MAX_BYTES:
        parser.error("File exceeds 10 MiB")
    print(json.dumps(analyze_wav(args.wav.read_bytes()), indent=2, allow_nan=False))

if __name__ == "__main__":
    main()
