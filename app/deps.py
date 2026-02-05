import os

from elevenlabs import ElevenLabs
from google import genai
from google.auth import default
from google.cloud import firestore, storage
from openai import OpenAI

# Clients startup and config
credentials, project = default()
gemini_client = genai.Client(
    vertexai=True,  # vertex for ADC so there are no keys
    project=project,
    location="global",
    credentials=credentials,
)

firestore_client = firestore.Client()

storage_client = storage.Client()

elevenlabs_client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),  # TODO look for more secure way later
)

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),  # TODO look for more secure way later
)


# Export all clients
def get_gemini_client():
    return gemini_client


def get_firestore_client():
    return firestore_client


def get_storage_client():
    return storage_client


def get_elevenlabs():
    return elevenlabs_client


def get_openai_client():
    return openai_client
