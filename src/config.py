"""
Configuration and constants for RtG Display
"""

# Display defaults
DEFAULT_DISPLAY_WIDTH = 8
DEFAULT_DISPLAY_HEIGHT = 8
DEFAULT_PIXEL_SPACING = 4.0  # Units in RtG space

# CFrame defaults
DEFAULT_CFRAME_IDENTITY = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]

# Connection types (TipoLocal)
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
