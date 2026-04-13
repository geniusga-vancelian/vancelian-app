"""
Backtest routes - API endpoints for backtest operations
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel

from database import get_db, BacktestRun, MarketDataInstrument, BundleComponent, MarketDataBundle
from auth import get_current_user, AdminUser

router = APIRouter(prefix="/api/backtests", tags=["backtests"])


# ============================================================================
# Schemas
# ============================================================================

class BacktestStrategyParams(BaseModel):
    lookback_days: Optional[int] = None
    # CPPI params
    floor_ratio: Optional[float] = None
    multiplier: Optional[float] = None
    risky_cap: Optional[float] = None
    core_min: Optional[float] = None
    core_yield: Optional[float] = None
    day_count: Optional[int] = None
    # Core-Satellite params (V1 + V2)
    target_te: Optional[float] = None
    te_tolerance: Optional[float] = None
    te_max_hard_mult: Optional[float] = None
    lookback_risk_days: Optional[int] = None
    lookback_return_days: Optional[int] = None
    max_weight_per_asset: Optional[float] = None
    core_grid_step: Optional[float] = None
    top_k_satellite: Optional[int] = None
    # V2 params
    sat_min: Optional[float] = None
    shrinkage: Optional[bool] = None
    turnover_penalty: Optional[float] = None
    stability_penalty: Optional[float] = None
    optimization_method: Optional[str] = None
    # V2.1 EDHEC-style allocation params
    allocation_mode: Optional[str] = None
    lambda_risk: Optional[float] = None
    multiplier: Optional[float] = None
    floor_rel_ratio: Optional[float] = None
    floor_accrues_with_core: Optional[bool] = None
    sat_max: Optional[float] = None
    debug: Optional[bool] = None


class BacktestStrategy(BaseModel):
    type: str  # "equal_weight", "momentum", "bundle_strategy", "CPPI", or "CORE_SATELLITE"
    params: Optional[BacktestStrategyParams] = None


class BacktestRunRequest(BaseModel):
    name: Optional[str] = None
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    instrument_ids: Optional[List[int]] = None
    bundle_id: Optional[str] = None
    strategy: BacktestStrategy
    rebalance: str  # "daily", "weekly", "monthly"
    fees_bps: float
    slippage_bps: float
    allow_weekend_trading: bool


class BacktestRunResponse(BaseModel):
    id: int
    name: Optional[str]
    status: str
    created_at: str
    start_date: str
    end_date: str
    message: Optional[str] = None


# ============================================================================
# Routes
# ============================================================================

@router.post("/run", status_code=status.HTTP_201_CREATED)
def create_backtest_run(
    request: BacktestRunRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create and run a new backtest"""
    # Validate dates
    try:
        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    
    # Get instrument IDs from bundle if bundle_id is provided
    instrument_ids = request.instrument_ids
    bundle_allocations = None  # Map of instrument_id -> allocation percentage (0-100)
    final_strategy_type = request.strategy.type  # Default to requested strategy type
    
    if request.bundle_id:
        try:
            bundle_id_int = int(request.bundle_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bundle_id format")
        
        bundle = db.query(MarketDataBundle).filter(MarketDataBundle.id == bundle_id_int).first()
        if not bundle:
            raise HTTPException(status_code=404, detail="Bundle not found")
        
        # Get instruments and allocations from bundle components
        components = db.query(BundleComponent).filter(
            BundleComponent.bundle_id == bundle.id,
            BundleComponent.component_type == "instrument",
            BundleComponent.instrument_id.isnot(None)
        ).all()
        
        instrument_ids = [comp.instrument_id for comp in components if comp.instrument_id]
        
        if not instrument_ids:
            raise HTTPException(status_code=400, detail="Bundle has no instruments")
        
        # Extract allocations (weights) from bundle components
        # weight is stored as Decimal percentage (0-100)
        bundle_allocations = {}
        for comp in components:
            if comp.instrument_id and comp.weight is not None:
                # Convert Decimal to float (weight is already in percentage 0-100)
                bundle_allocations[comp.instrument_id] = float(comp.weight)
        
        # If bundle has allocations and strategy is not CPPI or CORE_SATELLITE, strategy should be "bundle_strategy"
        # Override strategy type to bundle_strategy when bundle is selected (but preserve CPPI and CORE_SATELLITE if selected)
        if bundle_allocations and request.strategy.type not in ("CPPI", "CORE_SATELLITE"):
            final_strategy_type = "bundle_strategy"
    
    if not instrument_ids or len(instrument_ids) == 0:
        raise HTTPException(status_code=400, detail="instrument_ids or bundle_id must be provided")
    
    # Validate instruments exist
    instruments = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.id.in_(instrument_ids)
    ).all()
    
    if len(instruments) != len(instrument_ids):
        found_ids = {inst.id for inst in instruments}
        missing_ids = set(instrument_ids) - found_ids
        raise HTTPException(
            status_code=400,
            detail=f"Some instrument IDs not found: {list(missing_ids)}"
        )
    
    # Create backtest run (final_strategy_type already set above)
    backtest_run = BacktestRun(
        name=request.name,
        created_by_email=current_user.email,
        start_date=start_date,
        end_date=end_date,
        rebalance=request.rebalance,
        strategy_type=final_strategy_type,
        strategy_params_json=request.strategy.params.dict() if request.strategy.params else None,
        fees_bps=request.fees_bps,
        slippage_bps=request.slippage_bps,
        allow_weekend_trading="true" if request.allow_weekend_trading else "false",
        instrument_ids_json=instrument_ids,
        bundle_id=request.bundle_id,
        status="PENDING",
    )
    
    db.add(backtest_run)
    db.commit()
    db.refresh(backtest_run)
    
    # Execute backtest synchronously (for now)
    # TODO: In production, this should be queued as an async task
    try:
        from services.backtest.executor import execute_backtest
        
        # Parse strategy params
        strategy_params = None
        if request.strategy.params:
            strategy_params = request.strategy.params.dict()
        
        try:
            execute_backtest(
                db=db,
                run_id=backtest_run.id,
                instrument_ids=instrument_ids,
                start_date=start_date,
                end_date=end_date,
                strategy_type=final_strategy_type,
                rebalance=request.rebalance,
                fees_bps=request.fees_bps,
                slippage_bps=request.slippage_bps,
                allow_weekend_trading=request.allow_weekend_trading,
                bundle_allocations=bundle_allocations,  # Still used for bundle_strategy, not CPPI
                strategy_params_json=strategy_params,
            )
        except ValueError as e:
            # Catch bundle validation errors (raised as ValueError from executor)
            error_msg = str(e)
            if "Invalid bundle allocation" in error_msg or "weights must sum" in error_msg.lower():
                # Bundle validation error: return 422
                db.refresh(backtest_run)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=error_msg
                )
            else:
                # Other ValueError: return 400
                db.refresh(backtest_run)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
        
        # Refresh to get updated status
        db.refresh(backtest_run)
        
        if backtest_run.status == "SUCCESS":
            message = "Backtest completed successfully."
        elif backtest_run.status == "FAILED":
            message = f"Backtest failed: {backtest_run.error_message or 'Unknown error'}"
        else:
            message = "Backtest execution in progress."
    except Exception as e:
        # Error during execution
        import traceback
        error_msg = f"Error executing backtest: {str(e)}\n{traceback.format_exc()}"
        backtest_run.status = "FAILED"
        backtest_run.error_message = error_msg
        db.commit()
        message = f"Backtest execution error: {str(e)}"
    
    return {
        "run_id": backtest_run.id,  # Frontend expects run_id
        "id": backtest_run.id,  # Also include id for compatibility
        "name": backtest_run.name,
        "status": backtest_run.status,
        "created_at": backtest_run.created_at.isoformat() if backtest_run.created_at else "",
        "start_date": backtest_run.start_date.isoformat(),
        "end_date": backtest_run.end_date.isoformat(),
        "message": message,
    }


@router.get("/{run_id}")
def get_backtest_run(
    run_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a backtest run by ID"""
    backtest_run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    
    return {
        "run": {
            "id": backtest_run.id,
            "name": backtest_run.name,
            "status": backtest_run.status,
            "created_at": backtest_run.created_at.isoformat() if backtest_run.created_at else None,
            "start_date": backtest_run.start_date.isoformat(),
            "end_date": backtest_run.end_date.isoformat(),
            "effective_start_date": backtest_run.effective_start_date.isoformat() if backtest_run.effective_start_date else None,
            "effective_end_date": backtest_run.effective_end_date.isoformat() if backtest_run.effective_end_date else None,
            "rebalance": backtest_run.rebalance,
            "strategy_type": backtest_run.strategy_type,
            "strategy_params_json": backtest_run.strategy_params_json,
            "fees_bps": float(backtest_run.fees_bps) if backtest_run.fees_bps else 0.0,
            "slippage_bps": float(backtest_run.slippage_bps) if backtest_run.slippage_bps else 0.0,
            "allow_weekend_trading": backtest_run.allow_weekend_trading == "true",
            "instrument_ids_json": backtest_run.instrument_ids_json,
            "bundle_id": backtest_run.bundle_id,
            "error_message": backtest_run.error_message,
        }
    }


@router.get("/{run_id}/series")
def get_backtest_series(
    run_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get backtest series data (portfolio and instrument series)"""
    backtest_run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if not backtest_run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    
    from database import BacktestPortfolioSeries, BacktestInstrumentSeries
    from collections import defaultdict
    
    # Load portfolio series
    portfolio_series = db.query(BacktestPortfolioSeries).filter(
        BacktestPortfolioSeries.run_id == run_id
    ).order_by(BacktestPortfolioSeries.date).all()
    
    # Load instrument series
    instrument_series = db.query(BacktestInstrumentSeries).filter(
        BacktestInstrumentSeries.run_id == run_id
    ).order_by(BacktestInstrumentSeries.date).all()
    
    # Transform portfolio series to match frontend format
    portfolio = [
        {
            "date": ps.date.isoformat(),
            "nav_base100": float(ps.nav_base100),
            "portfolio_return": float(ps.portfolio_return),
            "drawdown": float(ps.drawdown),
            "turnover": float(ps.turnover),
            "costs": float(ps.costs),
            "weights_json": ps.weights_json or {},
            "tradable_json": ps.tradable_json or {},
        }
        for ps in portfolio_series
    ]
    
    # Group instrument series by instrument_id and get symbols
    instrument_dict = defaultdict(list)
    instrument_ids = set()
    
    for is_ in instrument_series:
        instrument_ids.add(is_.instrument_id)
        instrument_dict[is_.instrument_id].append({
            "date": is_.date.isoformat(),
            "base100": float(is_.base100),
            "instrument_return": float(is_.instrument_return) if is_.instrument_return else None,
        })
    
    # Get instrument symbols
    instruments_data = {}
    if instrument_ids:
        instruments_db = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.id.in_(list(instrument_ids))
        ).all()
        instruments_data = {inst.id: inst.symbol for inst in instruments_db}
    
    # Transform to frontend format: instruments: InstrumentSeries[]
    instruments_list = [
        {
            "instrument_id": inst_id,
            "symbol": instruments_data.get(inst_id, f"INST_{inst_id}"),
            "series": instrument_dict[inst_id],
        }
        for inst_id in sorted(instrument_ids)
    ]
    
    # Return in format expected by frontend: { portfolio: PortfolioBar[], instruments: InstrumentSeries[] }
    return {
        "portfolio": portfolio,
        "instruments": instruments_list,
    }


def should_rebalance(current_date: date, last_rebalance_date: date, rebalance_freq: str) -> bool:
    """Determine if rebalancing should occur"""
    # Stub implementation
    return False


@router.get("")
def list_backtests(
    status: Optional[str] = None,
    strategy_type: Optional[str] = None,
    q: Optional[str] = None,  # Search query (name or ID)
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List backtest runs with filtering and pagination"""
    from sqlalchemy import and_, or_
    from sqlalchemy.orm import Query
    
    # Build query
    query: Query = db.query(BacktestRun)
    
    # Filters
    filters = []
    
    if status:
        filters.append(BacktestRun.status == status.upper())
    
    if strategy_type:
        filters.append(BacktestRun.strategy_type == strategy_type)
    
    if q:
        # Search by name or ID
        try:
            run_id = int(q)
            filters.append(BacktestRun.id == run_id)
        except ValueError:
            # Search by name (partial match)
            filters.append(BacktestRun.name.ilike(f"%{q}%"))
    
    if date_from:
        try:
            date_from_obj = date.fromisoformat(date_from)
            filters.append(BacktestRun.created_at >= datetime.combine(date_from_obj, datetime.min.time()).replace(tzinfo=None))
        except ValueError:
            pass  # Invalid date format, ignore
    
    if date_to:
        try:
            date_to_obj = date.fromisoformat(date_to)
            filters.append(BacktestRun.created_at <= datetime.combine(date_to_obj, datetime.max.time()).replace(tzinfo=None))
        except ValueError:
            pass  # Invalid date format, ignore
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Get total count (before pagination)
    total = query.count()
    
    # Apply pagination and ordering
    runs = query.order_by(BacktestRun.created_at.desc()).offset(offset).limit(limit).all()
    
    # Format response
    runs_list = []
    for run in runs:
        # Build universe label
        universe_label = None
        if run.bundle_id:
            bundle = db.query(MarketDataBundle).filter(MarketDataBundle.id == int(run.bundle_id)).first()
            universe_label = bundle.name if bundle else f"Bundle {run.bundle_id}"
        elif run.instrument_ids_json:
            universe_label = f"{len(run.instrument_ids_json)} instrument{'s' if len(run.instrument_ids_json) > 1 else ''}"
        
        runs_list.append({
            "id": run.id,
            "name": run.name or f"Run #{run.id}",
            "status": run.status,
            "strategy_type": run.strategy_type,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "start_date": run.start_date.isoformat(),
            "end_date": run.end_date.isoformat(),
            "effective_start_date": run.effective_start_date.isoformat() if run.effective_start_date else None,
            "effective_end_date": run.effective_end_date.isoformat() if run.effective_end_date else None,
            "rebalance": run.rebalance,
            "universe_label": universe_label,
            "instrument_count": len(run.instrument_ids_json) if run.instrument_ids_json else 0,
        })
    
    return {
        "runs": runs_list,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


class CompareBacktestsRequest(BaseModel):
    run_ids: List[int]
    align_mode: Optional[str] = "intersection"  # "intersection" or "union"


@router.post("/compare")
def compare_backtests(
    request: CompareBacktestsRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare multiple backtest runs"""
    from collections import defaultdict
    from sqlalchemy import and_
    from database import BacktestPortfolioSeries, BacktestInstrumentSeries, BacktestMetrics
    
    # Validate run_ids
    if len(request.run_ids) < 1:
        raise HTTPException(status_code=400, detail="At least 1 run_id required")
    
    if len(request.run_ids) > 10:
        raise HTTPException(status_code=422, detail="Maximum 10 run_ids allowed")
    
    # Validate align_mode
    if request.align_mode not in ["intersection", "union"]:
        raise HTTPException(status_code=400, detail="align_mode must be 'intersection' or 'union'")
    
    # Load runs
    runs = db.query(BacktestRun).filter(BacktestRun.id.in_(request.run_ids)).all()
    
    if len(runs) != len(request.run_ids):
        found_ids = {run.id for run in runs}
        missing_ids = set(request.run_ids) - found_ids
        raise HTTPException(status_code=404, detail=f"Backtest runs not found: {list(missing_ids)}")
    
    # Build runs metadata
    runs_meta = {}
    for run in runs:
        # Build universe label
        universe_label = None
        if run.bundle_id:
            bundle = db.query(MarketDataBundle).filter(MarketDataBundle.id == int(run.bundle_id)).first()
            universe_label = bundle.name if bundle else f"Bundle {run.bundle_id}"
        elif run.instrument_ids_json:
            universe_label = f"{len(run.instrument_ids_json)} instrument{'s' if len(run.instrument_ids_json) > 1 else ''}"
        
        runs_meta[run.id] = {
            "id": run.id,
            "name": run.name or f"Run #{run.id}",
            "strategy_type": run.strategy_type,
            "strategy_params_json": run.strategy_params_json,
            "universe_label": universe_label,
            "start_date": run.start_date.isoformat(),
            "end_date": run.end_date.isoformat(),
            "effective_start_date": run.effective_start_date.isoformat() if run.effective_start_date else None,
            "effective_end_date": run.effective_end_date.isoformat() if run.effective_end_date else None,
            "rebalance": run.rebalance,
            "instrument_ids_json": run.instrument_ids_json,
            "bundle_id": run.bundle_id,
        }
    
    # Load portfolio series for all runs
    portfolio_series_all = db.query(BacktestPortfolioSeries).filter(
        BacktestPortfolioSeries.run_id.in_(request.run_ids)
    ).order_by(BacktestPortfolioSeries.date).all()
    
    # Group by run_id
    series_by_run = defaultdict(list)
    for ps in portfolio_series_all:
        series_by_run[ps.run_id].append({
            "date": ps.date.isoformat(),
            "nav_base100": float(ps.nav_base100),
        })
    
    # Get date sets for each run
    date_sets = {run_id: {item["date"] for item in series} for run_id, series in series_by_run.items()}
    
    # Determine alignment dates
    if request.align_mode == "intersection":
        # Intersection: only dates present in ALL runs
        if date_sets:
            aligned_dates = set.intersection(*date_sets.values())
        else:
            aligned_dates = set()
    else:  # union
        # Union: all dates from all runs
        if date_sets:
            aligned_dates = set.union(*date_sets.values())
        else:
            aligned_dates = set()
    
    aligned_dates = sorted(list(aligned_dates))
    
    # Build aligned series
    aligned_series = []
    for date_str in aligned_dates:
        values = {}
        for run_id in request.run_ids:
            # Find nav_base100 for this run_id and date
            nav_value = None
            run_series = series_by_run.get(run_id, [])
            for item in run_series:
                if item["date"] == date_str:
                    nav_value = item["nav_base100"]
                    break
            values[str(run_id)] = nav_value
        
        aligned_series.append({
            "date": date_str,
            "values": values,
        })
    
    # Load metrics for all runs
    metrics_all = db.query(BacktestMetrics).filter(
        and_(
            BacktestMetrics.run_id.in_(request.run_ids),
            BacktestMetrics.scope == "portfolio"
        )
    ).all()
    
    # Group metrics by run_id
    metrics_by_run = defaultdict(dict)
    for m in metrics_all:
        metrics_by_run[m.run_id][m.key] = float(m.value)
    
    # Calculate stats for each run (use DB metrics or fallback calculation)
    stats_by_run = {}
    
    for run_id in request.run_ids:
        run_metrics = metrics_by_run.get(run_id, {})
        run_series = series_by_run.get(run_id, [])
        
        # Get annualized_return (use DB or calculate)
        annualized_return = run_metrics.get("annualized_return")
        if annualized_return is None:
            # Fallback: calculate from nav_base100 series
            if len(run_series) >= 2:
                first_nav = run_series[0]["nav_base100"]
                last_nav = run_series[-1]["nav_base100"]
                if first_nav > 0:
                    total_return = (last_nav / first_nav) - 1.0
                    # Approximate annualization (assuming daily data)
                    days = len(run_series)
                    if days > 1:
                        annualized_return = ((1 + total_return) ** (365.0 / days)) - 1.0
                    else:
                        annualized_return = 0.0
                else:
                    annualized_return = 0.0
            else:
                annualized_return = 0.0
        
        # Get max_drawdown (use DB or calculate)
        max_drawdown = run_metrics.get("max_drawdown")
        if max_drawdown is None:
            # Fallback: calculate from nav_base100 series
            if len(run_series) >= 2:
                nav_values = [item["nav_base100"] for item in run_series]
                peak = nav_values[0]
                max_dd = 0.0
                for nav in nav_values:
                    if nav > peak:
                        peak = nav
                    drawdown = (nav - peak) / peak if peak > 0 else 0.0
                    if drawdown < max_dd:
                        max_dd = drawdown
                max_drawdown = max_dd
            else:
                max_drawdown = 0.0
        
        # Get sharpe_ratio (use DB or calculate)
        sharpe_ratio = run_metrics.get("sharpe_ratio")
        if sharpe_ratio is None:
            # Fallback: calculate from nav_base100 series
            if len(run_series) >= 2:
                nav_values = [item["nav_base100"] for item in run_series]
                returns = []
                for i in range(1, len(nav_values)):
                    if nav_values[i-1] > 0:
                        ret = (nav_values[i] / nav_values[i-1]) - 1.0
                        returns.append(ret)
                
                if returns and len(returns) > 1:
                    import numpy as np
                    mean_return = np.mean(returns)
                    std_return = np.std(returns, ddof=1)
                    if std_return > 0:
                        # Annualize
                        sharpe_ratio = (mean_return * np.sqrt(252)) / (std_return * np.sqrt(252))
                    else:
                        sharpe_ratio = 0.0
                else:
                    sharpe_ratio = 0.0
            else:
                sharpe_ratio = 0.0
        
        # Get calmar_ratio (use DB or calculate)
        calmar_ratio = run_metrics.get("calmar_ratio")
        if calmar_ratio is None:
            # Fallback: calculate from annualized_return and max_drawdown
            if max_drawdown != 0:
                calmar_ratio = annualized_return / abs(max_drawdown)
            else:
                calmar_ratio = None  # Cannot compute if max_drawdown is 0
        
        stats_by_run[str(run_id)] = {
            "annualized_performance": annualized_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "calmar_ratio": calmar_ratio,
        }
    
    return {
        "runs": runs_meta,
        "series": aligned_series,
        "stats": stats_by_run,
    }
