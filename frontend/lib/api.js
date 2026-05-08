const API_BASE = '/api';

export async function uploadFile(file, sessionId) {
  const form = new FormData();
  form.append('file', file);
  if (sessionId) form.append('session_id', sessionId);

  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
  return res.json();
}

export async function sendMessage(message, sessionId, mode = 'explain', voiceResponse = false) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      mode,
      voice_response: voiceResponse,
    }),
  });
  if (!res.ok) throw new Error('Chat failed');
  return res.json();
}

export async function explainDocument(sessionId, docIndex = 0, voice = false) {
  const form = new FormData();
  form.append('session_id', sessionId);
  form.append('doc_index', docIndex.toString());
  form.append('voice', voice.toString());

  const res = await fetch(`${API_BASE}/explain`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('Explain failed');
  return res.json();
}

export async function textToSpeech(text) {
  const form = new FormData();
  form.append('text', text);
  const res = await fetch(`${API_BASE}/tts`, { method: 'POST', body: form });
  if (!res.ok) throw new Error('TTS failed');
  return res.json();
}

export async function createSession() {
  const res = await fetch(`${API_BASE}/sessions/new`, { method: 'POST' });
  return res.json();
}

export async function listSessions() {
  const res = await fetch(`${API_BASE}/sessions`);
  return res.json();
}

export async function getSessionDocuments(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/documents`);
  return res.json();
}

export function getAudioUrl(filename) {
  return `${API_BASE}/audio/${filename}`;
}
