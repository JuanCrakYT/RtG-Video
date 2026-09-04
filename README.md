# RtG Video

Animated display generator for **Road To Gramby's (Roblox)**.

RtG Video converts videos into low-resolution animated pixel displays that can be exported as Road To Gramby's-compatible data. The project combines video processing, pixel-matrix generation, animation management, and RtG save-format handling into a single pipeline.

## Overview

RtG Video is a Python application designed to create physical pixel displays capable of reproducing animations.

The general pipeline is:

```md
Video
  ↓
Frame Processing
  ↓
Resize / Palette Quantization
  ↓
Pixel Matrix
  ↓
Animation Sequence
  ↓
RtG Export
  ↓
JSON
```

Instead of generating a completely different build for every frame, RtG Video creates a reusable display and changes the state of its pixels through animation data.

This makes the physical display independent from the animation itself.

## Features

* **Video input** — Load video files and process them frame by frame.
* **Configurable canvas** — Choose the width and height of the pixel display with sliders or numeric fields from 2 to 128.
* **Palette support** — Convert video frames to a configurable RGB palette.
* **Pixel matrix generation** — Create a reusable 2D matrix of controllable pixels.
* **Animation sequences** — Represent video playback as a sequence of timed frames.
* **RtG format support** — Build and serialize Road To Gramby's structures.
* **UUID-based pixel mapping** — Keep pixel identity independent from array order.
* **CFrame support** — Handle RtG coordinate-frame transformations.
* **EphemeralAttachments** — Position generated display components using UUID references.
* **JSON export** — Export display, animation, and metadata information.
* **Preview window** — Preview the processed video at the selected canvas resolution.
* **GUI configuration** — Configure the source video, canvas size, and color palette through a graphical interface.
* **Tests** — Includes tests for core functionality, canvas generation, signal logic, and output synchronization.

## Project Structure

The repository is organized into several layers:

```tree
RtG Video/
├─ assets/
│  ├─ pixel/
│  │  └─ pixel.json
│  └─ tools/
│     └─ json/
│        ├─ __pycache__/
│        │  └─ json.cpython-314.pyc
│        ├─ compact_json.py
│        ├─ input.json
│        ├─ output.json
│        └─ README.md
│
├─ examples/
│  └─ bad_apple/
│
├─ output/
│  ├─ canvas_2x2/
│  │  └─ display.json
│  ├─ color_demo/
│  │  ├─ animation.json
│  │  ├─ display.json
│  │  └─ info.json
│  ├─ topology_validation/
│  │  ├─ animation.json
│  │  ├─ display.json
│  │  └─ info.json
│  ├─ base64.json
│  └─ display.json
│
├─ screenshots/
│
├─ src/
│  ├─ animation/
│  │  ├─ __init__.py
│  │  ├─ frame.py
│  │  ├─ sequence.py
│  │  └─ signal_logic.py
│  │
│  ├─ display/
│  │  ├─ __init__.py
│  │  ├─ matrix.py
│  │  └─ pixel.py
│  │
│  ├─ export/
│  │  ├─ __init__.py
│  │  └─ rtg_exporter.py
│  │
│  ├─ rtg/
│  │  ├─ __init__.py
│  │  ├─ blocks.py
│  │  ├─ cframe.py
│  │  ├─ format.py
│  │  ├─ references.py
│  │  └─ uuid.py
│  │
│  ├─ ui/
│  │  ├─ __init__.py
│  │  ├─ base64.py
│  │  └─ gui.py
│  │
│  ├─ video/
│  │  ├─ __init__.py
│  │  └─ processing.py
│  │
│  ├─ __init__.py
│  └─ config.py
│
├─ tests/
│  ├─ test_canvas.py
│  ├─ test_core.py
│  ├─ test_output_sync.py
│  └─ test_signal_logic.py
│
├─ .gitattributes
├─ .gitignore
├─ capture_gui.py
├─ demo_gui.py
├─ GUI_COMPLETE.md
├─ GUI_DOCUMENTATION.md
├─ GUI_FIXES_SUMMARY.py
├─ GUI_SUMMARY.py
├─ IMPLEMENTATION_SUMMARY.md
├─ LICENSE
├─ main.py
├─ obj_ids-spanish.md
├─ preview_gui.py
├─ QUICKSTART.md
├─ README.md
├─ requirements.txt
├─ RtG_Save_Format_Specification-spanish.md
├─ SETUP_COMPLETE.md
├─ test_gui_features.py
└─ verify_gui_elements.py
```

### Source modules

| Module           | Purpose                                                        |
| ---------------- | -------------------------------------------------------------- |
| `src/rtg/`       | Core Road To Gramby's data structures and save-format handling |
| `src/display/`   | Pixel definitions and 2D display matrices                      |
| `src/animation/` | Animation frames, sequences, and signal behavior               |
| `src/video/`     | Video frame processing, resizing, and palette quantization     |
| `src/export/`    | Export generated display and animation data                    |
| `src/ui/`        | Graphical interface and Base64-related utilities               |
| `src/config.py`  | Project configuration                                          |

## Requirements

* Python 3.x
* OpenCV (`opencv-python`)
* NumPy
* Tkinter
* Pygame
* MoviePy
* Other dependencies listed in `requirements.txt`

Install the required Python packages with:

```bash
pip install -r requirements.txt
```

## Running the Application

The main entry point is:

```bash
python main.py
```

The project also contains dedicated GUI and preview entry points:

```bash
python demo_gui.py
python preview_gui.py
```

The exact behavior of each entry point depends on the current project configuration and workflow.

## GUI

RtG Video includes a graphical interface called **RtG Display**.

The GUI currently provides configuration for:

* video loading
* canvas width
* canvas height
* output size
* color palette management
* video preview
* display generation

Width and Height can be adjusted with either their sliders or the numeric fields beside them. Both dimensions accept values from `2` to `128`.

The preview system can display the source video after it has been reduced to the selected pixel resolution.

For example:

```md
Source Video
      ↓
40 × 30 Processing
      ↓
Pixel Preview
```

This makes it possible to visually inspect how a video will look on a low-resolution RtG display before generating the final output.

## Video Processing

Video processing is implemented in:

```text
src/video/processing.py
```

Frames are processed through the following stages:

1. Read a frame from the source video.
2. Convert the frame to RGB.
3. Resize the frame to the display dimensions.
4. Quantize each pixel to the nearest color in the selected palette.
5. Map each processed pixel to the corresponding display pixel.
6. Store the result as an animation frame.

The current processing implementation uses OpenCV for frame decoding and resizing and NumPy for color-distance calculations. 

## JavaScript Preview Experiment

The folder `tmp/` contains an isolated JavaScript translation of the Preview workflow. It is experimental and does not replace the Python/Tkinter Preview yet.

The experiment includes:

* `tmp/preview.js` — browser-based preview controller, pause/close handling, video-frame callbacks, area resize, frame quantization, palette normalization, and cleanup.
* `tmp/preview.html` — manual browser harness for selecting a video and opening the preview window.
* `tmp/preview-test.js` — Node.js checks for dimensions, palette deduplication, area resize, and quantization.

Node.js 18 or newer is required. Run the isolated checks with:

```bash
cd tmp
npm test
```

To try the visual experiment, serve the repository with a local HTTP server and open `tmp/preview.html` in a browser. This temporary implementation must be validated before moving or replacing the Python Preview code.

### Preview translation audit status

The current audit estimates the experimental translation at approximately 75% behavioral coverage:

| Area                                                           | Status      | Notes                                                                                                                                                |
| -------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Preview window, controls, pause, resume, close                 | Complete    | Adapted from Tkinter to a browser popup and native video element; paused playback stops the render loop and closed popups are cleaned up.            |
| Width/Height validation and pixel rendering                    | Complete    | Values are clamped to `2-128`; canvas cells use deterministic area resizing and palette quantization.                                                |
| Video loading and error handling                               | Complete    | Uses browser file input, metadata/error events, and Object URL cleanup.                                                                              |
| Frame scheduling and frame counter                             | Adapted     | Uses `requestVideoFrameCallback` when available, with `requestAnimationFrame` fallback; browser APIs do not expose OpenCV's exact total-frame count. |
| Audio synchronization                                          | Adapted     | Uses the native video audio clock instead of MoviePy temporary WAV extraction and Pygame.                                                            |
| OpenCV capture seeking and FPS timing                          | Not literal | These are Python/OpenCV APIs; browser media timing is the deliberate equivalent.                                                                     |
| Python/Tkinter dialogs, Toplevel lifecycle, and Pygame cleanup | Not literal | Replaced by browser APIs and native media lifecycle.                                                                                                 |

The translation is therefore not yet a drop-in replacement. The Python Preview remains the production implementation, while `tmp/` is the validation laboratory.

## Preview Performance Laboratory

The migration goal is now measured Preview performance, not line-for-line language parity. The Python Preview's likely bottlenecks are the Python-level per-cell quantization loop and one Tkinter canvas rectangle operation per output pixel on every scheduled frame. The JavaScript experiment uses browser video timing and Canvas 2D so that the same work can be measured separately as processing and rendering.

Run the synthetic benchmark with ten iterations per resolution by default:

```bash
python tmp/benchmark_python.py
```

Open `tmp/benchmark-browser.html` from a local HTTP server to measure the JavaScript Canvas 2D path. Both benchmarks use a deterministic `640x360` synthetic source, the default three-color palette, and `16x16`, `32x32`, `64x64`, `96x96`, and `128x128` output sizes. The reported FPS is derived from measured processing plus rendering time; CPU, memory, and dropped-frame metrics are not reported because this benchmark cannot measure them reliably in the current environment.

Final synthetic comparison, ten iterations per size after the typed-buffer and `putImageData` optimization:

| Resolution | Python total | JavaScript total | Python FPS | JavaScript FPS | Speedup |
| --- | ---: | ---: | ---: | ---: | ---: |
| 16x16 | 6.84 ms | 4.16 ms | 146.30 | 240.38 | 1.64x |
| 32x32 | 22.27 ms | 3.65 ms | 44.91 | 273.97 | 6.10x |
| 64x64 | 85.68 ms | 4.21 ms | 11.67 | 237.53 | 20.35x |
| 96x96 | 197.30 ms | 5.40 ms | 5.07 | 185.19 | 36.54x |
| 128x128 | 346.82 ms | 4.88 ms | 2.88 | 204.92 | 71.07x |

The JavaScript checksum now matches Python at all five resolutions, including the previously divergent `96x96` case. The optimization uses a flat `Uint8ClampedArray` for quantized RGBA output and one `putImageData` call per frame instead of one `fillRect` call per pixel. These are synthetic measurements, not real-video results; no CPU, memory, dropped-frame, or real-video claim is made. No Python code has been replaced.

### Palette Quantization

RtG Video supports configurable RGB palettes.

A palette always contains black and can contain additional colors.

For every processed pixel, the system selects the palette color with the smallest squared RGB distance:

```md
source pixel
    ↓
compare against palette
    ↓
nearest palette color
    ↓
display pixel
```

The default palette currently contains:

```md
Black
White
Gray
```

The GUI allows the palette to be modified before generating the display. 

## Display System

The display system represents the physical animation surface as a 2D matrix.

Each matrix position corresponds to a pixel object.

For example:

```text
(0,0) (1,0) (2,0) (3,0)

(0,1) (1,1) (2,1) (3,1)

(0,2) (1,2) (2,2) (3,2)
```

Each pixel has a stable UUID that can be used to reference it from animation data.

This separates the identity of a pixel from its position in the internal Python data structures.

## Animation System

Animations are represented as ordered sequences of frames.

A frame contains the state of the display for a specific duration.

Conceptually:

```md
Frame 0
  duration: 1 / FPS
  pixel states
       ↓
Frame 1
  duration: 1 / FPS
  pixel states
       ↓
Frame 2
  duration: 1 / FPS
  pixel states
       ↓
...
```

The animation system is implemented in:

```md
src/animation/
```

with the main components:

* `frame.py` — individual animation frames
* `sequence.py` — ordered frame sequences
* `signal_logic.py` — signal and pixel-state logic

## Creating a Display

A display can be created programmatically using a pixel template and a matrix builder.

Example:

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

# Build an 8 × 8 display
matrix = (
    MatrixBuilder()
    .set_dimensions(8, 8)
    .set_template(template)
    .build()
)
```

## Creating an Animation

Animation frames can be constructed using the animation builders:

```python
from src.animation.frame import FrameBuilder
from src.animation.sequence import SequenceBuilder

# Get pixel UUIDs
uuids = [pixel.get_uuid() for pixel in matrix.pixels.values()]

# Create an animation
sequence = SequenceBuilder("animation")

frame1 = (
    FrameBuilder(0)
    .add_pixels(uuids)
    .set_duration(1.0)
    .build()
)

frame2 = (
    FrameBuilder(1)
    .set_duration(0.5)
    .build()
)

sequence.add_frame(frame1)
sequence.add_frame(frame2)

animation = sequence.build()
```

## Exporting

The exporter converts the generated display and animation data into JSON output.

Example:

```python
from src.export.rtg_exporter import CombinedExporter

files = CombinedExporter.export_complete(
    matrix,
    animation,
    output_dir="output",
    prefix="my_animation"
)
```

Depending on the exporter configuration, the resulting data can include:

```md
my_animation_display.json
my_animation_animation.json
my_animation_info.json
```

The generated display data represents the RtG structure, while animation data describes the temporal state of the display.

## RtG Format

RtG Video is built around the Road To Gramby's save format.

The project does not treat the display as a collection of arbitrary absolute-positioned objects. Instead, it follows the relationships and references used by the RtG save structure.

The core RtG implementation is located in:

```md
src/rtg/
```

### UUIDs

UUIDs are used to uniquely identify generated pixels.

Example:

```json
{xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}
```

The UUID system is responsible for:

* generating UUIDs
* tracking UUID associations
* validating UUID format
* preventing collisions

### CFrames

A CFrame is represented by 12 numerical values:

```json
[x, y, z, r1, r2, r3, r4, r5, r6, r7, r8, r9]
```

The first three values represent position:

```js
X, Y, Z
```

The remaining nine values represent a 3 × 3 rotation matrix.

Example:

```json
[
  5.0,
  10.0,
  0.0,
  1.0,
  0.0,
  0.0,
  0.0,
  1.0,
  0.0,
  0.0,
  0.0,
  1.0
]
```

### RtG Block Tuples

RtG blocks follow the project's internal tuple representation:

```json
[
  "BlockType",
  [
    ["ConnectionType", "PointID", ParentIndex]
  ],
  {
    "PropertyKey": "value"
  }
]
```

The exact meaning of block types, connection points, and references depends on the RtG save format being implemented.

### EphemeralAttachments

Spatial placement can also use UUID-based ephemeral attachments:

```json
{
  "EphemeralAttachments": {
    "{uuid}": {
      "partName": "Base",
      "cframe": [
        0, 0, 0,
        1, 0, 0,
        0, 1, 0,
        0, 0, 1
      ]
    }
  }
}
```

This allows generated display components to be positioned independently from the order of the serialized block list.

## Design Principles

### Reusable Display

The display is generated once and reused for the entire animation.
The animation changes pixel states instead of generating an entirely new physical display for every frame.

### UUID-Based Pixel Identity

Pixels are identified by UUID rather than depending exclusively on array indices.
This provides stable references even when internal ordering changes.

### Separation of Geometry and Animation

The display defines:

```text
Where pixels exist
```

while the animation defines:

```text
Which pixels are active
and for how long
```

Keeping these concepts separate makes the system easier to extend and process.

### Palette-Based Rendering

Video frames are reduced to a finite palette so they can be represented by the available pixel colors.

This is especially useful for low-resolution displays where the number of available colors is intentionally limited.

## Output Examples

The repository contains several generated examples under:

```md
output/
```

including:

```md
canvas_2x2/
color_demo/
topology_validation/
```

These examples can be used to inspect generated display and animation JSON data.

The repository also contains a `bad_apple` example under:

```md
examples/bad_apple/
```

## Testing

Tests are located in:

```md
tests/
```

Run the core test suite with:

```bash
python tests/test_core.py
```

Individual tests can also be executed directly:

```bash
python tests/test_canvas.py
python tests/test_output_sync.py
python tests/test_signal_logic.py
```

Additional GUI verification scripts are available at the repository root:

```bash
python test_gui_features.py
python verify_gui_elements.py
```

## Current Status

### ✅ Implemented

* RtG UUID generation and management
* CFrame calculations and transformations
* RtG block structures
* Reference handling
* JSON serialization
* Pixel representation
* Pixel templates
* 2D display matrices
* Animation frames
* Animation sequences
* Signal logic
* Video frame loading
* Frame resizing
* Palette normalization
* Palette quantization
* Video-to-animation conversion
* GUI configuration
* Video preview
* JSON export
* Base64-related utilities
* Core tests
* GUI verification tools

The current GUI implementation includes video loading, canvas configuration, palette configuration, and preview playback functionality. 

The current video processor can read a video, resize frames to the matrix dimensions, quantize them to a palette, and map the resulting colors onto matrix pixels. 

### 🟡 In Progress / Future Work

Possible future improvements include:

* More advanced frame compression
* Delta-frame optimization
* Better performance for large videos
* More efficient animation serialization
* More extensive GUI controls
* Additional palette and rendering options
* Improved export workflows
* Additional validation tools
* Profiling and performance optimization

## Documentation

Additional project documentation is available in:

* `QUICKSTART.md`
* `GUI_DOCUMENTATION.md`
* `GUI_COMPLETE.md`
* `IMPLEMENTATION_SUMMARY.md`
* `SETUP_COMPLETE.md`
* `obj_ids-spanish.md`
* `RtG_Save_Format_Specification-spanish.md`

The RtG save-format documentation should be treated as the primary reference for the RtG structures implemented by this project.

## References

* [Road To Gramby's](https://www.roblox.com/)
* [RtG Save Format Specification](RtG_Save_Format_Specification-spanish.md)
* [Object and Connection IDs](obj_ids-spanish.md)

## Contributing

Contributions are welcome.

Useful areas for contribution include:

* video processing
* animation optimization
* export improvements
* testing
* validation
* GUI improvements
* performance optimization

Please keep changes consistent with the existing RtG data model and document any changes to the generated format.

## License

See [`LICENSE`](LICENSE) for the project's license information.
