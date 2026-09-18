"""Video color analysis with Gate-OR table planning."""

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence, Tuple, Set

from .processing import BLACK, analyze_video_colors, analyze_pixel_states


RGBColor = Tuple[int, int, int]


@dataclass
class ColorFrameUsage:
    """Frame usage information for a specific color at a specific position."""
    color: RGBColor
    position: Tuple[int, int]
    frames: List[int]
    frame_count: int
    gate_or_needed: int  # N-1 for N frames


@dataclass
class PixelColorAnalysis:
    """Complete analysis for one pixel position across all its colors."""
    position: Tuple[int, int]
    color_usages: List[ColorFrameUsage]
    total_gate_ors: int


@dataclass
class VideoAnalysisResult:
    """Complete video analysis result with Gate-OR planning."""
    width: int
    height: int
    total_frames: int
    frame_duration: float
    unique_colors: List[RGBColor]
    color_totals: Dict[RGBColor, int]  # total appearances across all pixels/frames
    pixel_analyses: List[PixelColorAnalysis]
    total_gate_ors_needed: int
    max_gate_ors_per_pixel: int


def analyze_video_with_gate_or_planning(
    video_path: str,
    width: int,
    height: int,
    palette: Sequence[RGBColor],
) -> VideoAnalysisResult:
    """
    Analyze video and compute Gate-OR requirements per pixel per color.
    
    This does NOT generate the RtG build - it produces an analytical report
    showing exactly what Gate-OR tables are needed for each color at each position.
    """
    duration, color_frames = analyze_video_colors(video_path, width, height, palette)
    pixel_states = analyze_pixel_states(color_frames)
    
    # Gather all unique colors (excluding BLACK)
    unique_colors: Set[RGBColor] = set()
    color_totals: Dict[RGBColor, int] = {}
    
    pixel_analyses: List[PixelColorAnalysis] = []
    
    for position, state in pixel_states.items():
        x, y = position
        color_usages: List[ColorFrameUsage] = []
        
        # Group frames by color for this position
        color_to_frames: Dict[RGBColor, List[int]] = {}
        for frame_idx, color in state["frames"].items():
            if color == BLACK:
                continue
            color_to_frames.setdefault(color, []).append(frame_idx)
        
        for color, frame_indices in color_to_frames.items():
            frame_indices.sort()
            frame_count = len(frame_indices)
            gate_or_needed = max(0, frame_count - 1)
            
            color_usages.append(ColorFrameUsage(
                color=color,
                position=position,
                frames=frame_indices,
                frame_count=frame_count,
                gate_or_needed=gate_or_needed,
            ))
            
            unique_colors.add(color)
            color_totals[color] = color_totals.get(color, 0) + frame_count
        
        if color_usages:
            total_gate_ors = sum(cu.gate_or_needed for cu in color_usages)
            pixel_analyses.append(PixelColorAnalysis(
                position=position,
                color_usages=color_usages,
                total_gate_ors=total_gate_ors,
            ))
    
    # Sort by position for consistent output
    pixel_analyses.sort(key=lambda p: (p.position[1], p.position[0]))
    
    total_gate_ors = sum(p.total_gate_ors for p in pixel_analyses)
    max_per_pixel = max((p.total_gate_ors for p in pixel_analyses), default=0)
    
    return VideoAnalysisResult(
        width=width,
        height=height,
        total_frames=len(color_frames),
        frame_duration=duration,
        unique_colors=sorted(unique_colors),
        color_totals=color_totals,
        pixel_analyses=pixel_analyses,
        total_gate_ors_needed=total_gate_ors,
        max_gate_ors_per_pixel=max_per_pixel,
    )


def build_gate_or_table_report(analysis: VideoAnalysisResult) -> Dict:
    """Build a detailed Gate-OR table report for JSON export."""
    report = {
        "video_info": {
            "width": analysis.width,
            "height": analysis.height,
            "total_frames": analysis.total_frames,
            "frame_duration": analysis.frame_duration,
        },
        "unique_colors": [list(c) for c in analysis.unique_colors],
        "color_totals": {str(k): v for k, v in analysis.color_totals.items()},
        "total_gate_ors_needed": analysis.total_gate_ors_needed,
        "max_gate_ors_per_pixel": analysis.max_gate_ors_per_pixel,
        "pixels": [],
    }
    
    for pixel in analysis.pixel_analyses:
        pixel_data = {
            "position": list(pixel.position),
            "total_gate_ors": pixel.total_gate_ors,
            "colors": [],
        }
        for usage in pixel.color_usages:
            pixel_data["colors"].append({
                "color": list(usage.color),
                "frames": usage.frames,
                "frame_count": usage.frame_count,
                "gate_or_needed": usage.gate_or_needed,
                "gate_or_table_size": usage.gate_or_needed,  # N-1
            })
        report["pixels"].append(pixel_data)
    
    return report


def export_analysis_json(analysis: VideoAnalysisResult, output_path: str) -> None:
    """Export the analysis to a JSON file."""
    import json
    from pathlib import Path
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    report = build_gate_or_table_report(analysis)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)