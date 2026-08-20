"""
Pixel template and instantiation for RtG Display.

Handles cloning complex pixel templates with index remapping.
"""

from copy import deepcopy
from typing import Dict, List, Tuple, Optional
from ..rtg.blocks import RtGBlock, RtGBuild, to_rtg_index
from ..rtg.cframe import CFrame
from ..rtg.uuid import get_uuid_manager


class Pixel:
    """
    Represents a single pixel instance in the display.
    
    A pixel is a collection of blocks (from a template) positioned at a grid location.
    """
    
    def __init__(
        self,
        x: int,
        y: int,
        blocks: List[RtGBlock],
        uuid: str,
        block_indices: Optional[Dict[int, int]] = None,
    ):
        """
        Initialize a pixel.
        
        Args:
            x: Grid X position
            y: Grid Y position
            blocks: List of RtGBlock instances for this pixel
            uuid: The unique identifier for this pixel
        """
        self.x = x
        self.y = y
        self.blocks = blocks
        self.uuid = uuid
        self.block_indices = block_indices or {}
        self.active = False  # Whether this pixel is currently "on"
    
    def activate(self) -> None:
        """Mark this pixel as active."""
        self.active = True
    
    def deactivate(self) -> None:
        """Mark this pixel as inactive."""
        self.active = False
    
    def set_active(self, active: bool) -> None:
        """Set the active state."""
        self.active = active
    
    def get_block_count(self) -> int:
        """Get the number of blocks in this pixel."""
        return len(self.blocks)

    def get_signal_endpoint(self) -> Tuple[int, str]:
        """Return the real Splitter_3 block and signal port for this pixel."""
        splitter_entries = [
            (template_index, global_index)
            for template_index, global_index in self.block_indices.items()
            if self.blocks[template_index].block_type == "Splitter_3"
        ]
        if len(splitter_entries) != 1:
            raise ValueError(
                f"Pixel {self.uuid} must contain exactly one Splitter_3, "
                f"found {len(splitter_entries)}"
            )

        template_index, global_index = splitter_entries[0]
        splitter = self.blocks[template_index]
        if not splitter.connections:
            raise ValueError(
                f"Pixel {self.uuid} Splitter_3 has no connections to resolve"
            )

        input_point = splitter.connections[0][0]
        if not isinstance(input_point, str):
            raise ValueError(
                f"Pixel {self.uuid} Splitter_3 input point must be numeric"
            )
        return global_index, input_point


class PixelTemplate:
    """
    Manages cloning of pixel templates with proper index remapping.
    
    When cloning a template, all internal references must be remapped
    to point to the new block indices in the target build.
    """
    
    def __init__(self, template_build: RtGBuild):
        """
        Initialize with a pixel template.
        
        Args:
            template_build: The RtGBuild containing the pixel template
        """
        self.template = template_build
    
    def _remap_reference(
        self,
        old_reference: List,
        index_mapping: Dict[int, int]
    ) -> List:
        """
        Remap a reference from template indices to new indices.
        
        Args:
            old_reference: Original [type, point_id, parent_index]
            index_mapping: Dict mapping old indices to new indices
            
        Returns:
            List: The remapped reference
        """
        if len(old_reference) != 3:
            return old_reference
        
        conn_type, point_id, parent_index = old_reference
        
        # Map the parent index to new location
        new_parent_index = index_mapping.get(parent_index, parent_index)
        
        return [conn_type, point_id, new_parent_index]
    
    def _remap_ephemeral_attachments(
        self,
        old_attachments: Dict,
        uuid_mapping: Dict[str, str]
    ) -> Dict:
        """
        Remap ephemeral attachment UUIDs.
        
        Args:
            old_attachments: Original attachments dict
            uuid_mapping: Dict mapping old UUIDs to new UUIDs
            
        Returns:
            Dict: The remapped attachments
        """
        new_attachments = {}
        
        for old_uuid, attachment in old_attachments.items():
            new_uuid = uuid_mapping.get(old_uuid, old_uuid)
            new_attachments[new_uuid] = attachment
        
        return new_attachments
    
    def create_pixel_instance(
        self,
        x: int,
        y: int,
        target_build: RtGBuild,
        base_index: int,
        spacing: float = 4.0
    ) -> Tuple[Pixel, Dict[int, int]]:
        """
        Create a pixel instance by cloning the template with remapped indices.
        
        Args:
            x: Grid X position
            y: Grid Y position
            target_build: The RtGBuild to add blocks to
            base_index: Index of the Base block in target_build
            spacing: Pixel spacing in RtG units
            
        Returns:
            Tuple[Pixel, Dict]: (Created pixel, index mapping old->new)
        """
        from ..rtg.cframe import create_pixel_offset_cframe
        
        uuid_manager = get_uuid_manager()
        
        # Generate unique UUID for this pixel
        pixel_uuid = uuid_manager.generate_and_register((x, y))
        
        # Template references are RtG indices (1-based), while the build list
        # is indexed by Python (0-based) internally.
        index_mapping = {
            old_idx + 1: to_rtg_index(len(target_build.blocks) + old_idx)
            for old_idx in range(len(self.template.blocks))
        }
        new_blocks = []
        uuid_mapping = {}
        
        # Clone each block from template
        for old_idx, template_block in enumerate(self.template.blocks):
            # Deep-copy properties so pixel instances never share nested data.
            new_block = RtGBlock(
                template_block.block_type,
                connections=[],  # Will be remapped
                properties=deepcopy(template_block.properties)
            )
            
            # Remap all connections
            for old_conn in template_block.connections:
                new_conn = self._remap_reference(old_conn, index_mapping)
                new_block.connections.append(new_conn)
            
            # Remap ephemeral attachments
            if "EphemeralAttachments" in new_block.properties:
                old_attachments = new_block.properties["EphemeralAttachments"]
                new_block.properties["EphemeralAttachments"] = \
                    self._remap_ephemeral_attachments(old_attachments, uuid_mapping)
            
            new_blocks.append(new_block)
        
        # Add all new blocks to target build
        for block in new_blocks:
            target_build.add_block(block)
        
        # Connect first block of pixel to Base using UUID + CFrame
        if len(new_blocks) > 0:
            first_block_index = len(target_build.blocks) - len(new_blocks)
            first_block = target_build.blocks[first_block_index]
            base_block = target_build.blocks[base_index]
            
            # Create positioning CFrame
            cframe = create_pixel_offset_cframe(x, y, spacing)
            
            # Add connection to Base using RtG's 1-based parent index.
            first_block.connections.append(["1", pixel_uuid, to_rtg_index(base_index)])
            
            # Add ephemeral attachment to Base
            if "EphemeralAttachments" not in base_block.properties:
                base_block.properties["EphemeralAttachments"] = {}
            
            base_block.properties["EphemeralAttachments"][pixel_uuid] = {
                "partName": "Base",
                "cframe": cframe.to_list()
            }
        
        # Create and return Pixel object
        pixel = Pixel(x, y, new_blocks, pixel_uuid, index_mapping)
        
        return pixel, index_mapping
