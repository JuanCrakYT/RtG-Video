# RtG Display - Quick Start Guide

## 🚀 Getting Started

### Option 1: GUI Mode (Recommended)
```bash
python main.py
```
This launches the professional GUI with:
- 📁 Video file loader
- 🎚️ Width slider (2-16 pixels)
- 🎚️ Height slider (2-16 pixels)
- ✨ Generate button
- 👁️ Preview button

### Option 2: Interactive GUI Demo
```bash
python main.py --gui-demo
```
Runs the GUI with console output showing:
- Which video was loaded
- Canvas size changes in real-time

### Option 3: Demo Mode (CLI)
```bash
python main.py --demo
```
Generates a 2×2 display with test animation:
- Loads real pixel template (22 blocks per pixel)
- Creates 3-frame animation
- Exports JSON files to `output/`
- Shows statistics

### Option 4: Custom CLI
```bash
python main.py --demo --width 4 --height 4 --output my_output
```

## 🎨 GUI Features

### Video Loading
1. Click **📁 Load Video** button
2. Select MP4, AVI, MOV, or MKV file
3. Status changes to **✓ Loaded** (green)
4. File info displays filename and size

### Canvas Configuration
1. **Width Slider**: Adjust 2-16 pixels
2. **Height Slider**: Adjust 2-16 pixels
3. Values update in real-time (shown in blue)

### Actions
- **👁️ Preview**: See animation preview
- **✨ Generate Display**: Create the RtG display

## 📋 System Requirements

- Python 3.7+
- tkinter (included with Python)
- pillow (optional, for image support)
- numpy, opencv-python (for video processing)

### Install Dependencies
```bash
pip install -r requirements.txt
```

## 📂 Project Structure
```
├── main.py                  # Entry point
├── src/
│   ├── ui/
│   │   ├── gui.py          # GUI implementation
│   │   └── __init__.py
│   ├── rtg/                # RtG format system
│   ├── display/            # Display matrix
│   ├── animation/          # Animation frames
│   └── export/             # JSON export
├── tests/
│   └── test_core.py        # Test suite
├── assets/
│   └── pixel/
│       └── pixel.json      # Pixel template
└── output/                 # Generated files
```

## 🧪 Testing

### Run Test Suite
```bash
python tests/test_core.py
```

### Test GUI Module
```bash
python -c "from src.ui.gui import launch_gui; print('✓ GUI module OK')"
```

## 🎯 Workflow

### Step 1: Load Video
```
[📁 Load Video] → Select file.mp4
```

### Step 2: Configure Display
```
Width:  [2 ━━●━━━━━━━━━━━━ 16] → 8
Height: [2 ━━●━━━━━━━━━━━━ 16] → 8
```

### Step 3: Generate
```
[👁️ Preview]  [✨ Generate Display]
```

### Step 4: Output
```
output/
├── display.json    # RtG block structure
├── animation.json  # Frame control data
└── info.json       # Statistics
```

## 💡 Tips

### Using the API Programmatically
```python
from src.ui.gui import RtGDisplayGUI
import tkinter as tk

root = tk.Tk()
gui = RtGDisplayGUI(root)

# Get settings anytime
settings = gui.get_settings()
print(f"Canvas: {settings['width']}×{settings['height']}")

gui.run()
```

### Integrate with Your App
```python
from src.ui.gui import launch_gui

def on_video_loaded(path):
    print(f"Video: {path}")

def on_settings_changed(settings):
    print(f"Size: {settings['width']}×{settings['height']}")

launch_gui(
    on_video_loaded=on_video_loaded,
    on_settings_changed=on_settings_changed
)
```

## 🐛 Troubleshooting

### GUI doesn't appear
```bash
# Check tkinter installation
python -m tkinter
# Should show a test window

# If not installed on Linux:
sudo apt install python3-tk
```

### Video file not loading
- Ensure file format is supported (MP4, AVI, MOV, MKV)
- Check file is readable
- Verify sufficient permissions

### Sliders not responding
- Python version < 3.7? Upgrade required
- tkinter corrupted? Reinstall: `pip install --upgrade tkinter`

### No GUI but CLI works
- Headless system? Use CLI mode
- Remote connection? Enable X11 forwarding

## 📊 Generated Output

### display.json
RtG format with all blocks and connections
```json
[
  ["Base", [], {}],
  ["Part", [["1", "{uuid}", 0]], {"RGB": [255, 0, 0]}],
  ...
]
```

### animation.json
Control data with pixel activation
```json
{
  "frames": [
    {"duration": 0.1, "activePixels": ["{uuid1}", "{uuid2}"]},
    ...
  ],
  "totalDuration": 0.3,
  "frameCount": 3
}
```

### info.json
Statistics and metadata
```json
{
  "display": {
    "type": "display",
    "width": 2,
    "height": 2,
    "total_pixels": 4,
    "total_blocks": 85
  },
  "animation": {
    "frameCount": 3,
    "totalDuration": 0.3,
    "pixelCount": 4
  }
}
```

## 📖 Documentation

- [GUI Documentation](GUI_DOCUMENTATION.md) - Detailed UI guide
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md) - Technical details
- [RtG Format Spec](RtG_Save_Format_Specification-spanish.md) - Format reference

## ✅ Checklist

- [x] Professional minimalist GUI
- [x] Video file loader
- [x] Canvas size controls
- [x] Real-time preview
- [x] JSON export
- [x] Test suite (8/8 passing)
- [x] Documentation
- [x] Ready for production

## 🎉 Ready to Use!

The RtG Display application is fully functional with a professional GUI. Enjoy creating animated displays!
