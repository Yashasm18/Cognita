"""Speech-to-Text service for Cognita using OpenAI Whisper.

Whisper runs locally — no API key needed, fully private.
"""

import os
import uuid
import logging
import tempfile

from config import WHISPER_MODEL

logger = logging.getLogger(__name__)

_whisper_model = None


def _load_whisper():
    """Lazy-load Whisper model to avoid slow startup."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper

            logger.info("Loading Whisper model: %s ...", WHISPER_MODEL)
            _whisper_model = whisper.load_model(WHISPER_MODEL)
            logger.info("✅ Whisper model loaded")
        except Exception as e:
            logger.error("Failed to load Whisper: %s", e)
            raise
    return _whisper_model


class STTService:
    """Transcribes audio to text using OpenAI Whisper (local)."""

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> dict:
        """Transcribe audio bytes to text.

        Accepts common audio formats: webm, wav, mp3, m4a, ogg, flac.

        Returns dict with transcript and language.
        """
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"

        # Write to temp file (Whisper needs a file path)
        tmp_path = os.path.join(tempfile.gettempdir(), f"cognita_stt_{uuid.uuid4().hex[:8]}.{ext}")
        try:
            with open(tmp_path, "wb") as f:
                f.write(audio_bytes)

            model = _load_whisper()
            result = model.transcribe(tmp_path, fp16=False)

            transcript = result.get("text", "").strip()
            language = result.get("language", "en")

            logger.info(
                "Transcribed %d bytes → %d chars (%s)",
                len(audio_bytes),
                len(transcript),
                language,
            )

            return {
                "transcript": transcript,
                "language": language,
                "confidence": 1.0,  # Whisper doesn't expose confidence directly
            }

        except Exception as e:
            logger.error("Whisper transcription failed: %s", e)
            return {
                "transcript": "",
                "language": "en",
                "confidence": 0.0,
                "error": str(e),
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
