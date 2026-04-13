"""
Admin routes for database migrations
"""
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db, engine
from auth import get_current_user, AdminUser
from sqlalchemy import text

router = APIRouter(prefix="/api/admin/migrations", tags=["admin-migrations"])


@router.get("/status")
def get_migration_status(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current migration status"""
    try:
        # Check if migration 013 columns exist
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'chatbot_sessions'
            AND column_name IN ('conversation_summary', 'conversation_facts', 'last_next_question_id')
        """))
        existing_columns = {row[0] for row in result}
        
        required_columns = {'conversation_summary', 'conversation_facts', 'last_next_question_id'}
        missing_columns = required_columns - existing_columns
        
        return {
            "migration_013_applied": len(missing_columns) == 0,
            "existing_columns": list(existing_columns),
            "missing_columns": list(missing_columns),
            "all_required_columns_exist": len(missing_columns) == 0,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking migration status: {str(e)}"
        )


@router.post("/apply/014")
def apply_migration_014(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply migration 014: Add security fields (expires_at, ip_hash, user_agent_hash) to chatbot_sessions"""
    try:
        # Check current status first
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'chatbot_sessions'
            AND column_name IN ('expires_at', 'ip_hash', 'user_agent_hash')
        """))
        existing_columns = {row[0] for row in result}
        
        required_columns = {'expires_at', 'ip_hash', 'user_agent_hash'}
        missing_columns = required_columns - existing_columns
        
        if len(missing_columns) == 0:
            return {
                "success": True,
                "message": "Migration 014 already applied",
                "applied_columns": list(existing_columns),
            }
        
        # Apply migration
        sql_statements = []
        
        if 'expires_at' not in existing_columns:
            sql_statements.append("""
                ALTER TABLE public.chatbot_sessions 
                ADD COLUMN expires_at TIMESTAMP WITH TIME ZONE;
            """)
        
        if 'ip_hash' not in existing_columns:
            sql_statements.append("""
                ALTER TABLE public.chatbot_sessions 
                ADD COLUMN ip_hash VARCHAR(64);
            """)
        
        if 'user_agent_hash' not in existing_columns:
            sql_statements.append("""
                ALTER TABLE public.chatbot_sessions 
                ADD COLUMN user_agent_hash VARCHAR(64);
            """)
        
        # Check if index exists
        index_result = db.execute(text("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'chatbot_sessions'
            AND indexname = 'ix_chatbot_sessions_expires_at'
        """))
        index_exists = index_result.fetchone() is not None
        
        if not index_exists:
            sql_statements.append("""
                CREATE INDEX ix_chatbot_sessions_expires_at 
                ON public.chatbot_sessions(expires_at);
            """)
        
        # Execute all statements in a transaction
        applied_columns = []
        for sql in sql_statements:
            db.execute(text(sql))
            # Extract column name from SQL
            if 'expires_at' in sql and 'ADD COLUMN' in sql:
                applied_columns.append('expires_at')
            elif 'ip_hash' in sql and 'ADD COLUMN' in sql:
                applied_columns.append('ip_hash')
            elif 'user_agent_hash' in sql and 'ADD COLUMN' in sql:
                applied_columns.append('user_agent_hash')
            elif 'CREATE INDEX' in sql:
                applied_columns.append('index_expires_at')
        
        db.commit()
        
        return {
            "success": True,
            "message": "Migration 014 applied successfully",
            "applied_columns": applied_columns,
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying migration 014: {str(e)}"
        )


@router.post("/apply/013")
def apply_migration_013(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply migration 013: Add conversation summary fields to chatbot_sessions"""
    try:
        # Check current status first
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'chatbot_sessions'
            AND column_name IN ('conversation_summary', 'conversation_facts', 'last_next_question_id')
        """))
        existing_columns = {row[0] for row in result}
        
        required_columns = {'conversation_summary', 'conversation_facts', 'last_next_question_id'}
        missing_columns = required_columns - existing_columns
        
        if len(missing_columns) == 0:
            return {
                "success": True,
                "message": "Migration 013 already applied",
                "applied_columns": list(existing_columns),
            }
        
        # Apply migration
        sql_statements = []
        
        if 'conversation_summary' not in existing_columns:
            sql_statements.append("""
                ALTER TABLE public.chatbot_sessions 
                ADD COLUMN conversation_summary TEXT;
            """)
        
        if 'conversation_facts' not in existing_columns:
            sql_statements.append("""
                ALTER TABLE public.chatbot_sessions 
                ADD COLUMN conversation_facts JSONB DEFAULT '[]';
            """)
        
        if 'last_next_question_id' not in existing_columns:
            sql_statements.append("""
                ALTER TABLE public.chatbot_sessions 
                ADD COLUMN last_next_question_id TEXT;
            """)
        
        # Execute all statements in a transaction
        applied_columns = []
        for sql in sql_statements:
            db.execute(text(sql))
            # Extract column name from SQL
            if 'conversation_summary' in sql:
                applied_columns.append('conversation_summary')
            elif 'conversation_facts' in sql:
                applied_columns.append('conversation_facts')
            elif 'last_next_question_id' in sql:
                applied_columns.append('last_next_question_id')
        
        db.commit()
        
        return {
            "success": True,
            "message": "Migration 013 applied successfully",
            "applied_columns": applied_columns,
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying migration 013: {str(e)}"
        )


@router.get("/list")
def list_migrations(
    current_user: AdminUser = Depends(get_current_user),
):
    """List available migrations"""
    migrations_dir = os.path.join(os.path.dirname(__file__), "../../alembic/versions")
    migrations = []
    
    if os.path.exists(migrations_dir):
        for filename in sorted(os.listdir(migrations_dir)):
            if filename.endswith(".py") and not filename.startswith("__"):
                migrations.append({
                    "filename": filename,
                    "revision": filename.split("_")[0] if "_" in filename else filename,
                })
    
    return {
        "migrations": migrations,
        "available_endpoints": {
            "status": "/api/admin/migrations/status",
            "apply_013": "/api/admin/migrations/apply/013",
            "apply_014": "/api/admin/migrations/apply/014",
        }
    }
