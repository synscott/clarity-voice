# Development Notes

## Audio preprocessing

Before analysis, all audio goes through `_preprocess()` in `core/analysis.py`:

1. **Trim 250ms from the start** — microphone recording start produces a transient that
   causes spurious pitch spikes. Trimming at the source is cleaner than post-hoc filtering.

2. **RMS normalize to -20 dBFS** — makes analysis parameters consistent across different
   microphone gains and room levels. Without this, the voicing and silence thresholds are
   effectively environment-dependent.

## Pitch detection

Uses `to_pitch_ac()` (autocorrelation method) with:
- `pitch_floor=75.0 Hz`, `pitch_ceiling=600.0 Hz` — covers bass through soprano
- `silence_threshold=0.01`, `voicing_threshold=0.15` — tuned for noisy environments
  (defaults of 0.03 / 0.45 miss too many voiced frames when a noise floor is present)

**Octave error filtering:** Praat's autocorrelation method occasionally detects pitch at 2x
the fundamental (harmonic doubling). Values above 1.75x the median pitch are suppressed.

For children's voices, `pitch_ceiling` should be raised and `maximum_formant` in
`to_formant_burg()` bumped from 5500 Hz to ~8000 Hz.

## Formant analysis

`to_formant_burg()` with `maximum_formant=5500.0` — appropriate for adult voices.

## Silence threshold / speech rate accuracy

Speech rate and pause detection use an intensity-based threshold:
`10th percentile of intensity + 3 dB`. The minimum pause duration is 0.5s.

This works reasonably in quiet environments but degrades when the noise floor is close to
speech level (e.g. fan noise), since the dynamic range between noise and speech can be as
little as 10-15 dB. In those conditions, voiced duration and pause count will be
underreported.

The right fix is a proper Voice Activity Detection (VAD) algorithm. Candidates for a future
iteration: WebRTC VAD (via `webrtcvad`), silero-vad, or py-webrtcvad. Until then, the pitch
data (F0, formants) is the primary reliable signal.

## librosa vs sounddevice

- `sounddevice`: real-time mic capture via PortAudio. Used for both fixed-duration (`record()`)
  and start/stop streaming (`StreamRecorder`).
- `librosa`: file decoding (WAV, MP3, FLAC, etc.) with automatic resampling. Used only in
  `load_file()` — not involved in live recording.

## PyPI package name

The Praat wrapper package is `praat-parselmouth` on PyPI (not `parselmouth`, which is an
unrelated package that pulls in `googleads` and will fail to build).

## GUI

Implemented with Tkinter. `gui/app.py` imports from `core/` only — no analysis logic lives
in the GUI layer. The `core/` module remains fully importable and runnable independently.

PyQt6 was considered but Tkinter covers the current feature set without the additional
dependency weight.

## Future: Claude API integration

Per the brief, opt-in only. When implemented: strip audio metadata before transmission,
require explicit user consent at the point of any external call.
