import pytest
from pydantic import ValidationError

from app.models import Transcript


def test_transcript_model_valid_data():
    data = {"text": "This is a test transcript."}
    transcript = Transcript(**data)
    assert transcript.text == data["text"]


def test_transcript_model_invalid_data():
    data = {
        "text": "",
    }
    with pytest.raises(ValidationError) as exc_info:
        Transcript(**data)
    errors = exc_info.value.errors()
    assert any(
        error["loc"] == ("text",) and error["type"] == "string_too_short"
        for error in errors
    )
