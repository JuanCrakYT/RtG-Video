"""Base64 export for the latest generated display JSON."""

import base64
from pathlib import Path
from typing import Optional


def encode_latest_display(
	display_path: Optional[Path] = None,
	output_path: Path = Path("output") / "base64.json",
) -> str:
	"""Read the latest display JSON, encode it, and save the Base64 text."""
	source_path = Path(display_path) if display_path is not None else Path("output") / "display.json"
	if not source_path.is_file():
		raise FileNotFoundError(
			f"No generated display.json found at {source_path}. Generate a canvas first."
		)

	display_json = source_path.read_bytes()
	encoded_json = base64.b64encode(display_json).decode("ascii")
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(encoded_json, encoding="ascii")
	return encoded_json
