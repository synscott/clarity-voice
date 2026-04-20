from __future__ import annotations

import queue
import time
from collections import deque

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.analysis import AnalysisResult, analyze_array
from core.recorder import load_file
from core.report import text_summary
from gui.realtime import CHUNK_SIZE, SAMPLE_RATE, RealtimePitchRecorder

# ── Theme ────────────────────────────────────────────────────────────────────
_BG = "#1c1c1e"
_SURFACE = "#2c2c2e"
_BORDER = "#3a3a3c"
_TEXT = "#ffffff"
_DIM = "#8e8e93"
_AMBER = "#ff9f0a"
_TEAL = "#30d5c8"
_RED = "#ff453a"

pg.setConfigOptions(antialias=True, background=_BG, foreground=_TEXT)

STYLESHEET = f"""
QWidget {{
    background-color: {_BG};
    color: {_TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}
QLabel {{ background: transparent; }}
QPushButton {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 8px 22px;
}}
QPushButton:hover {{ background-color: {_BORDER}; }}
QPushButton:pressed {{ background-color: #48484a; }}
QPushButton:disabled {{ color: #636366; border-color: #2c2c2e; }}
QLineEdit, QDoubleSpinBox {{
    background-color: {_SURFACE};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 4px 8px;
}}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {_BORDER};
    width: 16px;
}}
QRadioButton, QCheckBox {{ color: {_TEXT}; spacing: 6px; }}
QRadioButton::indicator {{
    width: 14px; height: 14px;
    border: 2px solid {_DIM};
    border-radius: 7px;
    background-color: transparent;
}}
QRadioButton::indicator:checked {{
    background-color: {_TEAL};
    border-color: {_TEAL};
}}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 2px solid {_DIM};
    border-radius: 3px;
    background-color: transparent;
}}
QCheckBox::indicator:checked {{
    background-color: {_TEAL};
    border-color: {_TEAL};
}}
QTextEdit {{
    background-color: #141416;
    color: #e5e5e7;
    border: none;
    border-radius: 6px;
    font-family: "Courier New", monospace;
    font-size: 11px;
    padding: 8px;
}}
QSplitter::handle {{ background: {_BORDER}; }}
"""

# ── Page indices ─────────────────────────────────────────────────────────────
_PAGE_IDLE = 0
_PAGE_LIVE = 1
_PAGE_RESULTS = 2

# ── Live display ──────────────────────────────────────────────────────────────
_LIVE_SECS = 10.0
_TIMER_MS = 40          # ~25 Hz UI refresh
_CPS = SAMPLE_RATE / CHUNK_SIZE   # callbacks per second (~43)


# ── Analysis worker ───────────────────────────────────────────────────────────

class _AnalysisThread(QThread):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, source, parent=None) -> None:
        super().__init__(parent)
        self._source = source   # str path  OR  (np.ndarray, int) tuple

    def run(self) -> None:
        try:
            if isinstance(self._source, str):
                audio, sr = load_file(self._source)
            else:
                audio, sr = self._source
            self.finished.emit(analyze_array(audio, sr))
        except Exception as exc:
            self.failed.emit(str(exc))


# ── Range overlay ─────────────────────────────────────────────────────────────

class _RangeOverlay:
    """Floor/ceiling target range visualized on a pyqtgraph PlotWidget."""

    def __init__(self, plot: pg.PlotWidget) -> None:
        pen = pg.mkPen(color=_TEAL, style=Qt.PenStyle.DashLine, width=1.5)
        self._floor_line = pg.InfiniteLine(pos=150, angle=0, pen=pen, movable=False)
        self._ceil_line = pg.InfiniteLine(pos=300, angle=0, pen=pen, movable=False)
        self._region = pg.LinearRegionItem(
            values=[150, 300],
            orientation="horizontal",
            brush=pg.mkBrush(color=(48, 213, 200, 22)),
            pen=pg.mkPen(color=_TEAL, style=Qt.PenStyle.DashLine, width=1.5),
            movable=False,
        )
        plot.addItem(self._region)
        plot.addItem(self._floor_line)
        plot.addItem(self._ceil_line)
        self._apply(False, False)

    def update(
        self, floor_en: bool, floor_hz: float, ceil_en: bool, ceil_hz: float
    ) -> None:
        self._floor_line.setPos(floor_hz)
        self._ceil_line.setPos(ceil_hz)
        self._region.setRegion([floor_hz, ceil_hz])
        self._apply(floor_en, ceil_en)

    def _apply(self, floor_en: bool, ceil_en: bool) -> None:
        both = floor_en and ceil_en
        self._floor_line.setVisible(floor_en and not both)
        self._ceil_line.setVisible(ceil_en and not both)
        self._region.setVisible(both)


# ── Main window ───────────────────────────────────────────────────────────────

class ClarityWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Clarity")
        self.resize(1100, 720)
        self.setMinimumSize(800, 550)

        self._recorder = RealtimePitchRecorder()
        self._analysis_thread: _AnalysisThread | None = None
        self._last_result: AnalysisResult | None = None
        self._recording = False
        self._recording_start = 0.0
        self._pitch_history: deque[tuple[float, float | None]] = deque()
        self._rms_history: deque[tuple[float, float]] = deque()
        self._result_pitch_items: list = []
        self._result_int_items: list = []
        self._live_overlays: list[_RangeOverlay] = []
        self._result_overlays: list[_RangeOverlay] = []

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_live_timer)

        self._build_ui()
        self._on_mode_changed()
        self._on_range_changed()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(16, 12, 16, 12)
        vbox.setSpacing(10)
        vbox.addWidget(self._build_header())
        vbox.addWidget(self._build_stack(), stretch=1)
        vbox.addWidget(self._build_footer())

        # Connect all signals after every widget exists
        self._mode_file.toggled.connect(self._on_mode_changed)
        self._floor_spin.valueChanged.connect(self._on_range_changed)
        self._ceil_spin.valueChanged.connect(self._on_range_changed)
        self._floor_check.stateChanged.connect(self._on_range_changed)
        self._ceil_check.stateChanged.connect(self._on_range_changed)

    def _build_header(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(12)

        self._mode_file = QRadioButton("File")
        self._mode_mic = QRadioButton("Microphone")
        row1.addWidget(self._mode_file)
        row1.addWidget(self._mode_mic)
        row1.addSpacing(12)

        self._action_btn = QPushButton("Analyze")
        self._action_btn.setFixedWidth(170)
        self._action_btn.clicked.connect(self._on_action)
        row1.addWidget(self._action_btn)
        row1.addSpacing(20)

        row1.addWidget(QLabel("Floor:"))
        self._floor_spin = QDoubleSpinBox()
        self._floor_spin.setRange(50, 800)
        self._floor_spin.setValue(150)
        self._floor_spin.setSuffix(" Hz")
        self._floor_spin.setSingleStep(5)
        self._floor_spin.setFixedWidth(100)
        self._floor_check = QCheckBox()
        self._floor_check.setToolTip("Enable floor line")
        row1.addWidget(self._floor_spin)
        row1.addWidget(self._floor_check)
        row1.addSpacing(12)

        row1.addWidget(QLabel("Ceiling:"))
        self._ceil_spin = QDoubleSpinBox()
        self._ceil_spin.setRange(50, 800)
        self._ceil_spin.setValue(300)
        self._ceil_spin.setSuffix(" Hz")
        self._ceil_spin.setSingleStep(5)
        self._ceil_spin.setFixedWidth(100)
        self._ceil_check = QCheckBox()
        self._ceil_check.setToolTip("Enable ceiling line")
        row1.addWidget(self._ceil_spin)
        row1.addWidget(self._ceil_check)
        row1.addStretch()
        outer.addLayout(row1)

        self._file_row = QWidget()
        file_layout = QHBoxLayout(self._file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select an audio file...")
        self._path_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(self._path_edit)
        file_layout.addWidget(browse_btn)
        outer.addWidget(self._file_row)

        return w

    def _build_stack(self) -> QStackedWidget:
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_idle_page())
        self._stack.addWidget(self._build_live_page())
        self._stack.addWidget(self._build_results_page())
        return self._stack

    def _build_idle_page(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.setSpacing(12)

        self._idle_hz = QLabel("- Hz")
        self._idle_hz.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._idle_hz.setFont(QFont("Segoe UI", 72, QFont.Weight.Light))
        self._idle_hz.setStyleSheet(f"color: {_DIM};")
        vbox.addWidget(self._idle_hz)

        hint = QLabel("Select a source and press the button above to begin.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color: {_DIM}; font-size: 12px;")
        vbox.addWidget(hint)
        return w

    def _build_live_page(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(6)

        self._live_hz = QLabel("- Hz")
        self._live_hz.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._live_hz.setFont(QFont("Segoe UI", 72, QFont.Weight.Light))
        self._live_hz.setStyleSheet(f"color: {_DIM};")
        vbox.addWidget(self._live_hz)

        self._live_pitch_plot = self._make_plot("Hz", "Time (s)")
        self._live_pitch_plot.setYRange(50, 700, padding=0.05)
        self._pitch_curve = self._live_pitch_plot.plot(
            pen=pg.mkPen(color=_TEXT, width=2), connect="finite"
        )
        self._live_overlays.append(_RangeOverlay(self._live_pitch_plot))
        vbox.addWidget(self._live_pitch_plot, stretch=3)

        self._live_int_plot = self._make_plot("dBFS", "")
        self._live_int_plot.setYRange(-70, 0, padding=0.05)
        self._int_curve = self._live_int_plot.plot(
            pen=pg.mkPen(color=_AMBER, width=1.5)
        )
        vbox.addWidget(self._live_int_plot, stretch=1)

        return w

    def _build_results_page(self) -> QWidget:
        w = QWidget()
        vbox = QVBoxLayout(w)
        vbox.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        vbox.addWidget(splitter)

        left = QWidget()
        left_vbox = QVBoxLayout(left)
        left_vbox.setContentsMargins(0, 0, 8, 0)
        self._metrics_text = QTextEdit()
        self._metrics_text.setReadOnly(True)
        left_vbox.addWidget(self._metrics_text, stretch=1)
        copy_btn = QPushButton("Copy Report")
        copy_btn.clicked.connect(self._copy_report)
        left_vbox.addWidget(copy_btn)
        splitter.addWidget(left)

        right = QWidget()
        right_vbox = QVBoxLayout(right)
        right_vbox.setContentsMargins(8, 0, 0, 0)
        right_vbox.setSpacing(6)
        self._result_pitch_plot = self._make_plot("Hz", "Time (s)")
        self._result_overlays.append(_RangeOverlay(self._result_pitch_plot))
        right_vbox.addWidget(self._result_pitch_plot, stretch=3)
        self._result_int_plot = self._make_plot("dB", "Time (s)")
        right_vbox.addWidget(self._result_int_plot, stretch=1)
        splitter.addWidget(right)
        splitter.setSizes([320, 780])

        return w

    def _build_footer(self) -> QWidget:
        w = QWidget()
        hbox = QHBoxLayout(w)
        hbox.setContentsMargins(0, 0, 0, 0)
        self._status_label = QLabel("Ready.")
        self._status_label.setStyleSheet(f"color: {_DIM}; font-size: 12px;")
        hbox.addWidget(self._status_label)
        return w

    @staticmethod
    def _make_plot(y_label: str, x_label: str) -> pg.PlotWidget:
        p = pg.PlotWidget()
        p.setLabel("left", y_label)
        p.setLabel("bottom", x_label)
        p.showGrid(x=False, y=True, alpha=0.15)
        p.getPlotItem().hideButtons()
        p.getPlotItem().getAxis("left").setTextPen(_DIM)
        p.getPlotItem().getAxis("bottom").setTextPen(_DIM)
        return p

    # ── State transitions ─────────────────────────────────────────────────────

    def _go_idle(self) -> None:
        self._recording = False
        self._timer.stop()
        self._stack.setCurrentIndex(_PAGE_IDLE)
        is_file = self._mode_file.isChecked()
        self._action_btn.setText("Analyze" if is_file else "Start Recording")
        self._action_btn.setEnabled(True)
        self._status_label.setText("Ready.")

    def _go_live(self) -> None:
        self._recording = True
        self._pitch_history.clear()
        self._rms_history.clear()
        self._pitch_curve.setData([], [])
        self._int_curve.setData([], [])
        self._recording_start = time.monotonic()
        self._stack.setCurrentIndex(_PAGE_LIVE)
        self._action_btn.setText("Stop && Analyze")
        self._action_btn.setEnabled(True)
        self._status_label.setText("Recording - speak now.")
        self._timer.start(_TIMER_MS)

    def _go_analyzing(self) -> None:
        self._recording = False
        self._timer.stop()
        self._action_btn.setEnabled(False)
        self._action_btn.setText("Analyzing...")
        self._status_label.setText("Analyzing...")

    def _go_results(self, result: AnalysisResult) -> None:
        self._last_result = result
        self._populate_results(result)
        self._stack.setCurrentIndex(_PAGE_RESULTS)
        self._action_btn.setText("New Analysis")
        self._action_btn.setEnabled(True)
        self._status_label.setText("Done.")

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_mode_changed(self) -> None:
        is_file = self._mode_file.isChecked()
        self._file_row.setVisible(is_file)
        if not self._recording and self._stack.currentIndex() != _PAGE_RESULTS:
            self._action_btn.setText("Analyze" if is_file else "Start Recording")

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select audio file",
            "",
            "Audio files (*.wav *.mp3);;All files (*)",
        )
        if path:
            self._path_edit.setText(path)

    def _on_range_changed(self) -> None:
        floor_en = self._floor_check.isChecked()
        floor_hz = self._floor_spin.value()
        ceil_en = self._ceil_check.isChecked()
        ceil_hz = self._ceil_spin.value()
        for overlay in self._live_overlays + self._result_overlays:
            overlay.update(floor_en, floor_hz, ceil_en, ceil_hz)

    def _on_action(self) -> None:
        page = self._stack.currentIndex()
        if page == _PAGE_RESULTS:
            self._go_idle()
            return
        if self._recording:
            self._stop_and_analyze()
            return
        if self._mode_file.isChecked():
            self._analyze_file()
        else:
            self._start_recording()

    # ── Recording ─────────────────────────────────────────────────────────────

    def _start_recording(self) -> None:
        self._recorder.start()
        self._go_live()

    def _stop_and_analyze(self) -> None:
        audio, sr = self._recorder.stop()
        self._go_analyzing()
        self._launch_analysis((audio, sr))

    # ── File analysis ─────────────────────────────────────────────────────────

    def _analyze_file(self) -> None:
        path = self._path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No file", "Please select an audio file.")
            return
        self._go_analyzing()
        self._launch_analysis(path)

    # ── Analysis thread ───────────────────────────────────────────────────────

    def _launch_analysis(self, source) -> None:
        self._analysis_thread = _AnalysisThread(source, self)
        self._analysis_thread.finished.connect(self._on_analysis_done)
        self._analysis_thread.failed.connect(self._on_analysis_failed)
        self._analysis_thread.start()

    def _on_analysis_done(self, result: AnalysisResult) -> None:
        self._go_results(result)

    def _on_analysis_failed(self, msg: str) -> None:
        self._go_idle()
        QMessageBox.critical(self, "Analysis failed", msg)

    # ── Live timer ────────────────────────────────────────────────────────────

    def _on_live_timer(self) -> None:
        samples = []
        while True:
            try:
                samples.append(self._recorder.queue.get_nowait())
            except queue.Empty:
                break
        if not samples:
            return

        t_now = time.monotonic() - self._recording_start
        for i, s in enumerate(samples):
            t = t_now - (len(samples) - 1 - i) / _CPS
            self._pitch_history.append((t, s.hz))
            self._rms_history.append((t, s.rms_db))

        cutoff = t_now - _LIVE_SECS
        while self._pitch_history and self._pitch_history[0][0] < cutoff:
            self._pitch_history.popleft()
        while self._rms_history and self._rms_history[0][0] < cutoff:
            self._rms_history.popleft()

        self._update_hz_display(self._live_hz, samples[-1].hz)

        all_t = np.asarray([t for t, _ in self._pitch_history], dtype=float)
        all_hz = np.asarray(
            [hz if hz is not None else np.nan for _, hz in self._pitch_history],
            dtype=float,
        )
        self._pitch_curve.setData(x=all_t, y=all_hz)
        x_lo = max(0.0, t_now - _LIVE_SECS)
        x_hi = t_now + 0.2
        self._live_pitch_plot.setXRange(x_lo, x_hi, padding=0)

        rms_t = np.asarray([t for t, _ in self._rms_history], dtype=float)
        rms_v = np.asarray([v for _, v in self._rms_history], dtype=float)
        self._int_curve.setData(x=rms_t, y=rms_v)
        self._live_int_plot.setXRange(x_lo, x_hi, padding=0)

    def _update_hz_display(self, label: QLabel, hz: float | None) -> None:
        floor_en = self._floor_check.isChecked()
        ceil_en = self._ceil_check.isChecked()

        if hz is None:
            label.setText("- Hz")
            label.setStyleSheet(f"color: {_DIM};")
            return

        label.setText(f"{hz:.0f} Hz")

        if not floor_en and not ceil_en:
            label.setStyleSheet(f"color: {_TEXT};")
            return

        in_range = True
        if floor_en and hz < self._floor_spin.value():
            in_range = False
        if ceil_en and hz > self._ceil_spin.value():
            in_range = False
        label.setStyleSheet(f"color: {_TEXT if in_range else _AMBER};")

    # ── Results ───────────────────────────────────────────────────────────────

    def _populate_results(self, result: AnalysisResult) -> None:
        self._metrics_text.setPlainText(text_summary(result))

        for item in self._result_pitch_items:
            self._result_pitch_plot.removeItem(item)
        self._result_pitch_items.clear()
        for item in self._result_int_items:
            self._result_int_plot.removeItem(item)
        self._result_int_items.clear()

        f0 = result.f0
        voiced_mask = f0.values > 0
        if voiced_mask.any():
            pitch_y = np.where(voiced_mask, f0.values, np.nan)
            pitch_curve = self._result_pitch_plot.plot(
                x=f0.times,
                y=pitch_y,
                pen=pg.mkPen(color=_TEXT, width=2),
                connect="finite",
            )
            self._result_pitch_items.append(pitch_curve)

            med_line = pg.InfiniteLine(
                pos=f0.median_hz,
                angle=0,
                pen=pg.mkPen(color=_RED, width=1.0, style=Qt.PenStyle.DashLine),
                label=f"Median {f0.median_hz:.1f} Hz",
                labelOpts={"color": _RED, "position": 0.95},
                movable=False,
            )
            self._result_pitch_plot.addItem(med_line)
            self._result_pitch_items.append(med_line)

        int_curve = self._result_int_plot.plot(
            x=result.intensity.times,
            y=result.intensity.values,
            pen=pg.mkPen(color=_AMBER, width=1.5),
        )
        self._result_int_items.append(int_curve)

        self._on_range_changed()

    def _copy_report(self) -> None:
        text = self._metrics_text.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            self._status_label.setText("Copied to clipboard.")


# ── Entry point ───────────────────────────────────────────────────────────────

def run() -> None:
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = ClarityWindow()
    window.show()
    app.exec()
