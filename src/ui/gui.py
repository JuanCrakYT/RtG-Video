"""
Modern GUI for RtG Video.

Professional and minimalist interface for video loading and canvas configuration.
"""

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
from pathlib import Path
from typing import Optional, Callable
import json
import os
import shutil
import subprocess
import tempfile

from src.video.processing import DEFAULT_PALETTE, normalize_palette, quantize_frame
from src.ui.base64 import encode_latest_display
from src.ui.preview.server import PreviewServer

try:
    import cv2
except ImportError:  # pragma: no cover - optional dependency for preview playback
    cv2 = None

try:
    import pygame
except ImportError:  # pragma: no cover - optional dependency for preview audio
    pygame = None

try:
    from moviepy import VideoFileClip
except ImportError:  # pragma: no cover - support older MoviePy releases
    try:
        from moviepy.editor import VideoFileClip
    except ImportError:  # pragma: no cover - optional dependency for audio extraction
        VideoFileClip = None


def _set_windows_app_user_model_id() -> None:
    """Give Windows a stable application identity instead of Python's identity."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RtG.Display")
    except (AttributeError, OSError):
        pass


def _show_startup_window(root: tk.Tk) -> tk.Toplevel:
    """Show a short-lived startup window so Windows registers the app icon."""
    startup_window = tk.Toplevel(root)
    startup_window.title("RtG Video")
    startup_window.geometry("240x90")
    startup_window.resizable(False, False)
    RtGDisplayGUI._set_window_icon(startup_window)
    tk.Label(startup_window, text="loading...", font=("Segoe UI", 10)).pack(pady=(16, 6))
    progressbar = ttk.Progressbar(startup_window, mode="indeterminate", length=180)
    progressbar.pack()
    progressbar.start(10)

    def close_startup_window():
        progressbar.stop()
        startup_window.destroy()

    startup_window.protocol("WM_DELETE_WINDOW", close_startup_window)
    startup_window.update_idletasks()
    startup_window.update()
    startup_window.after(150, close_startup_window)
    return startup_window


class RtGDisplayGUI:
    """
    Main GUI window for RtG Video application.
    """
    
    def __init__(self, root: tk.Tk):
        """
        Initialize the GUI.
        
        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("RtG Video")
        self._set_window_icon(self.root)
        self.root.geometry("760x800")
        self.root.minsize(600, 800)
        self.root.resizable(True, True)
        
        # Configure style
        self._configure_style()
        
        # State
        self.loaded_video_path: Optional[Path] = None
        self.on_video_loaded: Optional[Callable] = None
        self.on_settings_changed: Optional[Callable] = None
        self.on_generate: Optional[Callable] = None
        self.generated_json: Optional[str] = None
        self.generated_display_path: Optional[Path] = None
        self.preview_window: Optional[tk.Toplevel] = None
        self.preview_job = None
        self.preview_capture = None
        self.preview_audio_clip = None
        self.preview_audio_path = None
        self.preview_is_playing = False
        self.preview_frame_index = 0
        self.preview_total_frames = 0
        self.preview_counter_label = None
        self.preview_toggle_btn = None
        self.preview_server = None
        self.preview_process = None
        self.preview_token = None
        self.palette_colors = [list(color) for color in DEFAULT_PALETTE]
        self.asset_templates = self._discover_asset_templates()
        self.selected_asset_type = next(iter(self.asset_templates), "")
        self.pixel_base_object_count = self._load_asset_object_count(self.selected_asset_type)
        self.asset_combo = None
        self.palette_combo = None
        self._sound_cache = {}
        self._slider_sound_suppressed = False
        
        # Build GUI
        self._build_gui()
        self.root.bind_all("<ButtonPress-1>", self._on_mouse_press, add="+")
        self._center_window(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self._close_application)

    @staticmethod
    def _asset_path(name: str) -> Path:
        """Return an asset path independent of the current working directory."""
        return Path(__file__).resolve().parents[2] / "assets" / "logo" / name

    def _sound_path(self, name: str) -> Path:
        """Return the path of a UI sound effect."""
        return Path(__file__).resolve().parents[2] / "assets" / "sfx" / name

    @staticmethod
    def _discover_asset_templates() -> dict[str, Path]:
        """Return valid build JSON assets keyed by their display name."""
        asset_dir = Path(__file__).resolve().parents[2] / "assets" / "builds" / "pixel"
        templates = {}
        for template_path in sorted(asset_dir.glob("*.json")):
            try:
                with template_path.open(encoding="utf-8") as template_file:
                    template_data = json.load(template_file)
                if isinstance(template_data, list) and template_data:
                    templates[template_path.stem] = template_path
            except (OSError, TypeError, ValueError):
                continue
        return templates

    def _load_asset_object_count(self, asset_type: str) -> int:
        """Return the number of objects in the selected asset template."""
        template_path = self.asset_templates.get(asset_type)
        if template_path is None:
            return 0
        try:
            with template_path.open(encoding="utf-8") as template_file:
                return len(json.load(template_file))
        except (OSError, TypeError, ValueError):
            return 0

    def _play_sound(self, name: str) -> None:
        """Play a short UI sound without making audio a GUI requirement."""
        if pygame is None:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound = self._sound_cache.get(name)
            if sound is None:
                sound = pygame.mixer.Sound(str(self._sound_path(name)))
                self._sound_cache[name] = sound
            sound.play()
        except (OSError, pygame.error):
            return

    def _on_mouse_press(self, event):
        """Play the tap sound for buttons, including buttons in child dialogs."""
        widget = event.widget
        if isinstance(widget, str):
            try:
                widget = self.root.nametowidget(widget)
            except (KeyError, tk.TclError):
                return
        if widget.winfo_class() in {"Button", "TButton"}:
            if widget.cget("text") in {
                "Copy Base64", "+ Add", "Remove", "Custom colors..."
            }:
                return
            self._play_sound("tap.mp3")

    @classmethod
    def _set_window_icon(cls, window: tk.Misc) -> None:
        """Apply the project logo to a Tk window when the asset is available."""
        favicon_path = Path(__file__).resolve().parents[2] / "assets/logo/favicon.ico"
        logo_path = cls._asset_path("logotipe.png")

        if favicon_path.is_file():
            try:
                window.iconbitmap(default=str(favicon_path))
            except tk.TclError:
                pass

        if logo_path.is_file():
            try:
                logo_image = tk.PhotoImage(file=str(logo_path))
                resize_factor = max(1, max(logo_image.width(), logo_image.height()) // 32)
                if resize_factor > 1:
                    logo_image = logo_image.subsample(resize_factor, resize_factor)
                window._rtg_logo_image = logo_image
                window.iconphoto(True, window._rtg_logo_image)
            except tk.TclError:
                pass

    @staticmethod
    def _center_window(window: tk.Misc) -> None:
        """Center a realized window on the current screen."""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        window.geometry(f"{width}x{height}+{x}+{y}")

    def _show_message(self, title: str, message: str, message_type: str = "info") -> None:
        """Show a modal message with a left-aligned button to copy its exact body."""
        dialog = tk.Toplevel(self.root)
        self._set_window_icon(dialog)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_primary)

        content = tk.Frame(dialog, bg=self.bg_primary, padx=24, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        message_label = tk.Message(
            content,
            text=message,
            width=520,
            justify=tk.LEFT,
            bg=self.bg_primary,
            fg=self.text_primary,
            font=('Segoe UI', 10),
        )
        message_label.pack(fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(content, bg=self.bg_primary)
        button_frame.pack(fill=tk.X, pady=(18, 0))

        def copy_message():
            self.root.clipboard_clear()
            self.root.clipboard_append(message)
            copy_button.config(text="Copied")

        copy_button = tk.Button(
            button_frame,
            text="Copy",
            command=copy_message,
            bg=self.border_color,
            fg=self.text_primary,
            font=('Segoe UI', 10),
            padx=15,
            pady=8,
            border=0,
            cursor='hand2',
            activebackground='#D0D0D0',
        )
        copy_button.pack(side=tk.LEFT)

        tk.Button(
            button_frame,
            text="OK",
            command=dialog.destroy,
            bg=self.accent_color,
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            padx=20,
            pady=8,
            border=0,
            cursor='hand2',
            activebackground=self.accent_hover,
        ).pack(side=tk.RIGHT)

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.bind("<Return>", lambda _event: dialog.destroy())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self._center_window(dialog)
        dialog.grab_set()
        dialog.focus_set()
        self.root.wait_window(dialog)

    def _showinfo(self, title: str, message: str) -> None:
        self._show_message(title, message, "info")

    def _showwarning(self, title: str, message: str) -> None:
        if "no video" in f"{title} {message}".lower():
            self._play_sound("error.mp3")
        else:
            self._play_sound("notification.mp3")
        self._show_message(title, message, "warning")

    def _showerror(self, title: str, message: str) -> None:
        self._play_sound("error.mp3")
        self._show_message(title, message, "error")
    
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
            text="RtG Video",
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

        # Color palette card
        self._build_palette_card(main_frame)
        
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

        asset_frame = tk.Frame(content, bg=self.bg_secondary)
        asset_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            asset_frame,
            text="Asset Type",
            font=('Segoe UI', 10),
            bg=self.bg_secondary,
            fg=self.text_primary,
        ).pack(side=tk.LEFT)

        self.asset_combo = ttk.Combobox(
            asset_frame,
            state="readonly",
            values=list(self.asset_templates),
            width=28,
        )
        if self.selected_asset_type:
            self.asset_combo.set(self.selected_asset_type)
        self.asset_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(20, 0))
        self.asset_combo.bind("<<ComboboxSelected>>", self._on_asset_type_changed)
        
        # Width slider
        self._build_slider(
            content,
            "Width",
            2, 128, 8,
            self._on_width_changed,
            "width_value"
        )
        
        # Height slider
        self._build_slider(
            content,
            "Height",
            2, 128, 8,
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

        self.total_objects_label = tk.Label(
            output_frame,
            text="0 total objects",
            font=('Segoe UI', 9, 'bold'),
            bg=self.bg_secondary,
            fg=self.accent_color
        )
        self.total_objects_label.pack(side=tk.RIGHT)
        self._update_output_size()
    
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
        
        value_widget = tk.Entry(
            label_frame,
            width=5,
            font=('Segoe UI', 10, 'bold'),
            bg=self.bg_secondary,
            fg=self.accent_color
        )
        value_widget.insert(0, str(default_val))
        value_widget.pack(side=tk.RIGHT)
        
        # Store value widget
        setattr(self, attr_name, value_widget)
        
        # Slider
        def on_slider_change(val):
            slider_value = int(float(val))
            value_widget.delete(0, tk.END)
            value_widget.insert(0, str(slider_value))
            if self._slider_sound_suppressed:
                self._slider_sound_suppressed = False
            else:
                self._play_sound("slider.mp3")
            on_change(slider_value)

        def on_value_confirm(_event=None):
            try:
                input_value = int(value_widget.get())
            except ValueError:
                input_value = int(slider.get())

            input_value = max(min_val, min(max_val, input_value))
            changed = input_value != int(slider.get())
            value_widget.delete(0, tk.END)
            value_widget.insert(0, str(input_value))
            self._slider_sound_suppressed = changed
            slider.set(input_value)
            if changed:
                self._play_sound("tap.mp3")
            return "break"

        value_widget.bind("<Return>", on_value_confirm)
        value_widget.bind("<FocusOut>", on_value_confirm)
        
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

    def _build_palette_card(self, parent):
        """Build the editable quantization palette, keeping black mandatory."""
        card_frame = ttk.Frame(parent, relief='solid', borderwidth=1)
        card_frame.pack(fill=tk.X, pady=(0, 15))

        content = tk.Frame(card_frame, bg=self.bg_secondary)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        tk.Label(
            content,
            text="Color Palette",
            font=('Segoe UI', 11, 'bold'),
            bg=self.bg_secondary,
            fg=self.text_primary
        ).pack(anchor='w', pady=(0, 10))

        controls = tk.Frame(content, bg=self.bg_secondary)
        controls.pack(fill=tk.X)

        self.palette_combo = ttk.Combobox(
            controls,
            state="readonly",
            values=self._palette_labels(),
            width=34
        )
        self.palette_combo.current(0)
        self.palette_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.palette_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._play_sound("tap.mp3")
        )

        tk.Button(
            controls,
            text="+ Add",
            command=self._add_palette_color,
            bg=self.accent_color,
            fg="white",
            border=0,
            padx=12,
            pady=5,
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=(8, 0))

        tk.Button(
            controls,
            text="Remove",
            command=self._remove_palette_color,
            bg=self.border_color,
            fg=self.text_primary,
            border=0,
            padx=12,
            pady=5,
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=(8, 0))

    def _palette_labels(self):
        return [
            f"#{red:02X}{green:02X}{blue:02X} ({red}, {green}, {blue})"
            for red, green, blue in self.palette_colors
        ]

    def _refresh_palette_combo(self):
        if self.palette_combo is not None:
            self.palette_combo["values"] = self._palette_labels()
            self.palette_combo.current(0)

    def _show_palette_color_dialog(self):
        """Open the RGB editor used to add a custom palette color."""
        dialog = tk.Toplevel(self.root)
        self._set_window_icon(dialog)
        dialog.title("Add palette color")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.configure(bg=self.bg_primary)

        content = tk.Frame(dialog, bg=self.bg_primary, padx=20, pady=18)
        content.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            content,
            text="Custom color",
            font=("Segoe UI", 11, "bold"),
            bg=self.bg_primary,
            fg=self.text_primary,
        ).pack(anchor="w", pady=(0, 12))

        fields = {}
        fields_frame = tk.Frame(content, bg=self.bg_primary)
        fields_frame.pack(fill=tk.X)
        for channel in ("Red", "Green", "Blue"):
            field_frame = tk.Frame(fields_frame, bg=self.bg_primary)
            field_frame.pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(
                field_frame,
                text=channel,
                bg=self.bg_primary,
                fg=self.text_secondary,
                font=("Segoe UI", 9),
            ).pack()
            entry = tk.Entry(field_frame, width=5, justify=tk.CENTER)
            entry.insert(0, "255")
            entry.pack(pady=(4, 0))
            entry.bind("<ButtonPress-1>", lambda _event: self._play_sound("tap.mp3"))
            fields[channel] = entry

        def choose_custom_color():
            self._play_sound("tap.mp3")
            selected = colorchooser.askcolor(parent=dialog, title="Custom color")
            if selected[0] is None:
                return
            for channel, value in zip(("Red", "Green", "Blue"), selected[0]):
                fields[channel].delete(0, tk.END)
                fields[channel].insert(0, str(int(value)))

        tk.Button(
            content,
            text="Custom colors...",
            command=choose_custom_color,
            bg=self.border_color,
            fg=self.text_primary,
            border=0,
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(anchor="w", pady=(14, 0))

        result = {"color": None}

        def accept_color():
            try:
                color = tuple(
                    max(0, min(255, int(fields[channel].get())))
                    for channel in ("Red", "Green", "Blue")
                )
            except ValueError:
                self._showwarning("Invalid color", "RGB values must be numbers from 0 to 255.")
                return
            result["color"] = color
            dialog.destroy()

        buttons = tk.Frame(content, bg=self.bg_primary)
        buttons.pack(fill=tk.X, pady=(18, 0))
        tk.Button(
            buttons,
            text="Cancel",
            command=dialog.destroy,
            bg=self.border_color,
            fg=self.text_primary,
            border=0,
            padx=14,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.RIGHT)
        tk.Button(
            buttons,
            text="Accept",
            command=accept_color,
            bg=self.accent_color,
            fg="white",
            border=0,
            padx=14,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.RIGHT, padx=(0, 8))

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.bind("<Return>", lambda _event: accept_color())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self._center_window(dialog)
        dialog.grab_set()
        dialog.focus_set()
        self.root.wait_window(dialog)
        return result["color"]

    def _add_palette_color(self):
        self._play_sound("notification.mp3")
        selected_color = self._show_palette_color_dialog()
        if selected_color is None:
            return
        self.palette_colors = [list(color) for color in normalize_palette(
            self.palette_colors + [selected_color]
        )]
        self._refresh_palette_combo()
        self._update_output_size()

    def _remove_palette_color(self):
        if self.palette_combo is None:
            return
        selected_index = self.palette_combo.current()
        if selected_index <= 0:
            self._showinfo("Required color", "Black is always required in the palette.")
            return
        self.palette_colors.pop(selected_index)
        self._refresh_palette_combo()
        self._update_output_size()
        self._play_sound("notification.mp3")
    
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
            text="📋 Copy JSON",
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

        # Base64 copy button
        base64_btn = tk.Button(
            left_frame,
            text="Copy Base64",
            command=self._on_copy_base64,
            bg=self.border_color,
            fg=self.text_primary,
            font=('Segoe UI', 10),
            padx=15,
            pady=10,
            border=0,
            cursor='hand2',
            activebackground='#D0D0D0'
        )
        base64_btn.pack(side=tk.LEFT, padx=(0, 5))
        
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
            text="✨ Generate canvas",
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

            self.preview_total_frames = 0
            if cv2 is not None:
                capture = cv2.VideoCapture(str(self.loaded_video_path))
                if capture.isOpened():
                    self.preview_total_frames = int(
                        capture.get(cv2.CAP_PROP_FRAME_COUNT)
                    ) or 0
                capture.release()
            self._update_output_size()
            
            if self.on_video_loaded:
                self.on_video_loaded(file_path)
    
    def _on_width_changed(self, value: int):
        """Handle width slider change."""
        self._update_output_size()
        if self.on_settings_changed:
            width = getattr(self, 'width_value_slider').get()
            height = getattr(self, 'height_value_slider').get()
            self.on_settings_changed({'width': width, 'height': height})

    def _on_asset_type_changed(self, _event=None):
        """Apply the selected asset template to generation settings."""
        if self.asset_combo is None:
            return
        self.selected_asset_type = self.asset_combo.get()
        self.pixel_base_object_count = self._load_asset_object_count(self.selected_asset_type)
        self._update_output_size()
        if self.on_settings_changed:
            self.on_settings_changed({'pixel_template': str(self.asset_templates[self.selected_asset_type])})
    
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
        non_black_colors = sum(
            tuple(color) != (0, 0, 0)
            for color in self.palette_colors
        )
        total = width * height * non_black_colors
        black_pixels = width * height
        total_objects = (
            total * self.pixel_base_object_count
            + 2
            + 2 * self.preview_total_frames
        )
        self.output_size_label.config(
            text=(
                f"{width} × {height} × {non_black_colors} "
                f"({total} pixels, just {black_pixels} black pixels)"
            )
        )
        self.total_objects_label.config(text=f"{total_objects} total objects")
    
    def _close_preview(self):
        """Stop preview playback and close the preview window."""
        self.preview_is_playing = False

        if self.preview_job is not None and self.preview_window is not None and self.preview_window.winfo_exists():
            self.preview_window.after_cancel(self.preview_job)
        self.preview_job = None

        if self.preview_capture is not None:
            self.preview_capture.release()
            self.preview_capture = None

        if pygame is not None and pygame.mixer.get_init():
            pygame.mixer.music.stop()

        if self.preview_audio_clip is not None:
            self.preview_audio_clip.close()
            self.preview_audio_clip = None

        if self.preview_audio_path is not None:
            try:
                os.unlink(self.preview_audio_path)
            except OSError:
                pass
            self.preview_audio_path = None

        if self.preview_window is not None and self.preview_window.winfo_exists():
            self.preview_window.destroy()
        self.preview_window = None

    def _close_application(self):
        """Close preview windows and the local Preview server."""
        self._close_preview()
        self._close_javascript_preview()
        if self.preview_server is not None:
            self.preview_server.close()
            self.preview_server = None
        self.root.destroy()

    def _close_javascript_preview(self):
        """Close the independent Electron Preview process, if it is running."""
        if self.preview_server is not None and self.preview_token is not None:
            self.preview_server.send_event(
                self.preview_token,
                {"type": "close", "source": "main-window"},
            )
        if self.preview_process is None:
            self.preview_token = None
            return
        if self.preview_process.poll() is None:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(self.preview_process.pid), "/T", "/F"],
                    capture_output=True,
                    check=False,
                )
            else:
                self.preview_process.terminate()
                try:
                    self.preview_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.preview_process.kill()
        self.preview_process = None
        self.preview_token = None

    def _open_javascript_preview(self, video_path: Path):
        """Open the production JavaScript Preview in an independent Electron window."""
        self._close_javascript_preview()
        if self.preview_server is None:
            self.preview_server = PreviewServer()
        token = self.preview_server.register_video(video_path)
        self.preview_token = token
        width = max(2, min(128, int(getattr(self, "width_value").get())))
        height = max(2, min(128, int(getattr(self, "height_value").get())))
        url = self.preview_server.url(token, width, height, self.palette_colors)
        project_root = Path(__file__).resolve().parents[2]
        electron_entry = project_root / "src" / "ui" / "preview" / "electron_main.cjs"
        local_electron = project_root / "node_modules" / "electron" / "dist" / "electron.exe"
        if local_electron.is_file():
            command = [str(local_electron), str(electron_entry)]
        else:
            npx = shutil.which("npx.cmd") or shutil.which("npx")
            if npx is None:
                raise RuntimeError("Node.js and Electron are required for the JavaScript Preview")
            command = [npx, "--no-install", "electron", str(electron_entry)]
        environment = os.environ.copy()
        environment["RTG_PREVIEW_URL"] = url
        try:
            self.preview_process = subprocess.Popen(
                command,
                cwd=str(project_root),
                env=environment,
            )
        except OSError as error:
            raise RuntimeError(f"Could not start Electron: {error}") from error

    def _toggle_preview_pause(self):
        """Toggle pause/play state for the preview loop."""
        if self.preview_window is None or not self.preview_window.winfo_exists():
            return

        self.preview_is_playing = not self.preview_is_playing
        if pygame is not None and pygame.mixer.get_init():
            if self.preview_is_playing:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()
        if self.preview_toggle_btn is not None:
            self.preview_toggle_btn.config(text="⏸ Pause" if self.preview_is_playing else "▶ Play")

    def _start_preview_audio(self, video_path: Path):
        """Extract and start the video's audio, if the optional audio stack is available."""
        if pygame is None or VideoFileClip is None:
            self._showwarning(
                "Audio unavailable",
                "Install the preview audio dependencies with: pip install -r requirements.txt"
            )
            return False

        try:
            self.preview_audio_clip = VideoFileClip(str(video_path))
            if self.preview_audio_clip.audio is None:
                self.preview_audio_clip.close()
                self.preview_audio_clip = None
                return False

            audio_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            audio_file.close()
            self.preview_audio_path = audio_file.name
            self.preview_audio_clip.audio.write_audiofile(
                self.preview_audio_path,
                codec="pcm_s16le",
                logger=None
            )
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(self.preview_audio_path)
            pygame.mixer.music.play(loops=-1)
            return True
        except Exception as error:
            if self.preview_audio_clip is not None:
                self.preview_audio_clip.close()
                self.preview_audio_clip = None
            if self.preview_audio_path is not None:
                try:
                    os.unlink(self.preview_audio_path)
                except OSError:
                    pass
                self.preview_audio_path = None
            self._showwarning(
                "Audio unavailable",
                f"Could not load the video's audio: {error}"
            )
            return False

    def _update_preview_counter(self, frame_number: int):
        """Update the preview frame counter label."""
        if self.preview_counter_label is not None and self.preview_window is not None and self.preview_window.winfo_exists():
            total = self.preview_total_frames if self.preview_total_frames > 0 else "?"
            self.preview_counter_label.config(text=f"Frame: {frame_number} / {total}")

    def _open_video_preview(self, video_path: Path):
        """Open a separate window that replays the video as a low-resolution RtG pixel preview."""
        if cv2 is None:
            self._showerror(
                "Preview unavailable",
                "OpenCV is required for the preview. Install it with: pip install opencv-python"
            )
            return

        if self.preview_window is not None and self.preview_window.winfo_exists():
            self._close_preview()

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            self._showerror(
                "Preview failed",
                f"Could not open video: {video_path.name}"
            )
            return

        self.preview_capture = capture
        self.preview_window = tk.Toplevel(self.root)
        self._set_window_icon(self.preview_window)
        self.preview_window.title(f"RtG Preview - {video_path.name}")
        self.preview_window.geometry("560x520")
        self.preview_window.resizable(False, False)
        self.preview_window.protocol("WM_DELETE_WINDOW", self._close_preview)

        width = getattr(self, 'width_value_slider').get()
        height = getattr(self, 'height_value_slider').get()
        self.preview_is_playing = True
        self.preview_frame_index = 0
        self.preview_total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        audio_is_playing = self._start_preview_audio(video_path)

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
                if audio_is_playing and pygame is not None:
                    audio_position_ms = pygame.mixer.music.get_pos()
                    target_frame = int(max(audio_position_ms, 0) * fps / 1000)
                    if self.preview_total_frames > 0:
                        target_frame %= self.preview_total_frames
                    if target_frame < self.preview_frame_index:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    elif target_frame > self.preview_frame_index + 1:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

                ret, frame = capture.read()
                if not ret:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = capture.read()

                if ret:
                    self.preview_frame_index = int(capture.get(cv2.CAP_PROP_POS_FRAMES))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    quantized_frame = quantize_frame(
                        frame,
                        width,
                        height,
                        self.palette_colors,
                    )
                    canvas.delete("all")

                    for y in range(height):
                        for x in range(width):
                            red, green, blue = quantized_frame[y][x]
                            color = '#%02x%02x%02x' % (red, green, blue)
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
            self._showwarning("No Video", "Please load a video first")
            return

        try:
            self._open_javascript_preview(self.loaded_video_path)
        except Exception as error:
            self._showwarning(
                "JavaScript Preview unavailable",
                f"{error}\n\nFalling back to the Python Preview.",
            )
            self._open_video_preview(self.loaded_video_path)
    
    def _on_copy(self):
        """Handle copy button."""
        if self.generated_display_path is None or not self.generated_display_path.is_file():
            self._showwarning("No canvas", "Generate a canvas first")
            return
        
        try:
            self.generated_json = self.generated_display_path.read_text(encoding="utf-8")
            self.root.clipboard_clear()
            self.root.clipboard_append(self.generated_json)
            self._showinfo("Copied", "display.json copied to clipboard!")
        except Exception as e:
            self._showerror("Error", f"Failed to copy: {e}")

    def _on_copy_base64(self):
        """Encode the latest display JSON, save it, and copy it to the clipboard."""
        try:
            encoded_json = encode_latest_display(self.generated_display_path)
            self.root.clipboard_clear()
            self.root.clipboard_append(encoded_json)
            self._play_sound("notification.mp3")
            self._showinfo("Copied", "Base64 saved to output/base64.json and copied to clipboard!")
        except Exception as error:
            self._showerror("Base64 failed", str(error))
    
    def _on_generate(self):
        """Handle generate button."""
        width = getattr(self, 'width_value_slider').get()
        height = getattr(self, 'height_value_slider').get()
        
        if self.on_generate:
            try:
                output_paths = self.on_generate(self.get_settings())
                self.generated_json = output_paths.get('json')
                self.generated_display_path = Path(output_paths['display'])
                self._showinfo(
                    "Generated",
                    f"Generated physical canvas {width}×{height}\n"
                    f"Display exported to: {output_paths['display']}"
                )
            except Exception as error:
                self._showerror("Generation failed", str(error))
            return

        self._showinfo("Generate", f"Canvas configured: {width}×{height}")
    
    def get_settings(self) -> dict:
        """Get current settings."""
        return {
            'video': str(self.loaded_video_path) if self.loaded_video_path else None,
            'width': getattr(self, 'width_value_slider').get(),
            'height': getattr(self, 'height_value_slider').get(),
            'palette': [color.copy() for color in self.palette_colors],
            'pixel_template': str(self.asset_templates[self.selected_asset_type]),
        }
    
    def run(self):
        """Run the GUI."""
        self.root.mainloop()


def launch_gui(on_video_loaded=None, on_settings_changed=None, on_generate=None):
    """
    Launch the RtG Video GUI.
    
    Args:
        on_video_loaded: Callback function when video is loaded
        on_settings_changed: Callback function when settings change
    """
    _set_windows_app_user_model_id()
    root = tk.Tk()
    root.withdraw()
    _show_startup_window(root)
    gui = RtGDisplayGUI(root)
    gui.on_video_loaded = on_video_loaded
    gui.on_settings_changed = on_settings_changed
    gui.on_generate = on_generate
    root.deiconify()
    gui.run()
