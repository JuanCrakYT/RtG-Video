# RtG Video

Animated display generator for **Road To Gramby's (Roblox)**. Generates physical pixel matrices that can display animations by controlling which pixels receive input signals.

## Overview

RtG Display is a Python application that:

1. **Generates pixel displays** - Creates 2D matrices of controllable pixels
2. **Manages animations** - Converts frame sequences into activation patterns
3. **Exports to RtG format** - Produces JSON files compatible with Road To Gramby's

Instead of creating a separate build for each animation frame, this system creates a single reusable display that activates/deactivates pixels over time through signal control.

## Project Structure

```
src/
├── rtg/                 # RtG format core
│   ├── uuid.py         # UUID generation and tracking
│   ├── cframe.py       # Coordinate frame transformations
│   ├── blocks.py       # RtG block definitions
│   ├── references.py   # Block reference system
│   └── format.py       # JSON serialization
│
├── display/            # Display system
│   ├── pixel.py        # Individual pixel structure
│   ├── matrix.py       # 2D pixel matrix
│   └── layout.py       # (planned) pixel layout templates
│
├── animation/          # Animation system
│   ├── frame.py        # Animation frame representation
│   ├── sequence.py     # Frame sequence management
│   └── timing.py       # (planned) timing utilities
│
├── video/              # Video processing
│   ├── decoder.py      # (planned) video decoding
│   ├── frames.py       # (planned) frame extraction
│   ├── resize.py       # (planned) image resizing
│   └── threshold.py    # (planned) binary conversion
│
└── export/             # Export system
    ├── rtg_exporter.py # RtG format export
    └── json_exporter.py # (planned) JSON utilities
```

## Quick Start

### Installation

```bash
# Clone the repository
cd "RtG Display"

# Install dependencies
pip install -r requirements.txt
```

### Run Demo

```bash
python main.py --demo --width 2 --height 2 --output output
```

This creates a 2×2 pixel display with a simple animation and exports it to JSON files.

### Run Tests

```bash
python tests/test_core.py
```

## Usage

### Creating a Display

```python
from src.display.pixel import PixelTemplate
from src.display.matrix import MatrixBuilder
from src.rtg.blocks import RtGBuild
import src.rtg.blocks as blocks

# Create a pixel template
pixel_build = RtGBuild()
pixel_build.create_base()
visual = blocks.create_part([64, 64, 64])
pixel_build.add_block(visual)
template = PixelTemplate(pixel_build)

# Build a 8x8 display
matrix = (MatrixBuilder()
          .set_dimensions(8, 8)
          .set_template(template)
          .build())
```

### Creating an Animation

```python
from src.animation.frame import FrameBuilder
from src.animation.sequence import SequenceBuilder

# Get pixel UUIDs
uuids = [pixel.get_uuid() for pixel in matrix.pixels.values()]

# Build animation
sequence = SequenceBuilder("animation")
frame1 = FrameBuilder(0).add_pixels(uuids).set_duration(1.0).build()
frame2 = FrameBuilder(1).set_duration(0.5).build()  # Blank frame
sequence.add_frame(frame1).add_frame(frame2)

animation = sequence.build()
```

### Exporting

```python
from src.export.rtg_exporter import CombinedExporter

files = CombinedExporter.export_complete(
    matrix,
    animation,
    output_dir="output",
    prefix="my_animation"
)
# Creates:
#   - my_animation_display.json  (RtG build)
#   - my_animation_animation.json (animation sequence)
#   - my_animation_info.json      (metadata)
```

## Format Specifications

### UUID System

UUIDs are formatted as: `{xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}`

The UUID manager:
- Generates random valid UUIDs
- Tracks UUID → pixel position mapping
- Prevents collisions
- Validates format

### CFrame (Coordinate Frame)

A 12-element array representing 3D transformation:
- Elements 0-2: Position (X, Y, Z)
- Elements 3-11: 3×3 rotation matrix

Example: `[5.0, 10.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]`

### RtG Block Tuple

```json
[
    "BlockType",
    [["ConnectionType", "PointID", ParentIndex], ...],
    {"PropertyKey": value, ...}
]
```

### EphemeralAttachments

Attachments allow spatial positioning via UUID reference:

```json
{
    "EphemeralAttachments": {
        "{uuid}": {
            "partName": "Base",
            "cframe": [x, y, z, r1, r2, r3, r4, r5, r6, r7, r8, r9]
        }
    }
}
```

## Implementation Status

### ✅ Completed
- UUID generation and management
- CFrame calculations and transformations
- RtG block structure and serialization
- Reference system (direct and UUID-based)
- Pixel representation and template cloning
- Display matrix (2D grid)
- Animation frames and sequences
- JSON export (display and animation)
- Core test suite

### 🟡 Planned
- Image/video import
- Binary threshold conversion
- Advanced optimization (delta frames)
- Replay system integration
- GUI editor

### ❌ Not Started
- Video codec support
- Real-time preview
- Performance profiling

## Key Design Decisions

### No Absolute Coordinates
Following RtG format, blocks don't have absolute positions. Instead:
1. Position is computed relative to parent block
2. Each pixel is positioned via UUID + CFrame offset
3. All pixels attach to Base through EphemeralAttachments

### UUID Over Indices
While RtG supports direct index references, this system uses UUIDs for pixel positioning because:
- Allows spatial injection via CFrame
- Decouples pixel data from array order
- Supports animated spatial manipulation

### Stateless Frames
Animation frames contain only:
- Duration (time before next frame)
- Set of active pixel UUIDs
- No position or rotation data

This allows playback logic to be simplified and external to the RtG system.

## Contributing

Contributions welcome! Areas of focus:
- Image/video import pipeline
- Optimization algorithms
- Export format extensions
- Testing and validation

## License

MIT License - See LICENSE file for details

## References

- RtG Save Format Specification (v0.406 or later)
- obj_ids-spanish.md - Block and connection documentation
- Road To Gramby's - Roblox game
