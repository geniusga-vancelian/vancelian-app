#!/usr/bin/env python3
"""
Smoke test for yf_extract.py
Tests extraction for AAPL over 30 days and validates output files.
"""

import sys
import subprocess
from pathlib import Path
from datetime import date, timedelta

# Calculate date range (30 days ago to today)
end_date = date.today()
start_date = end_date - timedelta(days=30)

# Paths
script_dir = Path(__file__).parent
extract_script = script_dir / "yf_extract.py"
out_dir = script_dir / "data_test"
ticker = "AAPL"

print("=" * 60)
print("Yahoo Finance Extract - Smoke Test")
print("=" * 60)
print(f"Ticker: {ticker}")
print(f"Period: {start_date} to {end_date}")
print(f"Output: {out_dir}")
print()

# Run extraction
print("Running extraction...")
cmd = [
    sys.executable,
    str(extract_script),
    "--ticker",
    ticker,
    "--start",
    start_date.isoformat(),
    "--end",
    end_date.isoformat(),
    "--out_dir",
    str(out_dir),
]

try:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
except subprocess.CalledProcessError as e:
    print(f"ERROR: Extraction failed with exit code {e.returncode}")
    print(e.stdout)
    print(e.stderr)
    sys.exit(1)

# Validate output files
print()
print("Validating output files...")

expected_files = [
    out_dir / f"{ticker}_prices.csv",
    out_dir / f"{ticker}_actions.csv",
    out_dir / f"{ticker}_merged.csv",
]

all_ok = True
for file_path in expected_files:
    if not file_path.exists():
        print(f"✗ ERROR: File not found: {file_path}")
        all_ok = False
        continue

    # Check file size and line count
    with open(file_path, "r") as f:
        lines = f.readlines()
        line_count = len(lines)

    if line_count < 10:
        print(
            f"✗ ERROR: {file_path.name} has only {line_count} lines (expected >= 10)"
        )
        all_ok = False
    else:
        print(f"✓ {file_path.name}: {line_count} lines")

# Check prices file has required columns
prices_file = expected_files[0]
if prices_file.exists():
    with open(prices_file, "r") as f:
        header = f.readline().strip()
        required_cols = ["date", "open", "high", "low", "close", "adj_close", "volume"]
        header_cols = [col.strip() for col in header.split(",")]
        missing_cols = [col for col in required_cols if col not in header_cols]
        if missing_cols:
            print(f"✗ ERROR: Missing columns in prices file: {missing_cols}")
            all_ok = False
        else:
            print(f"✓ Prices file has all required columns")

# Check merged file has calculated returns
merged_file = expected_files[2]
if merged_file.exists():
    with open(merged_file, "r") as f:
        header = f.readline().strip()
        required_cols = ["daily_return_close", "daily_return_total"]
        header_cols = [col.strip() for col in header.split(",")]
        missing_cols = [col for col in required_cols if col not in header_cols]
        if missing_cols:
            print(f"✗ ERROR: Missing calculated columns in merged file: {missing_cols}")
            all_ok = False
        else:
            print(f"✓ Merged file has calculated returns")

print()
if all_ok:
    print("=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)
    sys.exit(0)
else:
    print("=" * 60)
    print("✗ TESTS FAILED")
    print("=" * 60)
    sys.exit(1)

