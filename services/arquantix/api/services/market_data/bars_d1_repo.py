"""
Centralized repository for MarketDataBarD1 (D1 price bars)
Provides unified access to price data for preview, backtests, and other services.
"""
from typing import List, Dict, Optional, Tuple
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import pandas as pd

from database import MarketDataBarD1


def get_bars_d1(
    db: Session,
    instrument_ids: List[int],
    start_date: date,
    end_date: date
) -> List[MarketDataBarD1]:
    """
    Get D1 bars for given instruments and date range
    
    Args:
        db: Database session
        instrument_ids: List of instrument IDs
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
    
    Returns:
        List of MarketDataBarD1 objects
    """
    return db.query(MarketDataBarD1).filter(
        and_(
            MarketDataBarD1.instrument_id.in_(instrument_ids),
            MarketDataBarD1.date >= start_date,
            MarketDataBarD1.date <= end_date
        )
    ).order_by(MarketDataBarD1.instrument_id, MarketDataBarD1.date).all()


def get_close_matrix(
    db: Session,
    instrument_ids: List[int],
    start_date: date,
    end_date: date
) -> Dict[int, Dict[date, float]]:
    """
    Get close prices as a nested dict: instrument_id -> date -> close_price
    
    Args:
        db: Database session
        instrument_ids: List of instrument IDs
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
    
    Returns:
        Dict[instrument_id][date] = close_price
    """
    bars = get_bars_d1(db, instrument_ids, start_date, end_date)
    
    matrix: Dict[int, Dict[date, float]] = {}
    for bar in bars:
        if bar.instrument_id not in matrix:
            matrix[bar.instrument_id] = {}
        matrix[bar.instrument_id][bar.date] = float(bar.close)
    
    return matrix


def get_ohlc_matrix(
    db: Session,
    instrument_ids: List[int],
    start_date: date,
    end_date: date
) -> Dict[int, Dict[date, Dict[str, float]]]:
    """
    Get OHLCV data as a nested dict: instrument_id -> date -> {open, high, low, close, volume}
    
    Args:
        db: Database session
        instrument_ids: List of instrument IDs
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
    
    Returns:
        Dict[instrument_id][date] = {open, high, low, close, volume}
    """
    bars = get_bars_d1(db, instrument_ids, start_date, end_date)
    
    matrix: Dict[int, Dict[date, Dict[str, float]]] = {}
    for bar in bars:
        if bar.instrument_id not in matrix:
            matrix[bar.instrument_id] = {}
        matrix[bar.instrument_id][bar.date] = {
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': int(bar.volume) if bar.volume else 0,
        }
    
    return matrix


def get_price_dataframe(
    db: Session,
    instrument_ids: List[int],
    start_date: date,
    end_date: date
) -> pd.DataFrame:
    """
    Get price data as a pandas DataFrame for use with resolver/preview
    
    Args:
        db: Database session
        instrument_ids: List of instrument IDs
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
    
    Returns:
        DataFrame with columns: date, instrument_id, open, high, low, close, volume
    """
    bars = get_bars_d1(db, instrument_ids, start_date, end_date)
    
    rows = []
    for bar in bars:
        rows.append({
            'date': bar.date,
            'instrument_id': bar.instrument_id,
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': int(bar.volume) if bar.volume else 0,
        })
    
    if not rows:
        return pd.DataFrame(columns=['date', 'instrument_id', 'open', 'high', 'low', 'close', 'volume'])
    
    df = pd.DataFrame(rows)
    # Ensure date is date type (not datetime)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.date
    
    return df


def get_available_date_range(
    db: Session,
    instrument_ids: List[int]
) -> Dict[int, Tuple[Optional[date], Optional[date]]]:
    """
    Get available date range (min, max) for each instrument
    
    Args:
        db: Database session
        instrument_ids: List of instrument IDs
    
    Returns:
        Dict[instrument_id] = (min_date, max_date) or (None, None) if no data
    """
    results = db.query(
        MarketDataBarD1.instrument_id,
        func.min(MarketDataBarD1.date).label('min_date'),
        func.max(MarketDataBarD1.date).label('max_date')
    ).filter(
        MarketDataBarD1.instrument_id.in_(instrument_ids)
    ).group_by(MarketDataBarD1.instrument_id).all()
    
    date_ranges: Dict[int, Tuple[Optional[date], Optional[date]]] = {}
    for inst_id in instrument_ids:
        date_ranges[inst_id] = (None, None)
    
    for result in results:
        date_ranges[result.instrument_id] = (result.min_date, result.max_date)
    
    return date_ranges


def check_data_coverage(
    db: Session,
    instrument_ids: List[int],
    start_date: date,
    end_date: date,
    min_coverage_pct: float = 0.95
) -> Tuple[bool, List[str]]:
    """
    Check if data coverage is sufficient for the date range
    
    Args:
        db: Database session
        instrument_ids: List of instrument IDs
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        min_coverage_pct: Minimum coverage percentage (default 95%)
    
    Returns:
        Tuple of (is_sufficient, warnings_list)
    """
    warnings = []
    total_days = (end_date - start_date).days + 1
    
    date_ranges = get_available_date_range(db, instrument_ids)
    
    for inst_id in instrument_ids:
        min_date, max_date = date_ranges[inst_id]
        
        if min_date is None or max_date is None:
            warnings.append(f"Instrument {inst_id} has no price data")
            continue
        
        # Check if range is covered
        actual_start = max(start_date, min_date)
        actual_end = min(end_date, max_date)
        
        if actual_start > actual_end:
            warnings.append(f"Instrument {inst_id} has no data in range {start_date} to {end_date}")
            continue
        
        covered_days = (actual_end - actual_start).days + 1
        coverage_pct = covered_days / total_days if total_days > 0 else 0.0
        
        if coverage_pct < min_coverage_pct:
            warnings.append(
                f"Instrument {inst_id} has only {coverage_pct:.1%} coverage "
                f"({covered_days}/{total_days} days) in range {start_date} to {end_date}"
            )
    
    is_sufficient = len(warnings) == 0
    return is_sufficient, warnings

