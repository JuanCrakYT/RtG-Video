"""Video analysis and the serializable RtG signal plan.

This module deliberately contains no ``RtGBuild`` objects. Analysis owns the
temporal data, required Gate-OR tree, and every logical Wire endpoint. The
build phase only assigns symbolic nodes to existing RtG blocks.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple
import json

from .processing import BLACK, analyze_pixel_states, analyze_video_colors


RGBColor = Tuple[int, int, int]
DELAYER_OUTPUT_POINT = "1"
# A Wire reaches a Delayer at point 1.  The Delayer's own parent reference to
# that Wire uses point 4; those are different sides of the relationship.
DELAYER_INPUT_POINT = "1"
GATE_OR_OUTPUT_POINT = "1"
GATE_OR_INPUT_A_POINT = "2"
GATE_OR_INPUT_B_POINT = "3"
SPLITTER_3_INPUT_POINT = "3"


class ConnectionPlanError(ValueError):
    """Raised before build creation when the planned topology is invalid."""

    def __init__(self, component, connection_point, expected_target, actual_target, reason):
        self.component = component
        self.connection_point = connection_point
        self.expected_target = expected_target
        self.actual_target = actual_target
        self.reason = reason
        super().__init__(
            "[CONNECTION ERROR]\n"
            f"Component: {component}\n"
            f"Connection point: {connection_point}\n"
            f"Expected target: {expected_target}\n"
            f"Actual target: {actual_target}\n"
            f"Reason: {reason}"
        )


@dataclass(frozen=True)
class ColorFrameUsage:
    color: RGBColor
    position: Tuple[int, int]
    frames: List[int]
    frame_count: int
    gate_or_needed: int


@dataclass(frozen=True)
class PixelColorAnalysis:
    position: Tuple[int, int]
    color_usages: List[ColorFrameUsage]
    total_gate_ors: int


@dataclass(frozen=True)
class PlannedFrame:
    """One decoded frame with its own, non-accumulated Delayer duration."""

    index: int
    duration: float
    active_layers: List[str]
    is_black: bool
    included_in_build: bool


@dataclass(frozen=True)
class PixelLayerPlan:
    """One physical colour layer and all frames that activate it."""

    id: str
    position: Tuple[int, int]
    color: RGBColor
    frame_indices: List[int]
    splitter_input_point: str = SPLITTER_3_INPUT_POINT


@dataclass(frozen=True)
class GateORPlan:
    id: str
    input_a: str
    input_b: str


@dataclass(frozen=True)
class PlannedWire:
    """A resolved Wire whose symbolic endpoints are known before build."""

    id: str
    source_node: str
    source_point: str
    target_node: str
    target_point: str
    frame_index: int
    purpose: str


@dataclass
class VideoAnalysisResult:
    """The complete intermediate artifact needed to build without re-analysis."""

    width: int
    height: int
    total_frames: int
    frame_duration: float
    frame_durations: List[float]
    unique_colors: List[RGBColor]
    color_totals: Dict[RGBColor, int]
    pixel_analyses: List[PixelColorAnalysis]
    total_gate_ors_needed: int
    max_gate_ors_per_pixel: int
    frames: List[PlannedFrame] = field(default_factory=list)
    pixel_layers: List[PixelLayerPlan] = field(default_factory=list)
    gate_ors: List[GateORPlan] = field(default_factory=list)
    wires: List[PlannedWire] = field(default_factory=list)
    start_target: Optional[str] = None

    @property
    def included_frame_indices(self) -> List[int]:
        return [frame.index for frame in self.frames if frame.included_in_build]


def _layer_id(position: Tuple[int, int], color: RGBColor) -> str:
    x, y = position
    r, g, b = color
    return f"pixel:{x}:{y}:{r},{g},{b}"


def _delayer_id(frame_index: int) -> str:
    return f"delayer:{frame_index}"


def _normalise_duration_list(frame_count, frame_duration, frame_durations) -> List[float]:
    if frame_durations is None:
        frame_durations = [0.0 if frame_duration is None else float(frame_duration)] * frame_count
    if len(frame_durations) != frame_count:
        raise ValueError(
            "frame_durations must contain exactly one duration per decoded frame "
            f"(expected {frame_count}, got {len(frame_durations)})"
        )
    values = [float(duration) for duration in frame_durations]
    if any(duration < 0 for duration in values):
        raise ValueError("Frame durations must be non-negative")
    return values


def _validate_color_frames(color_frames, width, height) -> None:
    if not color_frames:
        raise ValueError("Video contains no analyzed frames")
    for frame_index, frame in enumerate(color_frames):
        if len(frame) != height:
            raise ValueError(f"Frame {frame_index} has {len(frame)} rows; expected {height}")
        for row_index, row in enumerate(frame):
            if len(row) != width:
                raise ValueError(
                    f"Frame {frame_index}, row {row_index} has {len(row)} pixels; expected {width}"
                )
            for color in row:
                if len(color) != 3 or any(not isinstance(channel, int) for channel in color):
                    raise ValueError(
                        f"Frame {frame_index}, row {row_index} has invalid RGB color {color!r}"
                    )


def _build_or_tree(layer: PixelLayerPlan, gates: List[GateORPlan], wires: List[PlannedWire]) -> None:
    """Append the minimal balanced OR tree for one visible colour layer."""

    sources = [(_delayer_id(index), index) for index in layer.frame_indices]

    def make_node(nodes):
        if len(nodes) == 1:
            return nodes[0]
        middle = len(nodes) // 2
        left_id, left_frame = make_node(nodes[:middle])
        right_id, right_frame = make_node(nodes[middle:])
        gate_id = f"gate:{len(gates)}"
        gates.append(GateORPlan(gate_id, left_id, right_id))
        wires.append(PlannedWire(
            f"wire:{len(wires)}", left_id,
            DELAYER_OUTPUT_POINT if left_id.startswith("delayer:") else GATE_OR_OUTPUT_POINT,
            gate_id, GATE_OR_INPUT_A_POINT, left_frame, "pixel-signal",
        ))
        wires.append(PlannedWire(
            f"wire:{len(wires)}", right_id,
            DELAYER_OUTPUT_POINT if right_id.startswith("delayer:") else GATE_OR_OUTPUT_POINT,
            gate_id, GATE_OR_INPUT_B_POINT, right_frame, "pixel-signal",
        ))
        return gate_id, max(left_frame, right_frame)

    root_id, root_frame = make_node(sources)
    wires.append(PlannedWire(
        f"wire:{len(wires)}", root_id,
        DELAYER_OUTPUT_POINT if root_id.startswith("delayer:") else GATE_OR_OUTPUT_POINT,
        layer.id, layer.splitter_input_point, root_frame, "pixel-signal",
    ))


def _validate_signal_plan(analysis: VideoAnalysisResult) -> None:
    """Validate every symbolic endpoint before generation begins."""

    frame_ids = {_delayer_id(frame.index) for frame in analysis.frames if frame.included_in_build}
    layer_ids = {layer.id for layer in analysis.pixel_layers}
    gate_ids = {gate.id for gate in analysis.gate_ors}
    known = frame_ids | layer_ids | gate_ids
    included_indexes = set(analysis.included_frame_indices)
    if analysis.start_target is not None and analysis.start_target not in frame_ids:
        raise ConnectionPlanError("Button", "1", "first included Delayer", str(analysis.start_target), "Button target is absent from the timeline.")

    incoming = {}
    outgoing = {}
    for wire in analysis.wires:
        if wire.source_node not in known:
            raise ConnectionPlanError("Wire", "source", "known node", wire.source_node, "Unknown source node.")
        if wire.target_node not in known:
            raise ConnectionPlanError("Wire", "target", "known node", wire.target_node, "Unknown target node.")
        if wire.source_node == wire.target_node:
            raise ConnectionPlanError("Wire", "source/target", "different nodes", wire.source_node, "A Wire cannot connect a node to itself.")
        if wire.frame_index not in included_indexes:
            raise ConnectionPlanError("Wire", "frame", "included frame", str(wire.frame_index), "Wire is scheduled outside the build timeline.")

        expected_source = DELAYER_OUTPUT_POINT if wire.source_node.startswith("delayer:") else GATE_OR_OUTPUT_POINT
        if not wire.source_node.startswith(("delayer:", "gate:")):
            raise ConnectionPlanError("Wire", "source", "Delayer or Gate-OR", wire.source_node, "Pixel layers cannot drive a signal.")
        if wire.source_point != expected_source:
            raise ConnectionPlanError("Wire", "source point", expected_source, wire.source_point, "Invalid output point.")

        if wire.target_node.startswith("delayer:"):
            target_ok = wire.target_point == DELAYER_INPUT_POINT
            expected_target = DELAYER_INPUT_POINT
        elif wire.target_node.startswith("gate:"):
            target_ok = wire.target_point in {GATE_OR_INPUT_A_POINT, GATE_OR_INPUT_B_POINT}
            expected_target = "2 or 3"
        else:
            target_ok = wire.target_point == SPLITTER_3_INPUT_POINT
            expected_target = SPLITTER_3_INPUT_POINT
        if not target_ok:
            raise ConnectionPlanError("Wire", "target point", expected_target, wire.target_point, "Invalid input point.")

        key = (wire.target_node, wire.target_point)
        if key in incoming:
            raise ConnectionPlanError("Wire", "target", f"one Wire at {key[0]} point {key[1]}", wire.id, f"Already occupied by {incoming[key].id}.")
        incoming[key] = wire
        outgoing.setdefault((wire.source_node, wire.source_point), []).append(wire)

    for gate in analysis.gate_ors:
        for point in (GATE_OR_INPUT_A_POINT, GATE_OR_INPUT_B_POINT):
            if (gate.id, point) not in incoming:
                raise ConnectionPlanError("Gate-OR", point, "one input Wire", "none", f"{gate.id} is incomplete.")
        count = len(outgoing.get((gate.id, GATE_OR_OUTPUT_POINT), []))
        if count != 1:
            raise ConnectionPlanError("Gate-OR", GATE_OR_OUTPUT_POINT, "one output Wire", str(count), f"{gate.id} must have one output.")

    for layer in analysis.pixel_layers:
        if not layer.frame_indices:
            raise ConnectionPlanError("Splitter_3", layer.splitter_input_point, "active frames", "none", "Unused physical colour layer.")
        if (layer.id, layer.splitter_input_point) not in incoming:
            raise ConnectionPlanError("Splitter_3", layer.splitter_input_point, "one signal Wire", "none", f"{layer.id} has no signal source.")

    expected_gate_count = sum(max(0, len(layer.frame_indices) - 1) for layer in analysis.pixel_layers)
    if len(analysis.gate_ors) != expected_gate_count:
        raise ConnectionPlanError("Gate-OR", "count", str(expected_gate_count), str(len(analysis.gate_ors)), "Plan does not use the minimal OR count.")

    included = analysis.included_frame_indices
    if included:
        if analysis.start_target != _delayer_id(included[0]):
            raise ConnectionPlanError("Button", "1", _delayer_id(included[0]), str(analysis.start_target), "Button must start the first Delayer.")
        for previous, current in zip(included, included[1:]):
            matches = [wire for wire in analysis.wires if wire.purpose == "timeline" and wire.source_node == _delayer_id(previous) and wire.target_node == _delayer_id(current)]
            if len(matches) != 1:
                raise ConnectionPlanError("Delayer", DELAYER_OUTPUT_POINT, _delayer_id(current), str(matches), "Every frame must trigger the next Delayer exactly once.")


def analyze_color_frames(
    color_frames: Sequence[Sequence[Sequence[RGBColor]]],
    width: int,
    height: int,
    *,
    frame_duration: Optional[float] = None,
    frame_durations: Optional[Sequence[float]] = None,
) -> VideoAnalysisResult:
    """Plan all signal topology from quantized frames before physical creation."""

    _validate_color_frames(color_frames, width, height)
    durations = _normalise_duration_list(len(color_frames), frame_duration, frame_durations)
    pixel_states = analyze_pixel_states(color_frames)
    unique_colors: Set[RGBColor] = set()
    color_totals: Dict[RGBColor, int] = {}
    pixel_analyses: List[PixelColorAnalysis] = []
    candidates: List[PixelLayerPlan] = []

    for position, state in pixel_states.items():
        by_color: Dict[RGBColor, List[int]] = {}
        for frame_index, color in state["frames"].items():
            rgb = tuple(int(channel) for channel in color)
            if rgb != BLACK:
                by_color.setdefault(rgb, []).append(frame_index)
        usages = []
        for color, indexes in sorted(by_color.items()):
            indexes.sort()
            usage = ColorFrameUsage(color, position, indexes, len(indexes), max(0, len(indexes) - 1))
            usages.append(usage)
            candidates.append(PixelLayerPlan(_layer_id(position, color), position, color, indexes))
            unique_colors.add(color)
            color_totals[color] = color_totals.get(color, 0) + len(indexes)
        if usages:
            pixel_analyses.append(PixelColorAnalysis(position, usages, sum(item.gate_or_needed for item in usages)))

    pixel_analyses.sort(key=lambda item: (item.position[1], item.position[0]))
    candidates.sort(key=lambda item: (item.position[1], item.position[0], item.color))
    trailing_black = all(tuple(color) == BLACK for row in color_frames[-1] for color in row)
    included_indexes = list(range(len(color_frames) - (1 if trailing_black else 0)))
    included_set = set(included_indexes)
    layers = [
        PixelLayerPlan(layer.id, layer.position, layer.color, [index for index in layer.frame_indices if index in included_set], layer.splitter_input_point)
        for layer in candidates
        if any(index in included_set for index in layer.frame_indices)
    ]
    active_by_frame = {index: [] for index in range(len(color_frames))}
    for layer in layers:
        for index in layer.frame_indices:
            active_by_frame[index].append(layer.id)
    frames = [
        PlannedFrame(index, durations[index], sorted(active_by_frame[index]), not active_by_frame[index], index in included_set)
        for index in range(len(color_frames))
    ]

    gates: List[GateORPlan] = []
    wires: List[PlannedWire] = []
    for previous, current in zip(included_indexes, included_indexes[1:]):
        wires.append(PlannedWire(f"wire:{len(wires)}", _delayer_id(previous), DELAYER_OUTPUT_POINT, _delayer_id(current), DELAYER_INPUT_POINT, previous, "timeline"))
    for layer in layers:
        _build_or_tree(layer, gates, wires)

    result = VideoAnalysisResult(
        width, height, len(color_frames), durations[0], durations, sorted(unique_colors), color_totals,
        pixel_analyses, len(gates), max((item.total_gate_ors for item in pixel_analyses), default=0),
        frames, layers, gates, wires, _delayer_id(included_indexes[0]) if included_indexes else None,
    )
    _validate_signal_plan(result)
    return result


def analyze_video_with_gate_or_planning(
    video_path: str,
    width: int,
    height: int,
    palette: Sequence[RGBColor],
    color_frames: Optional[Sequence[Sequence[Sequence[RGBColor]]]] = None,
    frame_duration: Optional[float] = None,
    frame_durations: Optional[Sequence[float]] = None,
) -> VideoAnalysisResult:
    """Decode/quantize once, then return its fully verified logical plan."""

    if color_frames is None:
        detected_duration, color_frames = analyze_video_colors(video_path, width, height, palette)
        if frame_duration is None and frame_durations is None:
            frame_duration = detected_duration
    return analyze_color_frames(color_frames, width, height, frame_duration=frame_duration, frame_durations=frame_durations)


def _wire_to_dict(wire: PlannedWire) -> Dict[str, object]:
    return {
        "id": wire.id,
        "source": {"node": wire.source_node, "point": wire.source_point},
        "target": {"node": wire.target_node, "point": wire.target_point},
        "frame_index": wire.frame_index,
        "purpose": wire.purpose,
    }


def build_gate_or_table_report(analysis: VideoAnalysisResult) -> Dict[str, object]:
    """Return the data.json-compatible intermediate artifact."""

    return {
        "schema": "rtg-video.analysis/v1",
        "video_info": {
            "width": analysis.width,
            "height": analysis.height,
            "total_frames": analysis.total_frames,
            "frame_duration": analysis.frame_duration,
            "frame_durations": analysis.frame_durations,
        },
        "unique_colors": [list(color) for color in analysis.unique_colors],
        "color_totals": {str(color): total for color, total in analysis.color_totals.items()},
        "total_gate_ors_needed": analysis.total_gate_ors_needed,
        "max_gate_ors_per_pixel": analysis.max_gate_ors_per_pixel,
        "pixels": [
            {
                "position": list(pixel.position),
                "total_gate_ors": pixel.total_gate_ors,
                "colors": [
                    {"color": list(usage.color), "frames": usage.frames, "frame_count": usage.frame_count, "gate_or_needed": usage.gate_or_needed, "gate_or_table_size": usage.gate_or_needed}
                    for usage in pixel.color_usages
                ],
            }
            for pixel in analysis.pixel_analyses
        ],
        "signal_plan": {
            "button": {"target": analysis.start_target, "point": "2"},
            "frames": [
                {"index": frame.index, "duration": frame.duration, "active_layers": frame.active_layers, "is_black": frame.is_black, "included_in_build": frame.included_in_build}
                for frame in analysis.frames
            ],
            "pixel_layers": [
                {"id": layer.id, "position": list(layer.position), "color": list(layer.color), "frame_indices": layer.frame_indices, "splitter_input_point": layer.splitter_input_point}
                for layer in analysis.pixel_layers
            ],
            "gate_ors": [{"id": gate.id, "input_a": gate.input_a, "input_b": gate.input_b} for gate in analysis.gate_ors],
            "wires": [_wire_to_dict(wire) for wire in analysis.wires],
        },
    }


def export_analysis_json(analysis: VideoAnalysisResult, output_path: str) -> None:
    """Write analysis before any physical build is created."""

    _validate_signal_plan(analysis)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_gate_or_table_report(analysis), indent=2), encoding="utf-8")
