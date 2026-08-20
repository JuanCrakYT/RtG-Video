"""
RtG export functionality.

Handles exporting displays and animations to JSON formats compatible with RtG.
"""

import json
from typing import Dict, Any, List, Optional
from ..rtg.blocks import RtGBuild
from ..rtg.format import build_to_json_compact, save_build
from ..display.matrix import DisplayMatrix
from ..animation.sequence import AnimationSequence


class RtGExporter:
    """
    Exports DisplayMatrix to RtG JSON format.
    """
    
    @staticmethod
    def export_display(matrix: DisplayMatrix, compact: bool = False) -> str:
        """
        Export display matrix to RtG JSON format.
        
        Args:
            matrix: The DisplayMatrix to export
            compact: If True, use compact JSON format
            
        Returns:
            str: JSON string of the display
        """
        if compact:
            return build_to_json_compact(matrix.build)
        else:
            from ..rtg.format import build_to_json_string
            return build_to_json_string(matrix.build)
    
    @staticmethod
    def save_display(
        matrix: DisplayMatrix,
        filepath: str,
        compact: bool = False
    ) -> None:
        """
        Save display to a JSON file.
        
        Args:
            matrix: The DisplayMatrix to export
            filepath: Path to save file
            compact: If True, use compact JSON format
        """
        save_build(matrix.build, filepath, compact)
    
    @staticmethod
    def get_export_info(matrix: DisplayMatrix) -> Dict[str, Any]:
        """
        Get information about the display export.
        
        Args:
            matrix: The DisplayMatrix
            
        Returns:
            Dict: Export information and statistics
        """
        stats = matrix.get_stats()
        return {
            "type": "display",
            "width": stats["width"],
            "height": stats["height"],
            "total_pixels": stats["total_pixels"],
            "active_pixels": stats["active_pixels"],
            "total_blocks": stats["total_blocks"]
        }

    @staticmethod
    def export_physical_canvas(
        matrix: DisplayMatrix,
        output_dir: str,
        compact: bool = False,
    ) -> Dict[str, str]:
        """Export one synchronized physical-canvas generation."""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for filename in (
            "display.json",
            "info.json",
            "animation.json",
            "demo_display.json",
            "demo_info.json",
            "demo_animation.json",
        ):
            generated_file = output_path / filename
            if generated_file.exists():
                generated_file.unlink()

        display_path = output_path / "display.json"
        info_path = output_path / "info.json"
        RtGExporter.save_display(matrix, str(display_path), compact)

        info_data = {"display": RtGExporter.get_export_info(matrix)}
        with info_path.open("w", encoding="utf-8") as info_file:
            json.dump(info_data, info_file, indent=2)

        return {
            "display": str(display_path),
            "info": str(info_path),
        }


class AnimationExporter:
    """
    Exports AnimationSequence to RtG control format.
    """
    
    @staticmethod
    def export_animation(
        sequence: AnimationSequence,
        compact: bool = False
    ) -> str:
        """
        Export animation sequence to JSON format.
        
        Args:
            sequence: The AnimationSequence to export
            compact: If True, use compact JSON format
            
        Returns:
            str: JSON string of the animation control
        """
        animation_data = AnimationExporter._build_animation_data(sequence)
        
        if compact:
            return json.dumps(animation_data, separators=(',', ':'))
        else:
            return json.dumps(animation_data, indent=2)
    
    @staticmethod
    def _build_animation_data(sequence: AnimationSequence) -> Dict[str, Any]:
        """Build animation data structure."""
        frames = []
        
        for frame in sequence.frames:
            frames.append({
                "duration": frame.duration,
                "activePixels": frame.get_active_pixels(),
                "pixelColors": frame.get_pixel_colors(),
            })
        
        return {
            "frames": frames,
            "totalDuration": sequence.get_total_duration(),
            "frameCount": sequence.get_frame_count()
        }
    
    @staticmethod
    def save_animation(
        sequence: AnimationSequence,
        filepath: str,
        compact: bool = False
    ) -> None:
        """
        Save animation to a JSON file.
        
        Args:
            sequence: The AnimationSequence to export
            filepath: Path to save file
            compact: If True, use compact JSON format
        """
        animation_json = AnimationExporter.export_animation(sequence, compact)
        
        with open(filepath, 'w') as f:
            f.write(animation_json)
    
    @staticmethod
    def get_animation_info(sequence: AnimationSequence) -> Dict[str, Any]:
        """
        Get information about the animation export.
        
        Args:
            sequence: The AnimationSequence
            
        Returns:
            Dict: Animation information and statistics
        """
        pixel_stats = sequence.get_pixel_statistics()
        
        return {
            "type": "animation",
            "frameCount": sequence.get_frame_count(),
            "totalDuration": sequence.get_total_duration(),
            "pixelCount": len(pixel_stats),
            "averageActivePerFrame": (
                sum(f.count_active() for f in sequence.frames) / 
                max(1, sequence.get_frame_count())
            )
        }


class CombinedExporter:
    """
    Exports both display and animation as a complete package.
    """
    
    @staticmethod
    def export_complete(
        matrix: DisplayMatrix,
        sequence: AnimationSequence,
        output_dir: str,
        compact: bool = False
    ) -> Dict[str, str]:
        """
        Export display and animation as a complete package.
        
        Args:
            matrix: The DisplayMatrix
            sequence: The AnimationSequence
            output_dir: Directory to save files to
            compact: If True, use compact JSON format
            
        Returns:
            Dict: Mapping of 'display', 'animation', 'info' to file paths
        """
        import os
        from pathlib import Path
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Export display
        display_path = os.path.join(output_dir, "display.json")
        RtGExporter.save_display(matrix, display_path, compact)
        
        # Export animation
        animation_path = os.path.join(output_dir, "animation.json")
        AnimationExporter.save_animation(sequence, animation_path, compact)
        
        # Export info
        info_data = {
            "display": RtGExporter.get_export_info(matrix),
            "animation": AnimationExporter.get_animation_info(sequence)
        }
        info_path = os.path.join(output_dir, "info.json")
        with open(info_path, 'w') as f:
            json.dump(info_data, f, indent=2)
        
        return {
            "display": display_path,
            "animation": animation_path,
            "info": info_path
        }
