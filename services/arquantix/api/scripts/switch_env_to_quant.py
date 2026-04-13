#!/usr/bin/env python3
"""
Met à jour .env.local (ou .env) pour pointer DATABASE_URL vers la base unifiée (ex. arquantix).
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# Determine api directory
api_dir = Path(__file__).parent.parent
os.chdir(api_dir)

# Load current DATABASE_URL
try:
    from dotenv import load_dotenv, dotenv_values
    env_path = api_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        env_vars = dotenv_values(env_path)
    else:
        load_dotenv()
        env_vars = {}
except ImportError:
    env_vars = {}

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
print("SWITCH DATABASE_URL → BASE UNIFIÉE")
print("=" * 60)
print(f"Current DATABASE_URL: {mask_password(DATABASE_URL)}")
print()

try:
    # Parse current DATABASE_URL
    db_parts = parse_db_url(DATABASE_URL)
    current_db = db_parts["database"]
    new_db = "arquantix"
    
    # Build new DATABASE_URL
    new_db_url = urlunparse((
        db_parts["scheme"],
        f"{db_parts['user']}:{db_parts['password']}@{db_parts['host']}:{db_parts['port']}",
        f"/{new_db}",
        "",
        "",
        ""
    ))
    
    print(f"📊 Current database: {current_db}")
    print(f"🎯 Switching to: {new_db}")
    print()
    
    # Determine which file to update
    env_file = api_dir / ".env.local"
    env_file_exists = env_file.exists()
    
    # Check if .env exists (we'll use .env.local to avoid conflicts)
    main_env_file = api_dir / ".env"
    if main_env_file.exists():
        print(f"ℹ️  Found {main_env_file.name}, will create/update {env_file.name} instead")
        print("   (This avoids modifying the main .env file)")
        print()
    
    # Read existing .env.local if it exists
    existing_lines = []
    if env_file.exists():
        with open(env_file, "r") as f:
            existing_lines = f.readlines()
    
    # Update or add DATABASE_URL
    updated = False
    new_lines = []
    
    for line in existing_lines:
        if line.strip().startswith("DATABASE_URL="):
            new_lines.append(f'DATABASE_URL="{new_db_url}"\n')
            updated = True
        else:
            new_lines.append(line)
    
    if not updated:
        # Add DATABASE_URL at the end
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f'DATABASE_URL="{new_db_url}"\n')
    
    # Write to .env.local
    with open(env_file, "w") as f:
        f.writelines(new_lines)
    
    # Ensure .env.local is in .gitignore
    gitignore_path = api_dir / ".gitignore"
    gitignore_content = ""
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            gitignore_content = f.read()
    
    if ".env.local" not in gitignore_content:
        with open(gitignore_path, "a") as f:
            if gitignore_content and not gitignore_content.endswith("\n"):
                f.write("\n")
            f.write("# Local environment overrides (may contain secrets)\n")
            f.write(".env.local\n")
        print(f"✅ Added .env.local to .gitignore")
    
    print(f"✅ Updated {env_file.name}")
    print()
    print("=" * 60)
    print("✅ SUCCESS")
    print("=" * 60)
    print(f"New DATABASE_URL: {mask_password(new_db_url)}")
    print()
    print("⚠️  IMPORTANT:")
    print("   The backend will use .env.local if it exists.")
    print("   Make sure your backend loads .env.local (or restart with new env).")
    print()
    print("💡 Next steps:")
    print("   1. Run: python3 api/scripts/migrate_quant_db.py")
    print("   2. Restart backend to pick up new DATABASE_URL")
    print()
    
    sys.exit(0)

except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)






