"""Pydantic models for Cognita API request/response schemas."""

from pydantic import BaseModel
from typing import Optional


class FileUploadResponse(BaseModel):
    """Response after uploading a file."""
    file_id: str
    filename: str
    file_type: str
    content_preview: str
    page_count: Optional[int] = None
    char_count: int = 0
    status: str = "processed"
    session_id: str = ""


class ChatRequest(BaseModel):
    """Request to chat with the AI agent."""
    message: str
    session_id: Optional[str] = None
    voice_response: bool = False
    mode: str = "explain"  # explain, quiz, summarize, simplify


class ChatResponse(BaseModel):
    """Response from the AI agent."""
    message: str
    session_id: str
    has_audio: bool = False
    audio_url: Optional[str] = None
    suggested_questions: list[str] = []
    mode: str = "explain"


class VoiceUploadResponse(BaseModel):
    """Response after transcribing voice input."""
    transcript: str
    confidence: float = 0.0


class DocumentInfo(BaseModel):
    """A document in the knowledge base."""
    file_id: str
    filename: str
    file_type: str
    content_preview: str
    page_count: Optional[int] = None
    char_count: int = 0


class SessionInfo(BaseModel):
    """Information about a study session."""
    session_id: str
    title: str
    created_at: str
    document_count: int
    message_count: int
