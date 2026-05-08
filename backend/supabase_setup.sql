-- ═══════════════════════════════════════════════════════════════
--  Cognita 🧠 — Supabase Database Setup
--  Run this in Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- ═══════════════════════════════════════════════════════════════

-- 1. Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Sessions table — persistent study sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT UNIQUE NOT NULL,
    title TEXT DEFAULT 'New Study Session',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Documents table — uploaded study materials metadata
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id TEXT UNIQUE NOT NULL,
    session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    content_preview TEXT DEFAULT '',
    char_count INTEGER DEFAULT 0,
    page_count INTEGER,
    storage_path TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Chat messages table — persistent conversation history
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id TEXT REFERENCES sessions(session_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    mode TEXT DEFAULT 'explain',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id);
CREATE INDEX IF NOT EXISTS idx_documents_file_id ON documents(file_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at);

-- 6. Auto-update updated_at on sessions
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS sessions_updated_at ON sessions;
CREATE TRIGGER sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- 7. Create storage bucket for study materials
INSERT INTO storage.buckets (id, name, public)
VALUES ('study-materials', 'study-materials', false)
ON CONFLICT (id) DO NOTHING;

-- 8. Storage policy — allow authenticated and anon uploads (for now)
CREATE POLICY "Allow uploads" ON storage.objects
    FOR INSERT WITH CHECK (bucket_id = 'study-materials');
CREATE POLICY "Allow reads" ON storage.objects
    FOR SELECT USING (bucket_id = 'study-materials');

-- ✅ Done! Your Cognita database is ready.
