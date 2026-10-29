"""Base64 export for the latest generated display JSON."""

import base64
import json
from pathlib import Path
from typing import Optional


def encode_latest_display(
    display_path: Optional[Path] = None,
    output_path: Path = Path("output") / "base64.txt",
) -> str:
    """Compact the display JSON, save it, and return its Base64 encoding."""
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
    encoded_base64 = base64.b64encode(compact_json.encode("utf-8")).decode("ascii")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(encoded_base64, encoding="ascii")

    json_output_path = output_path.with_name("base64.json")
    json_output_path.write_text(compact_json, encoding="utf-8")
    return encoded_base64
