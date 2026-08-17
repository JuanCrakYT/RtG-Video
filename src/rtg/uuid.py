"""
UUID management for RtG Display.

Handles generation, validation, and tracking of UUIDs for RtG builds.
UUIDs are used to reference EphemeralAttachments and spatial transformations.
"""

import uuid
import re
from typing import Dict, Set, Tuple, Optional


class UUIDManager:
    """
    Manages UUID generation and tracking for RtG display system.
    
    RtG requires UUIDs in format: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}
    """
    
    def __init__(self):
        """Initialize UUID manager with empty tracking maps."""
        self._generated_uuids: Set[str] = set()
        self._pixel_uuid_map: Dict[Tuple[int, int], str] = {}  # (x, y) -> UUID
        self._uuid_pixel_map: Dict[str, Tuple[int, int]] = {}  # UUID -> (x, y)
    
    @staticmethod
    def generate() -> str:
        """
        Generate a new UUID in RtG format.
        
        Returns:
            str: UUID in format {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}
        """
        new_uuid = uuid.uuid4()
        return "{" + str(new_uuid) + "}"
    
    @staticmethod
    def validate(uuid_str: str) -> bool:
        """
        Validate if a string is a properly formatted UUID.
        
        Args:
            uuid_str: The UUID string to validate
            
        Returns:
            bool: True if valid RtG UUID format, False otherwise
        """
        # Pattern: {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}
        pattern = r'^\{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\}$'
        return bool(re.match(pattern, uuid_str, re.IGNORECASE))
    
    def register(self, uuid_str: str, pixel_pos: Tuple[int, int] = None) -> bool:
        """
        Register a UUID in the tracking system.
        
        Args:
            uuid_str: The UUID to register
            pixel_pos: Optional (x, y) position for pixel tracking
            
        Returns:
            bool: True if registered successfully, False if already exists
            
        Raises:
            ValueError: If UUID format is invalid
        """
        if not self.validate(uuid_str):
            raise ValueError(f"Invalid UUID format: {uuid_str}")
        
        if uuid_str in self._generated_uuids:
            return False
        
        self._generated_uuids.add(uuid_str)
        
        if pixel_pos is not None:
            self._pixel_uuid_map[pixel_pos] = uuid_str
            self._uuid_pixel_map[uuid_str] = pixel_pos
        
        return True
    
    def generate_and_register(self, pixel_pos: Tuple[int, int] = None) -> str:
        """
        Generate a new UUID and register it.
        
        Args:
            pixel_pos: Optional (x, y) position for pixel tracking
            
        Returns:
            str: The newly generated and registered UUID
        """
        new_uuid = self.generate()
        
        # Ensure uniqueness
        while new_uuid in self._generated_uuids:
            new_uuid = self.generate()
        
        self.register(new_uuid, pixel_pos)
        return new_uuid
    
    def get_pixel_uuid(self, x: int, y: int) -> Optional[str]:
        """
        Get the UUID assigned to a pixel position.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            str: The UUID, or None if not found
        """
        return self._pixel_uuid_map.get((x, y))
    
    def get_pixel_position(self, uuid_str: str) -> Tuple[int, int]:
        """
        Get the pixel position for a UUID.
        
        Args:
            uuid_str: The UUID to look up
            
        Returns:
            Tuple[int, int]: The (x, y) position, or None if not found
        """
        return self._uuid_pixel_map.get(uuid_str)
    
    def has_uuid(self, uuid_str: str) -> bool:
        """
        Check if a UUID is registered.
        
        Args:
            uuid_str: The UUID to check
            
        Returns:
            bool: True if registered
        """
        return uuid_str in self._generated_uuids
    
    def get_all_uuids(self) -> Set[str]:
        """Get all registered UUIDs."""
        return self._generated_uuids.copy()
    
    def get_pixel_map(self) -> Dict[Tuple[int, int], str]:
        """Get the complete pixel position to UUID map."""
        return self._pixel_uuid_map.copy()


# Global instance
_global_uuid_manager = None


def get_uuid_manager() -> UUIDManager:
    """Get or create the global UUID manager instance."""
    global _global_uuid_manager
    if _global_uuid_manager is None:
        _global_uuid_manager = UUIDManager()
    return _global_uuid_manager


def reset_uuid_manager():
    """Reset the global UUID manager (useful for testing)."""
    global _global_uuid_manager
    _global_uuid_manager = UUIDManager()
