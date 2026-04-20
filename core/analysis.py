from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import parselmouth
from parselmouth.praat import call


@dataclass
class F0Result:
    mean_hz: float
    median_hz: float
    min_hz: float
    max_hz: float
    std_hz: float
    voiced_fraction: float
    times: np.ndarray
    values: np.ndarray  # 0 where unvoiced


@dataclass
class FormantResult:
    f1_mean: float
    f2_mean: float
    f3_mean: float
    times: np.ndarray
    f1_values: np.ndarray
    f2_values: np.ndarray
    f3_values: np.ndarray


@dataclass
class IntensityResult:
    mean_db: float
    min_db: float
    max_db: float
    times: np.ndarray
    values: np.ndarray


@dataclass
class SpeechRateResult:
    total_duration: float
    voiced_duration: float
    speech_ratio: float
    pause_count: int
    mean_pause_duration: float


@dataclass
class AnalysisResult:
    duration: float
    sample_rate: int
    f0: F0Result
    formants: FormantResult
    intensity: IntensityResult
    speech_rate: SpeechRateResult


def analyze_file(path: str) -> AnalysisResult:
    sound = parselmouth.Sound(path)
    audio = sound.values[0]
    audio = _preprocess(audio, int(sound.sampling_frequency))
    sound = parselmouth.Sound(audio, sampling_frequency=sound.sampling_frequency)
    return _analyze_sound(sound)


def analyze_array(audio: np.ndarray, sample_rate: int) -> AnalysisResult:
    if audio.ndim > 1:
        audio = audio.mean(axis=-1)
    audio = _preprocess(audio.astype(np.float64), sample_rate)
    sound = parselmouth.Sound(audio, sampling_frequency=float(sample_rate))
    return _analyze_sound(sound)


def _preprocess(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    # Drop the first 250ms — recording-start transients cause spurious pitch spikes
    trim = int(0.25 * sample_rate)
    audio = audio[trim:]

    # RMS normalize to -20 dBFS so analysis parameters stay consistent
    # across different mic gains and room levels
    rms = np.sqrt(np.mean(audio ** 2))
    if rms > 1e-9:
        target_rms = 10 ** (-20.0 / 20.0)
        audio = np.clip(audio * (target_rms / rms), -1.0, 1.0)

    return audio


def _analyze_sound(sound: parselmouth.Sound) -> AnalysisResult:
    intensity = _analyze_intensity(sound)
    return AnalysisResult(
        duration=sound.duration,
        sample_rate=int(sound.sampling_frequency),
        f0=_analyze_f0(sound),
        formants=_analyze_formants(sound),
        intensity=intensity,
        speech_rate=_analyze_speech_rate(sound, intensity),
    )


def _analyze_f0(sound: parselmouth.Sound) -> F0Result:
    pitch = sound.to_pitch_ac(
        time_step=0.01,
        pitch_floor=75.0,
        pitch_ceiling=600.0,
        silence_threshold=0.01,
        voicing_threshold=0.15,
    )
    times = pitch.xs()
    values = pitch.selected_array["frequency"]  # 0 = unvoiced

    voiced_mask = values > 0
    voiced_values = values[voiced_mask]

    # Suppress octave errors: values above 1.75× the median are likely harmonic
    # doubling artifacts from Praat's autocorrelation method
    if len(voiced_values) > 0:
        cutoff = float(np.median(voiced_values)) * 1.75
        values[(values > 0) & (values > cutoff)] = 0.0
        voiced_mask = values > 0
        voiced_values = values[voiced_mask]
    voiced_fraction = voiced_mask.sum() / max(len(values), 1)

    if len(voiced_values) > 0:
        mean_hz = float(np.mean(voiced_values))
        median_hz = float(np.median(voiced_values))
        min_hz = float(np.min(voiced_values))
        max_hz = float(np.max(voiced_values))
        std_hz = float(np.std(voiced_values))
    else:
        mean_hz = median_hz = min_hz = max_hz = std_hz = 0.0

    return F0Result(
        mean_hz=mean_hz,
        median_hz=median_hz,
        min_hz=min_hz,
        max_hz=max_hz,
        std_hz=std_hz,
        voiced_fraction=float(voiced_fraction),
        times=times,
        values=values,
    )


def _analyze_formants(sound: parselmouth.Sound) -> FormantResult:
    formants = sound.to_formant_burg(
        time_step=0.01,
        max_number_of_formants=5,
        maximum_formant=5500.0,
        window_length=0.025,
        pre_emphasis_from=50.0,
    )
    n_frames = call(formants, "Get number of frames")
    times = np.array([call(formants, "Get time from frame number", i + 1) for i in range(n_frames)])

    def _get_formant(number: int) -> np.ndarray:
        vals = []
        for t in times:
            v = formants.get_value_at_time(number, t)
            vals.append(0.0 if v is None or math.isnan(v) else v)
        return np.array(vals)

    f1 = _get_formant(1)
    f2 = _get_formant(2)
    f3 = _get_formant(3)

    def _mean_nonzero(arr: np.ndarray) -> float:
        valid = arr[arr > 0]
        return float(np.mean(valid)) if len(valid) > 0 else 0.0

    return FormantResult(
        f1_mean=_mean_nonzero(f1),
        f2_mean=_mean_nonzero(f2),
        f3_mean=_mean_nonzero(f3),
        times=times,
        f1_values=f1,
        f2_values=f2,
        f3_values=f3,
    )


def _analyze_intensity(sound: parselmouth.Sound) -> IntensityResult:
    intensity = sound.to_intensity(time_step=0.01, minimum_pitch=75.0)
    times = intensity.xs()
    values = intensity.values[0]

    return IntensityResult(
        mean_db=float(np.mean(values)),
        min_db=float(np.min(values)),
        max_db=float(np.max(values)),
        times=times,
        values=values,
    )


def _analyze_speech_rate(sound: parselmouth.Sound, intensity: IntensityResult) -> SpeechRateResult:
    dt = 0.01
    # Estimate noise floor from the quietest 10% of frames, then threshold 10 dB above it.
    # More robust than mean-based threshold when background noise is present.
    noise_floor = float(np.percentile(intensity.values, 10))
    threshold = noise_floor + 3.0
    is_voiced = intensity.values > threshold

    voiced_duration = float(np.sum(is_voiced) * dt)
    speech_ratio = voiced_duration / sound.duration if sound.duration > 0 else 0.0

    pause_count, mean_pause = _count_pauses(is_voiced, dt, min_pause=0.5)

    return SpeechRateResult(
        total_duration=sound.duration,
        voiced_duration=voiced_duration,
        speech_ratio=speech_ratio,
        pause_count=pause_count,
        mean_pause_duration=mean_pause,
    )


def _count_pauses(is_voiced: np.ndarray, dt: float, min_pause: float = 0.15) -> tuple[int, float]:
    # Pad with voiced frames so edge silences are counted as pauses
    padded = np.concatenate([[True], is_voiced, [True]])
    diff = np.diff(padded.astype(int))
    starts = np.where(diff == -1)[0]
    ends = np.where(diff == 1)[0]
    durations = (ends - starts) * dt
    long_pauses = durations[durations >= min_pause]
    count = len(long_pauses)
    mean_dur = float(np.mean(long_pauses)) if count > 0 else 0.0
    return count, mean_dur
