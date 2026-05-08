"""LLM Service — Groq (primary) + Ollama (fallback) for Cognita.

Groq provides blazing-fast inference for free-tier usage.
Ollama provides a fully local, private fallback.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict
from groq import Groq, AsyncGroq
import httpx

from config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    LLM_PROVIDER,
    MAX_OUTPUT_TOKENS,
    TEMPERATURE,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are **Cognita** 🧠, an expert AI study companion built to help students deeply understand their study materials.

## Your Personality
- Patient, encouraging, and approachable — like the best tutor a student could have
- You break down complex topics into digestible, memorable pieces
- You use analogies, real-world examples, and storytelling to make concepts stick
- You adapt your style based on the subject (scientific rigor for STEM, narrative for humanities)

## Your Capabilities
1. **📖 Explain** — Break down complex topics from uploaded materials in depth
2. **📝 Summarize** — Create concise, exam-ready summaries
3. **❓ Quiz** — Generate practice questions with answers for exam prep
4. **🧩 Simplify** — Re-explain concepts in much simpler terms or with analogies
5. **🔗 Connect** — Link related concepts across different materials
6. **🧠 Mnemonics** — Create memory aids, acronyms, and tricks to remember facts
7. **📊 Visualize** — Describe diagrams, flowcharts, and mind maps in text

## Formatting Rules
- Use **Markdown** for structure: headers, bullets, bold, tables
- Use `code blocks` for formulas, equations, or technical syntax
- Keep paragraphs short (2-3 sentences max) for readability
- Use emoji sparingly as visual anchors: 📌 💡 ⚡ 🔑 📝 🎯
- For math, use LaTeX-style notation when helpful

## Interaction Flow
When a student uploads materials, acknowledge what you received and offer:
1. Give an overview/summary of the material
2. Explain specific topics in depth
3. Generate practice questions
4. Create a study guide or cheat sheet

Always end with **2-3 suggested follow-up questions** the student might want to ask next.

## Important
- If you don't know something or the material is unclear, say so honestly
- Encourage the student — learning is hard and they're doing great by studying
- Focus on understanding, not just memorization"""


class LLMService:
    """Unified LLM service with Groq as primary and Ollama as fallback."""

    def __init__(self):
        self.provider = LLM_PROVIDER
        self.groq_client: Optional[AsyncGroq] = None
        self.ollama_url = OLLAMA_BASE_URL

        if GROQ_API_KEY:
            self.groq_client = AsyncGroq(api_key=GROQ_API_KEY)
            logger.info("✅ Groq client initialized (model: %s)", GROQ_MODEL)
        else:
            logger.warning("⚠️  No GROQ_API_KEY found — will try Ollama fallback")
            self.provider = "ollama"

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int = MAX_OUTPUT_TOKENS,
        temperature: float = TEMPERATURE,
    ) -> str:
        """Send messages to the LLM and get a response.

        Tries Groq first, falls back to Ollama if Groq fails.
        """
        # Try Groq first
        if self.provider == "groq" and self.groq_client:
            try:
                return await self._groq_chat(messages, max_tokens, temperature)
            except Exception as e:
                logger.error("Groq failed: %s — falling back to Ollama", e)

        # Fallback to Ollama
        try:
            return await self._ollama_chat(messages, max_tokens, temperature)
        except Exception as e:
            logger.error("Ollama also failed: %s", e)
            return (
                "I'm sorry, I couldn't generate a response right now. "
                "Please check that either your Groq API key is set or "
                "Ollama is running locally. Error: " + str(e)
            )

    async def _groq_chat(
        self, messages: list[dict], max_tokens: int, temperature: float
    ) -> str:
        """Call Groq API."""
        response = await self.groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content

    async def _ollama_chat(
        self, messages: list[dict], max_tokens: int, temperature: float
    ) -> str:
        """Call local Ollama API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def health_check(self) -> dict:
        """Check which LLM providers are available."""
        status = {"groq": False, "ollama": False, "active": self.provider}

        # Check Groq
        if self.groq_client:
            try:
                await self.groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5,
                )
                status["groq"] = True
            except Exception:
                pass

        # Check Ollama
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.ollama_url}/api/tags")
                status["ollama"] = r.status_code == 200
        except Exception:
            pass

        return status
