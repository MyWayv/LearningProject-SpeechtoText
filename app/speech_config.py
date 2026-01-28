import os

from google.cloud.speech_v2.types import cloud_speech

from app.deps import get_project_id

# LINEAR 16 PCM 16kHz mono for better results

# Recognition config for batch transcription
config = cloud_speech.RecognitionConfig(
    explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
        encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        audio_channel_count=1,
    ),
    language_codes=["en-US"],
    model="chirp_3",
)


def get_batch_recognition_request(data) -> cloud_speech.RecognitionConfig:
    request = cloud_speech.RecognizeRequest(
        recognizer=f"projects/{get_project_id()}" + os.getenv("RECOGNIZER_NAME"),
        config=config,
        content=data,
    )
    return request


# Recognition config for streaming transcription
st_config = cloud_speech.RecognitionConfig(
    explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
        encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        audio_channel_count=1,
    ),
    language_codes=["en-US"],
    model="long",  # chirp3 doesnt support interim results
    features=cloud_speech.RecognitionFeatures(
        enable_automatic_punctuation=False,  # disabled for UI
    ),
)
streaming_config = cloud_speech.StreamingRecognitionConfig(
    config=st_config,
    streaming_features=cloud_speech.StreamingRecognitionFeatures(
        interim_results=True,
    ),
)
config_request = cloud_speech.StreamingRecognizeRequest(
    recognizer=f"projects/{get_project_id()}" + os.getenv("RECOGNIZER_NAME"),
    streaming_config=streaming_config,
)


def get_streaming_config_request() -> cloud_speech.StreamingRecognizeRequest:
    return config_request
