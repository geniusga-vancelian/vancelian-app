"""
Script pour charger et maintenir les données historiques D1 pour tous les instruments
Usage: python scripts/load_market_data.py [--all] [--update-recent] [--instrument-id ID]
"""
import sys
import os
from pathlib import Path
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, MarketDataInstrument, MarketDataBarD1, get_db
from services.market_data.yahoo_client import YahooFinanceClient
from sqlalchemy import and_, func
import argparse
import time


def check_instrument_coverage(db, instrument: MarketDataInstrument, end_date: Optional[date] = None) -> Dict[str, Any]:
    """Vérifier la couverture des données pour un instrument"""
    if end_date is None:
        end_date = date.today()
    
    # Get date range
    date_stats = db.query(
        func.min(MarketDataBarD1.date).label("min_date"),
        func.max(MarketDataBarD1.date).label("max_date"),
        func.count(MarketDataBarD1.date).label("count")
    ).filter(MarketDataBarD1.instrument_id == instrument.id).first()
    
    result = {
        "instrument_id": instrument.id,
        "symbol": instrument.symbol,
        "bars_count": date_stats.count if date_stats else 0,
        "date_min": date_stats.min_date if date_stats and date_stats.min_date else None,
        "date_max": date_stats.max_date if date_stats and date_stats.max_date else None,
        "needs_update": False,
        "gaps": [],
    }
    
    if result["bars_count"] == 0:
        result["needs_update"] = True
        return result
    
    # Check if data is recent (within 7 days)
    if result["date_max"] and (end_date - result["date_max"]).days > 7:
        result["needs_update"] = True
        result["gaps"].append(f"Données anciennes: dernière barre {result['date_max']} (il y a {(end_date - result['date_max']).days} jours)")
    
    # Check for large gaps (more than 5 days without data)
    if result["date_min"] and result["date_max"]:
        # Get all dates in the range
        existing_dates = set(
            row[0] for row in db.query(MarketDataBarD1.date)
            .filter(MarketDataBarD1.instrument_id == instrument.id)
            .all()
        )
        
        # Check for gaps (simplified: check first 1000 days and last 1000 days)
        expected_dates = set()
        start_check = max(result["date_min"], end_date - timedelta(days=1000))
        current = start_check
        while current <= min(result["date_max"], end_date):
            # Skip weekends for non-crypto
            if instrument.weekend_tradable == "false":
                weekday = current.weekday()
                if weekday < 5:  # Monday to Friday
                    expected_dates.add(current)
            else:
                expected_dates.add(current)
            current += timedelta(days=1)
        
        missing_dates = expected_dates - existing_dates
        if len(missing_dates) > 100:  # More than 100 missing days
            result["needs_update"] = True
            sorted_missing = sorted(missing_dates)
            result["gaps"].append(f"Environ {len(missing_dates)} jours manquants (ex: {sorted_missing[0]} à {sorted_missing[-1]})")
    
    return result


def load_instrument_data(
    db,
    instrument: MarketDataInstrument,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    force_full: bool = False
) -> Dict[str, Any]:
    """Charger les données historiques pour un instrument"""
    result = {
        "symbol": instrument.symbol,
        "bars_added": 0,
        "bars_updated": 0,
        "errors": [],
    }
    
    try:
        client = YahooFinanceClient()
        
        # Determine date range
        if end_date is None:
            end_date = date.today()
        
        # Get existing data range
        existing_stats = db.query(
            func.min(MarketDataBarD1.date).label("min_date"),
            func.max(MarketDataBarD1.date).label("max_date")
        ).filter(MarketDataBarD1.instrument_id == instrument.id).first()
        
        if not force_full and existing_stats and existing_stats.max_date:
            # Only fetch recent data (last 120 days or since last update)
            if start_date is None:
                start_date = max(existing_stats.max_date - timedelta(days=120), existing_stats.min_date or date(2020, 1, 1))
            else:
                start_date = min(start_date, existing_stats.max_date - timedelta(days=120))
        elif start_date is None:
            # First load: get last 2 years for crypto, 5 years for others
            if instrument.asset_class == "crypto":
                start_date = end_date - timedelta(days=730)  # ~2 years
            else:
                start_date = end_date - timedelta(days=1825)  # ~5 years
        
        # Fetch data from Yahoo Finance
        provider_symbol = instrument.provider_symbol or instrument.symbol
        
        print(f"  → Fetching {instrument.symbol} (provider: {provider_symbol}) from {start_date} to {end_date}...")
        
        bars = []
        last_error = None
        
        try:
            # Use Yahoo Finance client
            bars = client.get_historical_data(
                symbol=instrument.symbol,
                asset_class=instrument.asset_class,
                provider_symbol=provider_symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if bars:
                print(f"    → ✓ Successfully fetched {len(bars)} bars from Yahoo Finance")
        except Exception as e:
            last_error = str(e)
            print(f"    → ✗ Failed to fetch data: {last_error}")
        
        if not bars:
            if 'last_error' in locals():
                result["errors"].append(f"Yahoo Finance error: {last_error}")
            else:
                result["errors"].append("No bars returned from Yahoo Finance")
            return result
        
        # Filter by date range
        bars = [b for b in bars if start_date <= b["date"] <= end_date]
        
        if not bars:
            result["errors"].append(f"No bars in date range {start_date} to {end_date}")
            return result
        
        print(f"  → Fetched {len(bars)} bars, inserting/updating...")
        
        # Insert/update bars
        inserted = 0
        updated = 0
        for bar_data in bars:
            existing = db.query(MarketDataBarD1).filter(
                and_(
                    MarketDataBarD1.instrument_id == instrument.id,
                    MarketDataBarD1.date == bar_data["date"]
                )
            ).first()
            
            if existing:
                existing.open = bar_data["open"]
                existing.high = bar_data["high"]
                existing.low = bar_data["low"]
                existing.close = bar_data["close"]
                existing.volume = bar_data["volume"]
                existing.source = "yahoo"
                updated += 1
            else:
                new_bar = MarketDataBarD1(
                    instrument_id=instrument.id,
                    date=bar_data["date"],
                    open=bar_data["open"],
                    high=bar_data["high"],
                    low=bar_data["low"],
                    close=bar_data["close"],
                    volume=bar_data["volume"],
                    source="yahoo",
                )
                db.add(new_bar)
                inserted += 1
        
        db.commit()
        result["bars_added"] = inserted
        result["bars_updated"] = updated
        print(f"  → ✓ {inserted} bars added, {updated} bars updated")
        
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        result["errors"].append(error_msg)
        print(f"  → ❌ Error: {error_msg}")
    
    return result


def ensure_core_instruments(db) -> List[MarketDataInstrument]:
    """S'assurer que tous les instruments CORE_V1_INSTRUMENTS existent en base"""
    from services.market_data.routes import CORE_V1_INSTRUMENTS
    
    created = []
    for inst_def in CORE_V1_INSTRUMENTS:
        existing = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.symbol == inst_def["symbol"]
        ).first()
        
        if not existing:
            new_inst = MarketDataInstrument(
                symbol=inst_def["symbol"],
                name=inst_def["name"],
                asset_class=inst_def["asset_class"],
                weekend_tradable=inst_def["weekend_tradable"],
                provider="alphavantage",
                provider_symbol=inst_def["symbol"],  # Default: same as symbol
                is_active="true",
            )
            db.add(new_inst)
            created.append(new_inst)
            print(f"  → Created instrument: {inst_def['symbol']}")
    
    if created:
        db.commit()
        for inst in created:
            db.refresh(inst)
        print(f"  → ✓ {len(created)} instruments created")
    
    return created


def main():
    parser = argparse.ArgumentParser(description="Load historical market data D1 for instruments")
    parser.add_argument("--all", action="store_true", help="Load data for all active instruments")
    parser.add_argument("--update-recent", action="store_true", help="Update recent data (last 120 days)")
    parser.add_argument("--instrument-id", type=int, help="Load data for specific instrument ID")
    parser.add_argument("--check-only", action="store_true", help="Only check coverage, don't load data")
    parser.add_argument("--force-full", action="store_true", help="Force full reload (ignore existing data)")
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        print("=" * 80)
        print("📊 Market Data D1 Loader")
        print("=" * 80)
        
        # Ensure core instruments exist
        print("\n1. Ensuring core instruments exist...")
        ensure_core_instruments(db)
        
        # Determine which instruments to process
        instruments_to_process = []
        
        if args.instrument_id:
            instrument = db.query(MarketDataInstrument).filter(
                MarketDataInstrument.id == args.instrument_id
            ).first()
            if instrument:
                instruments_to_process = [instrument]
            else:
                print(f"❌ Instrument ID {args.instrument_id} not found")
                sys.exit(1)
        elif args.all or args.update_recent:
            instruments_to_process = db.query(MarketDataInstrument).filter(
                MarketDataInstrument.is_active == "true"
            ).order_by(MarketDataInstrument.symbol).all()
        else:
            # Default: check all instruments
            instruments_to_process = db.query(MarketDataInstrument).filter(
                MarketDataInstrument.is_active == "true"
            ).order_by(MarketDataInstrument.symbol).all()
        
        print(f"\n2. Processing {len(instruments_to_process)} instruments...")
        
        if args.check_only:
            print("\n📋 Coverage Report:")
            print("-" * 80)
            print(f"{'Symbol':<12} {'Asset Class':<12} {'Bars':<8} {'Date Min':<12} {'Date Max':<12} {'Status':<20}")
            print("-" * 80)
            
            for instrument in instruments_to_process:
                coverage = check_instrument_coverage(db, instrument)
                status = "✓ OK" if not coverage["needs_update"] else "⚠ Needs update"
                date_min_str = str(coverage["date_min"]) if coverage["date_min"] else "N/A"
                date_max_str = str(coverage["date_max"]) if coverage["date_max"] else "N/A"
                print(f"{coverage['symbol']:<12} {instrument.asset_class:<12} {coverage['bars_count']:<8} {date_min_str:<12} {date_max_str:<12} {status:<20}")
                if coverage["gaps"]:
                    for gap in coverage["gaps"]:
                        print(f"  └─ {gap}")
        else:
            # Load data
            total_added = 0
            total_updated = 0
            errors_count = 0
            
            for i, instrument in enumerate(instruments_to_process, 1):
                print(f"\n[{i}/{len(instruments_to_process)}] Processing {instrument.symbol} ({instrument.asset_class})...")
                
                # Check coverage first
                coverage = check_instrument_coverage(db, instrument)
                
                if not coverage["needs_update"] and not args.force_full and not args.update_recent:
                    print(f"  → ✓ Coverage OK ({coverage['bars_count']} bars), skipping")
                    continue
                
                # Load data
                if args.update_recent:
                    end_date = date.today()
                    start_date = end_date - timedelta(days=120)
                else:
                    start_date = None
                    end_date = None
                
                result = load_instrument_data(
                    db, instrument,
                    start_date=start_date,
                    end_date=end_date,
                    force_full=args.force_full
                )
                
                total_added += result["bars_added"]
                total_updated += result["bars_updated"]
                if result["errors"]:
                    errors_count += 1
                    print(f"  → ❌ Errors: {', '.join(result['errors'])}")
                
                # Rate limiting: wait between instruments
                if i < len(instruments_to_process):
                    time.sleep(15)  # Wait 15 seconds between API calls (Alpha Vantage rate limit: 5 calls/min)
            
            print("\n" + "=" * 80)
            print("📊 Summary:")
            print(f"  - Instruments processed: {len(instruments_to_process)}")
            print(f"  - Bars added: {total_added}")
            print(f"  - Bars updated: {total_updated}")
            print(f"  - Errors: {errors_count}")
            print("=" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

