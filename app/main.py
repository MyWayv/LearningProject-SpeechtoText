from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from .models import Mood, Transcript, Response

app = FastAPI()

# CORS fix
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/v1/transcribe/")
async def transcribe(file: UploadFile = File(...)):
    data = await file.read()
    return Transcript(
        uid="1231312313123",
        text="hi"
    )

@app.post("/v1/analyze_mood/")
async def analyze():
    return "Hi"