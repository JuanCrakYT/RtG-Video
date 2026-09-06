"""
Configuration and constants for RtG Video.
"""

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Project version
# ---------------------------------------------------------------------------

_VERSION_PATTERN = re.compile(
    r"^\s*>\s*\*\*Version:\*\*\s*(.+?)\s*$",
    re.MULTILINE,
)


def get_project_version():
    """
    Read the project version from the root README.md.

    The README is the single source of truth for RtG Video's version.

    Returns:
        int | float | str:
            Numeric versions are returned as int/float.
            Non-numeric versions are preserved as strings.

    Raises:
        FileNotFoundError:
            If the root README.md cannot be found.
        ValueError:
            If README.md exists but contains no valid Version entry.
    """
    readme_path = Path(__file__).resolve().parents[1] / "README.md"

    if not readme_path.is_file():
        raise FileNotFoundError(
            f"Project README.md not found: {readme_path}"
        )

    readme_text = readme_path.read_text(encoding="utf-8")

    match = _VERSION_PATTERN.search(readme_text)
    if not match:
        raise ValueError(
            "README.md does not contain a valid "
            "'> **Version:** <value>' entry"
        )

    raw_version = match.group(1).strip()

    # Preserve non-numeric versions as strings.
    # Examples:
    #   0.706       -> 0.706
    #   1           -> 1
    #   dev         -> "dev"
    #   0.707-beta  -> "0.707-beta"
    try:
        if re.fullmatch(r"[+-]?\d+", raw_version):
            return int(raw_version)

        if re.fullmatch(
            r"[+-]?(?:\d+\.\d*|\.\d+)",
            raw_version,
        ):
            return float(raw_version)
    except (TypeError, ValueError):
        pass

    return raw_version


# Display defaults
DEFAULT_DISPLAY_WIDTH = 8
DEFAULT_DISPLAY_HEIGHT = 8
DEFAULT_PIXEL_SPACING = 1.0  # Units in Part
DEFAULT_CANVAS_Y_OFFSET = 0.75

# CFrame defaults
DEFAULT_CFRAME_IDENTITY = [
    0.0, 0.0, 0.0, 1.0,
    0.0, 0.0, 0.0, 1.0,
    0.0, 0.0, 0.0, 1.0,
]

# Connection types
CONNECTION_TYPE_STANDARD = "1"
CONNECTION_TYPE_SECONDARY = "2"
CONNECTION_TYPE_DISTRIBUTION = "3"
CONNECTION_TYPE_LOGIC = "4"
CONNECTION_TYPE_CHANNEL = "5"
CONNECTION_TYPE_SPHERE = "6"

# RtG Block Types
BLOCK_TYPE_BASE = "Base"
BLOCK_TYPE_PART = "Part"
BLOCK_TYPE_SERVO = "Servo"
BLOCK_TYPE_CONNECTOR = "Connector"
BLOCK_TYPE_CONNECTOR_BALL = "ConnectorBall"

# Animation defaults
DEFAULT_FRAME_DURATION = 0.05  # seconds
DEFAULT_FPS = 24

# Display properties
PIXEL_ACTIVE_COLOR = [255, 0, 0]  # RGB red for active pixels
PIXEL_INACTIVE_COLOR = [64, 64, 64]  # RGB dark gray for inactive
