from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.analysis import analyze_array
from core.recorder import StreamRecorder, load_file
from core.report import pitch_contour_figure, text_summary


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Clarity")
        self.geometry("1060x700")
        self.minsize(800, 500)
        self._canvas_widget: tk.Widget | None = None
        self._recording = False
        self._recorder = StreamRecorder()
        self._build_ui()
        self.after(100, self._set_sash)

    def _build_ui(self) -> None:
        ctrl = ttk.Frame(self, padding=(12, 10))
        ctrl.pack(fill="x")

        # Input mode toggle
        self._mode = tk.StringVar(value="file")
        ttk.Radiobutton(
            ctrl, text="File", variable=self._mode, value="file", command=self._toggle_mode
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            ctrl, text="Microphone", variable=self._mode, value="record", command=self._toggle_mode
        ).grid(row=0, column=1, sticky="w", padx=(8, 0))

        # File input row
        self._file_row = ttk.Frame(ctrl)
        self._file_row.grid(row=1, column=0, columnspan=6, sticky="ew", pady=6)
        self._filepath = tk.StringVar()
        ttk.Entry(self._file_row, textvariable=self._filepath, width=55).pack(side="left", padx=(0, 6))
        ttk.Button(self._file_row, text="Browse...", command=self._browse).pack(side="left")

        # Mic row (no controls needed — button handles everything)
        self._rec_row = ttk.Frame(ctrl)
        self._rec_row.grid(row=1, column=0, columnspan=6, sticky="ew", pady=6)
        ttk.Label(self._rec_row, text="Press the button to start recording.").pack(side="left")

        # Action button + status
        self._btn_text = tk.StringVar(value="Analyze")
        self._btn = ttk.Button(ctrl, textvariable=self._btn_text, command=self._run)
        self._btn.grid(row=2, column=0, pady=(4, 0), sticky="w")
        self._status = tk.StringVar(value="Ready.")
        ttk.Label(ctrl, textvariable=self._status, foreground="gray").grid(
            row=2, column=1, padx=10, sticky="w"
        )

        self._toggle_mode()

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=12, pady=(6, 0))

        # Output panes
        self._paned = ttk.PanedWindow(self, orient="horizontal")
        self._paned.pack(fill="both", expand=True, padx=12, pady=8)

        # Left: text report
        left = ttk.Frame(self._paned)
        self._paned.add(left, weight=1)

        self._report_text = tk.Text(
            left, wrap="word", font=("Courier New", 10), state="disabled",
            relief="flat", background="#f8f8f8",
        )
        vsb = ttk.Scrollbar(left, command=self._report_text.yview)
        self._report_text.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._report_text.pack(fill="both", expand=True)
        ttk.Button(left, text="Copy Report", command=self._copy_report).pack(pady=(4, 0))

        # Right: plot
        self._plot_frame = ttk.Frame(self._paned, relief="flat")
        self._paned.add(self._plot_frame, weight=2)

    def _set_sash(self) -> None:
        self._paned.sashpos(0, 300)

    def _toggle_mode(self) -> None:
        if self._mode.get() == "file":
            self._file_row.lift()
            self._btn_text.set("Analyze")
        else:
            self._rec_row.lift()
            self._btn_text.set("Start Recording")

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[("Audio files", "*.wav *.mp3"), ("All files", "*.*")],
        )
        if path:
            self._filepath.set(path)

    def _run(self) -> None:
        if self._mode.get() == "file":
            self._btn.state(["disabled"])
            self._status.set("Working...")
            threading.Thread(target=self._analyze_file, daemon=True).start()
        else:
            if not self._recording:
                self._start_recording()
            else:
                self._stop_and_analyze()

    def _start_recording(self) -> None:
        self._recording = True
        self._btn_text.set("Stop & Analyze")
        self._status.set("Recording... speak now.")
        self._recorder.start()

    def _stop_and_analyze(self) -> None:
        self._recording = False
        self._btn.state(["disabled"])
        self._btn_text.set("Start Recording")
        self._status.set("Analyzing...")
        threading.Thread(target=self._analyze_stream, daemon=True).start()

    def _analyze_file(self) -> None:
        try:
            path = self._filepath.get().strip()
            if not path:
                self.after(0, lambda: messagebox.showerror("No file", "Please select an audio file."))
                return
            self.after(0, lambda: self._status.set("Loading file..."))
            audio, sr = load_file(path)
            self.after(0, lambda: self._status.set("Analyzing..."))
            self._run_analysis(audio, sr)
        except Exception as exc:
            msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Error", msg))
            self.after(0, lambda: self._status.set("Error."))
        finally:
            self.after(0, lambda: self._btn.state(["!disabled"]))

    def _analyze_stream(self) -> None:
        try:
            audio, sr = self._recorder.stop()
            self._run_analysis(audio, sr)
        except Exception as exc:
            msg = str(exc)
            self.after(0, lambda: messagebox.showerror("Error", msg))
            self.after(0, lambda: self._status.set("Error."))
        finally:
            self.after(0, lambda: self._btn.state(["!disabled"]))

    def _run_analysis(self, audio, sr) -> None:
        result = analyze_array(audio, sr)
        report = text_summary(result)
        fig = pitch_contour_figure(result)
        self.after(0, lambda: self._display(report, fig))

    def _display(self, report: str, fig) -> None:
        self._report_text.configure(state="normal")
        self._report_text.delete("1.0", "end")
        self._report_text.insert("1.0", report)
        self._report_text.configure(state="disabled")

        if self._canvas_widget:
            self._canvas_widget.destroy()

        canvas = FigureCanvasTkAgg(fig, master=self._plot_frame)
        canvas.draw()
        self._canvas_widget = canvas.get_tk_widget()
        self._canvas_widget.pack(fill="both", expand=True)

        self._status.set("Done.")

    def _copy_report(self) -> None:
        text = self._report_text.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._status.set("Copied to clipboard.")


def run() -> None:
    app = App()
    app.mainloop()
