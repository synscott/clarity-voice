import numpy as np
import pytest

from core.analysis import analyze_array, AnalysisResult


def _sine(freq: float, duration: float, sr: int = 16000) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def test_returns_analysis_result():
    result = analyze_array(_sine(220.0, 2.0), 16000)
    assert isinstance(result, AnalysisResult)


def test_duration_accurate():
    # 250ms is trimmed from the start during preprocessing
    result = analyze_array(_sine(200.0, 3.0, sr=16000), 16000)
    assert abs(result.duration - 2.75) < 0.05


def test_f0_detected_for_sine():
    result = analyze_array(_sine(220.0, 2.0), 16000)
    assert result.f0.mean_hz > 0
    assert result.f0.voiced_fraction > 0


def test_silence_produces_no_voiced_pitch():
    result = analyze_array(np.zeros(16000, dtype=np.float32), 16000)
    assert result.f0.voiced_fraction == 0.0
    assert result.f0.mean_hz == 0.0


def test_formants_non_negative():
    result = analyze_array(_sine(200.0, 2.0), 16000)
    assert result.formants.f1_mean >= 0
    assert result.formants.f2_mean >= 0
    assert result.formants.f3_mean >= 0


def test_speech_ratio_bounded():
    result = analyze_array(_sine(150.0, 2.0), 16000)
    assert 0.0 <= result.speech_rate.speech_ratio <= 1.0


def test_sample_rate_preserved():
    result = analyze_array(_sine(200.0, 1.0, sr=22050), 22050)
    assert result.sample_rate == 22050
