"""
Smart ingestion service for Yahoo Finance HTML tables
Detects conflicts, overlaps, and provides safe update modes
"""
from typing import List, Dict, Tuple, Optional
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import MarketDataBarD1
from .yahoo_html_parser import parse_yahoo_html_table, ParsedBar


# Precision for comparison (6 decimal places)
DECIMAL_PRECISION = Decimal('0.000001')


def quantize_decimal(value: Decimal) -> Decimal:
    """Quantize decimal to precision for comparison"""
    return value.quantize(DECIMAL_PRECISION, rounding=ROUND_HALF_UP)


class BarRow:
    """Represents a single bar row for ingestion"""
    def __init__(self, date: date, open: Decimal, high: Decimal, low: Decimal, close: Decimal, volume: int):
        self.date = date
        self.open = quantize_decimal(open)
        self.high = quantize_decimal(high)
        self.low = quantize_decimal(low)
        self.close = quantize_decimal(close)
        self.volume = volume
    
    def __eq__(self, other):
        """Compare two bars (for conflict detection)"""
        if not isinstance(other, BarRow):
            return False
        return (
            self.date == other.date and
            self.open == other.open and
            self.high == other.high and
            self.low == other.low and
            self.close == other.close and
            self.volume == other.volume
        )
    
    def to_dict(self) -> Dict:
        """Convert to dict for serialization"""
        return {
            'date': self.date,
            'open': float(self.open),
            'high': float(self.high),
            'low': float(self.low),
            'close': float(self.close),
            'volume': self.volume,
        }


class ConflictMismatch:
    """Represents a mismatch between existing and incoming data"""
    def __init__(self, date: date, field: str, existing_value: Decimal, incoming_value: Decimal):
        self.date = date
        self.field = field
        self.existing_value = quantize_decimal(existing_value)
        self.incoming_value = quantize_decimal(incoming_value)
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date.isoformat(),
            'field': self.field,
            'existing_value': float(self.existing_value),
            'incoming_value': float(self.incoming_value),
        }


class IngestAnalysis:
    """Result of analyzing an ingestion request"""
    def __init__(self):
        self.incoming_count = 0
        self.incoming_min_date: Optional[date] = None
        self.incoming_max_date: Optional[date] = None
        self.existing_count = 0
        self.existing_min_date: Optional[date] = None
        self.existing_max_date: Optional[date] = None
        self.overlap_count = 0
        self.mismatch_count = 0
        self.mismatches: List[ConflictMismatch] = []
        self.delta_count = 0
        self.has_conflict = False
    
    def to_dict(self) -> Dict:
        return {
            'incoming_count': self.incoming_count,
            'incoming_range': {
                'min': self.incoming_min_date.isoformat() if self.incoming_min_date else None,
                'max': self.incoming_max_date.isoformat() if self.incoming_max_date else None,
            },
            'existing_count': self.existing_count,
            'existing_range': {
                'min': self.existing_min_date.isoformat() if self.existing_min_date else None,
                'max': self.existing_max_date.isoformat() if self.existing_max_date else None,
            },
            'overlap_count': self.overlap_count,
            'mismatch_count': self.mismatch_count,
            'mismatches': [m.to_dict() for m in self.mismatches[:10]],  # Limit to 10 examples
            'delta_count': self.delta_count,
            'has_conflict': self.has_conflict,
        }


def analyze_ingest_conflicts(
    db: Session,
    instrument_id: int,
    incoming_bars: List[ParsedBar],
    source: str = "yahoo"
) -> IngestAnalysis:
    """
    Analyze conflicts between incoming bars and existing data
    
    Returns:
        IngestAnalysis with conflict details
    """
    analysis = IngestAnalysis()
    
    if not incoming_bars:
        return analysis
    
    # Convert ParsedBar to BarRow
    incoming_rows = [
        BarRow(bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume)
        for bar in incoming_bars
    ]
    
    # Analyze incoming data
    analysis.incoming_count = len(incoming_rows)
    analysis.incoming_min_date = min(row.date for row in incoming_rows)
    analysis.incoming_max_date = max(row.date for row in incoming_rows)
    
    # Load existing bars in the incoming date range
    existing_bars = db.query(MarketDataBarD1).filter(
        and_(
            MarketDataBarD1.instrument_id == instrument_id,
            MarketDataBarD1.date >= analysis.incoming_min_date,
            MarketDataBarD1.date <= analysis.incoming_max_date,
            MarketDataBarD1.source == source
        )
    ).order_by(MarketDataBarD1.date).all()
    
    # Build existing dict
    existing_dict: Dict[date, BarRow] = {}
    for bar in existing_bars:
        existing_dict[bar.date] = BarRow(
            bar.date,
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            int(bar.volume) if bar.volume else 0
        )
    
    # Analyze existing data
    if existing_bars:
        analysis.existing_count = len(existing_bars)
        analysis.existing_min_date = min(bar.date for bar in existing_bars)
        analysis.existing_max_date = max(bar.date for bar in existing_bars)
    
    # Find overlaps and mismatches
    incoming_dict: Dict[date, BarRow] = {row.date: row for row in incoming_rows}
    overlap_dates = set(incoming_dict.keys()) & set(existing_dict.keys())
    analysis.overlap_count = len(overlap_dates)
    
    # Compare overlapping dates
    for overlap_date in overlap_dates:
        existing_row = existing_dict[overlap_date]
        incoming_row = incoming_dict[overlap_date]
        
        if existing_row != incoming_row:
            analysis.mismatch_count += 1
            
            # Find which fields differ
            if existing_row.open != incoming_row.open:
                analysis.mismatches.append(ConflictMismatch(overlap_date, 'open', existing_row.open, incoming_row.open))
            if existing_row.high != incoming_row.high:
                analysis.mismatches.append(ConflictMismatch(overlap_date, 'high', existing_row.high, incoming_row.high))
            if existing_row.low != incoming_row.low:
                analysis.mismatches.append(ConflictMismatch(overlap_date, 'low', existing_row.low, incoming_row.low))
            if existing_row.close != incoming_row.close:
                analysis.mismatches.append(ConflictMismatch(overlap_date, 'close', existing_row.close, incoming_row.close))
            if existing_row.volume != incoming_row.volume:
                analysis.mismatches.append(ConflictMismatch(overlap_date, 'volume', Decimal(str(existing_row.volume)), Decimal(str(incoming_row.volume))))
    
    # Find delta (missing dates)
    delta_dates = set(incoming_dict.keys()) - set(existing_dict.keys())
    analysis.delta_count = len(delta_dates)
    
    # Has conflict if any mismatches
    analysis.has_conflict = (analysis.mismatch_count > 0)
    
    return analysis


def apply_ingest(
    db: Session,
    instrument_id: int,
    incoming_bars: List[ParsedBar],
    mode: str,
    source: str = "yahoo"
) -> Dict:
    """
    Apply ingestion according to mode
    
    Modes:
    - "insert_delta_only": Insert only missing dates
    - "overwrite_overlap": Upsert overlap + insert missing
    - "overwrite_all_range": Delete all in range, then insert all incoming
    
    Returns:
        Dict with counts and range
    """
    if not incoming_bars:
        return {
            'inserted_count': 0,
            'updated_count': 0,
            'deleted_count': 0,
            'range': {'min': None, 'max': None},
        }
    
    # Convert to BarRow
    incoming_rows = [
        BarRow(bar.date, bar.open, bar.high, bar.low, bar.close, bar.volume)
        for bar in incoming_bars
    ]
    
    min_date = min(row.date for row in incoming_rows)
    max_date = max(row.date for row in incoming_rows)
    
    inserted_count = 0
    updated_count = 0
    deleted_count = 0
    
    if mode == "overwrite_all_range":
        # Delete all existing bars in range
        deleted = db.query(MarketDataBarD1).filter(
            and_(
                MarketDataBarD1.instrument_id == instrument_id,
                MarketDataBarD1.date >= min_date,
                MarketDataBarD1.date <= max_date,
                MarketDataBarD1.source == source
            )
        ).delete(synchronize_session=False)
        deleted_count = deleted
        
        # Insert all incoming
        for row in incoming_rows:
            bar = MarketDataBarD1(
                instrument_id=instrument_id,
                date=row.date,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
                source=source,
            )
            db.add(bar)
            inserted_count += 1
        
        db.commit()
    
    elif mode == "overwrite_overlap":
        # Upsert all incoming (insert or update)
        for row in incoming_rows:
            existing = db.query(MarketDataBarD1).filter(
                and_(
                    MarketDataBarD1.instrument_id == instrument_id,
                    MarketDataBarD1.date == row.date,
                    MarketDataBarD1.source == source
                )
            ).first()
            
            if existing:
                existing.open = row.open
                existing.high = row.high
                existing.low = row.low
                existing.close = row.close
                existing.volume = row.volume
                updated_count += 1
            else:
                bar = MarketDataBarD1(
                    instrument_id=instrument_id,
                    date=row.date,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    volume=row.volume,
                    source=source,
                )
                db.add(bar)
                inserted_count += 1
        
        db.commit()
    
    elif mode == "insert_delta_only":
        # Insert only missing dates
        for row in incoming_rows:
            existing = db.query(MarketDataBarD1).filter(
                and_(
                    MarketDataBarD1.instrument_id == instrument_id,
                    MarketDataBarD1.date == row.date,
                    MarketDataBarD1.source == source
                )
            ).first()
            
            if not existing:
                bar = MarketDataBarD1(
                    instrument_id=instrument_id,
                    date=row.date,
                    open=row.open,
                    high=row.high,
                    low=row.low,
                    close=row.close,
                    volume=row.volume,
                    source=source,
                )
                db.add(bar)
                inserted_count += 1
        
        db.commit()
    
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    return {
        'inserted_count': inserted_count,
        'updated_count': updated_count,
        'deleted_count': deleted_count,
        'range': {
            'min': min_date.isoformat(),
            'max': max_date.isoformat(),
        },
    }

