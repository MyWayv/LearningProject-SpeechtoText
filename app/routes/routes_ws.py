import os
import threading
import time
from multiprocessing import Event, Process, Queue

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)
from google.cloud.speech_v2.types import cloud_speech

from app.deps import get_speech_v2_client
from app.models import Transcript
from app.services import (
    moodAnalysisStep,
    uploadToBucketStep,
    uploadToFirestoreStep,
)
from app.speech_config import get_streaming_config_request

router = APIRouter(tags=["ws"])

use_threading = False


# STT process function to run separately
def stt_process(audio_queue, res_queue, stop, start_time):
    last_response_time = None
    first_response = True
    while not stop.is_set():
        start = time.time()

        # gRPC request generator
        def requests():
            yield get_streaming_config_request()
            while not stop.is_set():
                # 4 min limit, then restart stream recognize
                if time.time() - start > 240:
                    break
                chunk = audio_queue.get()
                if chunk is None:
                    break
                # yield audio chunks to google stt
                yield cloud_speech.StreamingRecognizeRequest(audio=chunk)

        # process responses
        try:
            # call gRPC stt, return iterator
            responses = get_speech_v2_client().streaming_recognize(requests=requests())
            for response in responses:  # iterator blocks thread if no response
                for result in response.results:
                    transcript_text = result.alternatives[0].transcript
                    current_time = time.time()
                    if first_response:
                        print(
                            "[Process] Initial STT response in",
                            current_time - start_time,
                            "seconds",
                        )
                        first_response = False
                    if last_response_time is not None:
                        print(
                            "Time since last STT response:",
                            current_time - last_response_time,
                            "seconds",
                        )
                    last_response_time = current_time
                    res_queue.put(
                        {
                            "transcript": transcript_text,
                            "is_final": result.is_final,
                            "stability": result.stability,
                        }
                    )
        except Exception as e:
            print("error in STT process:", e)


# WebSocket for realtime audio transcription
@router.websocket(os.getenv("STREAM_PROCESS_AUDIO_URL"))
async def websocket_stream_process_audio(websocket: WebSocket):
    def stt_thread(start_time):
        last_response_time = None
        first_response = True
        while not stop.is_set():
            start = time.time()

            # gRPC request generator
            def requests():
                yield get_streaming_config_request()
                while not stop.is_set():
                    if (
                        time.time() - start > 240
                    ):  # 4 min limit, then restart stream recognize
                        break
                    chunk = audio_queue.get()
                    if chunk is None:
                        break
                    yield cloud_speech.StreamingRecognizeRequest(
                        audio=chunk
                    )  # yield audio chunks to google stt

            # call gRPC stt
            responses: cloud_speech.StreamingRecognizeResponse = (
                get_speech_v2_client().streaming_recognize(  # returns iterator
                    requests=requests()
                )
            )

            # process responses
            try:
                for response in responses:  # iterator blocks thread if no response
                    for result in response.results:
                        # print("STT Result received:\n", result)
                        transcript_text = result.alternatives[0].transcript
                        current_time = time.time()
                        if first_response:
                            print(
                                "[Thread] Initial STT response in",
                                current_time - start_time,
                                "seconds",
                            )
                            first_response = False
                        if last_response_time is not None:
                            print(
                                "Time since last STT response:",
                                current_time - last_response_time,
                                "seconds",
                            )
                        last_response_time = current_time
                        res_queue.put(
                            {
                                "transcript": transcript_text,
                                "is_final": result.is_final,
                                "stability": result.stability,
                            }
                        )
            except Exception as e:
                print("or in STT thread:", e)

    # queues for thread safe audio and results passing
    audio_queue = Queue()  # audio chunks from websocket, get consumed by stt thread
    audioBytes = bytearray()
    res_queue = Queue()  # send stt results from stt thread to main thread
    stop = Event()
    full_transcript = ""

    # initialization
    await websocket.accept()

    # start process/thread and record start time for measuring initial response
    start_process = time.time()
    if use_threading:
        print("Using threading for STT")
        threading.Thread(target=stt_thread, args=(start_process,), daemon=True).start()
    else:
        print("Using multiprocessing for STT")
        p1 = Process(
            target=stt_process, args=(audio_queue, res_queue, stop, start_process)
        )
        p1.start()
    print("STT process/thread started in", time.time() - start_process, "seconds")

    start_receiving_audio = time.time()
    try:
        while True:
            # receive audio data from websocket
            data = await websocket.receive_bytes()

            # put audio into q
            MAX_CHUNK_SIZE = 25600
            for i in range(0, len(data), MAX_CHUNK_SIZE):
                chunk = data[i : i + MAX_CHUNK_SIZE]
                audio_queue.put(chunk)
                audioBytes.extend(chunk)

            # read from results q
            while not res_queue.empty():
                res = res_queue.get()
                if res["is_final"]:
                    full_transcript += res["transcript"] + ". "
                # send result back to client for realtime display
                await websocket.send_json(res)
    except WebSocketDisconnect as e:
        print("websocket disconnected:", e)
    except Exception as e:
        print("error during websocket communication:", e)
    finally:
        print(
            "ended receiving audio and closed ws after",
            time.time() - start_receiving_audio,
            "seconds",
        )
        # cleanup
        stop.set()
        audio_queue.put(None)
        if not use_threading:
            p1.join()

        # process final transcript
        transcript = Transcript(
            text=full_transcript,
        )

        start_mood_analysis = time.time()
        mood = await moodAnalysisStep(transcript)
        print(
            "Mood analysis completed in", time.time() - start_mood_analysis, "seconds"
        )

        start_firestore_upload = time.time()
        res = await uploadToFirestoreStep(transcript, mood)
        print(
            "Firestore upload completed in",
            time.time() - start_firestore_upload,
            "seconds",
        )

        if res["uid"]:
            start_bucket_upload = time.time()
            await uploadToBucketStep(audioBytes, res["uid"])
            print(
                "Bucket upload completed in",
                time.time() - start_bucket_upload,
                "seconds",
            )
    return res
