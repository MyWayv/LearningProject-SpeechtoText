# Mood Analysis

## What the application does

1. Records microphone audio in the browser.
2. Streams the audio to Python backend.
3. Transcribes speech using elevenlabs.
4. Creates speech for next question using elevenlabs.
5. Sends the transcript to Gemini/OpenAI for mood analysis and question creation.
6. Stores the session's transcript and mood result in Firestore.
7. Stores the audio file in a Google Bucket.
8. Returns the transcript and mood to the browser for display.

---

## Mood analysis

The mood analysis step uses an LLM to classify the overall emotional tone of the transcript using the wheel of emotions.

---

## Question creation

The question creation happens after mood analysis and tries to prompt users to talk about their feelings in a natural way.

---

## Technology overview

Backend:

- Python

- FastAPI

- Pydantic

- Pydub

Frontend:

- TypeScript

- Web Audio API

Cloud services:

- Elevenlabs

- OpenAI

- Gemini

- Firestore

-Google Bucket

Infrastructure:

- Docker

- GitHub Actions

- Google Artifact Registry

- Pytest

- Ruff

---

## Local testing (production build):

Test the full application with static files served by FastAPI:

```bash
./rebuild.sh # from root
```

or run ./rebuild.sh from root.

Visit `http://localhost:8000` to access the complete application.

---

## GCP setup

This application requires the following Google Cloud services:

1. **Elevenlabs API key in env file**
2. **OpenAI API key in env file**
3. **Gemini API** (via Vertex AI)
4. **Cloud Firestore**
5. **Google Bucket**
6. **Google Artifact Registry**
7. **Workload Identity Federation**

#### Prerequisites

- A Google Cloud Platform account
- A GCP project with billing enabled
- The `gcloud` CLI installed
- The 6 services above enabled and configured on the project

#### Authentication using Application Default Credentials (ADC)

This application uses Application Default Credentials (ADC) to authenticate with Google Cloud services. ADC automatically finds credentials based on the application environment.

### Environmnent variables

Most of the env variables are just urls for both front and back ends. at root level env file there are also the keys for OpenAI and Elevenlabs.
