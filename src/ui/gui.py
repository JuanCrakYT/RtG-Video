"""
Modern GUI for RtG Display.

Professional and minimalist interface for video loading and canvas configuration.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import os

try:
    import cv2
except ImportError:  # pragma: no cover - optional dependency for preview playback
    cv2 = None


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
        self.root.geometry("700x660")
        self.root.resizable(False, False)
        
        # Configure style
        self._configure_style()
        
        # State
        self.loaded_video_path: Optional[Path] = None
        self.on_video_loaded: Optional[Callable] = None
        self.on_settings_changed: Optional[Callable] = None
        self.preview_window: Optional[tk.Toplevel] = None
        self.preview_job = None
        self.preview_capture = None
        self.preview_is_playing = False
        self.preview_frame_index = 0
        self.preview_total_frames = 0
        self.preview_counter_label = None
        self.preview_toggle_btn = None
        
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
            text="🎚️  Canvas Size",
            font=('Segoe UI', 11, 'bold'),
            bg=self.bg_secondary,
            fg=self.text_primary
        )
        title.pack(anchor='w', pady=(0, 20))
        
        # Width slider
        self._build_slider(
            content,
            "Width",
            2, 40, 8,
            self._on_width_changed,
            "width_value"
        )
        
        # Height slider
        self._build_slider(
            content,
            "Height",
            2, 40, 8,
            self._on_height_changed,
            "height_value"
        )
        
        # Output size display
        output_frame = tk.Frame(content, bg=self.bg_secondary)
        output_frame.pack(fill=tk.X, pady=(20, 0), padx=(0, 0))
        
        output_label = tk.Label(
            output_frame,
            text="Output Size:",
            font=('Segoe UI', 9),
            bg=self.bg_secondary,
            fg=self.text_secondary
        )
        output_label.pack(side=tk.LEFT)
        
        self.output_size_label = tk.Label(
            output_frame,
            text="8 × 8 (64 pixels)",
            font=('Segoe UI', 9, 'bold'),
            bg=self.bg_secondary,
            fg=self.accent_color
        )
        self.output_size_label.pack(side=tk.LEFT, padx=(10, 0))
    
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
        
        # Left buttons frame
        left_frame = tk.Frame(button_frame, bg=self.bg_primary)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Copy button
        copy_btn = tk.Button(
            left_frame,
            text="📋 Copy RtG",
            command=self._on_copy,
            bg=self.border_color,
            fg=self.text_primary,
            font=('Segoe UI', 10),
            padx=15,
            pady=10,
            border=0,
            cursor='hand2',
            activebackground='#D0D0D0'
        )
        copy_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Right buttons frame
        right_frame = tk.Frame(button_frame, bg=self.bg_primary)
        right_frame.pack(side=tk.RIGHT, fill=tk.X)
        
        # Preview button
        preview_btn = tk.Button(
            right_frame,
            text="👁️  Preview",
            command=self._on_preview,
            bg=self.border_color,
            fg=self.text_primary,
            font=('Segoe UI', 10),
            padx=15,
            pady=10,
            border=0,
            cursor='hand2',
            activebackground='#D0D0D0'
        )
        preview_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Generate button
        generate_btn = tk.Button(
            right_frame,
            text="✨ Generate RtG",
            command=self._on_generate,
            bg=self.accent_color,
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            padx=20,
            pady=10,
            border=0,
            cursor='hand2',
            activebackground=self.accent_hover
        )
        generate_btn.pack(side=tk.LEFT)
    
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
        self._update_output_size()
        if self.on_settings_changed:
            width = getattr(self, 'width_value_slider').get()
            height = getattr(self, 'height_value_slider').get()
            self.on_settings_changed({'width': width, 'height': height})
    
    def _on_height_changed(self, value: int):
        """Handle height slider change."""
        self._update_output_size()
        if self.on_settings_changed:
            width = getattr(self, 'width_value_slider').get()
            height = getattr(self, 'height_value_slider').get()
            self.on_settings_changed({'width': width, 'height': height})
    
    def _update_output_size(self):
        """Update the output size display."""
        width = getattr(self, 'width_value_slider').get()
        height = getattr(self, 'height_value_slider').get()
        total = width * height
        self.output_size_label.config(
            text=f"{width} × {height} ({total} pixels)"
        )
    
    def _close_preview(self):
        """Stop preview playback and close the preview window."""
        self.preview_is_playing = False

        if self.preview_job is not None and self.preview_window is not None and self.preview_window.winfo_exists():
            self.preview_window.after_cancel(self.preview_job)
        self.preview_job = None

        if self.preview_capture is not None:
            self.preview_capture.release()
            self.preview_capture = None

        if self.preview_window is not None and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        self.preview_window = None

    def _toggle_preview_pause(self):
        """Toggle pause/play state for the preview loop."""
        if self.preview_window is None or not self.preview_window.winfo_exists():
            return

        self.preview_is_playing = not self.preview_is_playing
        if self.preview_toggle_btn is not None:
            self.preview_toggle_btn.config(text="⏸ Pause" if self.preview_is_playing else "▶ Play")

    def _update_preview_counter(self, frame_number: int):
        """Update the preview frame counter label."""
        if self.preview_counter_label is not None and self.preview_window is not None and self.preview_window.winfo_exists():
            total = self.preview_total_frames if self.preview_total_frames > 0 else "?"
            self.preview_counter_label.config(text=f"Frame: {frame_number} / {total}")

    def _open_video_preview(self, video_path: Path):
        """Open a separate window that replays the video as a low-resolution RtG pixel preview."""
        if cv2 is None:
            messagebox.showerror(
                "Preview unavailable",
                "OpenCV is required for the preview. Install it with: pip install opencv-python"
            )
            return

        if self.preview_window is not None and self.preview_window.winfo_exists():
            self._close_preview()

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            messagebox.showerror(
                "Preview failed",
                f"Could not open video: {video_path.name}"
            )
            return

        self.preview_capture = capture
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title(f"RtG Preview - {video_path.name}")
        self.preview_window.geometry("560x520")
        self.preview_window.resizable(False, False)
        self.preview_window.protocol("WM_DELETE_WINDOW", self._close_preview)

        width = getattr(self, 'width_value_slider').get()
        height = getattr(self, 'height_value_slider').get()
        self.preview_is_playing = True
        self.preview_frame_index = 0
        self.preview_total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        canvas = tk.Canvas(self.preview_window, width=420, height=420, bg="#111111", highlightthickness=0)
        canvas.pack(padx=16, pady=(12, 8), fill=tk.BOTH, expand=True)

        info = tk.Label(
            self.preview_window,
            text=f"RtG preview: {width} × {height} pixels",
            bg="#F5F5F5",
            fg="#212121",
            font=('Segoe UI', 10, 'bold')
        )
        info.pack(pady=(0, 10))

        self.preview_counter_label = tk.Label(
            self.preview_window,
            text=f"Frame: 0 / {self.preview_total_frames if self.preview_total_frames > 0 else '?'}",
            bg="#F5F5F5",
            fg="#212121",
            font=('Segoe UI', 10)
        )
        self.preview_counter_label.pack(pady=(0, 8))

        controls = tk.Frame(self.preview_window, bg="#F5F5F5")
        controls.pack(pady=(0, 12))

        self.preview_toggle_btn = tk.Button(
            controls,
            text="⏸ Pause",
            command=self._toggle_preview_pause,
            bg=self.accent_color,
            fg="white",
            font=('Segoe UI', 10, 'bold'),
            padx=18,
            pady=8,
            border=0,
            cursor='hand2'
        )
        self.preview_toggle_btn.pack(side=tk.LEFT, padx=(0, 10))

        close_btn = tk.Button(
            controls,
            text="✕ Close",
            command=self._close_preview,
            bg="#E0E0E0",
            fg="#212121",
            font=('Segoe UI', 10),
            padx=18,
            pady=8,
            border=0,
            cursor='hand2'
        )
        close_btn.pack(side=tk.LEFT)

        fps = capture.get(cv2.CAP_PROP_FPS)
        delay_ms = int(1000 / fps) if fps and fps > 0 else 33
        cell_size = min(400 // max(width, 1), 400 // max(height, 1))
        base_x = 10
        base_y = 10

        def draw_pixel_frame():
            if self.preview_window is None or not self.preview_window.winfo_exists():
                return

            if self.preview_is_playing:
                ret, frame = capture.read()
                if not ret:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = capture.read()

                if ret:
                    self.preview_frame_index += 1
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    small = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                    canvas.delete("all")

                    for y in range(height):
                        for x in range(width):
                            b, g, r = small[y, x]
                            color = '#%02x%02x%02x' % (r, g, b)
                            canvas.create_rectangle(
                                base_x + x * cell_size,
                                base_y + y * cell_size,
                                base_x + (x + 1) * cell_size,
                                base_y + (y + 1) * cell_size,
                                fill=color,
                                outline="",
                                tags="pixel"
                            )

                    canvas.create_rectangle(
                        base_x,
                        base_y,
                        base_x + width * cell_size,
                        base_y + height * cell_size,
                        outline="#D0D0D0",
                        width=1
                    )

                    self._update_preview_counter(self.preview_frame_index)

            self.preview_job = self.preview_window.after(delay_ms, draw_pixel_frame)

        draw_pixel_frame()

    def _on_preview(self):
        """Handle preview button."""
        if not self.loaded_video_path:
            messagebox.showwarning("No Video", "Please load a video first")
            return

        self._open_video_preview(self.loaded_video_path)
    
    def _on_copy(self):
        """Handle copy button."""
        settings = self.get_settings()
        if not settings['video']:
            messagebox.showwarning("No Video", "Please load a video first")
            return
        
        # Copy settings to clipboard
        try:
            self.root.clipboard_clear()
            clipboard_text = f"Video: {settings['video']}\nCanvas: {settings['width']}×{settings['height']}"
            self.root.clipboard_append(clipboard_text)
            messagebox.showinfo("Copied", "Settings copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy: {e}")
    
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
