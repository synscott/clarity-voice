# Clarity

Open-source acoustic voice analysis tool. Provides real-time pitch feedback and detailed acoustic data to support voice practice.

Works for any voice goal - pitch training, accent work, professional vocal coaching, or personal development.

## Features

- Real-time pitch display during microphone recording
- Start/stop microphone recording or audio file input (WAV, MP3)
- Acoustic analysis: fundamental frequency (F0), formants (F1/F2/F3), intensity, speech rate and pauses
- Pitch contour and intensity visualization
- Target range overlay - set a floor and/or ceiling Hz, see when you're in range
- Copyable text report for use with external AI or notes
- Fully local - no network calls, no telemetry, no accounts

---

## Setup - Windows

### 1. Install Python

Download Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/).

> **Do not use Python 3.13 or 3.14.** Some audio dependencies do not have pre-built wheels for those versions yet.

During install, check **"Add Python to PATH"** before clicking Install Now.

Verify in a new Command Prompt or PowerShell window:

```
python --version
```

### 2. Install Git

Download Git from [git-scm.com](https://git-scm.com/download/win) and run the installer with default settings.

### 3. Clone the repository

Open **PowerShell** or **Command Prompt** and run:

```
git clone https://github.com/synscott/clarity-voice.git
cd clarity-voice
```

### 4. Create a virtual environment

```
python -m venv .venv
.venv\Scripts\activate
```

Your prompt should now show `(.venv)` at the start.

### 5. Install dependencies

```
pip install -r requirements.txt
```

This will take a few minutes - librosa has a large dependency tree.

> **If sounddevice fails to install:** It requires PortAudio. Try installing it via:
> ```
> pip install pipwin
> pipwin install sounddevice
> ```
> If that also fails, download the PortAudio binary from [portaudio.com](http://www.portaudio.com/download.html) and install manually, then retry `pip install sounddevice`.

### 6. Run the app

```
python main.py
```

> **Each time you open a new terminal**, you need to activate the virtual environment again before running:
> ```
> cd clarity-voice
> .venv\Scripts\activate
> python main.py
> ```

---

## Setup - Linux

Install system dependencies (Ubuntu/Debian):

```bash
sudo apt install python3 python3-venv python3-pip git portaudio19-dev
```

For Arch-based distros:

```bash
sudo pacman -S python python-pip git portaudio
```

Clone and set up:

```bash
git clone https://github.com/synscott/clarity-voice.git
cd clarity-voice
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

> PyQt6 on Linux may also require `libxcb` and related Qt platform libraries. If the app fails to start with an xcb error, run:
> ```bash
> sudo apt install libxcb-cursor0
> ```

---

## Usage

### GUI (default)

```bash
python main.py
```

Select **File** to load a WAV or MP3, or **Microphone** to record live.

**Live recording:** Click **Start Recording**, speak, and watch pitch update in real time. Click **Stop & Analyze** to get the full analysis report and plots.

**File mode:** Browse to your audio file and click **Analyze**. Results appear immediately.

Use the **Floor** and **Ceiling** controls to set a target pitch range. The Hz display turns amber when you're outside the range. A teal overlay appears on the pitch plot.

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

---

## Analysis Output

| Metric | Description |
|---|---|
| F0 mean / median | Average pitch in Hz |
| F0 range | Min to max pitch across voiced frames |
| F0 std dev | Pitch stability - lower is more consistent |
| Voiced frames | % of frames where pitch was detected |
| F1 / F2 / F3 | Mean formant frequencies - resonance proxy |
| Voiced duration | Time spent above the speech threshold |
| Pause count | Number of pauses longer than 0.5s |

---

## Project Structure

```
core/
  analysis.py   Parselmouth/Praat acoustic analysis
  recorder.py   Mic recording (fixed duration and start/stop stream)
  report.py     Text summary and matplotlib visualization
gui/
  app.py        PyQt6 GUI - three-state UI (idle, live, results)
  realtime.py   Real-time pitch detection via sounddevice + numpy
main.py         Entry point - GUI by default, CLI with arguments
tests/          Unit tests for core analysis
docs/           Development notes
```

---

## Known Limitations

**Speech rate accuracy** degrades in noisy environments (fan noise, HVAC, etc.) where the dynamic range between background noise and speech is less than ~15 dB. Pitch and formant data remain reliable regardless. See [docs/dev-notes.md](docs/dev-notes.md) for details.

---

## Privacy

All data stays local. Audio is not retained after analysis unless you explicitly save it. No data is transmitted anywhere.

---

## License

MIT
