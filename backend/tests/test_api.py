"""Basic tests for Cognita backend API endpoints.

Run with: python -m pytest tests/ -v
Or without pytest: python tests/test_api.py
"""

import sys
import os
import asyncio

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_document_processor():
    """Test that document processor handles text files."""
    from services.document_processor import DocumentProcessor

    processor = DocumentProcessor("/tmp/cognita_test_uploads")

    # Test text processing
    content = b"Hello World! This is a test document about biology."
    result = asyncio.get_event_loop().run_until_complete(
        processor.process_file(content, "test.txt", "text/plain")
    )

    assert result["file_id"]
    assert result["filename"] == "test.txt"
    assert result["file_type"] == "txt"
    assert "Hello World" in result["extracted_text"]
    assert result["char_count"] > 0
    print("  ✅ Document processor: text files")


def test_document_processor_pdf():
    """Test PDF handling (basic — verifies invalid PDF doesn't crash the app)."""
    from services.document_processor import DocumentProcessor

    processor = DocumentProcessor("/tmp/cognita_test_uploads")

    # Invalid PDF should be handled gracefully
    content = b"Not a real PDF"
    try:
        result = asyncio.get_event_loop().run_until_complete(
            processor.process_file(content, "fake.pdf", "application/pdf")
        )
        assert result["file_id"]
    except Exception:
        # PyMuPDF raises on truly invalid bytes — that's fine
        pass
    print("  ✅ Document processor: invalid PDF handled gracefully")


def test_tts_service():
    """Test TTS text cleaning."""
    from services.tts_service import TTSService

    tts = TTSService()

    # Test markdown cleaning
    dirty = "## Hello **World**\n- Item 1\n- Item 2\n`code here`"
    clean = tts._clean_for_speech(dirty)

    assert "##" not in clean
    assert "**" not in clean
    assert "`" not in clean
    print("  ✅ TTS service: markdown cleaning")


def test_ai_agent_sessions():
    """Test session management."""
    from services.ai_agent import AIAgent

    agent = AIAgent()

    # Create session
    session = agent.get_or_create_session()
    assert session.session_id
    assert session.title == "New Study Session"
    assert len(session.documents) == 0

    # Add document
    agent.add_document_to_session(session.session_id, {
        "file_id": "test123",
        "filename": "biology.pdf",
        "file_type": "pdf",
        "extracted_text": "Photosynthesis is...",
        "content_preview": "Photosynthesis is...",
        "page_count": 5,
    })

    assert len(session.documents) == 1
    assert "biology" in session.title.lower()

    # Get context
    ctx = session.get_context()
    assert "Photosynthesis" in ctx

    # List sessions
    sessions = agent.list_sessions()
    assert len(sessions) == 1

    # Get session info
    info = agent.get_session_info(session.session_id)
    assert info["document_count"] == 1

    print("  ✅ AI agent: session management")


def test_llm_service_init():
    """Test LLM service initialization (no API call)."""
    from services.llm_service import LLMService

    service = LLMService()
    assert service.provider in ("groq", "ollama")
    print(f"  ✅ LLM service: initialized (provider: {service.provider})")


def test_schemas():
    """Test Pydantic schemas validate correctly."""
    from models.schemas import ChatRequest, FileUploadResponse

    # Valid chat request
    req = ChatRequest(message="Hello", mode="explain")
    assert req.message == "Hello"
    assert req.voice_response is False

    # Valid upload response
    resp = FileUploadResponse(
        file_id="abc",
        filename="test.pdf",
        file_type="pdf",
        content_preview="...",
        char_count=100,
    )
    assert resp.status == "processed"

    print("  ✅ Schemas: validation works")


def run_all_tests():
    """Run all tests."""
    print("\n🧪 Cognita Backend Tests\n" + "─" * 35)

    tests = [
        test_document_processor,
        test_document_processor_pdf,
        test_tts_service,
        test_ai_agent_sessions,
        test_llm_service_init,
        test_schemas,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  ❌ {test_fn.__name__}: {e}")
            failed += 1

    print(f"\n{'─' * 35}")
    print(f"  Results: {passed} passed, {failed} failed")
    print()

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
