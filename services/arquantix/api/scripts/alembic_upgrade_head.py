#!/usr/bin/env python3
"""
Alembic Upgrade Head - Apply all pending migrations
Runs 'alembic upgrade head' programmatically and verifies tables
"""
import os
import sys
import subprocess
from pathlib import Path

# Determine api directory and change to it
api_dir = Path(__file__).parent.parent
os.chdir(api_dir)
sys.path.insert(0, str(api_dir))

# Load environment variables (same method as backend)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env

print("=" * 60)
print("ALEMBIC UPGRADE HEAD - Apply Database Migrations")
print("=" * 60)
print()

# Check if DATABASE_URL is set
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ ERROR: DATABASE_URL not found in environment variables")
    print("   Please set DATABASE_URL in .env file or environment")
    sys.exit(1)

# Get alembic directory
alembic_dir = api_dir / "alembic"
if not alembic_dir.exists():
    print(f"❌ ERROR: Alembic directory not found at {alembic_dir}")
    sys.exit(1)

print(f"📁 Alembic directory: {alembic_dir}")
print()

# Already in api directory (changed above)

try:
    # Run alembic upgrade head
    print("🔄 Running: alembic upgrade head")
    print()
    
    result = subprocess.run(
        ["python3", "-m", "alembic", "upgrade", "head"],
        cwd=str(api_dir),
        capture_output=True,
        text=True,
        check=False
    )
    
    # Print output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    if result.returncode != 0:
        print()
        print(f"❌ ERROR: Alembic upgrade failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    
    print()
    print("✅ Alembic upgrade completed successfully")
    print()
    
    # Re-run db_doctor to verify
    print("=" * 60)
    print("Verifying tables after migration...")
    print("=" * 60)
    print()
    
    db_doctor_script = api_dir / "scripts" / "db_doctor.py"
    if not db_doctor_script.exists():
        print("⚠️  WARNING: db_doctor.py not found, skipping verification")
        print("   Run manually: python3 scripts/db_doctor.py")
        sys.exit(0)
    
    result = subprocess.run(
        [sys.executable, str(db_doctor_script)],
        cwd=str(api_dir),
        check=False
    )
    
    if result.returncode == 0:
        print()
        print("✅ SUCCESS: All tables verified after migration")
        sys.exit(0)
    else:
        print()
        print("⚠️  WARNING: Some tables may still be missing")
        print("   Check the output above for details")
        sys.exit(result.returncode)

except subprocess.CalledProcessError as e:
    print(f"❌ ERROR: Failed to run alembic: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

