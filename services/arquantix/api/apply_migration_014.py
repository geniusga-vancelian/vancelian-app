#!/usr/bin/env python3
"""
Script to apply migration 014 manually.
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
    """Apply migration 014: Add chatbot session security fields"""
    sql = """
    -- Add expires_at column
    ALTER TABLE public.chatbot_sessions 
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;

    -- Add ip_hash column
    ALTER TABLE public.chatbot_sessions 
    ADD COLUMN IF NOT EXISTS ip_hash VARCHAR(64);

    -- Add user_agent_hash column
    ALTER TABLE public.chatbot_sessions 
    ADD COLUMN IF NOT EXISTS user_agent_hash VARCHAR(64);

    -- Create index on expires_at
    CREATE INDEX IF NOT EXISTS ix_chatbot_sessions_expires_at 
    ON public.chatbot_sessions(expires_at);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print("✅ Migration 014 applied successfully!")
        print("   - Added expires_at column")
        print("   - Added ip_hash column")
        print("   - Added user_agent_hash column")
        print("   - Created index on expires_at")
        return True
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
