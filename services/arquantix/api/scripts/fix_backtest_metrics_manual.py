#!/usr/bin/env python3
"""
Manual fix script for backtest_metrics table
Adds 'id' column, changes PK, ensures UNIQUE constraint
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Load environment
api_dir = Path(__file__).parent.parent
load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found")
    sys.exit(1)

print(f"Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

try:
    # Check if id column exists
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'backtest_metrics'
        AND column_name = 'id';
    """)
    has_id = cur.fetchone() is not None
    
    if not has_id:
        print("Adding 'id' column...")
        # Create sequence
        cur.execute("CREATE SEQUENCE IF NOT EXISTS backtest_metrics_id_seq;")
        # Add column
        cur.execute("ALTER TABLE public.backtest_metrics ADD COLUMN id INTEGER;")
        # Set values
        cur.execute("""
            UPDATE public.backtest_metrics 
            SET id = nextval('backtest_metrics_id_seq')
            WHERE id IS NULL;
        """)
        # Make NOT NULL with default
        cur.execute("""
            ALTER TABLE public.backtest_metrics 
            ALTER COLUMN id SET NOT NULL,
            ALTER COLUMN id SET DEFAULT nextval('backtest_metrics_id_seq');
        """)
        print("✅ Column 'id' added")
    else:
        print("✅ Column 'id' already exists")
    
    # Check current PK
    cur.execute("""
        SELECT column_name
        FROM information_schema.key_column_usage
        WHERE table_schema = 'public' 
        AND table_name = 'backtest_metrics'
        AND constraint_name = 'pk_backtest_metrics'
        ORDER BY ordinal_position;
    """)
    pk_cols = [r[0] for r in cur.fetchall()]
    
    if 'id' not in pk_cols:
        print(f"Changing PK from {pk_cols} to ['id']...")
        # Drop old PK
        cur.execute("ALTER TABLE public.backtest_metrics DROP CONSTRAINT pk_backtest_metrics;")
        # Create new PK on id
        cur.execute("ALTER TABLE public.backtest_metrics ADD CONSTRAINT pk_backtest_metrics PRIMARY KEY (id);")
        print("✅ PK changed to 'id'")
    else:
        print("✅ PK is already on 'id'")
    
    # Check UNIQUE constraint
    cur.execute("""
        SELECT constraint_name
        FROM information_schema.table_constraints 
        WHERE table_schema = 'public' 
        AND table_name = 'backtest_metrics'
        AND constraint_name = 'uq_backtest_metrics_run_scope_inst_key';
    """)
    has_unique = cur.fetchone() is not None
    
    if not has_unique:
        print("Creating UNIQUE constraint...")
        cur.execute("""
            ALTER TABLE public.backtest_metrics 
            ADD CONSTRAINT uq_backtest_metrics_run_scope_inst_key 
            UNIQUE (run_id, scope, instrument_id, key);
        """)
        print("✅ UNIQUE constraint created")
    else:
        print("✅ UNIQUE constraint already exists")
    
    # Ensure instrument_id is nullable
    cur.execute("""
        SELECT is_nullable
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'backtest_metrics'
        AND column_name = 'instrument_id';
    """)
    is_nullable = cur.fetchone()[0] == 'YES'
    
    if not is_nullable:
        print("Making instrument_id nullable...")
        cur.execute("ALTER TABLE public.backtest_metrics ALTER COLUMN instrument_id DROP NOT NULL;")
        print("✅ instrument_id is now nullable")
    else:
        print("✅ instrument_id is already nullable")
    
    conn.commit()
    print("\n✅ All fixes applied successfully!")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
    sys.exit(1)
finally:
    cur.close()
    conn.close()






