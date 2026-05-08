<div align="center">

# 🧠 Cognita

### Your AI study companion that speaks, shows, and teaches.

[![License: MIT](https://img.shields.io/badge/License-MIT-6C5CE7.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Groq](https://img.shields.io/badge/LLM-Groq-orange.svg)](https://groq.com)

*Upload your PDFs, images, and notes — get voice explanations, summaries, and practice questions powered by AI.*

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Multi-format Upload** | PDF, images (PNG/JPG), text files, Markdown, CSV |
| 🔊 **Voice Explanations** | AI reads and explains concepts aloud (Web Speech + gTTS/Piper) |
| 📝 **Smart Summaries** | Exam-ready summaries with key points highlighted |
| ❓ **Quiz Generation** | Auto-generate practice questions from your materials |
| 🧩 **Simplify Mode** | Re-explain complex topics in beginner-friendly language |
| ⚡ **Blazing Fast** | Powered by Groq (fastest LLM inference) with Ollama fallback |
| 🔒 **Privacy First** | Whisper STT runs locally — your voice never leaves your machine |
| 🎨 **Premium UI** | Dark glassmorphism design, responsive, buttery smooth |

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (React) |
| **Backend** | Python FastAPI |
| **LLM** | Groq (free tier) + Ollama (local fallback) |
| **Database** | Supabase (Postgres + pgvector + Storage) |
| **Voice In** | OpenAI Whisper (local STT) |
| **Voice Out** | gTTS / Piper TTS |
| **Deployment** | Docker → Vercel + Railway |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Groq API key](https://console.groq.com) (free)

### 1. Clone & Setup

```bash
git clone https://github.com/YOUR_USERNAME/cognita.git
cd cognita

# Copy env and add your Groq API key
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here
```

### 2. Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs at `http://localhost:8000` — API docs at `/api/docs`

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`

### 🐳 Docker (Alternative)

```bash
docker-compose up --build
```

## 📖 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload study material |
| `POST` | `/api/chat` | Chat with Cognita |
| `POST` | `/api/explain` | Get full document explanation |
| `POST` | `/api/tts` | Text-to-speech |
| `POST` | `/api/stt` | Speech-to-text (Whisper) |
| `GET` | `/api/sessions` | List study sessions |
| `GET` | `/api/health` | Health check + LLM status |

## 🗺️ Roadmap

- [x] Core chat with document context
- [x] PDF & image upload
- [x] Voice output (gTTS + browser TTS)
- [x] Multiple study modes (Explain, Quiz, Summarize, Simplify)
- [ ] Supabase persistent storage
- [ ] pgvector semantic search (RAG)
- [ ] Flashcard generation
- [ ] Spaced repetition scheduler
- [ ] Diagram/flowchart generation
- [ ] Mobile PWA
- [ ] Video explanations
- [ ] Collaborative study rooms
- [ ] Plugin system for custom LLMs

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

[MIT](LICENSE) — use it however you want.

---

<div align="center">

**Built with ❤️ for students everywhere**

*Cognita — Latin for "known/learned"*

</div>
