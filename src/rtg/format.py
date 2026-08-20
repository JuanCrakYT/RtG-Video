"""
RtG format utilities for JSON serialization and validation.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from .blocks import RtGBuild


class RtGJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles RtG-specific types."""
    
    def default(self, obj):
        """Encode RtG objects to JSON."""
        if isinstance(obj, RtGBuild):
            return obj.to_json()
        return super().default(obj)


def build_to_json_string(build: RtGBuild, indent: int = 2) -> str:
    """
    Convert an RtGBuild to formatted JSON string.
    
    Args:
        build: The RtGBuild to serialize
        indent: JSON indentation level
        
    Returns:
        str: The JSON string
    """
    return json.dumps(
        build.to_json(),
        cls=RtGJSONEncoder,
        indent=indent
    )


def build_to_json_compact(build: RtGBuild) -> str:
    """
    Convert an RtGBuild to compact JSON string (no whitespace).
    
    Args:
        build: The RtGBuild to serialize
        
    Returns:
        str: The compact JSON string
    """
    return json.dumps(build.to_json(), cls=RtGJSONEncoder, separators=(',', ':'))


def save_build(build: RtGBuild, filepath: str, compact: bool = False) -> None:
    """
    Save an RtGBuild to a JSON file.
    
    Args:
        build: The RtGBuild to save
        filepath: Path to save file
        compact: If True, use compact format; otherwise use formatted
    """
    if compact:
        json_str = build_to_json_compact(build)
    else:
        json_str = build_to_json_string(build)
    
    with open(filepath, 'w') as f:
        f.write(json_str)


def load_build(filepath: str) -> RtGBuild:
    """
    Load an RtGBuild from a JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        RtGBuild: The loaded build
    """
    from .blocks import RtGBlock
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    build = RtGBuild()
    
    for block_data in data:
        if len(block_data) != 3:
            raise ValueError(f"Invalid block format: {block_data}")
        
        block_type, connections, properties = block_data
        block = RtGBlock(block_type, connections, properties)
        build.add_block(block)
    
    return build


def validate_build_json(data: Any) -> Tuple[bool, Optional[str]]:
    """
    Validate that data is a valid RtG build JSON structure.
    
    Args:
        data: The data to validate (typically parsed JSON)
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message or None)
    """
    if not isinstance(data, list):
        return (False, "Root must be an array")
    
    for idx, block in enumerate(data):
        if not isinstance(block, list):
            return (False, f"Block {idx}: must be an array")
        
        if len(block) != 3:
            return (False, f"Block {idx}: must have 3 elements (type, connections, properties)")
        
        block_type, connections, properties = block
        
        # Validate block type
        if not isinstance(block_type, str):
            return (False, f"Block {idx}: type must be string")
        
        # Validate connections
        if not isinstance(connections, list):
            return (False, f"Block {idx}: connections must be array")
        
        for conn_idx, conn in enumerate(connections):
            if not isinstance(conn, list):
                return (False, f"Block {idx} connection {conn_idx}: must be array")
            
            if len(conn) != 3:
                return (False, f"Block {idx} connection {conn_idx}: must have 3 elements")
            
            conn_type, point_id, parent_idx = conn
            
            if not isinstance(conn_type, str):
                return (False, f"Block {idx} connection {conn_idx}: type must be string")
            
            if not isinstance(point_id, str):
                return (False, f"Block {idx} connection {conn_idx}: point_id must be string")
            
            if not isinstance(parent_idx, int):
                return (False, f"Block {idx} connection {conn_idx}: parent_index must be int")
            
            if parent_idx < 1 or parent_idx > len(data):
                return (False, f"Block {idx} connection {conn_idx}: parent_index out of range for 1-based RtG data")
        
        # Validate properties
        if not isinstance(properties, dict):
            return (False, f"Block {idx}: properties must be object")
    
    return (True, None)


def get_build_stats(build: RtGBuild) -> Dict[str, Any]:
    """
    Get statistics about a build.
    
    Args:
        build: The RtGBuild to analyze
        
    Returns:
        Dict: Statistics dictionary
    """
    block_types = {}
    total_connections = 0
    total_attachments = 0
    
    for block in build.blocks:
        # Count block types
        block_type = block.block_type
        block_types[block_type] = block_types.get(block_type, 0) + 1
        
        # Count connections
        total_connections += len(block.connections)
        
        # Count attachments
        if "EphemeralAttachments" in block.properties:
            total_attachments += len(block.properties["EphemeralAttachments"])
    
    return {
        "total_blocks": len(build.blocks),
        "block_types": block_types,
        "total_connections": total_connections,
        "total_attachments": total_attachments
    }


def load_pixel_template_from_file(filepath: str) -> 'RtGBuild':
    """
    Load a pixel template from a JSON file.
    
    Args:
        filepath: Path to pixel JSON file
        
    Returns:
        RtGBuild: The pixel template
    """
    return load_build(filepath)
