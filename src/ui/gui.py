"""
Modern GUI for RtG Display.

Professional and minimalist interface for video loading and canvas configuration.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import os


class RtGDisplayGUI:
    """
    Main GUI window for RtG Display application.
    """
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the GUI.
        
        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("RtG Display")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # Configure style
        self._configure_style()
        
        # State
        self.loaded_video_path: Optional[Path] = None
        self.on_video_loaded: Optional[Callable] = None
        self.on_settings_changed: Optional[Callable] = None
        
        # Build GUI
        self._build_gui()
    
    def _configure_style(self):
        """Configure the visual style."""
        # Colors
        self.bg_primary = "#F5F5F5"      # Light gray background
        self.bg_secondary = "#FFFFFF"    # White cards
        self.accent_color = "#2196F3"    # Material blue
        self.accent_hover = "#1976D2"    # Darker blue
        self.text_primary = "#212121"    # Dark text
        self.text_secondary = "#757575"  # Medium gray text
        self.border_color = "#E0E0E0"    # Light border
        
        self.root.configure(bg=self.bg_primary)
        
        # Configure ttk style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors for ttk widgets
        style.configure(
            'TFrame',
            background=self.bg_primary
        )
        
        style.configure(
            'Card.TFrame',
            background=self.bg_secondary,
            relief='flat',
            borderwidth=1
        )
        
        style.configure(
            'TLabel',
            background=self.bg_secondary,
            foreground=self.text_primary,
            font=('Segoe UI', 10)
        )
        
        style.configure(
            'Title.TLabel',
            background=self.bg_secondary,
            foreground=self.text_primary,
            font=('Segoe UI', 12, 'bold')
        )
        
        style.configure(
            'Small.TLabel',
            background=self.bg_secondary,
            foreground=self.text_secondary,
            font=('Segoe UI', 9)
        )
        
        style.configure(
            'TButton',
            font=('Segoe UI', 10),
            padding=10
        )
    
    def _build_gui(self):
        """Build the GUI components."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="RtG Display",
            font=('Segoe UI', 20, 'bold'),
            foreground=self.text_primary
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="Animated Display Generator for Road To Gramby's",
            font=('Segoe UI', 10),
            foreground=self.text_secondary
        )
        subtitle_label.pack(anchor='w', pady=(0, 25))
        
        # Video loading card
        self._build_video_card(main_frame)
        
        # Settings card
        self._build_settings_card(main_frame)
        
        # Action buttons
        self._build_action_buttons(main_frame)
    
    def _build_video_card(self, parent):
        """Build the video loading card."""
        card_frame = ttk.Frame(parent, relief='solid', borderwidth=1)
        card_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Add border with padding
        inner_frame = ttk.Frame(card_frame)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        inner_frame.configure(relief='solid', borderwidth=0)
        
        # Actual card content
        content = tk.Frame(inner_frame, bg=self.bg_secondary, relief='flat')
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title
        title = tk.Label(
            content,
            text="Video Source",
            font=('Segoe UI', 11, 'bold'),
            bg=self.bg_secondary,
            fg=self.text_primary
        )
        title.pack(anchor='w', pady=(0, 10))
        
        # Button and status frame
        button_frame = tk.Frame(content, bg=self.bg_secondary)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Load button
        load_btn = tk.Button(
            button_frame,
            text="📁 Load Video",
            command=self._on_load_video,
            bg=self.accent_color,
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            padx=20,
            pady=8,
            border=0,
            cursor='hand2',
            activebackground=self.accent_hover
        )
        load_btn.pack(side=tk.LEFT)
        
        # Status label
        self.video_status_label = tk.Label(
            button_frame,
            text="No video loaded",
            font=('Segoe UI', 9),
            bg=self.bg_secondary,
            fg=self.text_secondary
        )
        self.video_status_label.pack(side=tk.LEFT, padx=(15, 0))
        
        # File info (hidden initially)
        self.video_info_label = tk.Label(
            content,
            text="",
            font=('Segoe UI', 8),
            bg=self.bg_secondary,
            fg=self.text_secondary,
            wraplength=400,
            justify=tk.LEFT
        )
        self.video_info_label.pack(anchor='w', pady=(5, 0))
    
    def _build_settings_card(self, parent):
        """Build the settings card with sliders."""
        card_frame = ttk.Frame(parent, relief='solid', borderwidth=1)
        card_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Actual card content
        content = tk.Frame(card_frame, bg=self.bg_secondary, relief='flat')
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Title
        title = tk.Label(
            content,
            text="Canvas Size",
            font=('Segoe UI', 11, 'bold'),
            bg=self.bg_secondary,
            fg=self.text_primary
        )
        title.pack(anchor='w', pady=(0, 15))
        
        # Width slider
        self._build_slider(
            content,
            "Width",
            2, 16, 8,
            self._on_width_changed,
            "width_value"
        )
        
        # Height slider
        self._build_slider(
            content,
            "Height",
            2, 16, 8,
            self._on_height_changed,
            "height_value"
        )
    
    def _build_slider(self, parent, label: str, min_val: int, max_val: int, 
                     default_val: int, on_change: Callable, attr_name: str):
        """Build a slider with label and value display."""
        frame = tk.Frame(parent, bg=self.bg_secondary)
        frame.pack(fill=tk.X, pady=10)
        
        # Label and value
        label_frame = tk.Frame(frame, bg=self.bg_secondary)
        label_frame.pack(fill=tk.X, pady=(0, 8))
        
        label_widget = tk.Label(
            label_frame,
            text=label,
            font=('Segoe UI', 10),
            bg=self.bg_secondary,
            fg=self.text_primary
        )
        label_widget.pack(side=tk.LEFT)
        
        value_widget = tk.Label(
            label_frame,
            text=f"{default_val}",
            font=('Segoe UI', 10, 'bold'),
            bg=self.bg_secondary,
            fg=self.accent_color
        )
        value_widget.pack(side=tk.RIGHT)
        
        # Store value widget
        setattr(self, attr_name, value_widget)
        
        # Slider
        def on_slider_change(val):
            value_widget.config(text=str(int(float(val))))
            on_change(int(float(val)))
        
        slider = tk.Scale(
            frame,
            from_=min_val,
            to=max_val,
            orient=tk.HORIZONTAL,
            command=on_slider_change,
            bg=self.bg_secondary,
            fg=self.accent_color,
            troughcolor=self.border_color,
            highlightthickness=0,
            length=300,
            bd=0,
            activebackground=self.accent_color
        )
        slider.set(default_val)
        slider.pack(fill=tk.X)
        
        # Store slider for later access
        setattr(self, f"{attr_name}_slider", slider)
    
    def _build_action_buttons(self, parent):
        """Build the action buttons."""
        button_frame = tk.Frame(parent, bg=self.bg_primary)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        # Generate button
        generate_btn = tk.Button(
            button_frame,
            text="✨ Generate Display",
            command=self._on_generate,
            bg=self.accent_color,
            fg='white',
            font=('Segoe UI', 11, 'bold'),
            padx=30,
            pady=10,
            border=0,
            cursor='hand2',
            activebackground=self.accent_hover
        )
        generate_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Preview button
        preview_btn = tk.Button(
            button_frame,
            text="👁️  Preview",
            command=self._on_preview,
            bg=self.border_color,
            fg=self.text_primary,
            font=('Segoe UI', 11),
            padx=20,
            pady=10,
            border=0,
            cursor='hand2',
            activebackground='#D0D0D0'
        )
        preview_btn.pack(side=tk.RIGHT, padx=10)
    
    def _on_load_video(self):
        """Handle video loading."""
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.loaded_video_path = Path(file_path)
            file_name = self.loaded_video_path.name
            file_size_mb = self.loaded_video_path.stat().st_size / (1024 * 1024)
            
            self.video_status_label.config(
                text=f"✓ Loaded",
                fg="#4CAF50"
            )
            
            self.video_info_label.config(
                text=f"{file_name} • {file_size_mb:.1f} MB"
            )
            
            if self.on_video_loaded:
                self.on_video_loaded(file_path)
    
    def _on_width_changed(self, value: int):
        """Handle width slider change."""
        if self.on_settings_changed:
            width = getattr(self, 'width_value_slider').get()
            height = getattr(self, 'height_value_slider').get()
            self.on_settings_changed({'width': width, 'height': height})
    
    def _on_height_changed(self, value: int):
        """Handle height slider change."""
        if self.on_settings_changed:
            width = getattr(self, 'width_value_slider').get()
            height = getattr(self, 'height_value_slider').get()
            self.on_settings_changed({'width': width, 'height': height})
    
    def _on_preview(self):
        """Handle preview button."""
        if not self.loaded_video_path:
            messagebox.showwarning("No Video", "Please load a video first")
            return
        
        messagebox.showinfo(
            "Preview",
            f"Preview not yet implemented\n\nVideo: {self.loaded_video_path.name}"
        )
    
    def _on_generate(self):
        """Handle generate button."""
        if not self.loaded_video_path:
            messagebox.showwarning("No Video", "Please load a video first")
            return
        
        width = getattr(self, 'width_value_slider').get()
        height = getattr(self, 'height_value_slider').get()
        
        messagebox.showinfo(
            "Generate",
            f"Generating {width}×{height} display\nfrom: {self.loaded_video_path.name}"
        )
    
    def get_settings(self) -> dict:
        """Get current settings."""
        return {
            'video': str(self.loaded_video_path) if self.loaded_video_path else None,
            'width': getattr(self, 'width_value_slider').get(),
            'height': getattr(self, 'height_value_slider').get()
        }
    
    def run(self):
        """Run the GUI."""
        self.root.mainloop()


def launch_gui(on_video_loaded=None, on_settings_changed=None):
    """
    Launch the RtG Display GUI.
    
    Args:
        on_video_loaded: Callback function when video is loaded
        on_settings_changed: Callback function when settings change
    """
    root = tk.Tk()
    gui = RtGDisplayGUI(root)
    gui.on_video_loaded = on_video_loaded
    gui.on_settings_changed = on_settings_changed
    gui.run()
