"""Run the synthetic Python and browser JavaScript Preview benchmarks."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"


def run_python(iterations):
    command = [sys.executable, str(TMP / "benchmark_python.py"), "--iterations", str(iterations)]
    completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def main():
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print(json.dumps({"python": run_python(iterations)}, indent=2))
    print("Browser benchmark: open tmp/benchmark-browser.html with the browser automation harness.")


if __name__ == "__main__":
    main()
