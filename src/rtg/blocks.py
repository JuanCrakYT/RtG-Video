"""
RtG block definitions and data structures.

Represents the basic building blocks used in RtG builds.
Every block is a tuple: [TipoDelBloque, Conexiones, Propiedades]
"""

from typing import List, Dict, Any, Optional
from .cframe import CFrame


class RtGBlock:
    """
    Represents a single RtG block.
    
    Internal structure: [TipoDelBloque, Conexiones, Propiedades]
    """
    
    def __init__(
        self,
        block_type: str,
        connections: List[List[Any]] = None,
        properties: Dict[str, Any] = None
    ):
        """
        Initialize an RtG block.
        
        Args:
            block_type: Type identifier (e.g., "Base", "Part", "Servo")
            connections: List of connections to parent blocks
            properties: Dictionary of block properties
        """
        self.block_type = block_type
        self.connections = connections or []
        self.properties = properties or {}
    
    def to_json(self) -> List[Any]:
        """
        Convert block to JSON format for RtG.
        
        Returns:
            List: [TipoDelBloque, Conexiones, Propiedades]
        """
        return [self.block_type, self.connections, self.properties]
    
    def add_connection(
        self,
        connection_type: str,
        point_id: str,
        parent_index: int
    ) -> None:
        """
        Add a connection to a parent block.
        
        Args:
            connection_type: TipoLocal (typically "1")
            point_id: Point ID or UUID on parent
            parent_index: Index of parent block in main array
        """
        self.connections.append([connection_type, point_id, parent_index])
    
    def set_property(self, key: str, value: Any) -> None:
        """
        Set a block property.
        
        Args:
            key: Property name
            value: Property value
        """
        self.properties[key] = value
    
    def set_rgb(self, r: int, g: int, b: int) -> None:
        """
        Set the RGB color of the block.
        
        Args:
            r, g, b: Color values 0-255
        """
        self.properties["RGB"] = [r, g, b]
    
    def add_ephemeral_attachment(
        self,
        uuid: str,
        part_name: str,
        cframe: CFrame
    ) -> None:
        """
        Add an EphemeralAttachment to this block.
        
        Args:
            uuid: Unique identifier for the attachment
            part_name: Name of the part (e.g., "Base", "Part")
            cframe: The CFrame transformation
        """
        if "EphemeralAttachments" not in self.properties:
            self.properties["EphemeralAttachments"] = {}
        
        self.properties["EphemeralAttachments"][uuid] = {
            "partName": part_name,
            "cframe": cframe.to_list()
        }


class RtGBuild:
    """
    Represents a complete RtG build.
    
    A build is a list of blocks where the first block is typically "Base".
    """
    
    def __init__(self):
        """Initialize an empty build."""
        self.blocks: List[RtGBlock] = []
        self._index_map: Dict[str, int] = {}  # Optional: map identifiers to indices
    
    def add_block(self, block: RtGBlock) -> int:
        """
        Add a block to the build.
        
        Args:
            block: The RtGBlock to add
            
        Returns:
            int: The index of the newly added block
        """
        index = len(self.blocks)
        self.blocks.append(block)
        return index
    
    def get_block(self, index: int) -> Optional[RtGBlock]:
        """
        Get a block by index.
        
        Args:
            index: The block index
            
        Returns:
            RtGBlock or None if index out of range
        """
        if 0 <= index < len(self.blocks):
            return self.blocks[index]
        return None
    
    def to_json(self) -> List[List[Any]]:
        """
        Convert build to JSON format.
        
        Returns:
            List: Array of [TipoDelBloque, Conexiones, Propiedades] tuples
        """
        return [block.to_json() for block in self.blocks]
    
    def create_base(self) -> int:
        """
        Create and add a Base block.
        
        Returns:
            int: Index of the Base block (should be 0)
        """
        base = RtGBlock("Base")
        return self.add_block(base)
    
    def __len__(self) -> int:
        """Get the number of blocks in the build."""
        return len(self.blocks)
    
    def __getitem__(self, index: int) -> RtGBlock:
        """Get a block by index using array notation."""
        return self.blocks[index]


# Helper functions

def create_part(rgb: List[int] = None) -> RtGBlock:
    """Create a Part block with optional color."""
    block = RtGBlock("Part")
    if rgb:
        block.set_rgb(*rgb)
    return block


def create_servo() -> RtGBlock:
    """Create a Servo block."""
    return RtGBlock("Servo")


def create_connector() -> RtGBlock:
    """Create a Connector block."""
    return RtGBlock("Connector")


def create_connector_ball() -> RtGBlock:
    """Create a ConnectorBall block."""
    return RtGBlock("ConnectorBall")
