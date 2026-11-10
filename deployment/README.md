---
title: NyayaSaathi
emoji: ⚖️
colorFrom: teal
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: Scoped legal-information assistant for fictional Indian consumer and rental-deposit issues.
---

# NyayaSaathi Hugging Face Docker Space

This directory contains the Hugging Face Space metadata without replacing the
root GitHub `README.md`. The deployable application remains the repository
root, with the production entrypoint in `Dockerfile`.

## Space repository workflow

Create a separate Hugging Face Docker Space repository, then copy the tracked
runtime files from this repository into that Space:

- `Dockerfile`, `.dockerignore`, `requirements.txt`, `pyproject.toml`
- `app.py`, `nyayasaathi/`, `sources/`, and `.streamlit/config.toml`
- this file as the Space repository's root `README.md`

Do not copy `.env`, `.streamlit/secrets.toml`, virtual environments, evaluation
raw outputs, private records, or `app.py.backup`. Keep the Space repository
private until its secrets and content review are complete. The curated legal
catalogue is required at `sources/catalogue.json`; do not omit `sources/`.

## Required Space secrets

Add these in **Space Settings → Repository secrets**. Never commit them:

| Secret | Value |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `GEMINI_MODEL` | An account-available structured-output Gemini model; the locally verified configuration used `gemini-3.5-flash-lite` |
| `GROQ_API_KEY` | Groq API key for browser microphone transcription |
| `GROQ_MODEL` | `whisper-large-v3-turbo` |

Optional non-secret variables can be configured as Space variables. Keep
`APP_MODE=production` and `LLM_PROVIDER=gemini`; the application does not expose
an offline/simulation selector in production.

The container listens on `0.0.0.0:7860`. Text input, browser microphone
recording, transcript confirmation, curated legal grounding, case summaries,
and editable drafts remain enabled. The app makes no API call on startup, but
submitted fictional text and explicitly approved audio are sent to the
configured providers; review their terms before using the Space.

## Local verification before pushing the Space

From the repository root, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app.py nyayasaathi
.\.venv\Scripts\python.exe -m pip check
docker build --tag nyayasaathi-hf .
```

The Docker build command is optional when Docker is unavailable locally. Do not
run live provider calls as part of deployment verification.
