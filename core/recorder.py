from __future__ import annotations

from pathlib import Path

import numpy as np
import sounddevice as sd
import librosa

DEFAULT_SAMPLE_RATE = 44100


def record(duration: float, sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """Record from the default microphone for `duration` seconds."""
    frames = int(duration * sample_rate)
    audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten(), sample_rate


def load_file(path: str | Path) -> tuple[np.ndarray, int]:
    """Load a WAV or MP3 file. Returns (audio, sample_rate) with original sample rate preserved."""
    audio, sr = librosa.load(str(path), sr=None, mono=True)
    return audio, int(sr)
