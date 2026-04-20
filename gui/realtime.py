from __future__ import annotations

import queue

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 44100
CHUNK_SIZE = 1024       # ~23 ms per callback
_PITCH_BUF = 2048       # ~46 ms analysis window
_F_MIN = 75.0
_F_MAX = 600.0
_CONFIDENCE = 0.30      # normalized autocorr threshold for voiced decision


def _detect_pitch(buf: np.ndarray) -> float | None:
    buf = buf - buf.mean()
    rms = float(np.sqrt(np.mean(buf ** 2)))
    if rms < 5e-4:
        return None

    n = len(buf)
    fft = np.fft.rfft(buf, n=2 * n)
    acf = np.fft.irfft(fft * np.conj(fft))[:n].real
    if acf[0] < 1e-10:
        return None
    acf = acf / acf[0]

    lag_min = max(1, int(SAMPLE_RATE / _F_MAX))
    lag_max = min(n - 1, int(SAMPLE_RATE / _F_MIN))
    if lag_min >= lag_max:
        return None

    best = int(np.argmax(acf[lag_min:lag_max])) + lag_min
    if acf[best] < _CONFIDENCE:
        return None

    return float(SAMPLE_RATE) / best


class PitchSample:
    __slots__ = ("hz", "rms_db")

    def __init__(self, hz: float | None, rms_db: float) -> None:
        self.hz = hz
        self.rms_db = rms_db


class RealtimePitchRecorder:
    def __init__(self) -> None:
        self.queue: queue.Queue[PitchSample] = queue.Queue()
        self._chunks: list[np.ndarray] = []
        self._buf = np.zeros(_PITCH_BUF, dtype=np.float32)
        self._stream: sd.InputStream | None = None

    def start(self) -> None:
        self._chunks.clear()
        self._buf[:] = 0.0
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_SIZE,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> tuple[np.ndarray, int]:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        audio = (
            np.concatenate(self._chunks).flatten()
            if self._chunks
            else np.zeros(1, dtype=np.float32)
        )
        return audio, SAMPLE_RATE

    def _callback(
        self, indata: np.ndarray, frames: int, time_info, status
    ) -> None:
        chunk = indata[:, 0]
        self._chunks.append(chunk.reshape(-1, 1).copy())

        copy_n = min(frames, _PITCH_BUF)
        self._buf = np.roll(self._buf, -copy_n)
        self._buf[-copy_n:] = chunk[-copy_n:]

        rms = float(np.sqrt(np.mean(chunk ** 2)))
        rms_db = float(20.0 * np.log10(max(rms, 1e-9)))
        hz = _detect_pitch(self._buf.copy())
        self.queue.put_nowait(PitchSample(hz=hz, rms_db=rms_db))
