"""Cognita AI Agent — The core study companion brain.

Manages study sessions, document context, and conversational AI
powered by Groq / Ollama through the LLM service.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional

from services.llm_service import LLMService, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class StudySession:
    """Represents a study session with documents and chat history."""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or str(uuid.uuid4())[:12]
        self.created_at = datetime.now().isoformat()
        self.documents: list[dict] = []
        self.chat_history: list[dict] = []
        self.title = "New Study Session"

    def add_document(self, doc_info: dict):
        """Add a processed document to this session."""
        self.documents.append(doc_info)
        if self.title == "New Study Session" and doc_info.get("filename"):
            name = doc_info["filename"]
            if len(name) > 40:
                name = name[:37] + "..."
            self.title = f"Studying: {name}"

    def get_context(self) -> str:
        """Build full context from all documents for the LLM."""
        if not self.documents:
            return "No study materials uploaded yet."

        parts = ["=== UPLOADED STUDY MATERIALS ===\n"]
        for i, doc in enumerate(self.documents, 1):
            parts.append(f"📄 Document {i}: {doc['filename']}")
            if doc.get("page_count"):
                parts.append(f"   Pages: {doc['page_count']}")
            # Limit per-document text to keep within context window
            text = doc.get("extracted_text", "")
            if len(text) > 12000:
                text = text[:12000] + "\n\n[... content truncated for length ...]"
            parts.append(f"   Content:\n{text}\n")
            parts.append("---\n")

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "created_at": self.created_at,
            "document_count": len(self.documents),
            "message_count": len(self.chat_history),
        }


# ─── Mode-specific prompts ──────────────────────────────────

MODE_PROMPTS = {
    "explain": (
        "Explain the following in depth. Break it down into clear sections, "
        "use examples and analogies, and make it easy to understand."
    ),
    "summarize": (
        "Create a concise, exam-ready summary. Use bullet points, highlight "
        "key terms in bold, and keep it scannable."
    ),
    "quiz": (
        "Generate 5-10 practice questions based on the material. Include a mix of:\n"
        "- Multiple choice (4 options)\n"
        "- True/False\n"
        "- Short answer\n"
        "Provide the correct answers at the end."
    ),
    "simplify": (
        "Explain this like I'm a complete beginner. Use simple language, "
        "everyday analogies, and avoid jargon. If there's jargon, define it."
    ),
}


class AIAgent:
    """The core Cognita AI agent."""

    def __init__(self):
        self.llm = LLMService()
        self.sessions: dict[str, StudySession] = {}

    def get_or_create_session(self, session_id: str | None = None) -> StudySession:
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        session = StudySession(session_id)
        self.sessions[session.session_id] = session
        return session

    def add_document_to_session(self, session_id: str, doc_info: dict) -> StudySession:
        session = self.get_or_create_session(session_id)
        session.add_document(doc_info)
        return session

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        mode: str = "explain",
    ) -> dict:
        """Send a message to Cognita and get a response."""
        session = self.get_or_create_session(session_id)
        context = session.get_context()

        # Build message list for the LLM
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Inject document context
        if session.documents:
            messages.append(
                {
                    "role": "user",
                    "content": f"Here are my study materials:\n\n{context}",
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "I've analyzed your study materials and I'm ready to help! "
                        "I can explain concepts, create summaries, generate practice "
                        "questions, or simplify anything. What would you like to start with?"
                    ),
                }
            )

        # Add recent chat history (last 20 messages to stay in context window)
        for msg in session.chat_history[-20:]:
            messages.append(msg)

        # Apply mode-specific instruction
        mode_instruction = MODE_PROMPTS.get(mode, "")
        full_message = message
        if mode_instruction and mode != "explain":
            full_message = f"[Mode: {mode}]\n{mode_instruction}\n\nStudent's request: {message}"

        messages.append({"role": "user", "content": full_message})

        try:
            ai_response = await self.llm.chat(messages)

            # Update history
            session.chat_history.append({"role": "user", "content": message})
            session.chat_history.append({"role": "assistant", "content": ai_response})

            suggestions = self._extract_suggestions(ai_response)

            return {
                "message": ai_response,
                "session_id": session.session_id,
                "suggested_questions": suggestions,
                "mode": mode,
            }
        except Exception as e:
            logger.error("AI chat error: %s", e)
            return {
                "message": f"I encountered an error: {e}. Please check your API key and try again.",
                "session_id": session.session_id,
                "suggested_questions": [],
                "mode": mode,
            }

    async def explain_document(self, session_id: str, doc_index: int = 0) -> dict:
        """Generate a full explanation of a specific document."""
        session = self.get_or_create_session(session_id)
        if not session.documents:
            return {
                "message": "No documents uploaded yet! Upload your study materials first.",
                "session_id": session.session_id,
                "suggested_questions": [],
                "mode": "explain",
            }

        doc = session.documents[min(doc_index, len(session.documents) - 1)]
        prompt = (
            f'Please give me a comprehensive explanation of "{doc["filename"]}".\n\n'
            "Structure it as:\n"
            "1. 📌 **Overview** — What is this material about?\n"
            "2. 🔑 **Key Concepts** — List and explain the main ideas\n"
            "3. 💡 **Detailed Breakdown** — Walk through the important sections\n"
            "4. ⚡ **Quick Summary** — A brief recap\n"
            "5. 📝 **Practice Questions** — 3-5 questions to test understanding"
        )
        return await self.chat(prompt, session_id, mode="explain")

    def _extract_suggestions(self, text: str) -> list[str]:
        defaults = [
            "Can you explain this in simpler terms?",
            "Generate practice questions for me",
            "Create a summary of the key points",
        ]
        questions = []
        for line in text.split("\n"):
            line = line.strip()
            if line.endswith("?") and 15 < len(line) < 150:
                clean = line.lstrip("0123456789.-) ").lstrip("*").strip()
                if clean:
                    questions.append(clean)
        return questions[:3] if questions else defaults

    def list_sessions(self) -> list[dict]:
        return [s.to_dict() for s in self.sessions.values()]

    def get_session_info(self, session_id: str) -> dict | None:
        session = self.sessions.get(session_id)
        return session.to_dict() if session else None
