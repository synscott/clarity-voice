# Clarity

Open-source voice therapy analysis tool. Provides real-time acoustic feedback and structured practice support between clinic sessions.

Works for any voice therapy context — gender-affirming, post-surgical, accent modification, or professional coaching.

## Features (MVP)

- Microphone recording or audio file input (WAV, MP3)
- Acoustic analysis: fundamental frequency (F0), formants (F1/F2/F3), intensity, speech rate
- Text report and pitch contour visualization
- Fully local — no network calls, no telemetry, no accounts

## Setup

```bash
git clone https://github.com/synscott/clarity-voice.git
cd clarity-voice
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

> **Note:** `sounddevice` requires PortAudio on Windows. If the install fails, try `pipwin install sounddevice` or grab the PortAudio binary manually.

## Usage

```bash
# Analyze an audio file
python main.py --file recording.wav

# Record from microphone (10 seconds)
python main.py --record 10

# Save report and plot
python main.py --file recording.wav --out report.txt --plot contour.png
```

## Project Structure

```
core/         Analysis logic (Parselmouth/Praat), recorder, report generation
gui/          GUI layer (not yet implemented)
tests/        Unit tests for core analysis
docs/         Development notes
```

## Privacy

All data stays local. Audio is not retained after analysis unless you explicitly save it. No data is transmitted anywhere.

## License

MIT
