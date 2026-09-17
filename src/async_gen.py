"""
Asynchronous generation system for RtG Video.

Uses a worker thread for heavy generation tasks and a thread-safe queue
to communicate progress back to the main GUI thread.
"""

import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class GenerationStage(Enum):
    """Stages of the generation pipeline."""
    PREPARATION = ("Preparación", "Inicializando...")
    CANVAS = ("Canvas", "Generando matriz de píxeles...")
    TIMELINE = ("Timeline", "Construyendo timeline de animación...")
    GATE_OR = ("Gate-OR", "Creando tabla física de Gate-OR...")
    SIGNAL_NETWORK = ("Red de señales", "Construyendo red de señales...")
    VALIDATION = ("Validación", "Validando build...")
    EXPORT = ("Exportación", "Exportando JSON...")

    def __init__(self, name: str, description: str):
        self.stage_name = name
        self.description = description


@dataclass
class StageProgress:
    """Progress information for a single stage."""
    stage: GenerationStage
    status: str = "pending"  # pending, active, completed, error
    current: int = 0
    total: int = 0
    detail: str = ""


@dataclass
class ProgressUpdate:
    """Progress update from worker to main thread."""
    stage: Optional[GenerationStage] = None
    stage_progress: Optional[StageProgress] = None
    overall_percent: float = 0.0
    elapsed_time: float = 0.0
    message: str = ""
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    finished: bool = False
    # Block count tracking
    blocks_current: int = 0
    blocks_total: int = 0


class GenerationWorker:
    """
    Worker thread that runs the generation and reports progress.
    
    The worker communicates with the main thread via a queue.Queue.
    The main thread should call process_queue() periodically to handle updates.
    """
    
    # Approximate weight of each stage for overall percentage calculation
    STAGE_WEIGHTS = {
        GenerationStage.PREPARATION: 0.05,
        GenerationStage.CANVAS: 0.15,
        GenerationStage.TIMELINE: 0.15,
        GenerationStage.GATE_OR: 0.10,
        GenerationStage.SIGNAL_NETWORK: 0.30,
        GenerationStage.VALIDATION: 0.10,
        GenerationStage.EXPORT: 0.15,
    }
    
    def __init__(self, progress_queue: queue.Queue, settings: Dict[str, Any]):
        self.progress_queue = progress_queue
        self.settings = settings
        self.start_time = 0.0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Stage progress tracking
        self.stage_progress: Dict[GenerationStage, StageProgress] = {}
        for stage in GenerationStage:
            self.stage_progress[stage] = StageProgress(stage=stage)
    
    def _send_update(self, **kwargs):
        """Send a progress update to the main thread."""
        elapsed = time.perf_counter() - self.start_time if self.start_time else 0.0
        update = ProgressUpdate(
            elapsed_time=elapsed,
            **kwargs
        )
        self.progress_queue.put(update)
    
    def _update_stage(self, stage: GenerationStage, status: str = None, 
                      current: int = None, total: int = None, detail: str = None,
                      blocks_current: int = None, blocks_total: int = None):
        """Update progress for a specific stage."""
        prog = self.stage_progress[stage]
        if status:
            prog.status = status
        if current is not None:
            prog.current = current
        if total is not None:
            prog.total = total
        if detail is not None:
            prog.detail = detail
        self._send_update(stage=stage, stage_progress=prog, 
                          overall_percent=self._calculate_overall(),
                          blocks_current=blocks_current or 0,
                          blocks_total=blocks_total or 0)
    
    def update_blocks(self, blocks_current: int, blocks_total: int = None):
        """Update block count without changing stage progress."""
        self._send_update(blocks_current=blocks_current, blocks_total=blocks_total or 0)
    
    def _calculate_overall(self) -> float:
        """Calculate overall progress percentage."""
        total = 0.0
        for stage, weight in self.STAGE_WEIGHTS.items():
            prog = self.stage_progress[stage]
            if prog.status == "completed":
                total += weight * 100
            elif prog.status == "active" and prog.total > 0:
                total += weight * (prog.current / prog.total * 100)
        return min(total, 100.0)
    
    def start(self, target: Callable, *args, **kwargs):
        """Start the worker thread."""
        self.start_time = time.perf_counter()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_wrapper,
            args=(target, args, kwargs),
            daemon=True
        )
        self._thread.start()
    
    def _run_wrapper(self, target: Callable, args: tuple, kwargs: dict):
        """Wrapper that catches exceptions and reports them."""
        try:
            result = target(*args, **kwargs)
            self._send_update(finished=True, result=result, overall_percent=100.0)
        except Exception as e:
            import traceback
            self._send_update(
                finished=True,
                error=f"{type(e).__name__}: {e}",
                overall_percent=0.0
            )
    
    def stop(self):
        """Request the worker to stop."""
        self._stop_event.set()
    
    def is_alive(self) -> bool:
        """Check if the worker thread is still running."""
        return self._thread is not None and self._thread.is_alive()
    
    def join(self, timeout: float = None):
        """Wait for the worker thread to finish."""
        if self._thread:
            self._thread.join(timeout)


class ProgressWindow:
    """
    Progress window for displaying generation status.
    
    This window is shown on the main thread and updated by processing
    messages from the worker's progress queue.
    """
    
    def __init__(self, parent, title: str = "Generando build..."):
        import tkinter as tk
        from tkinter import ttk
        
        self.parent = parent
        self.title = title
        self.window: Optional[tk.Toplevel] = None
        self.progress_queue: Optional[queue.Queue] = None
        self.worker: Optional[GenerationWorker] = None
        self.generation_thread: Optional[threading.Thread] = None
        self.on_finish_callback: Optional[Callable] = None
        self.start_time = 0.0
        self._finished = False
        
        # UI components
        self.stage_label: Optional[tk.Label] = None
        self.status_label: Optional[tk.Label] = None
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.percent_label: Optional[tk.Label] = None
        self.time_label: Optional[tk.Label] = None
        self.blocks_label: Optional[tk.Label] = None
        self.stage_listbox: Optional[tk.Listbox] = None
        self.close_btn: Optional[tk.Button] = None
        
        # Stage items for listbox
        self.stage_items: Dict[GenerationStage, int] = {}
    
    def show(self, progress_queue: queue.Queue, worker: GenerationWorker, 
             on_finish: Callable = None):
        """Show the progress window and start polling."""
        import tkinter as tk
        from tkinter import ttk
        
        self.progress_queue = progress_queue
        self.worker = worker
        self.on_finish_callback = on_finish
        self.start_time = time.perf_counter()
        self._finished = False
        
        self.window = tk.Toplevel(self.parent)
        self.window.title(self.title)
        self.window.transient(self.parent)
        self.window.resizable(False, False)
        self.window.configure(bg="#F5F5F5")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close_attempt)
        
        # Build UI
        self._build_ui()
        
        # Center on screen
        self._center_window()
        
        # Make modal
        self.window.grab_set()
        self.window.focus_set()
        
        # Start polling queue
        self._poll_queue()
    
    def _build_ui(self):
        """Build the progress window UI."""
        import tkinter as tk
        from tkinter import ttk
        
        main_frame = tk.Frame(self.window, bg="#F5F5F5", padx=24, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text=self.title,
            font=('Segoe UI', 12, 'bold'),
            bg="#F5F5F5",
            fg="#212121"
        )
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Active script/section
        script_frame = tk.Frame(main_frame, bg="#F5F5F5")
        script_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            script_frame,
            text="Script activo:",
            font=('Segoe UI', 9),
            bg="#F5F5F5",
            fg="#757575"
        ).pack(anchor='w')
        
        self.stage_label = tk.Label(
            script_frame,
            text="Iniciando...",
            font=('Segoe UI', 10, 'bold'),
            bg="#F5F5F5",
            fg="#2196F3"
        )
        self.stage_label.pack(anchor='w', pady=(2, 0))
        
        # Status/description
        status_frame = tk.Frame(main_frame, bg="#F5F5F5")
        status_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            status_frame,
            text="Estado:",
            font=('Segoe UI', 9),
            bg="#F5F5F5",
            fg="#757575"
        ).pack(anchor='w')
        
        self.status_label = tk.Label(
            status_frame,
            text="Preparando...",
            font=('Segoe UI', 9),
            bg="#F5F5F5",
            fg="#212121",
            wraplength=500,
            justify=tk.LEFT
        )
        self.status_label.pack(anchor='w', pady=(2, 0))
        
        # Progress bar and percentage
        progress_frame = tk.Frame(main_frame, bg="#F5F5F5")
        progress_frame.pack(fill=tk.X, pady=(10, 8))
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=500
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.percent_label = tk.Label(
            progress_frame,
            text="0%",
            font=('Segoe UI', 10, 'bold'),
            bg="#F5F5F5",
            fg="#2196F3"
        )
        self.percent_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Stage list
        list_frame = tk.Frame(main_frame, bg="#F5F5F5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 8))
        
        tk.Label(
            list_frame,
            text="Etapas:",
            font=('Segoe UI', 9),
            bg="#F5F5F5",
            fg="#757575"
        ).pack(anchor='w')
        
        self.stage_listbox = tk.Listbox(
            list_frame,
            font=('Consolas', 9),
            bg="#FFFFFF",
            fg="#212121",
            selectbackground="#E3F2FD",
            selectforeground="#212121",
            borderwidth=1,
            relief='solid',
            height=7,
            activestyle='none'
        )
        self.stage_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Populate stages
        for stage in GenerationStage:
            idx = self.stage_listbox.size()
            self.stage_listbox.insert(tk.END, f"  ○  {stage.value[0]}: pendiente")
            self.stage_items[stage] = idx
        
        # Elapsed time
        time_frame = tk.Frame(main_frame, bg="#F5F5F5")
        time_frame.pack(fill=tk.X, pady=(8, 0))
        
        self.time_label = tk.Label(
            time_frame,
            text="Tiempo transcurrido: 0.00 s",
            font=('Segoe UI', 9),
            bg="#F5F5F5",
            fg="#757575"
        )
        self.time_label.pack(side=tk.LEFT)
        
        # Close button (initially disabled)
        self.close_btn = tk.Button(
            time_frame,
            text="Cerrar",
            command=self._on_close,
            bg="#E0E0E0",
            fg="#212121",
            font=('Segoe UI', 10),
            padx=20,
            pady=6,
            border=0,
            cursor='hand2',
            state=tk.DISABLED
        )
        self.close_btn.pack(side=tk.RIGHT)
    
    def _center_window(self):
        """Center the window on screen."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2, 0)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
    
    def _poll_queue(self):
        """Poll the progress queue for updates."""
        import tkinter as tk
        
        if not self.progress_queue:
            return
        
        try:
            while True:
                update = self.progress_queue.get_nowait()
                self._handle_update(update)
        except queue.Empty:
            pass
        
        # Update elapsed time only while generation is running
        if not self._finished and self.worker and self.worker.start_time:
            elapsed = time.perf_counter() - self.worker.start_time
            if self.time_label:
                self.time_label.config(text=f"Tiempo transcurrido: {elapsed:.2f} s")
        
        # Schedule next poll only if not finished
        if self.window and self.window.winfo_exists() and not self._finished:
            self.window.after(50, self._poll_queue)
    
    def _handle_update(self, update: ProgressUpdate):
        """Handle a progress update from the worker."""
        import tkinter as tk
        
        # Update overall progress
        if self.progress_bar:
            self.progress_bar['value'] = update.overall_percent
        if self.percent_label:
            self.percent_label.config(text=f"{update.overall_percent:.0f}%")
        
        # Update active stage
        if update.stage:
            self.stage_label.config(text=update.stage.value[0])
        
        # Update status/description
        if update.stage_progress:
            sp = update.stage_progress
            if sp.status == "active":
                self.status_label.config(text=sp.detail or sp.stage.value[1])
            elif sp.status == "completed":
                self.status_label.config(text=f"{sp.stage.value[0]} completado")
            elif sp.status == "error":
                self.status_label.config(text=f"Error en {sp.stage.value[0]}: {sp.detail}")
        
        # Update stage list
        if update.stage_progress and self.stage_listbox:
            sp = update.stage_progress
            idx = self.stage_items.get(sp.stage)
            if idx is not None:
                if sp.status == "pending":
                    prefix = "  ○  "
                elif sp.status == "active":
                    prefix = "  ●  "
                elif sp.status == "completed":
                    prefix = "  ✓  "
                elif sp.status == "error":
                    prefix = "  ✗  "
                else:
                    prefix = "  ○  "
                
                detail = f" ({sp.detail})" if sp.detail else ""
                self.stage_listbox.delete(idx)
                self.stage_listbox.insert(idx, f"{prefix}{sp.stage.value[0]}: {sp.status}{detail}")
                self.stage_listbox.see(idx)
        
        # Handle error
        if update.error:
            self._show_error(update.error)
        
        # Handle completion
        if update.finished:
            self._on_finished(update)
    
    def _show_error(self, error_msg: str):
        """Show error state."""
        import tkinter as tk
        from tkinter import messagebox
        
        if self.stage_label:
            self.stage_label.config(text="Error", fg="#F44336")
        if self.status_label:
            self.status_label.config(text=error_msg, fg="#F44336")
        if self.close_btn:
            self.close_btn.config(state=tk.NORMAL, bg="#F44336", fg="white")
        if self.progress_bar:
            self.progress_bar['value'] = 0
        
        messagebox.showerror("Error de generación", error_msg, parent=self.window)
    
    def _on_finished(self, update: ProgressUpdate):
        """Handle generation completion."""
        import tkinter as tk
        
        self._finished = True
        elapsed = time.perf_counter() - self.start_time
        if self.time_label:
            self.time_label.config(text=f"Tiempo total: {elapsed:.2f} s")
        
        if update.error:
            if self.stage_label:
                self.stage_label.config(text="Error", fg="#F44336")
            if self.close_btn:
                self.close_btn.config(state=tk.NORMAL, bg="#F44336", fg="white")
        else:
            if self.stage_label:
                self.stage_label.config(text="Completado", fg="#4CAF50")
            if self.status_label:
                self.status_label.config(text="Generación finalizada correctamente")
            if self.close_btn:
                self.close_btn.config(
                    state=tk.NORMAL,
                    bg="#4CAF50",
                    fg="white",
                    activebackground="#388E3C"
                )
            if self.progress_bar:
                self.progress_bar['value'] = 100
            if self.percent_label:
                self.percent_label.config(text="100%")
        
        if self.on_finish_callback and not update.error:
            self.on_finish_callback(update.result)
    
    def _on_close_attempt(self):
        """Handle window close attempt."""
        import tkinter as tk
        if self.worker and self.worker.is_alive():
            # Don't allow close while running
            pass
        else:
            self._on_close()
    
    def _on_close(self):
        """Close the progress window."""
        if self.window:
            self.window.grab_release()
            self.window.destroy()
            self.window = None


def run_async_generation(
    parent,
    settings: Dict[str, Any],
    generate_func: Callable,
    on_complete: Callable
):
    """
    Run generation asynchronously with a progress window.
    
    Args:
        parent: Parent tkinter window
        settings: Settings dict for generation
        generate_func: Function to run in worker thread (receives settings + progress callback + block callback)
        on_complete: Callback when generation finishes (receives result dict or None on error)
    """
    progress_queue = queue.Queue()
    worker = GenerationWorker(progress_queue, settings)
    
    def worker_target():
        # The generate_func will be called with a progress callback and block callback
        def progress_callback(stage: GenerationStage, status: str = None, 
                              current: int = None, total: int = None, detail: str = None):
            worker._update_stage(stage, status, current, total, detail)
        
        def block_callback(blocks_current: int, blocks_total: int = None):
            worker.update_blocks(blocks_current, blocks_total)
        
        return generate_func(settings, progress_callback, block_callback)
    
    progress_window = ProgressWindow(parent)
    progress_window.show(progress_queue, worker, on_complete)
    worker.start(worker_target)


def wrap_generation_for_async(generate_func: Callable) -> Callable:
    """
    Wrap a synchronous generation function to support async progress reporting.
    
    The wrapped function will receive (settings, progress_callback) and should
    call progress_callback at appropriate stages.
    """
    def async_wrapper(settings: Dict[str, Any], progress_callback: Callable):
        return generate_func(settings, progress_callback)
    return async_wrapper