"""
Diagnostic checks for Market Data and Backtest modules
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
from pathlib import Path
import time
import json
import os

from database import (
    MarketDataInstrument,
    MarketDataBarD1,
    BacktestRun,
    BacktestPortfolioSeries,
)
from services.market_data.routes import CORE_V1_INSTRUMENTS
from services.backtest.engine import (
    build_calendar,
    align_prices,
    compute_returns,
    compute_target_weights,
    apply_tradability_constraints,
    compute_nav,
    compute_metrics,
)
from services.backtest.repository import (
    load_instruments,
    load_open_bars,
    create_backtest_run,
    update_backtest_run_status,
    store_portfolio_series,
    store_instrument_series,
    store_metrics,
)
from services.backtest.routes import should_rebalance
import pandas as pd
import numpy as np


def check_router_availability() -> Dict[str, Any]:
    """
    CHECK 1: Verify that market_data and backtests routers are available
    """
    start_time = time.time()
    result = {
        "check": "Router Availability",
        "status": "PASS",
        "details": [],
        "errors": [],
    }
    
    try:
        # Check if modules can be imported
        try:
            from services.market_data.routes import router as market_data_router
            result["details"].append("✓ Market Data router importable")
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Market Data router not importable: {str(e)}")
        
        try:
            from services.backtest.routes import router as backtest_router
            result["details"].append("✓ Backtest router importable")
        except Exception as e:
            result["status"] = "FAIL"
            result["errors"].append(f"Backtest router not importable: {str(e)}")
        
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result
    
    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"Unexpected error: {str(e)}")
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result


def check_instruments_exist(db: Session) -> Dict[str, Any]:
    """
    CHECK 2: Verify instruments exist, seed if needed
    """
    start_time = time.time()
    result = {
        "check": "Instruments Exist",
        "status": "PASS",
        "details": [],
        "errors": [],
        "count_before": 0,
        "count_after": 0,
        "seeded": False,
    }
    
    try:
        # Count existing instruments
        count_before = db.query(MarketDataInstrument).count()
        result["count_before"] = count_before
        
        if count_before < 8:  # CORE_V1 has 10 instruments
            result["details"].append(f"Only {count_before} instruments found, seeding CORE_V1...")
            
            # Seed instruments (internal call, not HTTP)
            try:
                from services.market_data.config import MARKET_DATA_PROVIDER
                
                created = []
                for inst_data in CORE_V1_INSTRUMENTS:
                    existing = db.query(MarketDataInstrument).filter(
                        MarketDataInstrument.symbol == inst_data["symbol"]
                    ).first()
                    
                    if existing:
                        continue
                    
                    new_inst = MarketDataInstrument(
                        symbol=inst_data["symbol"],
                        name=inst_data["name"],
                        asset_class=inst_data["asset_class"],
                        weekend_tradable="true" if inst_data["weekend_tradable"] else "false",
                        provider=MARKET_DATA_PROVIDER,
                        provider_symbol=inst_data.get("provider_symbol", inst_data["symbol"]),
                        is_active="true",
                    )
                    db.add(new_inst)
                    created.append(inst_data["symbol"])
                
                db.commit()
                result["seeded"] = True
                result["details"].append(f"✓ Seeded {len(created)} instruments: {', '.join(created)}")
            except Exception as e:
                db.rollback()
                result["status"] = "FAIL"
                result["errors"].append(f"Failed to seed instruments: {str(e)}")
        
        # Recheck count
        count_after = db.query(MarketDataInstrument).count()
        result["count_after"] = count_after
        
        if count_after >= 8:
            result["details"].append(f"✓ {count_after} instruments available")
        else:
            result["status"] = "FAIL"
            result["errors"].append(f"Only {count_after} instruments after seeding (expected >= 8)")
        
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result
    
    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"Unexpected error: {str(e)}")
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result


def check_bars_existence(db: Session) -> Dict[str, Any]:
    """
    CHECK 3: Check bars existence and date ranges
    """
    start_time = time.time()
    result = {
        "check": "Bars Existence",
        "status": "PASS",
        "details": [],
        "errors": [],
        "total_bars": 0,
        "date_min": None,
        "date_max": None,
        "instruments_detail": [],
    }
    
    try:
        # Total bars count
        total_bars = db.query(MarketDataBarD1).count()
        result["total_bars"] = total_bars
        
        if total_bars == 0:
            result["status"] = "FAIL"
            result["errors"].append("No bars found in database")
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return result
        
        # Global date range
        date_stats = db.query(
            func.min(MarketDataBarD1.date).label("min_date"),
            func.max(MarketDataBarD1.date).label("max_date")
        ).first()
        
        if date_stats:
            result["date_min"] = date_stats.min_date.isoformat() if date_stats.min_date else None
            result["date_max"] = date_stats.max_date.isoformat() if date_stats.max_date else None
            result["details"].append(f"Global date range: {result['date_min']} to {result['date_max']}")
        
        # Per-instrument stats
        instruments = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.is_active == "true"
        ).all()
        
        instruments_with_bars = 0
        for inst in instruments:
            inst_bars_count = db.query(MarketDataBarD1).filter(
                MarketDataBarD1.instrument_id == inst.id
            ).count()
            
            inst_date_stats = db.query(
                func.min(MarketDataBarD1.date).label("min_date"),
                func.max(MarketDataBarD1.date).label("max_date")
            ).filter(MarketDataBarD1.instrument_id == inst.id).first()
            
            inst_detail = {
                "instrument_id": inst.id,
                "symbol": inst.symbol,
                "bars_count": inst_bars_count,
                "date_min": inst_date_stats.min_date.isoformat() if inst_date_stats and inst_date_stats.min_date else None,
                "date_max": inst_date_stats.max_date.isoformat() if inst_date_stats and inst_date_stats.max_date else None,
            }
            result["instruments_detail"].append(inst_detail)
            
            if inst_bars_count > 0:
                instruments_with_bars += 1
            else:
                result["details"].append(f"⚠ {inst.symbol}: 0 bars")
        
        result["details"].append(f"✓ {instruments_with_bars}/{len(instruments)} instruments have bars")
        
        if instruments_with_bars == 0:
            result["status"] = "FAIL"
            result["errors"].append("No instruments have bars")
        
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result
    
    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"Unexpected error: {str(e)}")
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result


def check_quick_backfill(
    db: Session,
    mode: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    CHECK 4: Quick backfill for 2 instruments (1 crypto + 1 tradfi)
    """
    start_time = time.time()
    result = {
        "check": "Quick Backfill",
        "status": "PASS",
        "details": [],
        "errors": [],
        "backfilled_instruments": [],
        "bars_added": 0,
    }
    
    try:
        result["status"] = "SKIP"
        result["details"].append("Backfill disabled (Yahoo Finance provider removed). Use Binance candle ingestion instead.")
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result
    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"Unexpected error: {str(e)}")
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result


def check_backtest_run_minimal(db: Session) -> Dict[str, Any]:
    """
    CHECK 5: Run a minimal backtest (BTC + SPY, equal weight, weekly rebalance)
    """
    start_time = time.time()
    result = {
        "check": "Backtest Run Minimal",
        "status": "PASS",
        "details": [],
        "errors": [],
        "run_id": None,
        "effective_start_date": None,
        "effective_end_date": None,
        "metrics": None,
    }
    
    try:
        # Find BTC and SPY
        btc = db.query(MarketDataInstrument).filter(MarketDataInstrument.symbol == "BTC").first()
        spy = db.query(MarketDataInstrument).filter(MarketDataInstrument.symbol == "SPY").first()
        
        if not btc or not spy:
            result["status"] = "FAIL"
            result["errors"].append("BTC or SPY not found in instruments")
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return result
        
        instrument_ids = [btc.id, spy.id]
        
        # Find date range from existing bars
        date_stats = db.query(
            func.min(MarketDataBarD1.date).label("min_date"),
            func.max(MarketDataBarD1.date).label("max_date")
        ).filter(MarketDataBarD1.instrument_id.in_(instrument_ids)).first()
        
        if not date_stats or not date_stats.min_date or not date_stats.max_date:
            result["status"] = "FAIL"
            result["errors"].append("No bars found for BTC or SPY")
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return result
        
        # Use intersection of date ranges (last 90 days if available)
        end_date = min(date_stats.max_date, date.today())
        start_date = max(date_stats.min_date, end_date - timedelta(days=90))
        
        if start_date >= end_date:
            result["status"] = "FAIL"
            result["errors"].append(f"Invalid date range: {start_date} to {end_date}")
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return result
        
        result["details"].append(f"Running backtest: {start_date} to {end_date}")
        
        # Load instruments
        instruments = load_instruments(db, instrument_ids)
        weekend_tradable_map = {inst["id"]: inst["weekend_tradable"] for inst in instruments}
        
        # Load price data
        price_series = load_open_bars(db, instrument_ids, start_date, end_date)
        
        if not price_series:
            result["status"] = "FAIL"
            result["errors"].append("No price data loaded")
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return result
        
        # Find effective date range
        all_dates = set()
        for series in price_series.values():
            if len(series) > 0:
                all_dates.update(series.index)
        
        if not all_dates:
            result["status"] = "FAIL"
            result["errors"].append("No valid price dates")
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return result
        
        effective_start = max([series.index.min() for series in price_series.values() if len(series) > 0])
        effective_end = min([series.index.max() for series in price_series.values() if len(series) > 0])
        
        if effective_start > effective_end:
            result["status"] = "FAIL"
            result["errors"].append("No overlapping date range")
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return result
        
        # Create run record
        run = create_backtest_run(
            db=db,
            name="Diagnostic Minimal Backtest",
            start_date=start_date,
            end_date=end_date,
            instrument_ids=instrument_ids,
            strategy_type="equal_weight",
            strategy_params=None,
            rebalance="weekly",
            fees_bps=0.0,
            slippage_bps=0.0,
            allow_weekend_trading=True,
            created_by_user_id=None,  # Diagnostic run
            created_by_email="diagnostic@system",  # Diagnostic run
        )
        
        run_id = run.id
        result["run_id"] = run_id
        
        # Build calendar
        calendar = build_calendar(effective_start, effective_end)
        
        # Align prices
        open_prices = align_prices(price_series, calendar)
        
        # Compute returns
        returns = compute_returns(open_prices)
        
        # Initialize weights (equal weight)
        prev_weights = {inst_id: 1.0 / len(instrument_ids) for inst_id in instrument_ids}
        
        # Run simulation
        weights_series = []
        turnover_series = []
        costs_series = []
        tradable_masks = []
        portfolio_returns = []
        
        last_rebalance_date = None
        
        for i, current_date in enumerate(calendar):
            current_date_py = current_date.date()
            
            should_rebal = should_rebalance(current_date_py, last_rebalance_date, "weekly")
            
            if should_rebal:
                target_weights = compute_target_weights(
                    date=current_date_py,
                    strategy_type="equal_weight",
                    open_prices=open_prices,
                    returns=returns,
                    lookback_days=None,
                    eligible_instruments=instrument_ids,
                    prev_weights=prev_weights,
                )
                
                new_weights, turnover, tradable_mask = apply_tradability_constraints(
                    date=current_date_py,
                    weekend_tradable_map=weekend_tradable_map,
                    target_weights=target_weights,
                    prev_weights=prev_weights,
                )
                
                prev_weights = new_weights
                last_rebalance_date = current_date_py
            else:
                new_weights = prev_weights.copy()
                turnover = 0.0
                tradable_mask = {inst_id: True for inst_id in instrument_ids}
            
            costs = 0.0  # fees_bps=0, slippage_bps=0
            
            weights_series.append(new_weights)
            turnover_series.append(turnover)
            costs_series.append(costs)
            tradable_masks.append(tradable_mask)
            
            if i > 0:
                portfolio_ret = 0.0
                prev_day_weights = weights_series[i-1] if len(weights_series) > 0 else prev_weights
                if i < len(returns):
                    for inst_id, weight in prev_day_weights.items():
                        if inst_id in returns.columns and not pd.isna(returns.iloc[i][inst_id]):
                            portfolio_ret += weight * returns.iloc[i][inst_id]
                portfolio_returns.append(portfolio_ret)
            else:
                portfolio_returns.append(0.0)
        
        # Compute NAV
        portfolio_returns_series = pd.Series(portfolio_returns, index=calendar)
        nav = compute_nav(weights_series, returns, costs_series, portfolio_returns)
        
        # Compute drawdown
        running_max = nav.expanding().max()
        drawdown_series = (nav - running_max) / running_max
        
        # Compute metrics
        portfolio_metrics = compute_metrics(portfolio_returns_series, nav)
        
        # Validate results
        validation_errors = []
        
        if len(nav) < 30:
            validation_errors.append(f"NAV series too short: {len(nav)} (expected >= 30)")
        
        if abs(nav.iloc[0] - 100.0) > 1e-6:
            validation_errors.append(f"NAV[0] != 100: {nav.iloc[0]}")
        
        if portfolio_metrics.get("max_drawdown", 0) > 0:
            validation_errors.append(f"Max drawdown > 0: {portfolio_metrics.get('max_drawdown')}")
        
        if portfolio_metrics.get("variance_daily_return", -1) < 0:
            validation_errors.append(f"Variance < 0: {portfolio_metrics.get('variance_daily_return')}")
        
        # Check for NaN
        if nav.isna().any():
            validation_errors.append("NaN found in NAV series")
        
        if portfolio_returns_series.isna().any():
            validation_errors.append("NaN found in portfolio returns")
        
        if validation_errors:
            result["status"] = "FAIL"
            result["errors"].extend(validation_errors)
        else:
            result["details"].append(f"✓ NAV series length: {len(nav)}")
            result["details"].append(f"✓ NAV[0] = {nav.iloc[0]:.6f}")
            result["details"].append(f"✓ Max drawdown: {portfolio_metrics.get('max_drawdown', 0):.4f}")
            result["details"].append(f"✓ No NaN in series")
        
        # Store portfolio series
        portfolio_bars = []
        for i, current_date in enumerate(calendar):
            current_date_py = current_date.date()
            portfolio_bars.append({
                "date": current_date_py,
                "nav_base100": float(nav.iloc[i]),
                "portfolio_return": float(portfolio_returns_series.iloc[i]) if i < len(portfolio_returns_series) else 0.0,
                "drawdown": float(drawdown_series.iloc[i]),
                "turnover": float(turnover_series[i]),
                "costs": float(costs_series[i]),
                "weights_json": weights_series[i],
                "tradable_json": tradable_masks[i],
            })
        
        store_portfolio_series(db, run_id, portfolio_bars)
        
        # Store instrument series
        for inst in instruments:
            inst_id = inst["id"]
            if inst_id in returns.columns:
                inst_returns = returns[inst_id].fillna(0.0)
                inst_base100 = 100.0 * (1 + inst_returns).cumprod()
                
                inst_bars = []
                for i, current_date in enumerate(calendar):
                    inst_bars.append({
                        "date": current_date.date(),
                        "base100": float(inst_base100.iloc[i]),
                        "instrument_return": float(inst_returns.iloc[i]) if not pd.isna(inst_returns.iloc[i]) else None,
                    })
                
                store_instrument_series(db, run_id, inst_id, inst_bars)
        
        # Store metrics
        store_metrics(db, run_id, "portfolio", None, portfolio_metrics)
        
        for inst in instruments:
            inst_id = inst["id"]
            if inst_id in returns.columns:
                inst_returns = returns[inst_id].fillna(0.0)
                inst_base100 = 100.0 * (1 + inst_returns).cumprod()
                inst_metrics = compute_metrics(inst_returns, inst_base100)
                store_metrics(db, run_id, "instrument", inst_id, inst_metrics)
        
        # Update run status
        update_backtest_run_status(db, run_id, "SUCCESS")
        
        result["effective_start_date"] = effective_start.isoformat()
        result["effective_end_date"] = effective_end.isoformat()
        result["metrics"] = portfolio_metrics
        result["details"].append(f"✓ Backtest run {run_id} completed successfully")
        
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result
    
    except Exception as e:
        if "run_id" in result and result["run_id"]:
            try:
                update_backtest_run_status(db, result["run_id"], "FAILED", error_message=str(e))
            except:
                pass
        
        result["status"] = "FAIL"
        result["errors"].append(f"Unexpected error: {str(e)}")
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result


def check_api_endpoints() -> Dict[str, Any]:
    """
    CHECK 6: Verify API endpoints are accessible (using FastAPI TestClient)
    """
    start_time = time.time()
    result = {
        "check": "API Endpoints",
        "status": "PASS",
        "details": [],
        "errors": [],
    }
    
    try:
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        # Test market-data endpoint (should return 401 without auth, but endpoint exists)
        response = client.get("/api/market-data/instruments")
        if response.status_code in [200, 401]:  # 401 is expected without auth
            result["details"].append("✓ /api/market-data/instruments endpoint exists")
        else:
            result["status"] = "FAIL"
            result["errors"].append(f"Unexpected status for market-data: {response.status_code}")
        
        # Test backtests endpoint
        response = client.get("/api/backtests/instruments")
        if response.status_code in [200, 401]:
            result["details"].append("✓ /api/backtests/instruments endpoint exists")
        else:
            result["status"] = "FAIL"
            result["errors"].append(f"Unexpected status for backtests: {response.status_code}")
        
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result
    
    except Exception as e:
        result["status"] = "FAIL"
        result["errors"].append(f"Unexpected error: {str(e)}")
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        return result


def run_full_diagnostic(
    db: Session,
    mode: str = "quick",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Run all diagnostic checks and generate report
    """
    overall_start = time.time()
    
    # Get database name for report
    db_url = os.getenv("DATABASE_URL", "")
    dbname = "unknown"
    if db_url:
        try:
            parsed = urlparse(db_url)
            dbname = parsed.path.lstrip("/")
        except:
            pass
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "mode": mode,
        "database_name": dbname,
        "checks": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        },
        "total_duration_ms": 0,
    }
    
    # CHECK 1: Router availability
    check1 = check_router_availability()
    report["checks"].append(check1)
    
    # CHECK 2: Instruments exist
    check2 = check_instruments_exist(db)
    report["checks"].append(check2)
    
    # CHECK 3: Bars existence
    check3 = check_bars_existence(db)
    report["checks"].append(check3)
    
    # CHECK 4: Quick backfill (only if needed or mode=full)
    if check3["status"] == "FAIL" or mode == "full" or check3["total_bars"] == 0:
        check4 = check_quick_backfill(db, mode, start_date, end_date)
        report["checks"].append(check4)
        
        # After backfill, recheck bars with a fresh query (ensure commit is visible)
        db.commit()  # Ensure any pending commits are flushed
        db.expire_all()  # Expire all objects to force fresh queries
        check3_after = check_bars_existence(db)
        # Update check3 with new results if bars were added
        if check3_after["total_bars"] > check3["total_bars"]:
            check3 = check3_after
            # Replace check3 in report
            report["checks"][-2] = check3  # -2 because check4 was just appended
    else:
        # Recheck bars after potential seeding
        db.commit()  # Ensure any pending commits are flushed
        db.expire_all()  # Expire all objects to force fresh queries
        check3_after = check_bars_existence(db)
        if check3_after["total_bars"] == 0:
            check4 = check_quick_backfill(db, mode, start_date, end_date)
            report["checks"].append(check4)
            # After backfill, recheck again
            db.commit()
            db.expire_all()
            check3_final = check_bars_existence(db)
            if check3_final["total_bars"] > 0:
                check3 = check3_final
                report["checks"][-2] = check3  # Update check3
        else:
            check4 = {
                "check": "Quick Backfill",
                "status": "SKIP",
                "details": ["Skipped: sufficient bars exist"],
                "duration_ms": 0,
            }
            report["checks"].append(check4)
    
    # CHECK 5: Backtest run minimal
    check5 = check_backtest_run_minimal(db)
    report["checks"].append(check5)
    
    # CHECK 6: API endpoints
    check6 = check_api_endpoints()
    report["checks"].append(check6)
    
    # Summary
    for check in report["checks"]:
        report["summary"]["total"] += 1
        if check["status"] == "PASS":
            report["summary"]["passed"] += 1
        elif check["status"] == "FAIL":
            report["summary"]["failed"] += 1
        elif check["status"] == "SKIP":
            report["summary"]["skipped"] += 1
    
    report["total_duration_ms"] = int((time.time() - overall_start) * 1000)
    
    return report


def generate_markdown_report(report: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate Markdown report from diagnostic results
    """
    lines = []
    lines.append("# Diagnostic Market Data + Backtest")
    lines.append("")
    lines.append(f"**Date** : {report['timestamp']}")
    lines.append(f"**Mode** : {report['mode']}")
    lines.append(f"**Database** : {report.get('database_name', 'unknown')}")
    lines.append(f"**Duration** : {report['total_duration_ms']} ms")
    lines.append("")
    
    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| ✅ PASS | {report['summary']['passed']} |")
    lines.append(f"| ❌ FAIL | {report['summary']['failed']} |")
    lines.append(f"| ⏭️ SKIP | {report['summary']['skipped']} |")
    lines.append(f"| **Total** | **{report['summary']['total']}** |")
    lines.append("")
    
    # Checks detail
    lines.append("## Checks Detail")
    lines.append("")
    
    for i, check in enumerate(report['checks'], 1):
        status_icon = "✅" if check['status'] == 'PASS' else ("❌" if check['status'] == 'FAIL' else "⏭️")
        lines.append(f"### {i}. {check['check']} - {status_icon} {check['status']}")
        lines.append("")
        
        if check.get('details'):
            lines.append("**Details:**")
            for detail in check['details']:
                lines.append(f"- {detail}")
            lines.append("")
        
        if check.get('errors'):
            lines.append("**Errors:**")
            for error in check['errors']:
                lines.append(f"- ❌ {error}")
            lines.append("")
        
        if check.get('duration_ms'):
            lines.append(f"**Duration:** {check['duration_ms']} ms")
            lines.append("")
        
        # Additional data
        if check.get('count_before') is not None:
            lines.append(f"- Count before: {check['count_before']}")
        if check.get('count_after') is not None:
            lines.append(f"- Count after: {check['count_after']}")
        if check.get('seeded'):
            lines.append("- Instruments were seeded")
        
        if check.get('total_bars') is not None:
            lines.append(f"- Total bars: {check['total_bars']}")
        if check.get('date_min'):
            lines.append(f"- Date min: {check['date_min']}")
        if check.get('date_max'):
            lines.append(f"- Date max: {check['date_max']}")
        
        if check.get('instruments_detail'):
            lines.append("**Instruments detail:**")
            lines.append("")
            lines.append("| Symbol | Bars | Date Min | Date Max |")
            lines.append("|--------|------|----------|----------|")
            for inst in check['instruments_detail']:
                lines.append(f"| {inst['symbol']} | {inst['bars_count']} | {inst['date_min'] or 'N/A'} | {inst['date_max'] or 'N/A'} |")
            lines.append("")
        
        if check.get('backfilled_instruments'):
            lines.append("**Backfilled:**")
            for inst in check['backfilled_instruments']:
                lines.append(f"- {inst['symbol']}: {inst['bars_added']} bars added")
            lines.append("")
        
        if check.get('run_id'):
            lines.append(f"- Backtest Run ID: {check['run_id']}")
        if check.get('effective_start_date'):
            lines.append(f"- Effective start: {check['effective_start_date']}")
        if check.get('effective_end_date'):
            lines.append(f"- Effective end: {check['effective_end_date']}")
        if check.get('metrics'):
            lines.append("**Metrics:**")
            metrics = check['metrics']
            lines.append(f"- CAGR: {metrics.get('cagr', 0) * 100:.2f}%")
            lines.append(f"- Volatility: {metrics.get('volatility', 0) * 100:.2f}%")
            lines.append(f"- Sharpe: {metrics.get('sharpe', 0):.2f}")
            lines.append(f"- Max Drawdown: {metrics.get('max_drawdown', 0) * 100:.2f}%")
            lines.append(f"- Calmar: {metrics.get('calmar', 0):.2f}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    
    has_failures = report['summary']['failed'] > 0
    has_warnings = any('⚠' in str(check.get('details', [])) for check in report['checks'])
    
    if not has_failures and not has_warnings:
        lines.append("✅ All checks passed. System is ready for use.")
    else:
        if has_failures:
            lines.append("❌ **Action required:** Some checks failed. Please review errors above.")
        if has_warnings:
            lines.append("⚠️ **Warnings:** Some checks have warnings. Review details above.")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated at {report['timestamp']}*")
    
    markdown = "\n".join(lines)
    
    # Write to file if path provided
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
    
    return markdown

