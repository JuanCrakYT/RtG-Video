"""
Quick GUI preview for screenshot
"""

import tkinter as tk
from src.ui.gui import RtGDisplayGUI

def show_gui():
    """Display the GUI for preview."""
    root = tk.Tk()
    gui = RtGDisplayGUI(root)
    
    # Schedule close after 3 seconds for demo
    root.after(3000, root.quit)
    
    gui.run()

if __name__ == "__main__":
    show_gui()
