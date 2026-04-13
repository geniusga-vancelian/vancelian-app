"""
Backtest repository - Database operations for backtests
"""
from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from decimal import Decimal
import pandas as pd

from database import MarketDataInstrument, MarketDataBarD1


def load_instruments(db: Session, instrument_ids: List[int]) -> List[Any]:
    """Load instruments from database"""
    instruments = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.id.in_(instrument_ids),
        MarketDataInstrument.is_active == "true"
    ).all()
    return instruments


def load_open_bars(db: Session, instrument_ids: List[int], start_date: date, end_date: date) -> Dict[int, pd.DataFrame]:
    """
    Load open price bars for instruments from market_data_bars_d1 table
    
    Returns:
        Dict mapping instrument_id to DataFrame with columns: date, open, high, low, close, volume
        DataFrame index is date, sorted ascending
    """
    if not instrument_ids:
        return {}
    
    # Query all bars for the instruments in the date range
    bars = db.query(MarketDataBarD1).filter(
        and_(
            MarketDataBarD1.instrument_id.in_(instrument_ids),
            MarketDataBarD1.date >= start_date,
            MarketDataBarD1.date <= end_date
        )
    ).order_by(MarketDataBarD1.instrument_id, MarketDataBarD1.date).all()
    
    # Group by instrument_id and create DataFrames
    result = {}
    for instrument_id in instrument_ids:
        instrument_bars = [b for b in bars if b.instrument_id == instrument_id]
        
        if not instrument_bars:
            # Return empty DataFrame with correct structure
            result[instrument_id] = pd.DataFrame(
                columns=['open', 'high', 'low', 'close', 'volume'],
                dtype=float
            )
            continue
        
        # Convert to DataFrame
        data = {
            'open': [float(b.open) for b in instrument_bars],
            'high': [float(b.high) for b in instrument_bars],
            'low': [float(b.low) for b in instrument_bars],
            'close': [float(b.close) for b in instrument_bars],
            'volume': [int(b.volume) for b in instrument_bars],
        }
        dates = [b.date for b in instrument_bars]
        
        df = pd.DataFrame(data, index=pd.DatetimeIndex(dates))
        df.index.name = 'date'
        result[instrument_id] = df
    
    return result


def create_backtest_run(db: Session, params: Dict[str, Any]) -> Any:
    """Create a new backtest run in database"""
    # Stub implementation
    return None


def update_backtest_run_status(db: Session, run_id: int, status: str, error_message: Optional[str] = None, effective_start_date: Optional[date] = None, effective_end_date: Optional[date] = None) -> None:
    """Update backtest run status"""
    from database import BacktestRun
    
    backtest_run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if backtest_run:
        backtest_run.status = status
        if error_message is not None:
            backtest_run.error_message = error_message
        if effective_start_date is not None:
            backtest_run.effective_start_date = effective_start_date
        if effective_end_date is not None:
            backtest_run.effective_end_date = effective_end_date
        db.commit()


def store_portfolio_series(db: Session, run_id: int, series: List[Dict[str, Any]]) -> None:
    """Store portfolio series data"""
    from database import BacktestPortfolioSeries
    from decimal import Decimal
    import json
    
    # Delete existing series for this run
    db.query(BacktestPortfolioSeries).filter(BacktestPortfolioSeries.run_id == run_id).delete()
    
    # Insert new series
    for item in series:
        # Clean weights_json: remove None values and ensure valid JSON
        weights_json = item.get('weights_json', {})
        if weights_json:
            # Remove None values and convert to valid JSON-serializable dict
            weights_json = {k: (v if v is not None else None) for k, v in weights_json.items()}
            # Ensure all values are valid (not NaN, inf, etc.)
            cleaned_weights = {}
            for k, v in weights_json.items():
                if v is None:
                    cleaned_weights[k] = None
                else:
                    try:
                        val = float(v)
                        if not (val != val or val == float('inf') or val == float('-inf')):  # Check for NaN or inf
                            cleaned_weights[k] = val
                        else:
                            cleaned_weights[k] = None
                    except (ValueError, TypeError):
                        cleaned_weights[k] = None
            weights_json = cleaned_weights
        
        portfolio_series = BacktestPortfolioSeries(
            run_id=run_id,
            date=item['date'],
            nav_base100=Decimal(str(item.get('nav_base100', 100.0))),
            portfolio_return=Decimal(str(item.get('portfolio_return', 0.0))),
            drawdown=Decimal(str(item.get('drawdown', 0.0))),
            turnover=Decimal(str(item.get('turnover', 0.0))),
            costs=Decimal(str(item.get('costs', 0.0))),
            weights_json=weights_json if weights_json else None,
            tradable_json=item.get('tradable_json'),
        )
        db.add(portfolio_series)
    
    db.commit()


def store_instrument_series(db: Session, run_id: int, series: Dict[int, List[Dict[str, Any]]]) -> None:
    """Store instrument series data"""
    from database import BacktestInstrumentSeries
    from decimal import Decimal
    
    # Delete existing series for this run
    db.query(BacktestInstrumentSeries).filter(BacktestInstrumentSeries.run_id == run_id).delete()
    
    # Insert new series for each instrument
    for instrument_id, instrument_series in series.items():
        for item in instrument_series:
            instrument_series_obj = BacktestInstrumentSeries(
                run_id=run_id,
                instrument_id=instrument_id,
                date=item['date'],
                base100=Decimal(str(item.get('base100', 100.0))),
                instrument_return=Decimal(str(item['instrument_return'])) if item.get('instrument_return') is not None else None,
            )
            db.add(instrument_series_obj)
    
    db.commit()


def store_metrics(db: Session, run_id: int, metrics: Dict[str, Any]) -> None:
    """Store computed metrics"""
    from database import BacktestMetrics
    from decimal import Decimal
    
    # Delete existing metrics for this run
    db.query(BacktestMetrics).filter(BacktestMetrics.run_id == run_id).delete()
    
    # Store portfolio metrics
    portfolio_metrics = metrics.get('portfolio', {})
    for key, value in portfolio_metrics.items():
        metric = BacktestMetrics(
            run_id=run_id,
            scope='portfolio',
            instrument_id=None,
            key=key,
            value=Decimal(str(value)),
        )
        db.add(metric)
    
    # Store instrument metrics
    instrument_metrics = metrics.get('instruments', {})
    for instrument_id, inst_metrics in instrument_metrics.items():
        for key, value in inst_metrics.items():
            metric = BacktestMetrics(
                run_id=run_id,
                scope='instrument',
                instrument_id=instrument_id,
                key=key,
                value=Decimal(str(value)),
            )
            db.add(metric)
    
    db.commit()
