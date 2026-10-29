"""Compact JSON export for the latest generated display."""

import json
from pathlib import Path
from typing import Optional


def encode_latest_display(
    display_path: Optional[Path] = None,
    output_path: Path = Path("output") / "base64.txt",
) -> str:
    """Read the latest display JSON, compact it to one line, save it, and return it."""
    source_path = Path(display_path) if display_path is not None else Path("output") / "display.json"
    if not source_path.is_file():
        raise FileNotFoundError(
            f"No generated display.json found at {source_path}. Generate a canvas first."
        )

    with source_path.open("r", encoding="utf-8") as source_file:
        display_data = json.load(source_file)

    compact_json = json.dumps(
        display_data,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(compact_json, encoding="utf-8")

    json_output_path = output_path.with_name("base64.json")
    json_output_path.write_text(compact_json, encoding="utf-8")
    return compact_json
