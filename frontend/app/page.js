'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { uploadFile, sendMessage, textToSpeech } from '@/lib/api';

const MODES = [
  { id: 'explain', label: '📖 Explain' },
  { id: 'summarize', label: '📝 Summarize' },
  { id: 'quiz', label: '❓ Quiz' },
  { id: 'simplify', label: '🧩 Simplify' },
];

export default function Home() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('explain');
  const [documents, setDocuments] = useState([]);
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessions, setSessions] = useState([]);

  // Audio state — tracks which message index is playing/loading
  const [playingIdx, setPlayingIdx] = useState(-1);
  const [ttsLoading, setTtsLoading] = useState(-1);
  const audioRef = useRef(null);

  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
      if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel();
    };
  }, []);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [input]);

  // ─── Send Message ─────────────────────────────────────────
  const handleSend = useCallback(async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;

    setInput('');
    setSuggestions([]);
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setLoading(true);

    try {
      const res = await sendMessage(msg, sessionId, mode, false);
      setSessionId(res.session_id);
      setMessages((prev) => [...prev, { role: 'assistant', content: res.message }]);
      if (res.suggested_questions?.length) setSuggestions(res.suggested_questions);
      setSessions((prev) => {
        const exists = prev.find((s) => s.session_id === res.session_id);
        if (!exists) return [{ session_id: res.session_id, title: 'Session', message_count: 1 }, ...prev];
        return prev;
      });
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ Error: ${err.message}. Make sure the backend is running.` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, sessionId, mode]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ─── File Upload ──────────────────────────────────────────
  const handleFileUpload = async (files) => {
    if (!files?.length) return;
    setUploading(true);
    try {
      for (const file of files) {
        const res = await uploadFile(file, sessionId);
        setSessionId(res.session_id);
        setDocuments((prev) => [...prev, {
          file_id: res.file_id, filename: res.filename, file_type: res.file_type,
          page_count: res.page_count, char_count: res.char_count,
        }]);
        setMessages((prev) => [...prev, {
          role: 'assistant',
          content: `📄 **${res.filename}** uploaded!\n\n${res.page_count ? `Pages: ${res.page_count} • ` : ''}${res.char_count ? `${res.char_count.toLocaleString()} chars extracted` : ''}\n\nReady to help you study. What would you like to know?`,
        }]);
      }
      setSuggestions(['Give me an overview', 'Explain key concepts', 'Generate practice questions']);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ Upload error: ${err.message}` }]);
    } finally {
      setUploading(false);
      setShowUpload(false);
    }
  };

  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); handleFileUpload(e.dataTransfer.files); };

  // ─── Audio / TTS ──────────────────────────────────────────
  const stopAll = useCallback(() => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ''; audioRef.current = null; }
    if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel();
    setPlayingIdx(-1);
    setTtsLoading(-1);
  }, []);

  const handleListen = useCallback(async (text, msgIdx) => {
    // If this message is already playing, stop it
    if (playingIdx === msgIdx) { stopAll(); return; }
    // If another message is playing, stop it first
    stopAll();

    setTtsLoading(msgIdx);

    try {
      const res = await textToSpeech(text);
      if (res.audio_url) {
        const audio = new Audio(res.audio_url);
        audioRef.current = audio;

        audio.oncanplaythrough = () => {
          setTtsLoading(-1);
          setPlayingIdx(msgIdx);
          audio.play().catch(() => {});
        };

        audio.onended = () => { setPlayingIdx(-1); audioRef.current = null; };
        audio.onerror = () => { setTtsLoading(-1); setPlayingIdx(-1); browserSpeak(text, msgIdx); };
        audio.load();
        return;
      }
    } catch {
      // Backend TTS unavailable
    }
    setTtsLoading(-1);
    browserSpeak(text, msgIdx);
  }, [playingIdx, stopAll]);

  const browserSpeak = (text, msgIdx) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const clean = text.replace(/[#*`_~\[\]]/g, '').slice(0, 3000);
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.onstart = () => setPlayingIdx(msgIdx);
    utterance.onend = () => setPlayingIdx(-1);
    utterance.onerror = () => setPlayingIdx(-1);
    window.speechSynthesis.speak(utterance);
  };

  // Bottom bar voice button — plays last assistant message
  const handleBottomVoice = () => {
    const lastAssistant = messages.filter(m => m.role === 'assistant').at(-1);
    if (!lastAssistant) return;
    const idx = messages.lastIndexOf(lastAssistant);
    if (playingIdx >= 0) { stopAll(); } else { handleListen(lastAssistant.content, idx); }
  };

  // ─── Helpers ──────────────────────────────────────────────
  const newSession = () => { stopAll(); setSessionId(null); setMessages([]); setDocuments([]); setSuggestions([]); };
  const getDocIcon = (t) => t === 'pdf' ? '📕' : ['png','jpg','jpeg','gif','webp'].includes(t) ? '🖼️' : '📄';
  const getDocIconClass = (t) => t === 'pdf' ? 'pdf' : ['png','jpg','jpeg','gif','webp'].includes(t) ? 'img' : 'txt';

  const getListenLabel = (idx) => {
    if (ttsLoading === idx) return '⏳ Loading...';
    if (playingIdx === idx) return '⏹️ Stop';
    return '🔊 Listen';
  };

  return (
    <div className="app-layout">
      {/* ─── Sidebar ────────────────────────── */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="logo-icon">🧠</div>
            <span>Cognita</span>
          </div>
          <div className="sidebar-tagline">Your AI study companion</div>
          <button className="new-session-btn" onClick={newSession}>✨ New Study Session</button>
        </div>

        {documents.length > 0 && (
          <div className="documents-panel">
            <div className="sidebar-section-label">📚 Materials ({documents.length})</div>
            {documents.map((doc) => (
              <div key={doc.file_id} className="doc-item">
                <div className={`doc-icon ${getDocIconClass(doc.file_type)}`}>{getDocIcon(doc.file_type)}</div>
                <div className="doc-name">{doc.filename}</div>
                <div className="doc-meta">{doc.page_count ? `${doc.page_count}p` : ''}</div>
              </div>
            ))}
          </div>
        )}

        <div className="sidebar-sessions">
          <div className="sidebar-section-label">💬 Sessions</div>
          {sessions.length === 0 && (
            <div style={{ padding: '8px 12px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>No sessions yet</div>
          )}
          {sessions.map((s) => (
            <div key={s.session_id} className={`session-item ${s.session_id === sessionId ? 'active' : ''}`} onClick={() => setSessionId(s.session_id)}>
              {s.title || 'Study Session'}
            </div>
          ))}
        </div>
      </aside>

      {/* ─── Main Area ──────────────────────── */}
      <main className="main-area">
        <header className="header">
          <div className="header-title">
            {documents.length > 0 ? `Studying ${documents.length} material${documents.length > 1 ? 's' : ''}` : 'Cognita 🧠'}
          </div>
          <div className="header-actions">
            <div className="mode-selector">
              {MODES.map((m) => (
                <button key={m.id} className={`mode-btn ${mode === m.id ? 'active' : ''}`} onClick={() => setMode(m.id)}>
                  {m.label}
                </button>
              ))}
            </div>
          </div>
        </header>

        {/* Chat */}
        <div className="chat-area">
          {messages.length === 0 ? (
            <div className="chat-empty">
              <div className="chat-empty-icon">🧠</div>
              <h2>Welcome to Cognita</h2>
              <p>Your AI study companion that speaks, shows, and teaches. Upload your study materials and I'll help you master them.</p>
              <div className="quick-actions">
                <button className="quick-action-btn" onClick={() => setShowUpload(true)}>📄 Upload PDF</button>
                <button className="quick-action-btn" onClick={() => setShowUpload(true)}>🖼️ Upload Images</button>
                <button className="quick-action-btn" onClick={() => handleSend('What can you help me with?')}>💡 What can you do?</button>
                <button className="quick-action-btn" onClick={() => handleSend('Help me create a study plan')}>📋 Study Plan</button>
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <div className="message-avatar">{msg.role === 'assistant' ? '🧠' : '👤'}</div>
                <div>
                  <div className="message-content">
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    ) : msg.content}
                  </div>
                  {msg.role === 'assistant' && (
                    <div className="message-actions">
                      <button
                        className={`msg-action-btn ${playingIdx === i ? 'active' : ''}`}
                        onClick={() => handleListen(msg.content, i)}
                        disabled={ttsLoading >= 0 && ttsLoading !== i}
                      >
                        {getListenLabel(i)}
                      </button>
                      <button className="msg-action-btn" onClick={() => { navigator.clipboard.writeText(msg.content); }}>
                        📋 Copy
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="message assistant">
              <div className="message-avatar">🧠</div>
              <div className="message-content">
                <div className="typing-indicator"><span></span><span></span><span></span></div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Suggestions */}
        {suggestions.length > 0 && !loading && (
          <div className="suggestions">
            {suggestions.map((q, i) => (
              <button key={i} className="suggestion-chip" onClick={() => handleSend(q)}>{q}</button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="input-area">
          <div className="input-wrapper">
            <button className="input-btn upload-btn" onClick={() => setShowUpload(true)} title="Upload file">📎</button>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={documents.length > 0 ? 'Ask about your study materials...' : 'Upload materials or ask anything...'}
              rows={1}
            />
            <button
              className={`input-btn voice-btn ${playingIdx >= 0 ? 'recording' : ''}`}
              onClick={handleBottomVoice}
              title={playingIdx >= 0 ? 'Stop speaking' : 'Read last response aloud'}
            >
              {playingIdx >= 0 ? '⏹️' : '🔊'}
            </button>
            <button className="input-btn send-btn" onClick={() => handleSend()} disabled={!input.trim() || loading} title="Send">
              ➤
            </button>
          </div>
          <div className="input-hint">Cognita • Groq AI + ElevenLabs Voice • Enter to send</div>
        </div>
      </main>

      {/* ─── Upload Modal ───────────────────── */}
      {showUpload && (
        <div className="upload-overlay" onClick={() => !uploading && setShowUpload(false)}>
          <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
            <h3>📤 Upload Study Materials</h3>
            <div
              className={`dropzone ${dragOver ? 'drag-over' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <div className="dropzone-icon">📁</div>
              <p>{uploading ? 'Processing...' : 'Drop files here or click to browse'}</p>
              <p className="formats">PDF, PNG, JPG, TXT, MD, CSV — up to 50MB</p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,.txt,.md,.csv"
              style={{ display: 'none' }}
              onChange={(e) => handleFileUpload(e.target.files)}
            />
            {uploading && (
              <div className="upload-progress">
                <span style={{ fontSize: '0.82rem' }}>Processing your files...</span>
                <div className="progress-bar"><div className="progress-fill" style={{ width: '60%' }} /></div>
              </div>
            )}
            <div className="modal-actions">
              <button className="btn-cancel" onClick={() => setShowUpload(false)} disabled={uploading}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
