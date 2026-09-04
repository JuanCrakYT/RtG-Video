"""Run the synthetic Python and browser JavaScript Preview benchmarks."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
VIDEO = TMP / "synthetic_test.mp4"


def ensure_video():
    if not VIDEO.exists():
        subprocess.run([sys.executable, str(TMP / "generate_test_video.py"), str(VIDEO)], cwd=ROOT, check=True)


def run_python(iterations):
    command = [sys.executable, str(TMP / "benchmark_python.py"), "--iterations", str(iterations)]
    completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def main():
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    ensure_video()
    print(json.dumps({"python": run_python(iterations)}, indent=2))
    print("End-to-end Python benchmark: python tmp/benchmark_python_playback.py --frames 60")
    print("End-to-end browser benchmark: open tmp/benchmark-playback.html?frames=60 in the browser harness.")


if __name__ == "__main__":
    main()
