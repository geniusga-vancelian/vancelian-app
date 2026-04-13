#!/usr/bin/env python3
"""
Alembic Repair and Upgrade - Fix alembic_version and apply migrations
Only repairs if DB appears empty (no application tables)
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import subprocess

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

# Application tables that indicate DB is not empty
APPLICATION_TABLES = [
    "market_data_instruments",
    "market_data_bars_d1",
    "backtest_runs",
    "backtest_portfolio_series",
    "backtest_instrument_series",
    "backtest_metrics",
    "email_templates",
    "email_modules",
    "pages",
    "news",
]

print("=" * 60)
print("ALEMBIC REPAIR AND UPGRADE")
print("=" * 60)
print(f"Database URL: {mask_password(DATABASE_URL)}")
print()

try:
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    # Get all tables in public schema
    existing_tables = inspector.get_table_names(schema="public")
    
    # Check if any application tables exist
    has_application_tables = any(table in existing_tables for table in APPLICATION_TABLES)
    
    print("📊 Database state:")
    print(f"   Total tables: {len(existing_tables)}")
    print(f"   Application tables found: {sum(1 for t in APPLICATION_TABLES if t in existing_tables)}/{len(APPLICATION_TABLES)}")
    print()
    
    if has_application_tables:
        print("❌ ERROR: Database contains application tables!")
        print("   This repair script only works on empty databases.")
        print("   Found application tables:")
        for table in APPLICATION_TABLES:
            if table in existing_tables:
                print(f"     - {table}")
        print()
        print("💡 For non-empty databases, manual repair is required:")
        print("   1. Check current revision: python3 scripts/alembic_state_inspect.py")
        print("   2. Manually fix alembic_version table if needed")
        print("   3. Run: python3 scripts/alembic_upgrade_head.py")
        sys.exit(1)
    
    print("✅ Database appears empty (no application tables found)")
    print()
    
    # Check alembic_version table
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
        
        if table_exists:
            # Get current revision
            result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            
            if row:
                current_revision = row[0]
                print(f"⚠️  Found revision in alembic_version: {current_revision}")
                
                # Check if this revision exists in repository
                os.chdir(api_dir)
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
                    print("   Removing invalid revision from alembic_version...")
                    
                    # Delete the invalid revision
                    conn.execute(text("DELETE FROM alembic_version"))
                    conn.commit()
                    print("✅ Removed invalid revision")
                else:
                    print(f"✅ Revision {current_revision} found in repository")
                    print("   No repair needed, proceeding to upgrade...")
            else:
                print("ℹ️  alembic_version table exists but is empty")
        else:
            print("ℹ️  alembic_version table does not exist (will be created by Alembic)")
    
    print()
    print("🔄 Running: alembic upgrade head")
    print()
    
    # Change to api directory
    os.chdir(api_dir)
    
    result = subprocess.run(
        ["python3", "-m", "alembic", "upgrade", "head"],
        cwd=str(api_dir),
        capture_output=False,  # Show output in real-time
        check=False
    )
    
    if result.returncode != 0:
        print()
        print(f"❌ ERROR: Alembic upgrade failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    
    print()
    print("✅ Alembic upgrade completed successfully")
    print()
    
    # Verify tables were created
    print("=" * 60)
    print("Verifying tables after migration...")
    print("=" * 60)
    print()
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names(schema="public")
    
    required_tables = [
        "market_data_instruments",
        "market_data_bars_d1",
        "backtest_runs",
        "backtest_portfolio_series",
        "backtest_instrument_series",
        "backtest_metrics",
    ]
    
    print(f"{'Table Name':<40} {'Exists':<10}")
    print("-" * 60)
    
    all_exist = True
    for table_name in required_tables:
        exists = table_name in existing_tables
        status = "✅ YES" if exists else "❌ NO"
        print(f"{table_name:<40} {status:<10}")
        if not exists:
            all_exist = False
    
    print("-" * 60)
    print()
    
    if all_exist:
        print("✅ SUCCESS: All required tables created")
        sys.exit(0)
    else:
        print("⚠️  WARNING: Some tables are still missing")
        print("   Check Alembic output above for errors")
        sys.exit(2)

except SQLAlchemyError as e:
    print(f"❌ Database error: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)






