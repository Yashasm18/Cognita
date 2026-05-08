"""Text-to-Speech service for Cognita.

Supports two engines:
  - gTTS (Google Text-to-Speech) — free, works out of the box, needs internet
  - Piper TTS — fast, offline, high quality, needs model download
"""

import os
import re
import uuid
import logging
from gtts import gTTS

from config import TTS_ENGINE, PIPER_MODEL_PATH, AUDIO_DIR

logger = logging.getLogger(__name__)


class TTSService:
    """Generates audio files from text."""

    def __init__(self):
        self.engine = TTS_ENGINE
        self.audio_dir = AUDIO_DIR
        os.makedirs(self.audio_dir, exist_ok=True)

        if self.engine == "piper" and PIPER_MODEL_PATH:
            try:
                from piper import PiperVoice

                self.piper_voice = PiperVoice.load(PIPER_MODEL_PATH)
                logger.info("✅ Piper TTS loaded: %s", PIPER_MODEL_PATH)
            except Exception as e:
                logger.warning("⚠️  Piper TTS failed to load: %s — falling back to gTTS", e)
                self.engine = "gtts"
        else:
            self.engine = "gtts"
            logger.info("Using gTTS engine (set TTS_ENGINE=piper for offline TTS)")

    def _clean_for_speech(self, text: str) -> str:
        """Strip markdown formatting for cleaner speech output."""
        text = re.sub(r"#{1,6}\s*", "", text)
        text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
        text = re.sub(r"`([^`]*)`", r"\1", text)
        text = re.sub(r"```[\s\S]*?```", "See the code block in the text.", text)
        text = re.sub(r"^[\s]*[-*+]\s", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[\s]*\d+\.\s", "", text, flags=re.MULTILINE)
        text = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r"\1", text)
        text = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r"\1", text)
        # Remove common emoji
        text = re.sub(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
            r"\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
            r"\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642"
            r"\u2600-\u2B55\u200d\u23cf\u23e9\u231a\ufe0f\u3030📌💡⚡🔑📝📚🎯❓🧩🔗🧠📊📖🎓]+",
            "",
            text,
        )
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    async def generate_audio(self, text: str, lang: str = "en") -> dict:
        """Generate an MP3 audio file from text.

        Returns dict with audio_id, filename, file_path on success,
        or dict with error key on failure.
        """
        clean = self._clean_for_speech(text)
        if not clean or len(clean) < 5:
            return {"error": "Text too short to generate audio"}

        # Limit length so TTS doesn't take forever
        if len(clean) > 5000:
            clean = clean[:5000] + "... For the full explanation, read the text response."

        audio_id = str(uuid.uuid4())[:8]
        filename = f"{audio_id}.mp3"
        filepath = os.path.join(self.audio_dir, filename)

        try:
            if self.engine == "piper":
                return await self._piper_generate(clean, filepath, audio_id, filename)
            else:
                return self._gtts_generate(clean, filepath, audio_id, filename, lang)
        except Exception as e:
            logger.error("TTS generation failed: %s", e)
            return {"error": f"Failed to generate audio: {e}"}

    def _gtts_generate(
        self, text: str, filepath: str, audio_id: str, filename: str, lang: str
    ) -> dict:
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(filepath)
        return {"audio_id": audio_id, "filename": filename, "file_path": filepath}

    async def _piper_generate(
        self, text: str, filepath: str, audio_id: str, filename: str
    ) -> dict:
        import wave
        import io

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            self.piper_voice.synthesize(text, wav_file)

        # Convert WAV to a file (Piper outputs WAV, not MP3)
        wav_path = filepath.replace(".mp3", ".wav")
        with open(wav_path, "wb") as f:
            f.write(wav_buffer.getvalue())

        wav_filename = filename.replace(".mp3", ".wav")
        return {
            "audio_id": audio_id,
            "filename": wav_filename,
            "file_path": wav_path,
        }
