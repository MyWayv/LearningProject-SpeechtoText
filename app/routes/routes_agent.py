import asyncio
import base64
import os
import threading
import uuid
from datetime import datetime

from elevenlabs import RealtimeAudioOptions, RealtimeEvents
from elevenlabs.realtime.scribe import AudioFormat, CommitStrategy
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from app.agent import analyze_mood, get_next_question
from app.deps import get_elevenlabs
from app.models import AgentSession, QAMoodPair
from app.services import upload_agent_audio_to_bucket, upload_agent_session
from app.wheel_of_emotions import get_emotion_depth, get_wheel_of_emotions

router = APIRouter(tags=["agent"])


async def stt_elevenlabs_session(
    audio_queue, res_queue, answer_transcript_container, answer_ready
):
    print("[STT] Starting ElevenLabs STT session")
    elevenlabs = get_elevenlabs()
    stop = asyncio.Event()

    connection = await elevenlabs.speech_to_text.realtime.connect(
        RealtimeAudioOptions(
            model_id="scribe_v2_realtime",
            audio_format=AudioFormat.PCM_16000,
            sample_rate=16000,
            include_timestamps=True,
            commit_strategy=CommitStrategy.VAD,
            vad_silence_threshold_secs=1.5,
            vad_threshold=0.4,
            min_speech_duration_ms=100,
            min_silence_duration_ms=100,
        )
    )

    def on_session_started(data):
        print(f"[STT] Session started: {data.get('session_id', 'unknown')}")

    def on_partial_transcript(data):
        res_queue.put_nowait(
            {
                "type": "transcript",
                "transcript": data.get("text", ""),
                "is_final": False,
            }
        )

    def on_committed_transcript(data):
        text = data.get("text", "")
        answer_transcript_container["current"] += text
        res_queue.put_nowait(
            {
                "type": "transcript",
                "transcript": text,
                "is_final": True,
            }
        )
        # signal that answer is ready (VAD detected end of speech)
        print(f"[STT] VAD detected silence, answer complete: {text}")
        answer_ready.set()

    def on_error(error):
        print(f"[STT] Error: {error}")
        stop.set()

    def on_close():
        print("[STT] Connection closed by server")
        stop.set()

    connection.on(RealtimeEvents.SESSION_STARTED, on_session_started)
    connection.on(RealtimeEvents.PARTIAL_TRANSCRIPT, on_partial_transcript)
    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT, on_committed_transcript)
    connection.on(RealtimeEvents.ERROR, on_error)
    connection.on(RealtimeEvents.CLOSE, on_close)

    async def send_audio():
        last_send_time = asyncio.get_event_loop().time()
        min_interval = 0.005  # 5ms between chunks

        while not stop.is_set() and not answer_ready.is_set():
            try:
                chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                if chunk is None:
                    break

                # rate limit to prevent queue overflow
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - last_send_time
                if time_since_last < min_interval:
                    await asyncio.sleep(min_interval - time_since_last)

                audio_base64 = base64.b64encode(chunk).decode("utf-8")
                await connection.send({"audio_base_64": audio_base64})
                last_send_time = asyncio.get_event_loop().time()
            except asyncio.TimeoutError:
                continue

    sender = asyncio.create_task(send_audio())
    try:
        # wait for either answer_ready or stop event
        await asyncio.wait(
            [
                asyncio.create_task(answer_ready.wait()),
                asyncio.create_task(stop.wait()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
    finally:
        print("[STT] Closing session")
        await connection.close()
        sender.cancel()
        try:
            await sender
        except asyncio.CancelledError:
            pass


async def receive_audio(
    websocket: WebSocket,
    audio_queue: asyncio.Queue,
    audioBytes: bytearray,
    res_queue: asyncio.Queue,
):
    try:
        while True:
            # get audio data
            data = await websocket.receive_bytes()
            audio_queue.put_nowait(data)
            audioBytes.extend(data)
            # check for responses and send to client
            while not res_queue.empty():
                res = await res_queue.get()
                await websocket.send_json(res)
    except WebSocketDisconnect:
        print("[STREAMING] receive_audio: WebSocket disconnected")
        raise
    except Exception as e:
        print(f"[STREAMING] receive_audio error: {e}")
        raise


def upload_session_in_background(
    audio_bytes: bytearray,
    session_id: str,
    session_timestamp: str,
    qa_pairs_with_moods: list[QAMoodPair],
    final_mood: str,
    final_confidence: float,
    final_depth: int,
    question_count: int,
):
    try:
        # only upload if we have audio data
        if not audio_bytes:
            print(f"[AGENT] No audio data to upload for session: {session_id}")
            return

        # upload audio to bucket
        audio_url = upload_agent_audio_to_bucket(
            bytes(audio_bytes), session_id, session_timestamp
        )

        # create session object
        session = AgentSession(
            session_id=session_id,
            created_at=datetime.fromisoformat(session_timestamp),
            qa_pairs=qa_pairs_with_moods,
            final_mood=final_mood,
            final_confidence=final_confidence,
            final_depth=final_depth,
            question_count=question_count,
            audio_url=audio_url,
        )

        # upload session to Firestore
        upload_agent_session(session)
        print(f"[AGENT] Background upload completed for session: {session_id}")
    except Exception as e:
        print(f"[AGENT] Background upload failed for session {session_id}: {e}")


@router.websocket(os.getenv("AGENT_URL"))
async def websocket_agent(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())
    session_timestamp = datetime.now().isoformat()
    audio_queue = asyncio.Queue()
    res_queue = asyncio.Queue()
    audioBytes = bytearray()

    try:
        mood_confidence = 0.0
        question_counter = 0
        current_depth = 0
        max_depth = 3
        max_questions = 5
        # [question, answer]
        qa_pairs: list[tuple[str, str]] = []
        # [mood, confidence]
        moods: list[tuple[str, float]] = []
        # QAPair objects for upload
        qa_pairs_with_moods: list[QAMoodPair] = []
        wheel = get_wheel_of_emotions()

        # start receiving audio continuously
        receive_task = asyncio.create_task(
            receive_audio(websocket, audio_queue, audioBytes, res_queue)
        )

        while question_counter < max_questions:
            # check if should stop: high confidence and max depth reached
            if mood_confidence >= 0.9 and current_depth >= max_depth:
                print(
                    f"[AGENT] Stopping: High confidence ({mood_confidence}) at depth {current_depth}"
                )
                break

            # get question from agent
            if question_counter == 0:
                question = "Hello! How are you feeling today?"
            else:
                question = await get_next_question(
                    qa_pairs, moods, current_depth, max_depth
                )

            # ask question
            print(f"[AGENT] Question {question_counter + 1}: {question}")
            await websocket.send_json({"type": "question", "text": question})

            # wait for user to read the question
            print("[AGENT] Waiting 5 seconds for user to read question...")
            await asyncio.sleep(5.0)

            # clear old audio from queue
            cleared = 0
            while not audio_queue.empty():
                try:
                    audio_queue.get_nowait()
                    cleared += 1
                except asyncio.QueueEmpty:
                    break
            if cleared > 0:
                print(f"[AGENT] Cleared {cleared} old audio chunks from queue")

            # signal frontend to update UI
            print("[AGENT] Now listening for user response...")
            await websocket.send_json({"type": "listening"})

            # start new STT session for this answer
            answer_transcript_container = {"current": ""}
            answer_ready = asyncio.Event()

            print(f"[AGENT] Starting STT session for question {question_counter + 1}")
            stt_task = asyncio.create_task(
                stt_elevenlabs_session(
                    audio_queue, res_queue, answer_transcript_container, answer_ready
                )
            )

            # wait for VAD to detect end of speech
            print(
                f"[AGENT] Waiting for user response to question {question_counter + 1}..."
            )
            await answer_ready.wait()

            # wait for STT task to complete cleanup
            await stt_task

            answer_transcript = answer_transcript_container["current"]
            print(f"[AGENT] Received answer: {answer_transcript}")

            # analyze response
            await websocket.send_json({"type": "analyzing"})
            mood, mood_confidence = await analyze_mood(
                qa_pairs, moods, question, answer_transcript
            )

            # determine depth of detected emotion
            current_depth = get_emotion_depth(mood, wheel)
            depth_name = (
                ["unknown", "primary", "secondary", "tertiary"][current_depth]
                if current_depth <= 3
                else "unknown"
            )

            print(
                f"[AGENT] Detected mood: {mood} ({depth_name} level), confidence: {mood_confidence}"
            )

            # go to next question
            qa_pairs.append((question, answer_transcript))
            moods.append((mood, mood_confidence))
            qa_pairs_with_moods.append(
                QAMoodPair(
                    question=question,
                    answer=answer_transcript,
                    mood=mood,
                    confidence=mood_confidence,
                    depth=current_depth,
                )
            )
            question_counter += 1

        # determine final depth
        final_depth = get_emotion_depth(mood, wheel)
        depth_name = (
            ["unknown", "primary", "secondary", "tertiary"][final_depth]
            if final_depth <= 3
            else "unknown"
        )

        if mood_confidence >= 0.9 and final_depth >= max_depth:
            print(
                f"[AGENT] Mood detected with high confidence at maximum depth: {mood} ({depth_name})"
            )
            await websocket.send_json(
                {"type": "result", "mood": mood, "confidence": mood_confidence}
            )
        elif mood_confidence >= 0.9:
            print(
                f"[AGENT] Mood detected with high confidence but not at max depth: {mood} ({depth_name}, depth {final_depth}/{max_depth})"
            )
            await websocket.send_json(
                {"type": "result", "mood": mood, "confidence": mood_confidence}
            )
        else:
            print(
                f"[AGENT] Max questions reached. Best mood: {mood} ({depth_name}), confidence: {mood_confidence}"
            )
            # send the best mood, even if not 0.9 confidence
            await websocket.send_json(
                {"type": "result", "mood": mood, "confidence": mood_confidence}
            )

        # give frontend time to receive final message before cleanup
        await asyncio.sleep(0.5)

    except WebSocketDisconnect as e:
        print(f"[AGENT] Websocket disconnected: {e}")
    except Exception as e:
        print(f"[AGENT] error during websocket communication: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        # cleanup
        print("[AGENT] Cleaning up websocket session")
        if "receive_task" in locals():
            receive_task.cancel()
            try:
                await receive_task
            except (asyncio.CancelledError, WebSocketDisconnect):
                pass
            except Exception as e:
                print(f"[AGENT] Error during receive_task cleanup: {e}")

        # upload session data in background (works for complete and incomplete sessions)
        if "qa_pairs_with_moods" in locals():
            upload_thread = threading.Thread(
                target=upload_session_in_background,
                args=(
                    audioBytes,
                    session_id,
                    session_timestamp,
                    qa_pairs_with_moods,
                    mood if "mood" in locals() else "unknown",
                    mood_confidence if "mood_confidence" in locals() else 0.0,
                    final_depth if "final_depth" in locals() else 0,
                    question_counter if "question_counter" in locals() else 0,
                ),
                daemon=True,
            )
            upload_thread.start()
            print(f"[AGENT] Started background upload for session: {session_id}")
