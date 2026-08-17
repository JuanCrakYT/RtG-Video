"""
Animation frame representation for RtG Display.

A frame represents a single snapshot in an animation with a duration
and a set of active pixels.
"""

from typing import Set, List, Dict, Any


class AnimationFrame:
    """
    Represents a single animation frame.
    
    Contains duration and which pixels are active in this frame.
    """
    
    def __init__(self, duration: float, frame_number: int = 0):
        """
        Initialize an animation frame.
        
        Args:
            duration: How long this frame lasts (in seconds)
            frame_number: Frame index (for reference)
        """
        self.duration = duration
        self.frame_number = frame_number
        self.active_pixels: Set[str] = set()  # Set of UUID strings
        self.metadata: Dict[str, Any] = {}
    
    def add_pixel(self, pixel_uuid: str) -> None:
        """
        Add a pixel to this frame's active set.
        
        Args:
            pixel_uuid: UUID of the pixel to activate
        """
        self.active_pixels.add(pixel_uuid)
    
    def remove_pixel(self, pixel_uuid: str) -> None:
        """
        Remove a pixel from this frame's active set.
        
        Args:
            pixel_uuid: UUID of the pixel to deactivate
        """
        self.active_pixels.discard(pixel_uuid)
    
    def set_active_pixels(self, pixel_uuids: List[str]) -> None:
        """
        Set the complete active pixel set.
        
        Args:
            pixel_uuids: List of UUIDs to activate
        """
        self.active_pixels = set(pixel_uuids)
    
    def get_active_pixels(self) -> List[str]:
        """Get list of active pixel UUIDs."""
        return list(self.active_pixels)
    
    def count_active(self) -> int:
        """Get count of active pixels."""
        return len(self.active_pixels)
    
    def is_empty(self) -> bool:
        """Check if frame has no active pixels."""
        return len(self.active_pixels) == 0


class FrameBuilder:
    """
    Builder pattern for creating AnimationFrame instances.
    """
    
    def __init__(self, duration: float = 0.05):
        """
        Initialize builder.
        
        Args:
            duration: Frame duration in seconds
        """
        self.duration = duration
        self.frame_number = 0
        self.active_pixels: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    def set_duration(self, duration: float) -> 'FrameBuilder':
        """Set frame duration."""
        self.duration = duration
        return self
    
    def set_frame_number(self, frame_number: int) -> 'FrameBuilder':
        """Set frame number."""
        self.frame_number = frame_number
        return self
    
    def add_pixel(self, pixel_uuid: str) -> 'FrameBuilder':
        """Add an active pixel."""
        self.active_pixels.append(pixel_uuid)
        return self
    
    def set_active_pixels(self, pixel_uuids: List[str]) -> 'FrameBuilder':
        """Set the active pixel list."""
        self.active_pixels = pixel_uuids.copy()
        return self
    
    def set_metadata(self, key: str, value: Any) -> 'FrameBuilder':
        """Set metadata value."""
        self.metadata[key] = value
        return self
    
    def build(self) -> AnimationFrame:
        """Build and return the AnimationFrame."""
        frame = AnimationFrame(self.duration, self.frame_number)
        frame.set_active_pixels(self.active_pixels)
        frame.metadata = self.metadata.copy()
        return frame
