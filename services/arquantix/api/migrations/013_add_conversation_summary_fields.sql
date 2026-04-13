-- Migration 013: Add conversation_summary and conversation_facts to chatbot_sessions
-- Run this SQL directly on your database if alembic is not accessible

BEGIN;

-- Add conversation_summary column
ALTER TABLE public.chatbot_sessions 
ADD COLUMN IF NOT EXISTS conversation_summary TEXT;

-- Add conversation_facts column
ALTER TABLE public.chatbot_sessions 
ADD COLUMN IF NOT EXISTS conversation_facts JSONB DEFAULT '[]';

-- Add last_next_question_id column
ALTER TABLE public.chatbot_sessions 
ADD COLUMN IF NOT EXISTS last_next_question_id TEXT;

COMMIT;
