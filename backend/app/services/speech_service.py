from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from threading import Lock

from faster_whisper import WhisperModel

from backend.app.config import settings

logger = logging.getLogger(__name__)

_model: WhisperModel | None = None
_model_lock = Lock()
_MODEL_LOAD_OPTIONS = {
    "device": "cpu",
    "compute_type": "int8",
    "cpu_threads": 4,
}


class SpeechTranscriptionError(Exception):
    """Raised when recorded audio cannot be transcribed."""


class SpeechModelUnavailableError(Exception):
    """Raised when the Whisper model cannot be loaded."""


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    logger.info("Loading Whisper model '%s' on CPU", settings.whisper_model)
                    _model = WhisperModel(settings.whisper_model, **_MODEL_LOAD_OPTIONS)
                except Exception as exc:
                    logger.exception("Unable to load Whisper model '%s'", settings.whisper_model)
                    raise SpeechModelUnavailableError(
                        "Speech transcription is temporarily unavailable. Please type your answer."
                    ) from exc
    return _model


def transcribe_audio(audio: bytes, content_type: str) -> str:
    if not audio:
        raise SpeechTranscriptionError("The recording is empty.")

    mime_type = content_type.split(";", maxsplit=1)[0].strip().lower()
    suffix = {
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
    }.get(mime_type, ".webm")

    recording_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as recording:
            recording.write(audio)
            recording.flush()
            recording_path = Path(recording.name)
        segments, _ = _get_model().transcribe(
            str(recording_path),
            language=settings.stt_language or None,
            vad_filter=True,
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
    except SpeechModelUnavailableError:
        raise
    except Exception as exc:
        logger.exception("Whisper transcription failed")
        raise SpeechTranscriptionError(
            "Unable to transcribe the recording. Please try again or type your answer."
        ) from exc
    finally:
        if recording_path is not None:
            recording_path.unlink(missing_ok=True)

    if not transcript:
        raise SpeechTranscriptionError(
            "No speech was detected. Please try again or type your answer."
        )
    return transcript
