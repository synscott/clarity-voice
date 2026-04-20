# Clarity

Open-source acoustic voice analysis tool. Provides real-time pitch feedback and detailed acoustic data to support voice practice.

Works for any voice goal — pitch training, accent work, professional vocal coaching, or personal development.

## Features

- Start/stop microphone recording or audio file input (WAV, MP3)
- Acoustic analysis: fundamental frequency (F0), formants (F1/F2/F3), intensity, speech rate and pauses
- Pitch contour and intensity visualization
- Copyable text report for use with external AI or notes
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
>
> `librosa` has a large dependency tree — expect a slow first install.

## Usage

### GUI (default)

```bash
python main.py
```

Select **File** to load a WAV or MP3, or **Microphone** to record. Click **Start Recording**, speak, then click **Stop & Analyze**. Results appear in the text pane and plot automatically.

Use **Copy Report** to copy the text output for use with an AI assistant or your own notes.

### CLI

```bash
# Analyze an audio file
python main.py --file recording.wav

# Record from microphone for a fixed duration
python main.py --record 10

# Save report and plot to files
python main.py --file recording.wav --out report.txt --plot contour.png
```

## Analysis Output

| Metric | Description |
|---|---|
| F0 mean / median | Average pitch in Hz |
| F0 range | Min to max pitch across voiced frames |
| F0 std dev | Pitch stability — lower is more consistent |
| Voiced frames | % of frames where pitch was detected |
| F1 / F2 / F3 | Mean formant frequencies — resonance proxy |
| Voiced duration | Time spent above the speech threshold |
| Pause count | Number of pauses longer than 0.5s |

## Project Structure

```
core/
  analysis.py   Parselmouth/Praat acoustic analysis
  recorder.py   Mic recording (fixed duration and start/stop stream)
  report.py     Text summary and matplotlib visualization
gui/
  app.py        Tkinter GUI
main.py         Entry point — GUI by default, CLI with arguments
tests/          Unit tests for core analysis
docs/           Development notes
```

## Known Limitations

**Speech rate accuracy** degrades in noisy environments (fan noise, HVAC, etc.) where the dynamic range between background noise and speech is less than ~15 dB. Pitch and formant data remain reliable regardless. See [docs/dev-notes.md](docs/dev-notes.md) for details.

## Privacy

All data stays local. Audio is not retained after analysis unless you explicitly save it. No data is transmitted anywhere.

## License

MIT
