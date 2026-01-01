# STT-Mood

Minimal web application that records microphone audio, transcribes speech using Google Cloud Speech-to-Text, and analyzes the mood of the transcript using a Google LLM (Gemini), then saves it on Firestore.

---

## What the application does

1. Records microphone audio in the browser.
2. Uploads the audio to a Python backend.
3. Transcribes speech using Google Cloud Speech-to-Text.
4. Sends the transcript to Gemini for mood analysis.
5. Stores the transcript and mood result in Firestore.
6. Returns the transcript and mood to the browser for display.

---

## Mood analysis

The mood analysis step uses a large language model to classify the overall emotional tone of the transcript.

The model returns structured JSON that includes:
- a mood label
- a confidence score between 0 and 1
- optional evidence phrases extracted from the transcript

---

## API

### POST /v1/transcribe

Accepts a microphone audio upload and runs the full pipeline.

Returns:
- the transcript text
- the mood analysis result
- a record identifier

Example response:

```json
{
  "record_id": "abc123",
  "transcript": "I had a really good day and feel relieved.",
  "mood": {
    "label": "happy",
    "confidence": 0.86,
    "evidence": ["really good day", "feel relieved"]
  }
}
```
---

## Technology overview
Backend:

- Python

- FastAPI

- Pydantic

Frontend:

- TypeScript

- Minimal UI using browser MediaRecorder

Cloud services:

- Google Cloud Speech-to-Text

- Gemini (LLM)

- Firestore

Infrastructure:

- Docker

- GitHub Actions

---

## Development

### Run the backend locally:
```
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Run the frontend locally:
```
cd web
npm install
npm run dev
```

### GCP setup

This application requires the following Google Cloud services:

1. **Google Cloud Speech-to-Text API**
2. **Gemini API** (via Vertex AI)
3. **Cloud Firestore**

#### Prerequisites

- A Google Cloud Platform account
- A GCP project with billing enabled
- The `gcloud` CLI installed
- The 3 services above enabled on the project

#### Authentication using Application Default Credentials (ADC)

This application uses Application Default Credentials (ADC) to authenticate with Google Cloud services. ADC automatically finds credentials based on the application environment.