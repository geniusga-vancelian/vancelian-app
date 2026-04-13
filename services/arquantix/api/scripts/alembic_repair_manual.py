#!/usr/bin/env python3
"""
Alembic Manual Repair - Fix alembic_version for non-empty databases
⚠️ USE WITH CAUTION: Only use if you understand the implications
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import subprocess

# Determine api directory and change to it
api_dir = Path(__file__).parent.parent
os.chdir(api_dir)
sys.path.insert(0, str(api_dir))

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = api_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found")
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
print("ALEMBIC MANUAL REPAIR")
print("=" * 60)
print(f"Database URL: {mask_password(DATABASE_URL)}")
print()
print("⚠️  WARNING: This will modify the alembic_version table")
print("   Make sure you understand what you're doing!")
print()

# Ask for confirmation
response = input("Do you want to proceed? (yes/no): ").strip().lower()
if response != "yes":
    print("Aborted.")
    sys.exit(0)

try:
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check current revision
        result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        row = result.fetchone()
        
        if row:
            current_revision = row[0]
            print(f"📌 Current revision in DB: {current_revision}")
            print()
            
            # Check if revision exists in repo
            result_cmd = subprocess.run(
                ["python3", "-m", "alembic", "history"],
                cwd=str(api_dir),
                capture_output=True,
                text=True,
                check=False
            )
            
            revision_found = result_cmd.returncode == 0 and current_revision in result_cmd.stdout
            
            if not revision_found:
                print(f"❌ Revision {current_revision} not found in repository")
                print("   Removing invalid revision...")
                
                conn.execute(text("DELETE FROM alembic_version"))
                conn.commit()
                print("✅ Removed invalid revision")
                print()
            else:
                print(f"✅ Revision {current_revision} found in repository")
                print("   No repair needed.")
                sys.exit(0)
        else:
            print("ℹ️  alembic_version table is empty")
            print()
    
    # Now try to upgrade
    print("🔄 Running: alembic upgrade head")
    print()
    
    result = subprocess.run(
        ["python3", "-m", "alembic", "upgrade", "head"],
        cwd=str(api_dir),
        check=False
    )
    
    if result.returncode != 0:
        print()
        print(f"❌ ERROR: Alembic upgrade failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    
    print()
    print("✅ Alembic upgrade completed successfully")
    print()
    print("💡 Next step: Run db_doctor.py to verify tables")
    sys.exit(0)

except SQLAlchemyError as e:
    print(f"❌ Database error: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)






