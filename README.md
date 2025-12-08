<<<<<<< HEAD
# Skye-assistant
=======
Alexa Voice Assistant (local)

This repository contains a local Python-based voice assistant (`alexa_assistant.py`) that supports:

- Voice or text input (uses `speech_recognition` for microphone input)
- Text-to-speech using `pyttsx3` and optional higher-quality `gTTS` playback
- Math/calculation support (WolframAlpha first, `eval()` fallback)
- Weather lookup (OpenWeather by default) — configure a `WEATHER_API_KEY`
- Reminders stored in `reminders.db` with a background checker
- Send email (via SMTP) using environment `EMAIL_ADDRESS` and `EMAIL_PASSWORD`
- Play local music from a `music/` folder (uses `python-vlc` if VLC is available, otherwise `pygame`)
- Open applications (Windows shortcuts used)
- Wikipedia search, YouTube playback, jokes, news headlines

Files of interest
- `alexa_assistant.py` — main assistant implementation (voice loop + features)
- `app.py` — small Flask web UI (optional, basic front-end included in `templates/`)
- `requirements.txt` — Python dependencies
- `.env.example` — example environment variables to configure API keys and email

Quick setup (Windows PowerShell)

1. Create and activate a virtual environment (recommended):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
py -m pip install -r requirements.txt
```

3. Configure environment variables:
- Copy `.env.example` to `.env` and fill in your keys (do NOT commit `.env`).

Required (or recommended) environment variables
- `OPENAI_API_KEY` — optional (for GPT integration)
- `WOLFRAM_APP_ID` — recommended for accurate math/calculation
- `NEWS_API_KEY` — for top headlines (NewsAPI)
- `WEATHER_API_KEY` — OpenWeather API key (or modify `get_weather()` to use Open-Meteo)
- `EMAIL_ADDRESS`, `EMAIL_PASSWORD` — for `send_email()` (SMTP). Use an app-password for Gmail.

4. Create a `music/` folder and add MP3/WAV files if you want local playback:

```powershell
mkdir music
# add some .mp3 files into ./music
```

Run the assistant

```powershell
py alexa_assistant.py
```

Usage notes
- Say your assistant name (default “Alexa”) followed by a command, or just speak normally.
- Examples: "What's the time?", "Set reminder", "Send email", "Play <song name>", "What is 2 + 2?"
- Use Ctrl+C to stop the assistant; it will attempt a graceful shutdown of audio subsystems.

Troubleshooting
- If you see issues importing `cgi` on Python 3.13+, a small shim `cgi.py` is included in the repo to restore minimal functionality.
- If `python-vlc` playback fails, ensure VLC is installed and available in PATH, or rely on `pygame` playback.
- If `pyttsx3` has driver errors, install `pywin32`:

```powershell
py -m pip install pywin32
```

Security
- Do NOT commit real API keys or email passwords to version control. Use `.env` and `.gitignore`.

Want improvements?
- I can refactor the assistant into smaller modules, add a configuration UI, or add safer math parsing (e.g. `asteval` or `sympy`).
>>>>>>> 1f6e2b0 (abc)
