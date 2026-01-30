import os
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    UploadFile,
)

from app.services import (
    batch_transcription_step,
    get_from_firestore,
    mood_analysis_step,
    upload_to_bucket_step,
    upload_to_firestore_step,
)

router = APIRouter(tags=["http"])


# POST batch audio processing endpoint
@router.post(os.getenv("BATCH_PROCESS_AUDIO_URL"))
async def batch_process_audio(file: Annotated[UploadFile, File(...)]):
    transcript, data = await batch_transcription_step(file)
    mood = await mood_analysis_step(transcript)
    res = await upload_to_firestore_step(transcript, mood)
    if res["uid"]:
        await upload_to_bucket_step(data, res["uid"])
    return res


# GET records from firestore endpoint
@router.get(os.getenv("FIRESTORE_GET_URL"))
async def firestore_get_records():
    records = await get_from_firestore()
    return records
