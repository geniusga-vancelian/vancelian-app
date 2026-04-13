#!/usr/bin/env python3
"""
Crée une nouvelle base PostgreSQL dédiée (ex. arquantix) sans toucher à l’existante.
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from urllib.parse import urlparse, urlunparse

# Determine api directory and change to it
api_dir = Path(__file__).parent.parent
os.chdir(api_dir)
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

def parse_db_url(url: str):
    """Parse database URL and extract components"""
    parsed = urlparse(url)
    return {
        "scheme": parsed.scheme,
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
    }

print("=" * 60)
print("CREATE CLEAN DB FOR MARKET DATA + BACKTEST")
print("=" * 60)
print(f"Source Database URL: {mask_password(DATABASE_URL)}")
print()

try:
    # Parse current DATABASE_URL
    db_parts = parse_db_url(DATABASE_URL)
    current_db = db_parts["database"]
    new_db = "arquantix"
    
    print(f"📊 Current database: {current_db}")
    print(f"🎯 Target database: {new_db}")
    print()
    
    # Build connection URL to 'postgres' database (default admin DB)
    admin_url = urlunparse((
        db_parts["scheme"],
        f"{db_parts['user']}:{db_parts['password']}@{db_parts['host']}:{db_parts['port']}",
        "/postgres",
        "",
        "",
        ""
    ))
    
    print(f"🔌 Connecting to admin database (postgres)...")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    
    with admin_engine.connect() as conn:
        # Check if database already exists
        result = conn.execute(text("""
            SELECT EXISTS(
                SELECT FROM pg_database 
                WHERE datname = :dbname
            )
        """), {"dbname": new_db})
        
        exists = result.scalar()
        
        if exists:
            print(f"⚠️  Database '{new_db}' already exists")
            print(f"🔄 Dropping and recreating to ensure clean state...")
            # Terminate all connections to the database first
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :dbname AND pid <> pg_backend_pid()
            """), {"dbname": new_db})
            # Drop database
            conn.execute(text(f'DROP DATABASE IF EXISTS "{new_db}"'))
            print(f"✅ Database '{new_db}' dropped")
        
        print(f"🔄 Creating database '{new_db}'...")
        # Create database
        conn.execute(text(f'CREATE DATABASE "{new_db}"'))
        print(f"✅ Database '{new_db}' created successfully")
    
    # Build new DATABASE_URL
    new_db_url = urlunparse((
        db_parts["scheme"],
        f"{db_parts['user']}:{db_parts['password']}@{db_parts['host']}:{db_parts['port']}",
        f"/{new_db}",
        "",
        "",
        ""
    ))
    
    print()
    print("=" * 60)
    print("✅ SUCCESS")
    print("=" * 60)
    print(f"New Database URL: {mask_password(new_db_url)}")
    print()
    print("💡 Next steps:")
    print("   1. Run: python3 api/scripts/switch_env_to_quant.py")
    print("   2. Run: python3 api/scripts/migrate_quant_db.py")
    print("   3. Restart backend")
    print()
    
    sys.exit(0)

except SQLAlchemyError as e:
    print(f"❌ Database error: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

