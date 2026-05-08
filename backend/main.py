"""Cognita 🧠 — FastAPI Backend Server.

Your AI study companion that speaks, shows, and teaches.
Open-source • Groq + Ollama • Supabase • Whisper + Piper TTS
"""

import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Optional

from config import (
    UPLOAD_DIR,
    AUDIO_DIR,
    CORS_ORIGINS,
    HOST,
    PORT,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
)
from services.document_processor import DocumentProcessor
from services.ai_agent import AIAgent
from services.tts_service import TTSService
from services.stt_service import STTService
from services.knowledge_base import KnowledgeBase
from models.schemas import ChatRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────

app = FastAPI(
    title="Cognita 🧠",
    description="Your AI study companion that speaks, shows, and teaches.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Services ────────────────────────────────────────────────

doc_processor = DocumentProcessor(UPLOAD_DIR)
ai_agent = AIAgent()
tts_service = TTSService()
stt_service = STTService()
knowledge_base = KnowledgeBase()


# ═══════════════════════════════════════════════════════════════
#  Health
# ═══════════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    llm_status = await ai_agent.llm.health_check()
    return {
        "status": "healthy",
        "service": "Cognita 🧠",
        "version": "1.0.0",
        "llm": llm_status,
    }


# ═══════════════════════════════════════════════════════════════
#  File Upload
# ═══════════════════════════════════════════════════════════════

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
):
    """Upload a study material (PDF, image, text)."""
    if file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                400,
                f"File type '.{ext}' not supported. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Max: {MAX_FILE_SIZE // (1024*1024)}MB")

    doc_info = await doc_processor.process_file(
        content, file.filename or "unnamed", file.content_type or "application/octet-stream"
    )

    # Create / get session
    if not session_id:
        session = ai_agent.get_or_create_session()
        session_id = session.session_id
    ai_agent.add_document_to_session(session_id, doc_info)

    # Persist in knowledge base
    await knowledge_base.store_document(doc_info)

    return {
        "file_id": doc_info["file_id"],
        "filename": doc_info["filename"],
        "file_type": doc_info["file_type"],
        "content_preview": doc_info["content_preview"],
        "page_count": doc_info.get("page_count"),
        "char_count": doc_info.get("char_count", 0),
        "session_id": session_id,
        "status": "processed",
    }


# ═══════════════════════════════════════════════════════════════
#  Chat
# ═══════════════════════════════════════════════════════════════

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Chat with Cognita about your study materials."""
    response = await ai_agent.chat(
        message=request.message,
        session_id=request.session_id,
        mode=request.mode,
    )

    result = {
        "message": response["message"],
        "session_id": response["session_id"],
        "suggested_questions": response.get("suggested_questions", []),
        "mode": response.get("mode", "explain"),
        "has_audio": False,
        "audio_url": None,
    }

    if request.voice_response:
        audio = await tts_service.generate_audio(response["message"])
        if "error" not in audio:
            result["has_audio"] = True
            result["audio_url"] = f"/api/audio/{audio['filename']}"

    return result


# ═══════════════════════════════════════════════════════════════
#  Explain Document
# ═══════════════════════════════════════════════════════════════

@app.post("/api/explain")
async def explain_document(
    session_id: str = Form(...),
    doc_index: int = Form(0),
    voice: bool = Form(False),
):
    """Get a comprehensive explanation of an uploaded document."""
    response = await ai_agent.explain_document(session_id, doc_index)

    result = {
        "message": response["message"],
        "session_id": response["session_id"],
        "suggested_questions": response.get("suggested_questions", []),
        "has_audio": False,
        "audio_url": None,
    }

    if voice:
        audio = await tts_service.generate_audio(response["message"])
        if "error" not in audio:
            result["has_audio"] = True
            result["audio_url"] = f"/api/audio/{audio['filename']}"

    return result


# ═══════════════════════════════════════════════════════════════
#  Text-to-Speech
# ═══════════════════════════════════════════════════════════════

@app.post("/api/tts")
async def text_to_speech(text: str = Form(...)):
    """Convert any text to speech audio."""
    audio = await tts_service.generate_audio(text)
    if "error" in audio:
        raise HTTPException(500, audio["error"])
    return {"audio_url": f"/api/audio/{audio['filename']}", "audio_id": audio["audio_id"]}


@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """Serve an audio file."""
    filepath = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Audio file not found")
    media = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    return FileResponse(filepath, media_type=media)


# ═══════════════════════════════════════════════════════════════
#  Speech-to-Text (Whisper)
# ═══════════════════════════════════════════════════════════════

@app.post("/api/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Transcribe audio to text using Whisper."""
    content = await audio.read()
    result = await stt_service.transcribe(content, audio.filename or "audio.webm")
    if "error" in result:
        raise HTTPException(500, result["error"])
    return {"transcript": result["transcript"], "language": result.get("language", "en")}


# ═══════════════════════════════════════════════════════════════
#  Sessions
# ═══════════════════════════════════════════════════════════════

@app.post("/api/sessions/new")
async def create_session():
    session = ai_agent.get_or_create_session()
    return session.to_dict()


@app.get("/api/sessions")
async def list_sessions():
    return {"sessions": ai_agent.list_sessions()}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    info = ai_agent.get_session_info(session_id)
    if not info:
        raise HTTPException(404, "Session not found")
    return info


@app.get("/api/sessions/{session_id}/documents")
async def get_session_documents(session_id: str):
    session = ai_agent.sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "documents": [
            {
                "file_id": d["file_id"],
                "filename": d["filename"],
                "file_type": d["file_type"],
                "content_preview": d["content_preview"],
                "page_count": d.get("page_count"),
                "char_count": d.get("char_count", 0),
            }
            for d in session.documents
        ]
    }


# ═══════════════════════════════════════════════════════════════
#  Run
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    print()
    print("  🧠  Cognita — Your AI Study Companion")
    print("  ─────────────────────────────────────")
    print(f"  📡  Server:   http://{HOST}:{PORT}")
    print(f"  📚  API Docs: http://{HOST}:{PORT}/api/docs")
    print(f"  📁  Uploads:  {UPLOAD_DIR}")
    print()

    uvicorn.run(app, host=HOST, port=PORT)
