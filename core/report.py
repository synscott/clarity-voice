from __future__ import annotations

import io
from pathlib import Path

import matplotlib
import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np

from .analysis import AnalysisResult

matplotlib.use("Agg")


def text_summary(result: AnalysisResult) -> str:
    f0 = result.f0
    fmt = result.formants
    sr = result.speech_rate

    lines = [
        "=== Clarity Voice Analysis ===",
        "",
        f"Duration:          {result.duration:.2f}s",
        "",
        "--- Pitch (F0) ---",
    ]

    if f0.mean_hz > 0:
        lines += [
            f"  Mean:            {f0.mean_hz:.1f} Hz",
            f"  Median:          {f0.median_hz:.1f} Hz",
            f"  Range:           {f0.min_hz:.1f} - {f0.max_hz:.1f} Hz",
            f"  Std dev:         {f0.std_hz:.1f} Hz  (pitch stability)",
            f"  Voiced frames:   {f0.voiced_fraction * 100:.1f}%",
        ]
    else:
        lines.append("  No voiced speech detected.")

    lines += [
        "",
        "--- Resonance (mean over voiced frames) ---",
        f"  F1:              {fmt.f1_mean:.0f} Hz",
        f"  F2:              {fmt.f2_mean:.0f} Hz",
        f"  F3:              {fmt.f3_mean:.0f} Hz",
        "",
        "--- Speech Rate & Pauses ---",
        f"  Voiced duration: {sr.voiced_duration:.2f}s  ({sr.speech_ratio * 100:.1f}% of total)",
        f"  Pause count:     {sr.pause_count}",
    ]

    if sr.pause_count > 0:
        lines.append(f"  Mean pause:      {sr.mean_pause_duration:.2f}s")
    else:
        lines.append("  Mean pause:      -")

    lines.append("")
    return "\n".join(lines)


def pitch_contour_figure(result: AnalysisResult) -> matplotlib.figure.Figure:
    f0 = result.f0
    voiced_mask = f0.values > 0

    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.suptitle("Clarity — Pitch & Intensity Contour", fontsize=13)

    ax_pitch = axes[0]
    voiced_times = f0.times[voiced_mask]
    voiced_vals = f0.values[voiced_mask]
    ax_pitch.scatter(voiced_times, voiced_vals, s=2, color="steelblue", label="F0 (voiced)")
    if len(voiced_vals) > 0:
        ax_pitch.axhline(
            f0.median_hz,
            color="tomato",
            linewidth=1.0,
            linestyle="--",
            label=f"Median {f0.median_hz:.1f} Hz",
        )
    ax_pitch.set_ylabel("Frequency (Hz)")
    ax_pitch.set_ylim(bottom=0)
    ax_pitch.legend(fontsize=8, loc="upper right")
    ax_pitch.grid(True, alpha=0.3)

    ax_int = axes[1]
    ax_int.plot(result.intensity.times, result.intensity.values, color="darkorange", linewidth=0.8)
    ax_int.set_ylabel("Intensity (dB)")
    ax_int.set_xlabel("Time (s)")
    ax_int.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def save_figure(fig: matplotlib.figure.Figure, path: str | Path) -> None:
    fig.savefig(str(path), dpi=150, bbox_inches="tight")
    plt.close(fig)


def figure_to_bytes(fig: matplotlib.figure.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
