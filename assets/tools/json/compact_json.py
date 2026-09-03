import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "input.json"
OUTPUT_FILE = BASE_DIR / "output.json"

with INPUT_FILE.open("r", encoding="utf-8") as f:
    data = json.load(f)

with OUTPUT_FILE.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

print(f"JSON compactado correctamente:")
print(f"Entrada: {INPUT_FILE}")
print(f"Salida:  {OUTPUT_FILE}")