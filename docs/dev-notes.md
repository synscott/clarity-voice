# Development Notes

## Pitch floor / ceiling

`to_pitch()` uses `pitch_floor=75.0, pitch_ceiling=600.0`. This covers bass (80 Hz) through
soprano (~1100 Hz fundamental, but second harmonic detected). Adjust if extreme vocal ranges
are a common use case.

## Formant analysis

Using `to_formant_burg()` with `maximum_formant=5500.0` (appropriate for adult voices).
For children's voices this should be raised to ~8000 Hz. Worth exposing as a parameter
if child voice use cases emerge.

## Silence threshold

Speech rate / pause detection uses `mean_intensity - 20 dB` as the voiced/unvoiced boundary.
This is heuristic. Could be replaced with a proper voice activity detection approach if
accuracy becomes a priority.

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
