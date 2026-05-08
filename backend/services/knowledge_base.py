"""Knowledge Base service — Supabase integration for persistent storage.

Uses Supabase for:
  - File storage (PDFs, images)
  - Document metadata (Postgres)
  - Vector embeddings (pgvector) for semantic search
  - User authentication (future)

If Supabase is not configured, falls back to local in-memory storage.
"""

import logging
from typing import Optional
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

    @property
    def supabase(self):
        return _get_supabase()

    async def store_document(self, doc_info: dict) -> dict:
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
        }

        if self.supabase:
            try:
                # Store metadata
                result = (
                    self.supabase.table("documents")
                    .insert(record)
                    .execute()
                )
                logger.info("Document stored in Supabase: %s", doc_info["file_id"])

                # Store file in Supabase Storage
                if doc_info.get("file_path"):
                    with open(doc_info["file_path"], "rb") as f:
                        self.supabase.storage.from_("study-materials").upload(
                            f"{doc_info['file_id']}_{doc_info['filename']}",
                            f.read(),
                        )

                return record
            except Exception as e:
                logger.warning("Supabase store failed: %s — using local", e)

        # Local fallback
        self._local_docs.append(record)
        return record

    async def search_documents(self, query: str, limit: int = 5) -> list[dict]:
        """Search documents by keyword (or semantic search with pgvector).

        TODO: Implement pgvector semantic search when embeddings are set up.
        """
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
                self.supabase.table("documents").delete().eq(
                    "file_id", file_id
                ).execute()
                return True
            except Exception as e:
                logger.warning("Supabase delete failed: %s", e)

        self._local_docs = [d for d in self._local_docs if d["file_id"] != file_id]
        return True
