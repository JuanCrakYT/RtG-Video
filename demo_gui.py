"""
Interactive GUI demonstration
"""

import tkinter as tk
from pathlib import Path

def demo_gui():
    """Run an interactive GUI demo."""
    from src.ui.gui import RtGDisplayGUI
    
    root = tk.Tk()
    
    print("\n" + "="*60)
    print("RtG Display - GUI Demo")
    print("="*60)
    print("\nStarting GUI window...")
    print("\nGUI Features Demonstrated:")
    print("  1. Professional minimalist design")
    print("  2. Video file loader with status display")
    print("  3. Width slider (2-16 pixels)")
    print("  4. Height slider (2-16 pixels)")
    print("  5. Generate and Preview buttons")
    print("\nInstructions:")
    print("  - Click 'Load Video' to select a video file")
    print("  - Drag sliders to adjust canvas size")
    print("  - Click 'Generate Display' to create output")
    print("  - Close window to exit demo")
    print("\n" + "="*60 + "\n")
    
    # Callbacks
    def on_video_loaded(path):
        print(f"✓ Video loaded: {Path(path).name}")
    
    def on_settings_changed(settings):
        print(f"✓ Settings changed: {settings['width']}×{settings['height']}")
    
    # Create GUI
    gui = RtGDisplayGUI(root)
    gui.on_video_loaded = on_video_loaded
    gui.on_settings_changed = on_settings_changed
    
    print("→ GUI window is now open")
    print("→ Try loading a video and adjusting the sliders\n")
    
    gui.run()


if __name__ == "__main__":
    demo_gui()
