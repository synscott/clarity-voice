from __future__ import annotations

from pathlib import Path

import numpy as np
import sounddevice as sd
import librosa

DEFAULT_SAMPLE_RATE = 44100


def record(duration: float, sample_rate: int = DEFAULT_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    """Record from the default microphone for a fixed duration."""
    frames = int(duration * sample_rate)
    audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten(), sample_rate


def load_file(path: str | Path) -> tuple[np.ndarray, int]:
    """Load a WAV or MP3 file. Returns (audio, sample_rate) with original sample rate preserved."""
    audio, sr = librosa.load(str(path), sr=None, mono=True)
    return audio, int(sr)


class StreamRecorder:
    """Start/stop microphone recording without a fixed duration."""

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
        self._sr = sample_rate
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

    def start(self) -> None:
        self._chunks.clear()
        self._stream = sd.InputStream(
            samplerate=self._sr,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> tuple[np.ndarray, int]:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        audio = np.concatenate(self._chunks, axis=0).flatten() if self._chunks else np.zeros(1)
        return audio, self._sr

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        self._chunks.append(indata.copy())
