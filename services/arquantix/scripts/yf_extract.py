#!/usr/bin/env python3
"""
Yahoo Finance Data Extractor
Extracts historical price data, dividends, and splits from Yahoo Finance.

Usage:
    python scripts/yf_extract.py --ticker AAPL --start 2025-01-01 --end 2026-01-09
    python scripts/yf_extract.py --ticker MSFT --start 2024-01-01 --end 2026-01-09 --interval 1d --out_dir ./exports
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Tuple
import time

try:
    import yfinance as yf
    import pandas as pd
except ImportError as e:
    print(f"ERROR: Missing required library: {e}")
    print("Please install dependencies: pip install -r api/requirements.txt")
    sys.exit(1)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Extract historical data from Yahoo Finance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ticker",
        required=True,
        type=str,
        help="Ticker symbol (e.g., AAPL, MSFT, BTC-USD)",
    )
    parser.add_argument(
        "--start",
        required=True,
        type=str,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        required=True,
        type=str,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--interval",
        default="1d",
        type=str,
        choices=["1d", "1wk", "1mo"],
        help="Data interval (default: 1d)",
    )
    parser.add_argument(
        "--out_dir",
        default="./data",
        type=str,
        help="Output directory (default: ./data)",
    )
    return parser.parse_args()


def validate_dates(start_str: str, end_str: str) -> Tuple[date, date]:
    """Validate and parse date strings"""
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
    except ValueError as e:
        print(f"ERROR: Invalid date format. Use YYYY-MM-DD. {e}")
        sys.exit(1)

    if start_date >= end_date:
        print(f"ERROR: Start date ({start_date}) must be before end date ({end_date})")
        sys.exit(1)

    return start_date, end_date


def fetch_data_with_retry(
    ticker: str, start: date, end: date, interval: str, max_retries: int = 3
) -> tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Fetch data from Yahoo Finance with retry logic
    
    Returns:
        (hist_df, dividends_df, splits_df) or (None, None, None) on failure
    """
    for attempt in range(max_retries):
        try:
            # Create ticker object
            stock = yf.Ticker(ticker)

            # Fetch historical data
            hist_df = stock.history(
                start=start.isoformat(),
                end=end.isoformat(),
                interval=interval,
                auto_adjust=False,  # We want both close and adj_close
                prepost=False,
            )

            # Fetch dividends
            dividends_df = stock.dividends

            # Fetch splits
            splits_df = stock.splits

            if hist_df.empty:
                print(f"WARNING: No historical data found for {ticker}")
                return None, None, None

            return hist_df, dividends_df, splits_df

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                error_msg = str(e)
                print(f"WARNING: Attempt {attempt + 1} failed: {error_msg}")
                if "Expecting value" in error_msg or "No timezone found" in error_msg:
                    print("  → Possible API issue: Yahoo Finance may be rate-limiting or unavailable")
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                error_msg = str(e)
                print(f"ERROR: Failed to fetch data after {max_retries} attempts")
                print(f"  Error: {error_msg}")
                if "Expecting value" in error_msg or "No timezone found" in error_msg:
                    print("\n  Possible causes:")
                    print("  - Yahoo Finance API is rate-limiting requests")
                    print("  - Network connectivity issue")
                    print("  - Ticker symbol may be invalid or delisted")
                    print("  - Try again later or use a different ticker")
                return None, None, None

    return None, None, None


def process_historical_data(hist_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process historical data: extract OHLCV + adj_close, validate, sort
    """
    # Select required columns
    required_cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    missing_cols = [col for col in required_cols if col not in hist_df.columns]
    if missing_cols:
        print(f"ERROR: Missing required columns: {missing_cols}")
        print(f"Available columns: {list(hist_df.columns)}")
        sys.exit(1)

    # Create clean dataframe
    prices_df = pd.DataFrame(
        {
            "date": hist_df.index.date,
            "open": hist_df["Open"].round(8),
            "high": hist_df["High"].round(8),
            "low": hist_df["Low"].round(8),
            "close": hist_df["Close"].round(8),
            "adj_close": hist_df["Adj Close"].round(8),
            "volume": hist_df["Volume"].astype(int),
        }
    )

    # Remove duplicates (keep first)
    initial_count = len(prices_df)
    prices_df = prices_df.drop_duplicates(subset=["date"], keep="first")
    if len(prices_df) < initial_count:
        print(f"WARNING: Removed {initial_count - len(prices_df)} duplicate dates")

    # Sort by date
    prices_df = prices_df.sort_values("date").reset_index(drop=True)

    # Validate: check for gaps (optional warning)
    if len(prices_df) > 1:
        date_diff = (prices_df["date"].iloc[-1] - prices_df["date"].iloc[0]).days
        expected_days = date_diff + 1
        if len(prices_df) < expected_days * 0.8:  # Allow 20% missing days
            print(
                f"WARNING: Only {len(prices_df)} days found, expected ~{expected_days} days"
            )

    return prices_df


def process_actions(
    dividends_df: pd.Series, splits_df: pd.Series, start: date, end: date
) -> pd.DataFrame:
    """
    Process dividends and splits into a single actions dataframe
    
    Returns:
        DataFrame with columns: date, type, value
    """
    actions_list = []

    # Process dividends
    if dividends_df is not None and not dividends_df.empty:
        for date_idx, value in dividends_df.items():
            action_date = date_idx.date() if hasattr(date_idx, "date") else date_idx
            if start <= action_date <= end:
                actions_list.append(
                    {"date": action_date, "type": "dividend", "value": float(value)}
                )

    # Process splits
    if splits_df is not None and not splits_df.empty:
        for date_idx, value in splits_df.items():
            action_date = date_idx.date() if hasattr(date_idx, "date") else date_idx
            if start <= action_date <= end:
                actions_list.append(
                    {"date": action_date, "type": "split", "value": float(value)}
                )

    if not actions_list:
        return pd.DataFrame(columns=["date", "type", "value"])

    actions_df = pd.DataFrame(actions_list)
    actions_df = actions_df.sort_values("date").reset_index(drop=True)

    return actions_df


def create_merged_data(
    prices_df: pd.DataFrame, actions_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge prices with actions (dividends and splits)
    
    Adds columns:
        - dividend: dividend amount (0 if none)
        - split_factor: split ratio (1 if none)
        - daily_return_close: close / close.shift(1) - 1
        - daily_return_total: adj_close / adj_close.shift(1) - 1
    """
    merged_df = prices_df.copy()

    # Add dividend column (0 if none)
    dividends = actions_df[actions_df["type"] == "dividend"].copy()
    if not dividends.empty:
        dividends = dividends.rename(columns={"value": "dividend"})[
            ["date", "dividend"]
        ]
        merged_df = merged_df.merge(dividends, on="date", how="left")
    else:
        merged_df["dividend"] = 0.0

    merged_df["dividend"] = merged_df["dividend"].fillna(0.0)

    # Add split_factor column (1 if none)
    splits = actions_df[actions_df["type"] == "split"].copy()
    if not splits.empty:
        splits = splits.rename(columns={"value": "split_factor"})[
            ["date", "split_factor"]
        ]
        merged_df = merged_df.merge(splits, on="date", how="left")
    else:
        merged_df["split_factor"] = 1.0

    merged_df["split_factor"] = merged_df["split_factor"].fillna(1.0)

    # Calculate daily returns
    merged_df["daily_return_close"] = (
        merged_df["close"] / merged_df["close"].shift(1) - 1.0
    )
    merged_df["daily_return_total"] = (
        merged_df["adj_close"] / merged_df["adj_close"].shift(1) - 1.0
    )

    # First row will have NaN returns (no previous value)
    merged_df["daily_return_close"] = merged_df["daily_return_close"].fillna(0.0)
    merged_df["daily_return_total"] = merged_df["daily_return_total"].fillna(0.0)

    return merged_df


def save_dataframes(
    ticker: str,
    out_dir: Path,
    prices_df: pd.DataFrame,
    actions_df: pd.DataFrame,
    merged_df: pd.DataFrame,
):
    """Save dataframes to CSV files"""
    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize ticker for filename
    safe_ticker = ticker.replace("-", "_").replace("/", "_")

    # Save prices
    prices_path = out_dir / f"{safe_ticker}_prices.csv"
    prices_df.to_csv(prices_path, index=False, float_format="%.8f")
    print(f"✓ Saved prices: {prices_path} ({len(prices_df)} rows)")

    # Save actions
    actions_path = out_dir / f"{safe_ticker}_actions.csv"
    actions_df.to_csv(actions_path, index=False, float_format="%.8f")
    print(f"✓ Saved actions: {actions_path} ({len(actions_df)} rows)")

    # Save merged
    merged_path = out_dir / f"{safe_ticker}_merged.csv"
    merged_df.to_csv(merged_path, index=False, float_format="%.8f")
    print(f"✓ Saved merged: {merged_path} ({len(merged_df)} rows)")


def main():
    """Main execution"""
    args = parse_args()

    # Validate dates
    start_date, end_date = validate_dates(args.start, args.end)

    print(f"Extracting data for {args.ticker}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Interval: {args.interval}")
    print(f"Output directory: {args.out_dir}")
    print()

    # Fetch data with retry
    hist_df, dividends_df, splits_df = fetch_data_with_retry(
        args.ticker, start_date, end_date, args.interval
    )

    if hist_df is None:
        print("ERROR: Failed to fetch historical data")
        sys.exit(1)

    # Process data
    print("Processing data...")
    prices_df = process_historical_data(hist_df)
    actions_df = process_actions(dividends_df, splits_df, start_date, end_date)
    merged_df = create_merged_data(prices_df, actions_df)

    # Validate output
    if len(prices_df) == 0:
        print("ERROR: No data to export")
        sys.exit(1)

    # Save files
    print()
    print("Saving files...")
    out_dir = Path(args.out_dir)
    save_dataframes(args.ticker, out_dir, prices_df, actions_df, merged_df)

    print()
    print("✓ Extraction complete!")
    print(f"  - Prices: {len(prices_df)} rows")
    print(f"  - Actions: {len(actions_df)} rows (dividends + splits)")
    print(f"  - Merged: {len(merged_df)} rows")


if __name__ == "__main__":
    main()

