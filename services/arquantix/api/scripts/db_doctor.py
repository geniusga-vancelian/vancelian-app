#!/usr/bin/env python3
"""
DB Doctor - Diagnostic script for database tables
Checks if required tables exist in the database
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

# Determine api directory and change to it
api_dir = Path(__file__).parent.parent
os.chdir(api_dir)
sys.path.insert(0, str(api_dir))

# Load environment variables (prioritize .env.local like backend)
try:
    from dotenv import load_dotenv
    env_local_path = api_dir / ".env.local"
    env_path = api_dir / ".env"
    
    if env_local_path.exists():
        load_dotenv(env_local_path)
    elif env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment variables")
    print("   Please set DATABASE_URL in .env file or environment")
    sys.exit(1)

# Mask password in URL for display
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
print("DB DOCTOR - Database Table Diagnostic")
print("=" * 60)
print(f"Database URL: {mask_password(DATABASE_URL)}")
print(f"Database name: {get_dbname(DATABASE_URL)}")
print()

# Required tables to check
REQUIRED_TABLES = [
    "market_data_instruments",
    "market_data_bars_d1",
    "backtest_runs",
    "backtest_portfolio_series",
    "backtest_instrument_series",
    "backtest_metrics",
]

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Test connection
    print("🔌 Testing database connection...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.fetchone()
    print("✅ Database connection successful")
    print()
    
    # Get inspector
    inspector = inspect(engine)
    
    # Get all existing tables in public schema
    existing_tables = inspector.get_table_names(schema="public")
    
    # Check required tables
    print("📊 Checking required tables:")
    print()
    print(f"{'Table Name':<40} {'Exists':<10}")
    print("-" * 60)
    
    all_exist = True
    missing_tables = []
    
    for table_name in REQUIRED_TABLES:
        exists = table_name in existing_tables
        status = "✅ YES" if exists else "❌ NO"
        print(f"{table_name:<40} {status:<10}")
        
        if not exists:
            all_exist = False
            missing_tables.append(table_name)
    
    print("-" * 60)
    print()
    
    # Summary
    if all_exist:
        print("✅ SUCCESS: All required tables exist")
        print()
        print("Database is ready for use.")
        sys.exit(0)
    else:
        print("❌ ERROR: Some required tables are missing:")
        for table in missing_tables:
            print(f"   - {table}")
        print()
        print("💡 Recommendation: Run migrations with:")
        print("   python3 scripts/alembic_upgrade_head.py")
        sys.exit(2)

except SQLAlchemyError as e:
    print(f"❌ Database error: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

