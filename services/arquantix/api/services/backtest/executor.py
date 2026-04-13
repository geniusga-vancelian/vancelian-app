"""
Backtest executor - Execute backtest runs
"""
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session
import numpy as np

from services.backtest.repository import (
    load_instruments, load_open_bars,
    update_backtest_run_status, store_portfolio_series, store_instrument_series, store_metrics
)


def execute_backtest(db: Session, run_id: int, instrument_ids: List[int], start_date: date, end_date: date,
                     strategy_type: str, rebalance: str, fees_bps: float, slippage_bps: float,
                     allow_weekend_trading: bool, bundle_allocations: Optional[Dict[int, float]] = None,
                     strategy_params_json: Optional[Dict] = None) -> None:
    """
    Execute a backtest run
    
    This is a simplified implementation that:
    1. Loads price data from market_data_bars_d1
    2. Computes equal-weight portfolio (or momentum if specified)
    3. Computes NAV series
    4. Stores results in database
    """
    try:
        # Update status to RUNNING
        update_backtest_run_status(db, run_id, "RUNNING")
        
        # Load instruments
        instruments = load_instruments(db, instrument_ids)
        if not instruments:
            update_backtest_run_status(db, run_id, "FAILED", "No instruments found")
            return
        
        # Load price data from market_data_bars_d1
        price_data = load_open_bars(db, instrument_ids, start_date, end_date)
        
        if not price_data:
            update_backtest_run_status(db, run_id, "FAILED", "No price data found for instruments in date range")
            return
        
        # Check if we have data for all instruments
        missing_instruments = [inst.id for inst in instruments if inst.id not in price_data or price_data[inst.id].empty]
        if missing_instruments:
            missing_symbols = [inst.symbol for inst in instruments if inst.id in missing_instruments]
            update_backtest_run_status(db, run_id, "FAILED", f"No price data found for instruments: {', '.join(missing_symbols)}")
            return
        
        # Build calendar from available dates
        all_dates = set()
        for df in price_data.values():
            all_dates.update(df.index)
        
        calendar = sorted([d.date() if isinstance(d, pd.Timestamp) else d for d in all_dates])
        
        if not calendar:
            update_backtest_run_status(db, run_id, "FAILED", "No dates in calendar")
            return
        
        # Filter calendar by date range
        calendar = [d for d in calendar if start_date <= d <= end_date]
        
        # Filter out weekends if needed
        if not allow_weekend_trading:
            calendar = [d for d in calendar if d.weekday() < 5]
        
        if not calendar:
            update_backtest_run_status(db, run_id, "FAILED", "No trading dates in calendar after filtering")
            return
        
        effective_start = calendar[0]
        effective_end = calendar[-1]
        
        # Create aligned price DataFrames (close prices)
        aligned_prices = {}
        for instrument_id, df in price_data.items():
            # Reindex to calendar, forward fill missing values
            df_aligned = df.reindex(pd.DatetimeIndex(calendar))
            df_aligned = df_aligned.ffill()  # Forward fill (pandas 2.0+ syntax)
            aligned_prices[instrument_id] = df_aligned['close']
        
        # Combine into single DataFrame (instruments as columns)
        prices_df = pd.DataFrame(aligned_prices, index=pd.DatetimeIndex(calendar))
        prices_df = prices_df.ffill().bfill()  # Forward then backward fill (pandas 2.0+ syntax)
        
        # Compute returns
        returns_df = prices_df.pct_change().fillna(0)
        
        # CPPI strategy
        if strategy_type == "CPPI":
            from services.backtest.strategies.cppi import run_cppi_backtest
            from services.bundles.resolver import resolve_bundle_effective_weights
            from services.bundles.errors import BundleValidationError
            from database import MarketDataBundle
            
            # Parse CPPI params
            params = strategy_params_json or {}
            floor_ratio = params.get('floor_ratio', 0.90)
            multiplier = params.get('multiplier', 4.0)
            risky_cap = params.get('risky_cap', 1.0)
            core_min = params.get('core_min', 0.0)
            core_yield = params.get('core_yield', 0.035)
            day_count = params.get('day_count', 365)
            
            # Get bundle_id from run (stored in backtest_run)
            from database import BacktestRun
            backtest_run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
            bundle_id = backtest_run.bundle_id if backtest_run else None
            
            # Create weights resolver
            def weights_resolver(d: date) -> Dict[int, float]:
                if bundle_id:
                    # Bundle: use resolver to get effective weights for date
                    try:
                        bundle_id_int = int(bundle_id) if isinstance(bundle_id, str) else bundle_id
                        weights = resolve_bundle_effective_weights(db, bundle_id_int, d)
                        # Resolver already validates: all weights > 0, sum == 1.0
                        return weights
                    except BundleValidationError as e:
                        # Re-raise BundleValidationError to be caught by executor
                        raise
                    except Exception as e:
                        # Wrap other errors
                        raise ValueError(f"Failed to resolve bundle {bundle_id} weights at date {d}: {str(e)}")
                else:
                    # No bundle: equal weight across instrument_ids
                    if not instrument_ids or len(instrument_ids) == 0:
                        raise ValueError("No instrument_ids provided for CPPI")
                    n = len(instrument_ids)
                    if n == 0:
                        raise ValueError("Empty instrument_ids list")
                    equal_weight = 1.0 / n
                    weights = {inst_id: equal_weight for inst_id in instrument_ids}
                    # Validate sum
                    total = sum(weights.values())
                    if abs(total - 1.0) > 1e-6:
                        raise ValueError(f"Equal weights sum to {total:.6f}, expected 1.0")
                    return weights
            
            # Validate that bundle instrument_ids match prices_df columns
            if bundle_id:
                # Get bundle weights to check instrument_ids
                try:
                    sample_weights = weights_resolver(effective_start)
                    bundle_inst_ids = set(sample_weights.keys())
                    prices_inst_ids = set(prices_df.columns)
                    missing_ids = bundle_inst_ids - prices_inst_ids
                    if missing_ids:
                        raise ValueError(
                            f"Bundle {bundle_id} contains instrument_ids {missing_ids} that are not in prices_df. "
                            f"Available instrument_ids in prices_df: {sorted(prices_inst_ids)}"
                        )
                except BundleValidationError as e:
                    # Bundle validation error: return clear error message
                    error_msg = f"Invalid bundle allocation: {e.message}. Weights must sum to 100% (or 1.0) and be > 0."
                    update_backtest_run_status(db, run_id, "FAILED", error_msg)
                    raise ValueError(error_msg)
                except Exception as e:
                    # If resolver fails with other error, let CPPI handle it
                    pass
            
            # Run CPPI
            try:
                # Enable debug if strategy_params_json has debug flag
                debug_mode = (strategy_params_json or {}).get('debug', False)
                
                result = run_cppi_backtest(
                    prices_df=prices_df,
                    weights_resolver=weights_resolver,
                    start_date=effective_start,
                    end_date=effective_end,
                    initial_capital=100.0,  # Base 100
                    rebalance_frequency=rebalance,
                    fees_bps=fees_bps,
                    slippage_bps=slippage_bps,
                    floor_ratio=floor_ratio,
                    multiplier=multiplier,
                    risky_cap=risky_cap,
                    core_min=core_min,
                    core_yield=core_yield,
                    day_count=day_count,
                    debug=debug_mode,
                )
                
                # Store results
                store_portfolio_series(db, run_id, result['portfolio_series'])
                store_instrument_series(db, run_id, result['instrument_series'])
                store_metrics(db, run_id, result['metrics'])
                
                # Update status to SUCCESS
                update_backtest_run_status(db, run_id, "SUCCESS", None, effective_start, effective_end)
                return
            except BundleValidationError as e:
                # Bundle validation error: return clear error message
                error_msg = f"Invalid bundle allocation: {e.message}. Weights must sum to 100% (or 1.0) and be > 0."
                update_backtest_run_status(db, run_id, "FAILED", error_msg)
                raise ValueError(error_msg)
        
        # Core-Satellite strategy
        if strategy_type == "CORE_SATELLITE":
            from services.backtest.strategies.core_satellite import run_core_satellite_backtest
            from database import BacktestRun
            
            # Parse Core-Satellite params (V1 + V2 + V2.1)
            params = strategy_params_json or {}
            core_yield = params.get('core_yield', 0.035)
            target_te = params.get('target_te', 0.10)
            te_tolerance = params.get('te_tolerance', 0.0025)
            te_max_hard_mult = params.get('te_max_hard_mult', 1.10)
            lookback_risk_days = params.get('lookback_risk_days', 63)
            lookback_return_days = params.get('lookback_return_days', 63)
            day_count = params.get('day_count', 252)
            core_min = params.get('core_min', 0.0)
            max_weight_per_asset = params.get('max_weight_per_asset', 0.40)
            core_grid_step = params.get('core_grid_step', 0.01)
            top_k_satellite = params.get('top_k_satellite')
            # V2 params (optional, defaults maintain V1 behavior)
            sat_min = params.get('sat_min', 0.0)
            shrinkage = params.get('shrinkage', False)
            turnover_penalty = params.get('turnover_penalty', 0.0)
            stability_penalty = params.get('stability_penalty', 0.0)
            optimization_method = params.get('optimization_method', 'grid')  # 'grid' (V1) or 'quadratic' (V2)
            # V2.1 EDHEC-style allocation params
            allocation_mode = params.get('allocation_mode', 'te_target')
            lambda_risk = params.get('lambda_risk', 0.2)
            multiplier = params.get('multiplier', 4.0)
            floor_rel_ratio = params.get('floor_rel_ratio', 0.95)
            floor_accrues_with_core = params.get('floor_accrues_with_core', True)
            sat_max = params.get('sat_max')  # None means 1 - core_min
            debug = params.get('debug', False)
            
            # Get bundle_id from run (if present)
            backtest_run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
            bundle_id = backtest_run.bundle_id if backtest_run else None
            
            # If bundle_id is present, use bundle instrument_ids as universe (ignore weights)
            # Bundle in Core-Satellite means "universe definition", not allocation constraint
            if bundle_id:
                from services.bundles.resolver import resolve_bundle_effective_weights
                try:
                    # Get bundle instrument_ids from resolver (use first date as sample)
                    bundle_id_int = int(bundle_id) if isinstance(bundle_id, str) else bundle_id
                    sample_weights = resolve_bundle_effective_weights(db, bundle_id_int, effective_start)
                    instrument_ids = list(sample_weights.keys())  # Use bundle constituents as universe
                except Exception as e:
                    # If resolver fails, fall back to instrument_ids from request
                    pass
            
            # Validate instrument_ids
            if not instrument_ids or len(instrument_ids) == 0:
                error_msg = "No instrument_ids provided for CORE_SATELLITE (bundle or manual selection required)"
                update_backtest_run_status(db, run_id, "FAILED", error_msg)
                raise ValueError(error_msg)
            
            # Validate all instrument_ids exist in prices_df
            prices_inst_ids = set(prices_df.columns)
            missing_ids = set(instrument_ids) - prices_inst_ids
            if missing_ids:
                error_msg = f"CORE_SATELLITE instrument_ids {missing_ids} not found in prices_df. Available: {sorted(prices_inst_ids)}"
                update_backtest_run_status(db, run_id, "FAILED", error_msg)
                raise ValueError(error_msg)
            
            # Run Core-Satellite
            try:
                result = run_core_satellite_backtest(
                    prices_df=prices_df,
                    instrument_ids=instrument_ids,
                    start_date=effective_start,
                    end_date=effective_end,
                    initial_capital=100.0,  # Base 100
                    rebalance_frequency=rebalance,
                    fees_bps=fees_bps,
                    slippage_bps=slippage_bps,
                    core_yield=core_yield,
                    target_te=target_te,
                    te_tolerance=te_tolerance,
                    te_max_hard_mult=te_max_hard_mult,
                    lookback_risk_days=lookback_risk_days,
                    lookback_return_days=lookback_return_days,
                    day_count=day_count,
                    core_min=core_min,
                    max_weight_per_asset=max_weight_per_asset,
                    core_grid_step=core_grid_step,
                    top_k_satellite=top_k_satellite,
                    sat_min=sat_min,  # V2
                    shrinkage=shrinkage,  # V2
                    turnover_penalty=turnover_penalty,  # V2
                    stability_penalty=stability_penalty,  # V2
                    optimization_method=optimization_method,  # V2
                    allocation_mode=allocation_mode,  # V2.1
                    lambda_risk=lambda_risk,  # V2.1
                    multiplier=multiplier,  # V2.1
                    floor_rel_ratio=floor_rel_ratio,  # V2.1
                    floor_accrues_with_core=floor_accrues_with_core,  # V2.1
                    sat_max=sat_max,  # V2.1
                    debug=debug,
                )
                
                # Store results
                store_portfolio_series(db, run_id, result['portfolio_series'])
                store_instrument_series(db, run_id, result['instrument_series'])
                store_metrics(db, run_id, result['metrics'])
                
                # Update status to SUCCESS
                update_backtest_run_status(db, run_id, "SUCCESS", None, effective_start, effective_end)
                return
            except Exception as e:
                error_msg = f"CORE_SATELLITE backtest failed: {str(e)}"
                update_backtest_run_status(db, run_id, "FAILED", error_msg)
                raise ValueError(error_msg)
        
        # Compute strategy weights
        if strategy_type == "bundle_strategy" and bundle_allocations:
            # Bundle strategy: use fixed allocations from bundle (in percentage 0-100)
            # Convert percentages to decimal weights (0-1)
            # Allocations should already sum to 100%, so we divide by 100 to get weights
            bundle_weights = {}
            total_allocation = sum(bundle_allocations.values()) if bundle_allocations else 0.0
            
            if total_allocation > 0:
                # Normalize: allocations are in percentage (0-100), convert to decimal (0-1)
                # If total is exactly 100%, each allocation / 100 gives the weight
                # If total is not 100%, normalize to sum to 1
                for inst_id in instrument_ids:
                    allocation_pct = bundle_allocations.get(inst_id, 0.0)
                    if abs(total_allocation - 100.0) < 0.01:  # Already normalized to 100%
                        bundle_weights[inst_id] = allocation_pct / 100.0
                    else:
                        # Normalize to sum to 1 (handle case where total != 100%)
                        bundle_weights[inst_id] = allocation_pct / total_allocation
            else:
                # Fallback to equal weight if no allocations defined
                target_weight = 1.0 / len(instrument_ids) if len(instrument_ids) > 0 else 0.0
                bundle_weights = {inst_id: target_weight for inst_id in instrument_ids}
            
            # Create DataFrame with fixed weights for all dates (bundle strategy is static)
            weights_df = pd.DataFrame(
                {inst_id: bundle_weights.get(inst_id, 0.0) for inst_id in instrument_ids},
                index=prices_df.index
            )
        elif strategy_type == "equal_weight":
            # Equal weight: 1/n for each instrument
            n_instruments = len(instrument_ids)
            target_weight = 1.0 / n_instruments if n_instruments > 0 else 0.0
            weights_df = pd.DataFrame(
                {inst_id: target_weight for inst_id in instrument_ids},
                index=prices_df.index
            )
        elif strategy_type == "momentum":
            # Momentum: weight by past returns (simple momentum)
            lookback = 20  # 20 days lookback
            momentum = returns_df.rolling(window=lookback, min_periods=1).mean()
            # Normalize to sum to 1 (long-only)
            momentum = momentum.clip(lower=0)  # Only positive momentum
            row_sums = momentum.sum(axis=1)
            weights_df = momentum.div(row_sums, axis=0).fillna(1.0 / len(instrument_ids))
        else:
            # Default to equal weight
            n_instruments = len(instrument_ids)
            target_weight = 1.0 / n_instruments if n_instruments > 0 else 0.0
            weights_df = pd.DataFrame(
                {inst_id: target_weight for inst_id in instrument_ids},
                index=prices_df.index
            )
        
        # Rebalance based on frequency
        if rebalance == "daily":
            # Already daily, no change
            pass
        elif rebalance == "weekly":
            # Only rebalance on Mondays
            weekly_weights = weights_df.resample('W-MON').first()
            weights_df = weekly_weights.reindex(weights_df.index).ffill()
        elif rebalance == "monthly":
            # Only rebalance on first trading day of month
            monthly_rebalance = weights_df.resample('MS').first()
            weights_df = monthly_rebalance.reindex(weights_df.index).ffill()
        
        # Compute portfolio returns
        portfolio_returns = (weights_df.shift(1) * returns_df).sum(axis=1).fillna(0)
        
        # Apply fees and slippage (on rebalancing days)
        fees_per_trade = fees_bps / 10000.0
        slippage_per_trade = slippage_bps / 10000.0
        
        # Detect rebalancing: weight changes
        weight_changes = weights_df.diff().abs().sum(axis=1)
        rebalance_days = weight_changes > 0.001  # Threshold for rebalancing
        
        # Apply costs
        costs = pd.Series(0.0, index=portfolio_returns.index)
        costs[rebalance_days] = fees_per_trade + slippage_per_trade
        portfolio_returns = portfolio_returns - costs
        
        # Compute NAV (cumulative product)
        nav_series = (1 + portfolio_returns).cumprod()
        nav_base100 = nav_series * 100.0 / nav_series.iloc[0] if len(nav_series) > 0 else pd.Series([100.0])
        
        # Compute drawdown
        running_max = nav_base100.cummax()
        drawdown = (nav_base100 - running_max) / running_max * 100.0
        
        # Compute turnover
        turnover = weight_changes * 100.0
        
        # Prepare portfolio series
        portfolio_series = []
        for i, (idx, row) in enumerate(nav_base100.items()):
            date_val = idx.date() if isinstance(idx, pd.Timestamp) else idx
            # Handle NaN values in weights: convert to None (null in JSON)
            weights_dict = {}
            for k, v in weights_df.loc[idx].items():
                val = float(v) if not pd.isna(v) else None
                if val is not None and (np.isnan(val) or np.isinf(val)):
                    val = None
                weights_dict[str(k)] = val
            
            portfolio_series.append({
                'date': date_val,
                'nav_base100': float(nav_base100.iloc[i]) if not pd.isna(nav_base100.iloc[i]) else 100.0,
                'portfolio_return': float(portfolio_returns.iloc[i]) * 100.0 if not pd.isna(portfolio_returns.iloc[i]) else 0.0,  # In percentage
                'drawdown': float(drawdown.iloc[i]) if not pd.isna(drawdown.iloc[i]) else 0.0,
                'turnover': float(turnover.iloc[i]) if not pd.isna(turnover.iloc[i]) else 0.0,
                'costs': float(costs.iloc[i]) * 100.0 if not pd.isna(costs.iloc[i]) else 0.0,  # In percentage
                'weights_json': weights_dict,
                'tradable_json': {str(k): True for k in instrument_ids},  # Simplified: all tradable
            })
        
        # Prepare instrument series (base100 for each instrument)
        instrument_series = {}
        for instrument_id in instrument_ids:
            inst_prices = prices_df[instrument_id]
            inst_base100 = inst_prices / inst_prices.iloc[0] * 100.0 if len(inst_prices) > 0 else pd.Series([100.0])
            inst_returns = returns_df[instrument_id] * 100.0  # In percentage
            
            instrument_series[instrument_id] = []
            for i, (idx, price) in enumerate(inst_prices.items()):
                date_val = idx.date() if isinstance(idx, pd.Timestamp) else idx
                base100_val = float(inst_base100.iloc[i]) if i < len(inst_base100) and not pd.isna(inst_base100.iloc[i]) else 100.0
                return_val = float(inst_returns.iloc[i]) if i < len(inst_returns) and not pd.isna(inst_returns.iloc[i]) else 0.0
                
                # Check for NaN or inf and replace with defaults
                if np.isnan(base100_val) or np.isinf(base100_val):
                    base100_val = 100.0
                if np.isnan(return_val) or np.isinf(return_val):
                    return_val = 0.0
                
                instrument_series[instrument_id].append({
                    'date': date_val,
                    'base100': base100_val,
                    'instrument_return': return_val,
                })
        
        # Compute basic metrics
        total_return = (nav_base100.iloc[-1] / nav_base100.iloc[0] - 1) * 100.0 if len(nav_base100) > 0 else 0.0
        annualized_return = (1 + total_return / 100.0) ** (252.0 / len(calendar)) - 1 if len(calendar) > 0 else 0.0
        annualized_return_pct = annualized_return * 100.0
        
        volatility = portfolio_returns.std() * np.sqrt(252) * 100.0  # Annualized volatility
        sharpe = (annualized_return_pct / volatility) if volatility > 0 else 0.0
        
        max_drawdown = drawdown.min()
        
        metrics = {
            'portfolio': {
                'total_return': total_return,
                'annualized_return': annualized_return_pct,
                'volatility': volatility,
                'sharpe_ratio': sharpe,
                'max_drawdown': float(max_drawdown),
            },
            'instruments': {}
        }
        
        # Store results
        store_portfolio_series(db, run_id, portfolio_series)
        store_instrument_series(db, run_id, instrument_series)
        store_metrics(db, run_id, metrics)
        
        # Update status to SUCCESS
        update_backtest_run_status(db, run_id, "SUCCESS", None, effective_start, effective_end)
        
    except Exception as e:
        import traceback
        error_msg = f"Backtest execution failed: {str(e)}\n{traceback.format_exc()}"
        update_backtest_run_status(db, run_id, "FAILED", error_msg)
        raise
