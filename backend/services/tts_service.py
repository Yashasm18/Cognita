"""Text-to-Speech service for Cognita.

Supports three engines (in order of quality):
  1. ElevenLabs — Premium, warm, human-like voices (free tier: 10K chars/month)
  2. gTTS — Free, decent quality, needs internet
  3. Piper TTS — Fast, offline, good quality, needs model download
"""

from __future__ import annotations

import os
import re
import uuid
import logging

from config import TTS_ENGINE, PIPER_MODEL_PATH, AUDIO_DIR

logger = logging.getLogger(__name__)

# ElevenLabs config (read from env)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")  # "George" — warm, calm
ELEVENLABS_MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")


class TTSService:
    """Generates audio files from text using ElevenLabs, gTTS, or Piper."""

    def __init__(self):
        self.audio_dir = AUDIO_DIR
        os.makedirs(self.audio_dir, exist_ok=True)

        # Determine best available engine
        self.engine = TTS_ENGINE

        if ELEVENLABS_API_KEY:
            self.engine = "elevenlabs"
            logger.info("✅ ElevenLabs TTS enabled (voice: %s)", ELEVENLABS_VOICE_ID)
        elif self.engine == "elevenlabs":
            logger.warning("⚠️  ELEVENLABS_API_KEY not set — falling back to gTTS")
            self.engine = "gtts"

        if self.engine == "piper" and PIPER_MODEL_PATH:
            try:
                from piper import PiperVoice
                self.piper_voice = PiperVoice.load(PIPER_MODEL_PATH)
                logger.info("✅ Piper TTS loaded: %s", PIPER_MODEL_PATH)
            except Exception as e:
                logger.warning("⚠️  Piper failed: %s — falling back to gTTS", e)
                self.engine = "gtts"
        elif self.engine not in ("elevenlabs",):
            self.engine = "gtts"
            logger.info("Using gTTS engine (set ELEVENLABS_API_KEY for premium voices)")

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
        text = re.sub(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
            r"\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
            r"\U0001f926-\U0001f937\U00010000-\U0010ffff\u2640-\u2642"
            r"\u2600-\u2B55\u200d\u23cf\u23e9\u231a\ufe0f\u3030📌💡⚡🔑📝📚🎯❓🧩🔗🧠📊📖🎓]+",
            "", text,
        )
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    async def generate_audio(self, text: str, lang: str = "en") -> dict:
        """Generate an audio file from text.

        Returns dict with audio_id, filename, file_path on success.
        """
        clean = self._clean_for_speech(text)
        if not clean or len(clean) < 5:
            return {"error": "Text too short to generate audio"}

        # Limit length to stay within free tier limits
        if len(clean) > 5000:
            clean = clean[:5000] + "... For the full explanation, read the text."

        audio_id = str(uuid.uuid4())[:8]

        try:
            if self.engine == "elevenlabs":
                return self._elevenlabs_generate(clean, audio_id)
            elif self.engine == "piper":
                return self._piper_generate(clean, audio_id)
            else:
                return self._gtts_generate(clean, audio_id, lang)
        except Exception as e:
            logger.error("TTS (%s) failed: %s", self.engine, e)
            # Fallback chain: elevenlabs → gtts
            if self.engine == "elevenlabs":
                try:
                    logger.info("Falling back to gTTS...")
                    return self._gtts_generate(clean, audio_id, lang)
                except Exception as e2:
                    logger.error("gTTS fallback also failed: %s", e2)
            return {"error": f"Failed to generate audio: {e}"}

    # ─── ElevenLabs ──────────────────────────────────────────

    def _elevenlabs_generate(self, text: str, audio_id: str) -> dict:
        """Generate audio using ElevenLabs API — warm, human-like voices."""
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        filename = f"{audio_id}.mp3"
        filepath = os.path.join(self.audio_dir, filename)

        # Generate audio
        audio_generator = client.text_to_speech.convert(
            text=text,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id=ELEVENLABS_MODEL,
            output_format="mp3_44100_128",
        )

        # Write audio bytes to file
        with open(filepath, "wb") as f:
            for chunk in audio_generator:
                f.write(chunk)

        logger.info("ElevenLabs TTS: %d chars → %s", len(text), filename)
        return {"audio_id": audio_id, "filename": filename, "file_path": filepath}

    # ─── gTTS ────────────────────────────────────────────────

    def _gtts_generate(self, text: str, audio_id: str, lang: str = "en") -> dict:
        """Generate audio using Google TTS (free, decent quality)."""
        from gtts import gTTS

        filename = f"{audio_id}.mp3"
        filepath = os.path.join(self.audio_dir, filename)

        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(filepath)

        return {"audio_id": audio_id, "filename": filename, "file_path": filepath}

    # ─── Piper ───────────────────────────────────────────────

    def _piper_generate(self, text: str, audio_id: str) -> dict:
        """Generate audio using Piper TTS (offline, fast)."""
        import wave
        import io

        wav_filename = f"{audio_id}.wav"
        wav_path = os.path.join(self.audio_dir, wav_filename)

        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            self.piper_voice.synthesize(text, wav_file)

        with open(wav_path, "wb") as f:
            f.write(wav_buffer.getvalue())

        return {"audio_id": audio_id, "filename": wav_filename, "file_path": wav_path}
