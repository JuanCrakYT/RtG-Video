"""
Generate a screenshot of the GUI for documentation
"""

import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab
from pathlib import Path
import time

def capture_gui_screenshot():
    """Capture the GUI window as an image."""
    # Create root window
    root = tk.Tk()
    root.title("RtG Display")
    root.geometry("600x400")
    root.resizable(False, False)
    
    # Import and create GUI
    from src.ui.gui import RtGDisplayGUI
    gui = RtGDisplayGUI(root)
    
    # Schedule the screenshot and close
    def take_screenshot_and_close():
        # Give window time to render
        root.update()
        time.sleep(0.5)
        
        # Get window position and size
        x = root.winfo_rootx()
        y = root.winfo_rooty()
        w = root.winfo_width()
        h = root.winfo_height()
        
        # Take screenshot
        screenshot = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        
        # Save to docs
        output_path = Path(__file__).parent / "docs" / "gui_screenshot.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot.save(str(output_path))
        
        print(f"✓ Screenshot saved to: {output_path}")
        root.quit()
    
    root.after(1000, take_screenshot_and_close)
    root.mainloop()

if __name__ == "__main__":
    try:
        capture_gui_screenshot()
    except Exception as e:
        print(f"Note: Could not capture screenshot (Pillow required)")
        print(f"Error: {e}")
        print("\nGUI features:")
        print("- Professional minimalist design with Segoe UI font")
        print("- Video loading section with file browser")
        print("- Width & height sliders (2-16 pixels)")
        print("- Generate and Preview buttons")
