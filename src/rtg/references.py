"""
Reference system for RtG Display.

Handles connections between blocks using the documented RtG reference format.
References can be made via direct indices or via UUID + EphemeralAttachment.
"""

from typing import Tuple, Optional
from .blocks import RtGBlock, RtGBuild
from .cframe import CFrame
from .uuid import get_uuid_manager


class Reference:
    """
    Represents a reference from one block to another.
    
    Can be either:
    1. Direct index reference: connects to parent at specific point
    2. UUID reference: connects via EphemeralAttachment spatial transformation
    """
    
    def __init__(
        self,
        connection_type: str = "1",
        point_id: Optional[str] = None,
        parent_index: Optional[int] = None
    ):
        """
        Initialize a reference.
        
        Args:
            connection_type: TipoLocal (typically "1" for standard)
            point_id: Point ID on parent (numeric string) or UUID (string with braces)
            parent_index: Index of parent block
        """
        self.connection_type = connection_type
        self.point_id = point_id or "1"
        self.parent_index = parent_index or 0
    
    def to_json(self) -> list:
        """Convert reference to JSON format."""
        return [self.connection_type, self.point_id, self.parent_index]


class ReferenceManager:
    """
    Manages the creation and validation of references between blocks.
    """
    
    @staticmethod
    def create_direct_reference(
        child_block: RtGBlock,
        parent_index: int,
        point_id: str = "1",
        connection_type: str = "1"
    ) -> None:
        """
        Create a direct reference from child to parent by index.
        
        Args:
            child_block: The child block
            parent_index: Index of parent block
            point_id: Point ID on parent (default "1")
            connection_type: Connection type (default "1")
        """
        child_block.add_connection(connection_type, point_id, parent_index)
    
    @staticmethod
    def create_uuid_reference(
        child_block: RtGBlock,
        parent_block: RtGBlock,
        parent_index: int,
        uuid: str,
        cframe: CFrame,
        connection_type: str = "1"
    ) -> None:
        """
        Create a UUID-based reference with spatial attachment.
        
        This allows specifying exact 3D positioning via CFrame.
        
        Args:
            child_block: The child block
            parent_block: The parent block (to receive attachment)
            parent_index: Index of parent block
            uuid: The UUID for this attachment
            cframe: The CFrame transformation
            connection_type: Connection type (default "1")
        """
        from .uuid import get_uuid_manager
        
        # Validate and register UUID
        uuid_manager = get_uuid_manager()
        if not uuid_manager.validate(uuid):
            raise ValueError(f"Invalid UUID format: {uuid}")
        
        uuid_manager.register(uuid)
        
        # Add attachment to parent block
        parent_block.add_ephemeral_attachment(uuid, "Base", cframe)
        
        # Add connection to child block referencing the UUID
        child_block.add_connection(connection_type, uuid, parent_index)
    
    @staticmethod
    def connect_pixel_to_base(
        pixel_block: RtGBlock,
        base_block: RtGBlock,
        base_index: int,
        x: int,
        y: int,
        spacing: float = 4.0
    ) -> str:
        """
        Connect a pixel block to the Base using UUID + CFrame positioning.
        
        Args:
            pixel_block: The pixel block to connect
            base_block: The Base block
            base_index: Index of Base block
            x: Grid X position
            y: Grid Y position
            spacing: Pixel spacing in RtG units
            
        Returns:
            str: The UUID used for this reference
        """
        from .cframe import create_pixel_offset_cframe
        
        uuid_manager = get_uuid_manager()
        
        # Generate and register UUID
        pixel_uuid = uuid_manager.generate_and_register((x, y))
        
        # Create positioning CFrame
        cframe = create_pixel_offset_cframe(x, y, spacing)
        
        # Create the reference
        ReferenceManager.create_uuid_reference(
            pixel_block,
            base_block,
            base_index,
            pixel_uuid,
            cframe
        )
        
        return pixel_uuid


def validate_references(build: RtGBuild) -> Tuple[bool, list]:
    """
    Validate all references in a build.
    
    Args:
        build: The RtGBuild to validate
        
    Returns:
        Tuple[bool, list]: (is_valid, list_of_errors)
    """
    errors = []
    
    for idx, block in enumerate(build.blocks):
        for conn_idx, connection in enumerate(block.connections):
            if len(connection) != 3:
                errors.append(f"Block {idx} connection {conn_idx}: Invalid length")
                continue
            
            connection_type, point_id, parent_index = connection
            
            # Validate parent index
            if not isinstance(parent_index, int):
                errors.append(
                    f"Block {idx} connection {conn_idx}: "
                    f"parent_index must be int, got {type(parent_index)}"
                )
            elif parent_index < 0 or parent_index >= len(build.blocks):
                errors.append(
                    f"Block {idx} connection {conn_idx}: "
                    f"parent_index {parent_index} out of range [0, {len(build.blocks)-1}]"
                )
            
            # Validate connection type
            if not isinstance(connection_type, str):
                errors.append(
                    f"Block {idx} connection {conn_idx}: "
                    f"connection_type must be string"
                )
            
            # Validate point_id
            if not isinstance(point_id, str):
                errors.append(
                    f"Block {idx} connection {conn_idx}: "
                    f"point_id must be string"
                )
    
    return (len(errors) == 0, errors)
