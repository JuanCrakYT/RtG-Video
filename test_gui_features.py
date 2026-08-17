#!/usr/bin/env python3
"""
Test script to verify all GUI features are visible and working.
"""

import tkinter as tk
import tkinter.messagebox as messagebox
from pathlib import Path
from src.ui.gui import RtGDisplayGUI

def create_test_gui():
    """Create and display the test GUI."""
    
    root = tk.Tk()
    
    def on_video_loaded(path):
        print(f"📹 Video loaded: {path}")
        messagebox.showinfo("Callback", f"Video loaded callback:\n{path}")
    
    def on_settings_changed(settings):
        print(f"🎚️  Settings changed: {settings}")
    
    # Create GUI
    gui = RtGDisplayGUI(root)
    gui.on_video_loaded = on_video_loaded
    gui.on_settings_changed = on_settings_changed
    
    # Run
    gui.run()

if __name__ == "__main__":
    print("=" * 60)
    print("RtG Display GUI Test - All Features Check")
    print("=" * 60)
    print()
    print("✅ Features to verify:")
    print("   1. Video loading card with 'Load Video' button")
    print("   2. Video status indicator (should say 'No video loaded')")
    print("   3. Canvas Size card with TWO sliders:")
    print("      - Width slider (2-16, default 8)")
    print("      - Height slider (2-16, default 8)")
    print("   4. Output Size display (e.g., '8 × 8 (64 pixels)')")
    print("   5. Three action buttons at the bottom:")
    print("      - Copy RtG button (left)")
    print("      - Preview button (middle-right)")
    print("      - Generate RtG button (right, blue)")
    print()
    print("🎨 Window: 700×520 pixels")
    print("🎨 Material Design Color Scheme applied")
    print()
    print("Starting GUI...")
    print("=" * 60)
    print()
    
    create_test_gui()
