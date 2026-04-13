#!/usr/bin/env python3
"""
Apply Alembic migrations to the database in DATABASE_URL (base unique, ex. arquantix).
Uses .env.local if available, otherwise .env
"""
import os
import sys
import subprocess
from pathlib import Path

# Determine api directory and change to it
api_dir = Path(__file__).parent.parent
os.chdir(api_dir)
sys.path.insert(0, str(api_dir))

# Load environment variables (prioritize .env.local)
try:
    from dotenv import load_dotenv
    env_local_path = api_dir / ".env.local"
    env_path = api_dir / ".env"
    
    if env_local_path.exists():
        print(f"📁 Loading .env.local")
        load_dotenv(env_local_path)
    elif env_path.exists():
        print(f"📁 Loading .env")
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass

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

def get_dbname(url: str) -> str:
    """Extract database name from URL"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.path.lstrip("/")

print("=" * 60)
print("MIGRATE API DB (ALEMBIC)")
print("=" * 60)
print(f"Database URL: {mask_password(DATABASE_URL)}")
print(f"Database name: {get_dbname(DATABASE_URL)}")
print()

try:
    dbname = get_dbname(DATABASE_URL)
    if dbname in ("arquantix_quant", "arquantix_admin"):
        print(f"⚠️  WARNING: DATABASE_URL pointe encore vers l’ancienne base {dbname!r}.")
        print("   Cible attendue après unification : arquantix (voir DB_UNIFICATION_PHASE_2_REPORT.md).")
        print("   Poursuite des migrations sur la base configurée…")
        print()
    
    # Run alembic upgrade head
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
    
    # Run db_doctor to verify
    print("=" * 60)
    print("Verifying tables with db_doctor...")
    print("=" * 60)
    print()
    
    db_doctor_script = api_dir / "scripts" / "db_doctor.py"
    if not db_doctor_script.exists():
        print("⚠️  WARNING: db_doctor.py not found, skipping verification")
        sys.exit(0)
    
    result = subprocess.run(
        [sys.executable, str(db_doctor_script)],
        cwd=str(api_dir),
        check=False
    )
    
    if result.returncode == 0:
        print()
        print("✅ SUCCESS: All required tables verified")
        print()
        print("💡 Next step: Restart backend to use the new database")
        sys.exit(0)
    else:
        print()
        print("⚠️  WARNING: Some tables may still be missing")
        print("   Check the output above for details")
        sys.exit(result.returncode)

except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)






