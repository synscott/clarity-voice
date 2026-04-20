# Development Notes

## Pitch floor / ceiling

`to_pitch()` uses `pitch_floor=75.0, pitch_ceiling=600.0`. This covers bass (80 Hz) through
soprano (~1100 Hz fundamental, but second harmonic detected). Adjust if extreme vocal ranges
are a common use case.

## Formant analysis

Using `to_formant_burg()` with `maximum_formant=5500.0` (appropriate for adult voices).
For children's voices this should be raised to ~8000 Hz. Worth exposing as a parameter
if child voice use cases emerge.

## Silence threshold / speech rate accuracy

Speech rate and pause detection use an intensity-based threshold (10th percentile of intensity
+ 3 dB). This works reasonably in quiet environments but degrades when the noise floor is
close to speech level (e.g. fan noise), since the dynamic range between noise and speech can
be as little as 10-15 dB. In those conditions, voiced duration and pause count will be
underreported.

The right fix is a proper Voice Activity Detection (VAD) algorithm. Candidates for a future
iteration: WebRTC VAD (via `webrtcvad`), silero-vad, or py-webrtcvad. Until then, the pitch
data (F0, formants) is reliable and is the primary clinical signal anyway.

## librosa vs sounddevice

- `sounddevice`: real-time mic capture via PortAudio
- `librosa`: file decoding (WAV, MP3, FLAC, etc.) with automatic resampling support

## GUI decision (deferred)

Tkinter is acceptable for MVP. PyQt6 only if layout complexity demands it. Do not begin GUI
until the core pipeline is validated end-to-end via CLI.

## Future: Claude API integration

Per the brief, Claude API integration is opt-in only. When implemented, strip any
identifying information from audio metadata before transmission. Explicit user consent
required at the point of transmission.
