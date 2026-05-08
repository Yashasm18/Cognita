"""Knowledge Base service — Full Supabase integration for persistent storage.

Uses Supabase for:
  - File storage (PDFs, images) via Supabase Storage
  - Document metadata (Postgres)
  - Chat message persistence
  - Session persistence
  - Search across documents

If Supabase is not configured, falls back to local in-memory storage.
"""

import logging
from typing import Optional, List
from config import SUPABASE_URL, SUPABASE_ANON_KEY

logger = logging.getLogger(__name__)

_supabase_client = None


def _get_supabase():
    """Lazy-initialize Supabase client."""
    global _supabase_client
    if _supabase_client is None and SUPABASE_URL and SUPABASE_ANON_KEY:
        try:
            from supabase import create_client

            _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            logger.info("✅ Supabase client initialized")
        except Exception as e:
            logger.warning("⚠️  Supabase initialization failed: %s", e)
    return _supabase_client


class KnowledgeBase:
    """Persistent knowledge base backed by Supabase.

    Falls back to in-memory storage when Supabase is not configured.
    """

    def __init__(self):
        self._local_docs: list[dict] = []
        self._local_sessions: dict[str, dict] = {}
        self._local_messages: list[dict] = []

    @property
    def supabase(self):
        return _get_supabase()

    @property
    def is_connected(self) -> bool:
        return self.supabase is not None

    # ═══════════════════════════════════════════════════════════
    #  Sessions
    # ═══════════════════════════════════════════════════════════

    async def create_session(self, session_id: str, title: str = "New Study Session") -> dict:
        """Create a new study session in the database."""
        record = {"session_id": session_id, "title": title}

        if self.supabase:
            try:
                result = (
                    self.supabase.table("sessions")
                    .upsert(record, on_conflict="session_id")
                    .execute()
                )
                logger.info("Session created in Supabase: %s", session_id)
                return result.data[0] if result.data else record
            except Exception as e:
                logger.warning("Supabase session create failed: %s", e)

        self._local_sessions[session_id] = record
        return record

    async def update_session_title(self, session_id: str, title: str):
        """Update a session's title."""
        if self.supabase:
            try:
                self.supabase.table("sessions").update({"title": title}).eq(
                    "session_id", session_id
                ).execute()
                return
            except Exception as e:
                logger.warning("Supabase session update failed: %s", e)

        if session_id in self._local_sessions:
            self._local_sessions[session_id]["title"] = title

    async def list_sessions(self) -> list[dict]:
        """List all sessions, most recent first."""
        if self.supabase:
            try:
                result = (
                    self.supabase.table("sessions")
                    .select("*")
                    .order("updated_at", desc=True)
                    .execute()
                )
                return result.data
            except Exception as e:
                logger.warning("Supabase list sessions failed: %s", e)

        return list(self._local_sessions.values())

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get a single session by ID."""
        if self.supabase:
            try:
                result = (
                    self.supabase.table("sessions")
                    .select("*")
                    .eq("session_id", session_id)
                    .single()
                    .execute()
                )
                return result.data
            except Exception as e:
                logger.warning("Supabase get session failed: %s", e)

        return self._local_sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its data."""
        if self.supabase:
            try:
                self.supabase.table("sessions").delete().eq(
                    "session_id", session_id
                ).execute()
                return True
            except Exception as e:
                logger.warning("Supabase delete session failed: %s", e)

        self._local_sessions.pop(session_id, None)
        self._local_messages = [m for m in self._local_messages if m.get("session_id") != session_id]
        self._local_docs = [d for d in self._local_docs if d.get("session_id") != session_id]
        return True

    # ═══════════════════════════════════════════════════════════
    #  Chat Messages
    # ═══════════════════════════════════════════════════════════

    async def save_message(self, session_id: str, role: str, content: str, mode: str = "explain") -> dict:
        """Save a chat message to the database."""
        record = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "mode": mode,
        }

        if self.supabase:
            try:
                result = self.supabase.table("chat_messages").insert(record).execute()
                return result.data[0] if result.data else record
            except Exception as e:
                logger.warning("Supabase save message failed: %s", e)

        self._local_messages.append(record)
        return record

    async def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict]:
        """Get chat history for a session."""
        if self.supabase:
            try:
                result = (
                    self.supabase.table("chat_messages")
                    .select("role, content, mode, created_at")
                    .eq("session_id", session_id)
                    .order("created_at", desc=False)
                    .limit(limit)
                    .execute()
                )
                return result.data
            except Exception as e:
                logger.warning("Supabase get history failed: %s", e)

        return [m for m in self._local_messages if m.get("session_id") == session_id][-limit:]

    # ═══════════════════════════════════════════════════════════
    #  Documents
    # ═══════════════════════════════════════════════════════════

    async def store_document(self, doc_info: dict, session_id: Optional[str] = None) -> dict:
        """Store a processed document.

        If Supabase is available, stores metadata in Postgres and
        the file in Supabase Storage. Otherwise, stores in memory.
        """
        record = {
            "file_id": doc_info["file_id"],
            "filename": doc_info["filename"],
            "file_type": doc_info["file_type"],
            "content_preview": doc_info["content_preview"],
            "char_count": doc_info.get("char_count", 0),
            "page_count": doc_info.get("page_count"),
            "session_id": session_id,
        }

        if self.supabase:
            try:
                # Store metadata in Postgres
                result = self.supabase.table("documents").insert(record).execute()
                logger.info("Document stored in Supabase: %s", doc_info["file_id"])

                # Store file in Supabase Storage
                if doc_info.get("file_path"):
                    storage_path = f"{doc_info['file_id']}_{doc_info['filename']}"
                    try:
                        with open(doc_info["file_path"], "rb") as f:
                            self.supabase.storage.from_("study-materials").upload(
                                storage_path, f.read()
                            )
                        # Update storage path
                        self.supabase.table("documents").update(
                            {"storage_path": storage_path}
                        ).eq("file_id", doc_info["file_id"]).execute()
                    except Exception as storage_err:
                        logger.warning("Storage upload failed: %s", storage_err)

                return result.data[0] if result.data else record
            except Exception as e:
                logger.warning("Supabase store failed: %s — using local", e)

        # Local fallback
        self._local_docs.append(record)
        return record

    async def search_documents(self, query: str, limit: int = 5) -> list[dict]:
        """Search documents by keyword."""
        if self.supabase:
            try:
                result = (
                    self.supabase.table("documents")
                    .select("*")
                    .ilike("content_preview", f"%{query}%")
                    .limit(limit)
                    .execute()
                )
                return result.data
            except Exception as e:
                logger.warning("Supabase search failed: %s", e)

        # Local fallback — simple text search
        results = []
        q = query.lower()
        for doc in self._local_docs:
            if q in doc.get("filename", "").lower() or q in doc.get(
                "content_preview", ""
            ).lower():
                results.append(doc)
        return results[:limit]

    async def get_session_documents(self, session_id: str) -> list[dict]:
        """Get all documents for a specific session."""
        if self.supabase:
            try:
                result = (
                    self.supabase.table("documents")
                    .select("*")
                    .eq("session_id", session_id)
                    .order("created_at", desc=False)
                    .execute()
                )
                return result.data
            except Exception as e:
                logger.warning("Supabase get session docs failed: %s", e)

        return [d for d in self._local_docs if d.get("session_id") == session_id]

    async def list_documents(self) -> list[dict]:
        """List all stored documents."""
        if self.supabase:
            try:
                result = (
                    self.supabase.table("documents")
                    .select("*")
                    .order("created_at", desc=True)
                    .execute()
                )
                return result.data
            except Exception as e:
                logger.warning("Supabase list failed: %s", e)

        return self._local_docs

    async def delete_document(self, file_id: str) -> bool:
        """Delete a document by file_id."""
        if self.supabase:
            try:
                # Delete from storage
                doc = self.supabase.table("documents").select("storage_path").eq(
                    "file_id", file_id
                ).single().execute()
                if doc.data and doc.data.get("storage_path"):
                    try:
                        self.supabase.storage.from_("study-materials").remove(
                            [doc.data["storage_path"]]
                        )
                    except Exception:
                        pass

                # Delete metadata
                self.supabase.table("documents").delete().eq(
                    "file_id", file_id
                ).execute()
                return True
            except Exception as e:
                logger.warning("Supabase delete failed: %s", e)

        self._local_docs = [d for d in self._local_docs if d["file_id"] != file_id]
        return True
