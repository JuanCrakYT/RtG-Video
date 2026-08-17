# RtG Display - GUI Documentation

## 🎨 User Interface Overview

The RtG Display application features a professional, minimalist GUI built with tkinter.

### Design Philosophy
- **Modern Design**: Segoe UI font, Material Design color scheme
- **Minimalist Layout**: Clean, uncluttered interface
- **Responsive**: All controls are accessible and intuitive
- **Professional**: Suitable for production use

### Color Scheme
- **Primary Background**: #F5F5F5 (Light gray)
- **Card Background**: #FFFFFF (White)
- **Accent**: #2196F3 (Material Blue)
- **Text Primary**: #212121 (Dark)
- **Text Secondary**: #757575 (Gray)
- **Borders**: #E0E0E0 (Light Gray)

## 🖼️ Layout Structure

### Header Section
```
RtG Display
Animated Display Generator for Road To Gramby's
```
- Large title with professional subtitle
- Sets context for the application

### Video Loading Card
```
┌─────────────────────────────────┐
│ Video Source                    │
│ [📁 Load Video] ✓ Loaded        │
│ example_video.mp4 • 45.2 MB     │
└─────────────────────────────────┘
```

**Components:**
- **Load Button**: Blue button with file browser dialog
- **Status Label**: Shows "No video loaded" or "✓ Loaded" with status color
- **File Info**: Displays filename and file size in MB

**Supported Formats:**
- MP4, AVI, MOV, MKV
- Any other video format supported by OpenCV

### Canvas Size Settings Card
```
┌─────────────────────────────────┐
│ Canvas Size                     │
│                                 │
│ Width                      8    │
│ [========●====================]│
│                                 │
│ Height                     8    │
│ [========●====================]│
└─────────────────────────────────┘
```

**Components:**
- **Width Slider**: Range 2-16 pixels, default 8
- **Height Slider**: Range 2-16 pixels, default 8
- **Current Values**: Displayed in blue (right-aligned)
- **Real-time Updates**: Changes take effect immediately

### Action Buttons
```
[👁️  Preview]  [✨ Generate Display]
```

**Buttons:**
- **Preview Button**: Shows animation preview (light gray)
- **Generate Button**: Creates the display (blue)

## 🎯 User Workflow

### Step 1: Load Video
1. Click "📁 Load Video" button
2. Select video file from file browser
3. Status shows "✓ Loaded" in green
4. File info displays filename and size

### Step 2: Configure Canvas
1. Adjust "Width" slider (2-16 pixels)
2. Adjust "Height" slider (2-16 pixels)
3. Values update in real-time in blue text

### Step 3: Generate
1. Click "✨ Generate Display" button
2. System processes video and generates RtG blocks
3. Exports JSON files to output folder

### Step 4: Preview (Optional)
1. Click "👁️  Preview" to see animation
2. Validates settings before generation

## 🔧 Interactive Elements

### Video Loader
```python
# Callback when video is loaded
def on_video_loaded(file_path):
    print(f"Video loaded: {file_path}")

# Callback when settings change
def on_settings_changed(settings):
    print(f"Canvas: {settings['width']}×{settings['height']}")
```

### Getting Current Settings
```python
from src.ui.gui import RtGDisplayGUI

gui = RtGDisplayGUI(root)
settings = gui.get_settings()
# Returns:
# {
#     'video': '/path/to/video.mp4',
#     'width': 8,
#     'height': 8
# }
```

## 💻 API Integration

### Launch GUI from Code
```python
from src.ui.gui import launch_gui

def on_video_loaded(path):
    print(f"Video: {path}")

def on_settings_changed(settings):
    print(f"Settings: {settings}")

launch_gui(
    on_video_loaded=on_video_loaded,
    on_settings_changed=on_settings_changed
)
```

### GUI Class Reference
```python
class RtGDisplayGUI:
    def __init__(self, root: tk.Tk)
    def get_settings(self) -> dict
    def run(self)
    
    # Callbacks (set these)
    on_video_loaded: Optional[Callable]
    on_settings_changed: Optional[Callable]
```

## 🚀 Running the Application

### Start GUI (Default)
```bash
python main.py
```

### Run Demo CLI
```bash
python main.py --demo --width 2 --height 2
```

### Preview Only (No Actions)
```bash
python preview_gui.py
```

## 📦 Dependencies
- tkinter (included with Python)
- pathlib (standard library)

## 🎨 Customization

### Change Colors
Edit `_configure_style()` method in `gui.py`:
```python
self.bg_primary = "#F5F5F5"      # Your color
self.accent_color = "#2196F3"    # Your color
```

### Change Slider Ranges
Modify `_build_slider()` calls:
```python
self._build_slider(
    content,
    "Width",
    2, 16,      # min, max
    8,          # default
    self._on_width_changed,
    "width_value"
)
```

### Add More Sliders
Duplicate the slider building code and add callbacks:
```python
self._build_slider(
    content,
    "Frame Rate",
    10, 60, 24,  # FPS range
    self._on_fps_changed,
    "fps_value"
)
```

## 🐛 Troubleshooting

### Window doesn't appear
- Ensure tkinter is installed: `python -m tkinter`
- Check display connection on remote systems

### Sliders not responding
- Verify Python version (requires 3.6+)
- Check tkinter.Scale implementation

### File dialog not working
- Ensure tkinter is properly installed
- May fail on headless systems

## ✅ Status
- ✓ Video loading with file browser
- ✓ Width/Height sliders with real-time updates
- ✓ Professional minimalist design
- ✓ Callback system for external integration
- ✓ Ready for production use
