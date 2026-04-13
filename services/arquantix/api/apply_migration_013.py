#!/usr/bin/env python3
"""
Script to apply migration 013 manually.
Run this when the database is accessible.
"""
import sys
import os
from pathlib import Path

# Add api directory to path
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))

from database import engine
from sqlalchemy import text

def apply_migration():
    """Apply migration 013: Add conversation summary fields"""
    sql = """
    -- Add conversation_summary column
    ALTER TABLE public.chatbot_sessions 
    ADD COLUMN IF NOT EXISTS conversation_summary TEXT;

    -- Add conversation_facts column
    ALTER TABLE public.chatbot_sessions 
    ADD COLUMN IF NOT EXISTS conversation_facts JSONB DEFAULT '[]';

    -- Add last_next_question_id column
    ALTER TABLE public.chatbot_sessions 
    ADD COLUMN IF NOT EXISTS last_next_question_id TEXT;
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print("✅ Migration 013 applied successfully!")
        return True
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
