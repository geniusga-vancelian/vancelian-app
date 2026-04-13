#!/usr/bin/env python3
"""
Cleanup Market Data Instruments - Yahoo Only

This script:
1. Archives non-Yahoo instruments (sets is_active=false, archived_at=now())
2. Identifies and deduplicates Yahoo instruments
3. Migrates bars from duplicates to canonical instruments
4. Archives duplicate instruments

Supports DRY_RUN mode (set DRY_RUN=1 environment variable).

Usage:
    DRY_RUN=1 python3 api/scripts/cleanup_market_instruments_yahoo_only.py
    python3 api/scripts/cleanup_market_instruments_yahoo_only.py
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import json

# Add api directory to path
api_dir = Path(__file__).parent.parent
sys.path.insert(0, str(api_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from sqlalchemy import create_engine, and_, func, or_
from sqlalchemy.orm import sessionmaker
from database import MarketDataInstrument, MarketDataBarD1, BacktestRun, BacktestInstrumentSeries, BacktestMetric
from database import Base

DRY_RUN = os.getenv("DRY_RUN", "0") == "1"

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('DB_USER', 'arquantix')}:{os.getenv('DB_PASSWORD', 'arquantix')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5433')}/{os.getenv('DB_NAME', 'arquantix')}"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def normalize_symbol(symbol: str, asset_class: str) -> str:
    """
    Normalize symbol for deduplication
    - For crypto: prefer format with -USD (BTC-USD over BTCUSD)
    - For equities: use as-is (AAPL, MSFT)
    """
    symbol = symbol.strip().upper()
    
    if asset_class == "crypto":
        # If symbol ends with USD but no dash, add dash
        if symbol.endswith("USD") and "-" not in symbol:
            base = symbol[:-3]
            return f"{base}-USD"
        # If symbol is just base (BTC), add -USD
        if len(symbol) <= 5 and "-" not in symbol:
            return f"{symbol}-USD"
    
    return symbol


def get_canonical_instrument(instruments: List[MarketDataInstrument]) -> Optional[MarketDataInstrument]:
    """
    Choose canonical instrument from a list of duplicates
    Priority:
    1. Has provider_symbol matching normalized symbol
    2. Has most bars
    3. Most recent created_at
    """
    if not instruments:
        return None
    
    # Group by normalized symbol
    normalized = {}
    for inst in instruments:
        norm = normalize_symbol(inst.symbol, inst.asset_class)
        if norm not in normalized:
            normalized[norm] = []
        normalized[norm].append(inst)
    
    # For each normalized symbol, pick canonical
    canonical = None
    for norm_symbol, insts in normalized.items():
        # Prefer one with provider_symbol matching normalized
        for inst in insts:
            if inst.provider_symbol and inst.provider_symbol.upper() == norm_symbol:
                canonical = inst
                break
        
        if not canonical:
            # Prefer one with most bars
            db = SessionLocal()
            try:
                bars_counts = {}
                for inst in insts:
                    count = db.query(func.count(MarketDataBarD1.instrument_id)).filter(
                        MarketDataBarD1.instrument_id == inst.id
                    ).scalar()
                    bars_counts[inst.id] = count
                
                # Sort by bars count (desc), then created_at (desc)
                insts_sorted = sorted(
                    insts,
                    key=lambda i: (bars_counts.get(i.id, 0), i.created_at or datetime.min),
                    reverse=True
                )
                canonical = insts_sorted[0]
            finally:
                db.close()
    
    return canonical


def check_instrument_referenced(db, instrument_id: int) -> bool:
    """Check if instrument is referenced in backtests"""
    # Check BacktestRun.instrument_ids_json
    runs = db.query(BacktestRun).filter(
        BacktestRun.instrument_ids_json.isnot(None)
    ).all()
    
    for run in runs:
        if run.instrument_ids_json:
            if isinstance(run.instrument_ids_json, list):
                if instrument_id in run.instrument_ids_json:
                    return True
            elif isinstance(run.instrument_ids_json, dict):
                if instrument_id in run.instrument_ids_json.values():
                    return True
    
    # Check BacktestInstrumentSeries
    count = db.query(func.count(BacktestInstrumentSeries.instrument_id)).filter(
        BacktestInstrumentSeries.instrument_id == instrument_id
    ).scalar()
    if count > 0:
        return True
    
    # Check BacktestMetric
    count = db.query(func.count(BacktestMetric.instrument_id)).filter(
        BacktestMetric.instrument_id == instrument_id
    ).scalar()
    if count > 0:
        return True
    
    return False


def migrate_bars(db, from_instrument_id: int, to_instrument_id: int) -> int:
    """
    Migrate bars from duplicate instrument to canonical
    Returns number of bars migrated
    """
    bars = db.query(MarketDataBarD1).filter(
        MarketDataBarD1.instrument_id == from_instrument_id
    ).all()
    
    migrated = 0
    for bar in bars:
        # Check if bar already exists for canonical instrument
        existing = db.query(MarketDataBarD1).filter(
            and_(
                MarketDataBarD1.instrument_id == to_instrument_id,
                MarketDataBarD1.date == bar.date
            )
        ).first()
        
        if existing:
            # Update existing bar
            existing.open = bar.open
            existing.high = bar.high
            existing.low = bar.low
            existing.close = bar.close
            existing.volume = bar.volume
            existing.source = bar.source
        else:
            # Create new bar
            new_bar = MarketDataBarD1(
                instrument_id=to_instrument_id,
                date=bar.date,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                source=bar.source,
            )
            db.add(new_bar)
        
        migrated += 1
    
    return migrated


def main():
    db = SessionLocal()
    report = {
        "archived_instruments": [],
        "migrated_bars_count": 0,
        "deleted_instruments": [],
        "warnings": [],
        "dry_run": DRY_RUN,
    }
    
    try:
        print("=" * 80)
        print("Market Data Instruments Cleanup - Yahoo Only")
        print("=" * 80)
        if DRY_RUN:
            print("⚠️  DRY RUN MODE - No changes will be made to database")
        print()
        
        # Step 1: Archive non-Yahoo instruments
        print("Step 1: Archiving non-Yahoo instruments...")
        non_yahoo = db.query(MarketDataInstrument).filter(
            or_(
                MarketDataInstrument.provider.is_(None),
                MarketDataInstrument.provider != "yahoo"
            )
        ).all()
        
        for inst in non_yahoo:
            bars_count = db.query(func.count(MarketDataBarD1.instrument_id)).filter(
                MarketDataBarD1.instrument_id == inst.id
            ).scalar()
            
            if bars_count == 0:
                # No bars, safe to archive
                print(f"  - Archiving {inst.symbol} (provider={inst.provider}, no bars)")
                if not DRY_RUN:
                    inst.is_active = "false"
                    inst.archived_at = datetime.utcnow()
                report["archived_instruments"].append({
                    "id": inst.id,
                    "symbol": inst.symbol,
                    "provider": inst.provider,
                    "reason": "non-yahoo, no bars"
                })
            else:
                # Has bars, check references
                referenced = check_instrument_referenced(db, inst.id)
                if referenced:
                    print(f"  - Archiving {inst.symbol} (provider={inst.provider}, {bars_count} bars, referenced in backtests)")
                    if not DRY_RUN:
                        inst.is_active = "false"
                        inst.archived_at = datetime.utcnow()
                    report["archived_instruments"].append({
                        "id": inst.id,
                        "symbol": inst.symbol,
                        "provider": inst.provider,
                        "reason": "non-yahoo, referenced"
                    })
                else:
                    print(f"  - Archiving {inst.symbol} (provider={inst.provider}, {bars_count} bars, not referenced)")
                    if not DRY_RUN:
                        inst.is_active = "false"
                        inst.archived_at = datetime.utcnow()
                    report["archived_instruments"].append({
                        "id": inst.id,
                        "symbol": inst.symbol,
                        "provider": inst.provider,
                        "reason": "non-yahoo, not referenced"
                    })
        
        if not DRY_RUN:
            db.commit()
        print(f"  ✓ Archived {len(non_yahoo)} non-Yahoo instruments\n")
        
        # Step 2: Find duplicates among Yahoo instruments
        print("Step 2: Finding duplicates among Yahoo instruments...")
        yahoo_instruments = db.query(MarketDataInstrument).filter(
            and_(
                MarketDataInstrument.provider == "yahoo",
                MarketDataInstrument.is_active == "true"
            )
        ).all()
        
        # Group by normalized symbol + asset_class
        groups: Dict[Tuple[str, str], List[MarketDataInstrument]] = {}
        for inst in yahoo_instruments:
            norm_symbol = normalize_symbol(inst.symbol, inst.asset_class)
            key = (norm_symbol, inst.asset_class)
            if key not in groups:
                groups[key] = []
            groups[key].append(inst)
        
        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        print(f"  Found {len(duplicates)} duplicate groups\n")
        
        # Step 3: Deduplicate
        print("Step 3: Deduplicating...")
        for (norm_symbol, asset_class), insts in duplicates.items():
            canonical = get_canonical_instrument(insts)
            if not canonical:
                report["warnings"].append(f"Could not determine canonical for {norm_symbol} ({asset_class})")
                continue
            
            duplicates_list = [i for i in insts if i.id != canonical.id]
            print(f"  - Group: {norm_symbol} ({asset_class})")
            print(f"    Canonical: {canonical.symbol} (id={canonical.id})")
            
            for dup in duplicates_list:
                print(f"    Duplicate: {dup.symbol} (id={dup.id})")
                
                # Check if duplicate has bars
                dup_bars_count = db.query(func.count(MarketDataBarD1.instrument_id)).filter(
                    MarketDataBarD1.instrument_id == dup.id
                ).scalar()
                
                canonical_bars_count = db.query(func.count(MarketDataBarD1.instrument_id)).filter(
                    MarketDataBarD1.instrument_id == canonical.id
                ).scalar()
                
                if dup_bars_count > 0:
                    if canonical_bars_count > 0:
                        # Both have bars - check for overlapping dates
                        dup_dates = set(
                            db.query(MarketDataBarD1.date).filter(
                                MarketDataBarD1.instrument_id == dup.id
                            ).all()
                        )
                        canonical_dates = set(
                            db.query(MarketDataBarD1.date).filter(
                                MarketDataBarD1.instrument_id == canonical.id
                            ).all()
                        )
                        overlap = dup_dates & canonical_dates
                        
                        if overlap:
                            print(f"      ⚠️  Both have bars with {len(overlap)} overlapping dates - archiving duplicate only")
                            report["warnings"].append(
                                f"Duplicate {dup.symbol} has overlapping bars with canonical {canonical.symbol}"
                            )
                        else:
                            # No overlap, migrate bars
                            print(f"      Migrating {dup_bars_count} bars to canonical...")
                            if not DRY_RUN:
                                migrated = migrate_bars(db, dup.id, canonical.id)
                                report["migrated_bars_count"] += migrated
                    else:
                        # Canonical has no bars, migrate
                        print(f"      Migrating {dup_bars_count} bars to canonical...")
                        if not DRY_RUN:
                            migrated = migrate_bars(db, dup.id, canonical.id)
                            report["migrated_bars_count"] += migrated
                
                # Archive duplicate
                referenced = check_instrument_referenced(db, dup.id)
                if referenced:
                    print(f"      ⚠️  Referenced in backtests - archiving only")
                    report["warnings"].append(f"Duplicate {dup.symbol} is referenced in backtests")
                
                print(f"      Archiving duplicate...")
                if not DRY_RUN:
                    dup.is_active = "false"
                    dup.archived_at = datetime.utcnow()
                
                report["archived_instruments"].append({
                    "id": dup.id,
                    "symbol": dup.symbol,
                    "provider": dup.provider,
                    "reason": f"duplicate of {canonical.symbol}"
                })
            
            print()
        
        if not DRY_RUN:
            db.commit()
        
        print("=" * 80)
        print("Cleanup Complete")
        print("=" * 80)
        print(json.dumps(report, indent=2, default=str))
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

