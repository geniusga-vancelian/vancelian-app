#!/usr/bin/env python3
"""
Alembic State Inspector - Check current revision and available revisions
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add api directory to path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

# Load environment variables (same method as backend)
try:
    from dotenv import load_dotenv
    env_path = api_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment variables")
    sys.exit(1)

def mask_password(url: str) -> str:
    """Mask password in database URL"""
    if "@" in url:
        parts = url.split("@")
        if "://" in parts[0]:
            scheme_user = parts[0]
            if ":" in scheme_user:
                scheme, user_pass = scheme_user.rsplit("://", 1)
                if ":" in user_pass:
                    user, password = user_pass.rsplit(":", 1)
                    return f"{scheme}://{user}:***@{parts[1]}"
    return url

print("=" * 60)
print("ALEMBIC STATE INSPECTOR")
print("=" * 60)
print(f"Database URL: {mask_password(DATABASE_URL)}")
print()

try:
    engine = create_engine(DATABASE_URL)
    
    # Check if alembic_version table exists
    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'alembic_version'
            );
        """))
        table_exists = result.scalar()
        
        if not table_exists:
            print("⚠️  Table 'alembic_version' does not exist")
            print("   This means no migrations have been applied yet.")
            print()
        else:
            # Get current revision
            result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            
            if row:
                current_revision = row[0]
                print(f"📌 Current revision in DB: {current_revision}")
            else:
                print("⚠️  Table 'alembic_version' exists but is empty")
                print()
    
    # Get available revisions from Alembic
    print("📋 Available revisions in repository:")
    print()
    
    # Change to api directory for alembic command
    os.chdir(api_dir)
    
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "alembic", "history"],
        cwd=str(api_dir),
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("⚠️  Could not retrieve Alembic history")
        if result.stderr:
            print(f"Error: {result.stderr}")
    
    print()
    print("=" * 60)
    
    if table_exists and row:
        # Check if current revision exists in history
        if result.returncode == 0 and current_revision not in result.stdout:
            print("❌ WARNING: Current revision in DB not found in repository!")
            print("   This indicates a mismatch. Consider running repair script.")
            sys.exit(2)
        else:
            print("✅ Current revision found in repository")
            sys.exit(0)
    else:
        print("ℹ️  No revision set in database (fresh DB or needs initialization)")
        sys.exit(0)

except SQLAlchemyError as e:
    print(f"❌ Database error: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)






