"""
Core-Satellite Strategy v1.0 / v2.0

Strategy that targets a tracking error (TE) vs Core benchmark while maximizing expected excess return.

Core-Satellite splits portfolio into:
- Core: synthetic fixed-yield accrual (like CPPI core_yield)
- Satellite: optimized risky assets (weights optimized to target TE)

Benchmark = Core only (same as CPPI simplification).

V2 improvements (optional, via optimization_method="quadratic"):
- Quadratic optimization for satellite weights
- Ledoit-Wolf shrinkage for covariance matrix
- Turnover/stability penalties
- Enhanced reporting
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional, Tuple
from datetime import date, timedelta
import warnings


def run_core_satellite_backtest(
    prices_df: pd.DataFrame,  # Index: date, Columns: instrument_id
    instrument_ids: List[int],  # Universe of instruments (bundle constituents or manually selected)
    start_date: date,
    end_date: date,
    initial_capital: float,
    rebalance_frequency: str,  # "daily", "weekly", "monthly"
    fees_bps: float,
    slippage_bps: float,
    core_yield: float = 0.035,
    target_te: float = 0.10,
    te_tolerance: float = 0.0025,
    te_max_hard_mult: float = 1.10,
    lookback_risk_days: int = 63,
    lookback_return_days: int = 63,
    day_count: int = 252,
    core_min: float = 0.0,
    max_weight_per_asset: float = 0.40,
    core_grid_step: float = 0.01,
    top_k_satellite: Optional[int] = None,
    sat_min: float = 0.0,  # V2: minimum satellite weight
    shrinkage: bool = False,  # V2: enable Ledoit-Wolf shrinkage
    turnover_penalty: float = 0.0,  # V2: penalty for turnover
    stability_penalty: float = 0.0,  # V2: penalty for weight changes
    optimization_method: str = "grid",  # V2: "grid" (V1) or "quadratic" (V2)
    # V2.1 EDHEC-style allocation modes
    allocation_mode: str = "te_target",  # "te_target", "utility_lambda", "dynamic_cushion"
    lambda_risk: float = 0.2,  # Risk aversion for utility_lambda mode
    multiplier: float = 4.0,  # Multiplier for dynamic_cushion mode
    floor_rel_ratio: float = 0.95,  # Relative floor ratio for dynamic_cushion
    floor_accrues_with_core: bool = True,  # Whether floor accrues with core_yield
    sat_max: Optional[float] = None,  # Maximum satellite weight (default: 1 - core_min)
    debug: bool = False,
) -> Dict:
    """
    Run Core-Satellite backtest
    
    Returns dict with:
    - portfolio_series: List[Dict] with nav, core_weight, te_realized, te_pred, core_nav_base100
    - instrument_series: Dict[instrument_id, List[Dict]]
    - metrics: Dict
    """
    # Validate inputs
    if target_te <= 0 or target_te > 1:
        raise ValueError(f"target_te must be in (0, 1], got {target_te}")
    if lookback_risk_days < 5 or lookback_return_days < 5:
        raise ValueError(f"lookback_*_days must be >= 5")
    if core_min < 0 or core_min > 1:
        raise ValueError(f"core_min must be in [0, 1], got {core_min}")
    if max_weight_per_asset <= 0 or max_weight_per_asset > 1:
        raise ValueError(f"max_weight_per_asset must be in (0, 1], got {max_weight_per_asset}")
    if not instrument_ids or len(instrument_ids) == 0:
        raise ValueError("instrument_ids must be provided and non-empty")
    
    # Calendar
    calendar = sorted([d.date() if isinstance(d, pd.Timestamp) else d for d in prices_df.index if start_date <= (d.date() if isinstance(d, pd.Timestamp) else d) <= end_date])
    
    if not calendar:
        raise ValueError("No dates in calendar")
    
    # Filter prices_df to only include instrument_ids that exist
    available_inst_ids = [inst_id for inst_id in instrument_ids if inst_id in prices_df.columns]
    if not available_inst_ids:
        raise ValueError(f"None of the provided instrument_ids {instrument_ids} exist in prices_df columns {list(prices_df.columns)}")
    if len(available_inst_ids) < len(instrument_ids):
        missing = set(instrument_ids) - set(available_inst_ids)
        warnings.warn(f"Some instrument_ids {missing} are not in prices_df, ignoring them")
    
    instrument_ids = available_inst_ids
    prices_df = prices_df[instrument_ids].copy()
    
    # Rebalance dates
    rebalance_dates = set()
    if rebalance_frequency == "daily":
        rebalance_dates = set(calendar)
    elif rebalance_frequency == "weekly":
        for d in calendar:
            if d.weekday() == 0:  # Monday
                rebalance_dates.add(d)
        if calendar and calendar[0] not in rebalance_dates:
            rebalance_dates.add(calendar[0])
    elif rebalance_frequency == "monthly":
        current_month = None
        for d in calendar:
            if current_month is None or d.month != current_month:
                rebalance_dates.add(d)
                current_month = d.month
    else:
        rebalance_dates = set(calendar)
    
    rebalance_dates = sorted(rebalance_dates)
    
    # Compute returns
    returns_df = prices_df.pct_change().fillna(0)
    
    # Core daily growth factor
    core_daily_growth = (1 + core_yield) ** (1.0 / day_count)
    core_daily_return = core_daily_growth - 1
    
    # State
    portfolio_nav = initial_capital
    core_weight = 1.0  # Start 100% core
    satellite_weights = {inst_id: 0.0 for inst_id in instrument_ids}
    core_nav = initial_capital
    last_rebalance_date = None
    
    # V2.1: State for dynamic_cushion mode
    rel_index = 1.0  # Relative performance index (portfolio vs core)
    rel_floor = floor_rel_ratio  # Relative floor (starts at floor_rel_ratio)
    
    # Storage
    portfolio_series = []
    instrument_series = {inst_id: [] for inst_id in instrument_ids}
    debug_log = []  # Debug output
    
    # For TE calculation
    portfolio_returns_list = []
    core_returns_list = []
    
    # Daily loop
    for i, current_date in enumerate(calendar):
        date_ts = pd.Timestamp(current_date)
        
        # Get prices for this date
        current_prices = prices_df.loc[date_ts] if date_ts in prices_df.index else None
        
        # Check if rebalance day
        should_rebalance = current_date in rebalance_dates
        prices_available = True
        missing_instruments = []
        
        if should_rebalance and i > 0:
            # Check prices available
            if current_prices is None:
                prices_available = False
            else:
                for inst_id in instrument_ids:
                    if inst_id not in current_prices.index or pd.isna(current_prices[inst_id]) or current_prices[inst_id] <= 0:
                        prices_available = False
                        missing_instruments.append(inst_id)
            
            if not prices_available:
                # Skip rebalance, keep last weights
                if debug:
                    debug_log.append({
                        'date': current_date.isoformat(),
                        'event': 'rebalance_skipped',
                        'reason': 'missing_prices',
                        'missing_instruments': missing_instruments,
                        'nav': float(portfolio_nav),
                    })
            else:
                # Rebalance: optimize weights
                try:
                    # Get historical data up to (and including) current_date
                    hist_end_idx = calendar.index(current_date) + 1
                    hist_start_idx = max(0, hist_end_idx - max(lookback_risk_days, lookback_return_days))
                    hist_dates = calendar[hist_start_idx:hist_end_idx]
                    
                    if len(hist_dates) < 5:
                        # Not enough history, skip optimization
                        if debug:
                            debug_log.append({
                                'date': current_date.isoformat(),
                                'event': 'rebalance_skipped',
                                'reason': 'insufficient_history',
                                'nav': float(portfolio_nav),
                            })
                    else:
                        # Get historical prices/returns
                        hist_prices = prices_df.loc[pd.DatetimeIndex(hist_dates)]
                        hist_returns = returns_df.loc[pd.DatetimeIndex(hist_dates)]
                        
                        # V2.1: Build unit satellite portfolio (w_unit sums to 1)
                        previous_satellite_weights_unit = {inst_id: sat_weight / (1 - core_weight) if (1 - core_weight) > 1e-6 else 0.0 for inst_id, sat_weight in satellite_weights.items()} if core_weight < 1.0 - 1e-6 else {inst_id: 0.0 for inst_id in instrument_ids}
                        
                        w_unit_result = build_unit_satellite_portfolio(
                            hist_returns=hist_returns,
                            core_daily_return=core_daily_return,
                            lookback_risk_days=lookback_risk_days,
                            lookback_return_days=lookback_return_days,
                            day_count=day_count,
                            max_weight_per_asset=max_weight_per_asset,
                            top_k_satellite=top_k_satellite,
                            shrinkage=shrinkage,
                            turnover_penalty=turnover_penalty,
                            stability_penalty=stability_penalty,
                            optimization_method=optimization_method,
                            previous_satellite_weights=previous_satellite_weights_unit,
                            instrument_ids=instrument_ids,
                        )
                        
                        w_unit = w_unit_result['w_unit']  # Dict[instrument_id, float], sums to 1.0
                        te_sat = w_unit_result['te_sat']  # Annualized TE for unit portfolio
                        ir_sat = w_unit_result['ir_sat']  # IR for unit portfolio
                        cov_matrix_use = w_unit_result.get('cov_matrix_shrunk') if shrinkage else w_unit_result['cov_matrix']
                        
                        # V2.1: Compute scalar satellite weight w using allocation_mode
                        # Default sat_max
                        sat_max_computed = sat_max if sat_max is not None else (1.0 - core_min)
                        
                        w_scalar, alloc_metadata = compute_scalar_satellite_weight(
                            w_unit_result=w_unit_result,
                            allocation_mode=allocation_mode,
                            target_te=target_te,
                            lambda_risk=lambda_risk,
                            multiplier=multiplier,
                            sat_min=sat_min,
                            sat_max=sat_max_computed,
                            rel_index=rel_index,
                            rel_floor=rel_floor,
                            core_daily_return=core_daily_return,
                            day_count=day_count,
                            te_max_hard_mult=te_max_hard_mult,
                        )
                        
                        # Apply scalar: final satellite weights = w_scalar * w_unit
                        new_satellite_weights = {inst_id: w_scalar * w_unit.get(inst_id, 0.0) for inst_id in instrument_ids}
                        
                        # Core weight = 1 - w_scalar, but enforce core_min
                        new_core_weight = max(1.0 - w_scalar, core_min)
                        
                        # If core_min forces core_weight up, reduce satellite accordingly
                        if new_core_weight > 1.0 - w_scalar:
                            actual_sat_weight = 1.0 - new_core_weight
                            if actual_sat_weight < 1e-6:
                                new_satellite_weights = {inst_id: 0.0 for inst_id in instrument_ids}
                            else:
                                # Scale down satellite weights proportionally
                                scale = actual_sat_weight / w_scalar if w_scalar > 1e-6 else 0.0
                                new_satellite_weights = {inst_id: scale * new_satellite_weights.get(inst_id, 0.0) for inst_id in instrument_ids}
                            w_scalar = actual_sat_weight
                        
                        # Compute predicted TE for final portfolio
                        w_sat_vector = np.array([new_satellite_weights.get(inst_id, 0.0) for inst_id in instrument_ids])
                        if len(w_sat_vector) > 0 and cov_matrix_use.size > 0:
                            te_pred = float(np.sqrt(w_sat_vector @ cov_matrix_use @ w_sat_vector))
                        else:
                            te_pred = 0.0
                        
                        te_pred_shrunk = te_pred if shrinkage else None
                        optimization_score = None  # Not available with V2.1 approach
                        
                        # Compute turnover (based on unit portfolio changes if available, else use absolute changes)
                        satellite_turnover = sum(abs(new_satellite_weights.get(inst_id, 0.0) - satellite_weights.get(inst_id, 0.0)) for inst_id in instrument_ids) / 2.0
                        portfolio_turnover = abs(new_core_weight - core_weight) + satellite_turnover
                        
                        # Apply transaction costs
                        if last_rebalance_date is not None:
                            cost_amount = portfolio_turnover * (fees_bps + slippage_bps) / 10000.0 * portfolio_nav
                            portfolio_nav = portfolio_nav - cost_amount
                        else:
                            cost_amount = 0.0
                        
                        # Update weights
                        core_weight = new_core_weight
                        satellite_weights = new_satellite_weights.copy()
                        last_rebalance_date = current_date
                        
                        # Store V2.1 metadata for debug log
                        v2_1_metadata = {
                            'alloc_mode': allocation_mode,
                            'w_scalar': float(w_scalar),
                            'te_sat': float(te_sat),
                            'ir_sat': float(ir_sat) if ir_sat is not None and not np.isnan(ir_sat) else None,
                        }
                        if allocation_mode == "dynamic_cushion":
                            cushion = max(rel_index - rel_floor, 0.0)
                            v2_1_metadata.update({
                                'rel_index': float(rel_index),
                                'rel_floor': float(rel_floor),
                                'cushion': float(cushion),
                            })
                        
                        if debug:
                            debug_log.append({
                                'date': current_date.isoformat(),
                                'event': 'rebalance',
                                'core_weight': float(core_weight),
                                'satellite_weights': {str(k): float(v) for k, v in satellite_weights.items()},
                                'te_pred': float(te_pred),
                                'te_pred_shrunk': float(te_pred_shrunk) if te_pred_shrunk is not None else None,
                                'optimization_score': float(optimization_score) if optimization_score is not None else None,
                                'satellite_turnover': float(satellite_turnover),
                                'portfolio_turnover': float(portfolio_turnover),
                                'nav': float(portfolio_nav),
                                'cost': float(cost_amount),
                                **v2_1_metadata,
                            })
                        
                except Exception as e:
                    # Optimization failed, skip rebalance
                    if debug:
                        debug_log.append({
                            'date': current_date.isoformat(),
                            'event': 'rebalance_skipped',
                            'reason': f'optimization_error: {str(e)}',
                            'nav': float(portfolio_nav),
                        })
        
        # Compute portfolio return for this day (BEFORE updating NAV)
        # Portfolio return = core_weight * core_return + sum(satellite_weights * instrument_returns)
        portfolio_return = core_weight * core_daily_return
        
        if current_prices is not None:
            for inst_id in instrument_ids:
                if inst_id in current_prices.index and not pd.isna(current_prices[inst_id]) and inst_id in satellite_weights:
                    inst_return = returns_df.loc[date_ts, inst_id] if date_ts in returns_df.index else 0.0
                    if not pd.isna(inst_return):
                        portfolio_return += satellite_weights[inst_id] * inst_return
        
        # Store portfolio return BEFORE updating NAV (for TE calculation)
        portfolio_returns_list.append(portfolio_return)
        core_returns_list.append(core_daily_return)
        
        # V2.1: Update relative performance index (for dynamic_cushion mode)
        if allocation_mode == "dynamic_cushion":
            if i > 0:
                # rel_index(t) = rel_index(t-1) * (1 + r_p(t)) / (1 + r_c(t))
                rel_index = rel_index * (1 + portfolio_return) / (1 + core_daily_return)
                
                # Update relative floor (if floor_accrues_with_core)
                if floor_accrues_with_core:
                    days_since_last = (current_date - calendar[i-1]).days
                    if days_since_last > 0:
                        rel_floor = rel_floor * (core_daily_growth ** days_since_last)
                # else: rel_floor stays at initial floor_rel_ratio
            else:
                # Initialize on first date
                rel_index = 1.0
                rel_floor = floor_rel_ratio
        
        # Update NAV
        portfolio_nav = portfolio_nav * (1 + portfolio_return)
        
        # Update core NAV (for benchmark)
        if i > 0:
            days_since_last = (current_date - calendar[i-1]).days
            if days_since_last > 0:
                core_nav = core_nav * (core_daily_growth ** days_since_last)
        else:
            core_nav = initial_capital
        
        # Compute realized TE (rolling window)
        te_realized = None
        if len(portfolio_returns_list) >= lookback_risk_days:
            # Get active returns for last lookback_risk_days
            active_returns_window = []
            start_idx = max(0, len(portfolio_returns_list) - lookback_risk_days)
            for j in range(start_idx, len(portfolio_returns_list)):
                port_ret = portfolio_returns_list[j]
                core_ret = core_returns_list[j]
                active_return = port_ret - core_ret
                active_returns_window.append(active_return)
            
            if len(active_returns_window) >= 2:
                te_realized = np.std(active_returns_window, ddof=1) * np.sqrt(day_count)
        
        # Store portfolio series
        nav_base100 = (portfolio_nav / initial_capital) * 100.0
        core_nav_base100 = (core_nav / initial_capital) * 100.0
        
        # Get V2 metrics from last rebalance (if available)
        satellite_turnover = 0.0
        portfolio_turnover = 0.0
        te_pred_current = None
        te_pred_shrunk_current = None
        optimization_score_current = None
        
        # V2.1: Get metadata from last rebalance
        w_scalar_current = None
        te_sat_current = None
        ir_sat_current = None
        alloc_mode_current = allocation_mode
        rel_index_current = rel_index if allocation_mode == "dynamic_cushion" else None
        rel_floor_current = rel_floor if allocation_mode == "dynamic_cushion" else None
        cushion_current = None
        
        if debug_log and debug_log[-1].get('event') == 'rebalance' and debug_log[-1].get('date') == current_date.isoformat():
            satellite_turnover = debug_log[-1].get('satellite_turnover', 0.0)
            portfolio_turnover = debug_log[-1].get('portfolio_turnover', 0.0)
            te_pred_current = debug_log[-1].get('te_pred')
            te_pred_shrunk_current = debug_log[-1].get('te_pred_shrunk')
            optimization_score_current = debug_log[-1].get('optimization_score')
            # V2.1 fields
            w_scalar_current = debug_log[-1].get('w_scalar')
            te_sat_current = debug_log[-1].get('te_sat')
            ir_sat_current = debug_log[-1].get('ir_sat')
            if allocation_mode == "dynamic_cushion":
                rel_index_current = debug_log[-1].get('rel_index', rel_index)
                rel_floor_current = debug_log[-1].get('rel_floor', rel_floor)
                cushion_current = debug_log[-1].get('cushion')
        
        # For dates after rebalance, use last rebalance's w_scalar, or compute from current weights
        if w_scalar_current is None:
            # Estimate w_scalar from current weights
            total_sat_weight = sum(satellite_weights.values())
            w_scalar_current = total_sat_weight if total_sat_weight > 1e-6 else 0.0
        
        # Compute cushion for current date (dynamic_cushion mode)
        if allocation_mode == "dynamic_cushion":
            cushion_current = max(rel_index - rel_floor, 0.0) if rel_index_current is not None and rel_floor_current is not None else None
        
        weights_dict = {str(inst_id): float(satellite_weights.get(inst_id, 0.0)) for inst_id in instrument_ids}
        weights_dict['_core_weight'] = float(core_weight)
        if te_realized is not None:
            weights_dict['_te_realized'] = float(te_realized)
        if te_pred_current is not None:
            weights_dict['_te_pred'] = float(te_pred_current)
        if te_pred_shrunk_current is not None:
            weights_dict['_te_pred_shrunk'] = float(te_pred_shrunk_current)
        if satellite_turnover > 0:
            weights_dict['_satellite_turnover'] = float(satellite_turnover)
        if portfolio_turnover > 0:
            weights_dict['_portfolio_turnover'] = float(portfolio_turnover)
        if optimization_score_current is not None:
            weights_dict['_optimization_score'] = float(optimization_score_current)
        
        # V2.1: Store EDHEC-style allocation fields (ALWAYS stored)
        weights_dict['_cs_alloc_mode'] = str(alloc_mode_current)
        weights_dict['_cs_sat_weight_scalar'] = float(w_scalar_current) if w_scalar_current is not None else 0.0
        if te_sat_current is not None:
            weights_dict['_cs_te_sat'] = float(te_sat_current)
        else:
            weights_dict['_cs_te_sat'] = 0.0
        if ir_sat_current is not None and not (isinstance(ir_sat_current, float) and np.isnan(ir_sat_current)):
            weights_dict['_cs_ir_sat'] = float(ir_sat_current)
        else:
            weights_dict['_cs_ir_sat'] = None
        
        # V2.1: Store dynamic_cushion fields (if applicable)
        if allocation_mode == "dynamic_cushion":
            if rel_index_current is not None:
                weights_dict['_cs_rel_index'] = float(rel_index_current)
            if rel_floor_current is not None:
                weights_dict['_cs_rel_floor'] = float(rel_floor_current)
            if cushion_current is not None:
                weights_dict['_cs_cushion'] = float(cushion_current)
        
        portfolio_bar = {
            'date': current_date,  # date object, not ISO string
            'nav_base100': float(nav_base100),
            'portfolio_return': float(portfolio_return) * 100.0,  # In percentage
            'drawdown': 0.0,  # Computed later if needed
            'turnover': float(portfolio_turnover) * 100.0,  # In percentage (V2)
            'costs': 0.0,  # Computed later if needed
            'weights_json': weights_dict,
            'tradable_json': {str(inst_id): True for inst_id in instrument_ids},
        }
        
        portfolio_series.append(portfolio_bar)
        
        # Store instrument series
        for inst_id in instrument_ids:
            if current_prices is not None and inst_id in current_prices.index and not pd.isna(current_prices[inst_id]):
                price = float(current_prices[inst_id])
                inst_return = returns_df.loc[date_ts, inst_id] if date_ts in returns_df.index else 0.0
                if pd.isna(inst_return):
                    inst_return = 0.0
                
                # Compute base100
                first_price = prices_df.iloc[0][inst_id] if len(prices_df) > 0 else price
                inst_base100 = (price / first_price) * 100.0 if first_price > 0 else 100.0
                
                instrument_series[inst_id].append({
                    'date': current_date,  # date object, not ISO string
                    'base100': float(inst_base100),
                    'instrument_return': float(inst_return) * 100.0,  # In percentage
                })
    
    # Compute metrics
    if len(portfolio_series) > 1:
        nav_base100_series = [bar['nav_base100'] for bar in portfolio_series]
        returns_series = [bar['portfolio_return'] / 100.0 for bar in portfolio_series[1:]]  # Convert from percentage
        
        total_return = (nav_base100_series[-1] / nav_base100_series[0] - 1) * 100.0
        annualized_return = (1 + total_return / 100.0) ** (day_count / len(calendar)) - 1
        annualized_return_pct = annualized_return * 100.0
        volatility = np.std(returns_series) * np.sqrt(day_count) * 100.0 if returns_series else 0.0
        sharpe = (annualized_return_pct / volatility) if volatility > 0 else 0.0
        
        # Max drawdown
        running_max = []
        max_val = nav_base100_series[0]
        for nav in nav_base100_series:
            max_val = max(max_val, nav)
            running_max.append(max_val)
        drawdowns = [(nav - max_nav) / max_nav * 100.0 for nav, max_nav in zip(nav_base100_series, running_max)]
        max_drawdown = min(drawdowns) if drawdowns else 0.0
        
        # Realized TE (final) - use stored portfolio_returns_list
        te_realized_final = None
        if len(portfolio_returns_list) >= lookback_risk_days:
            active_returns_final = []
            start_idx = max(0, len(portfolio_returns_list) - lookback_risk_days)
            for j in range(start_idx, len(portfolio_returns_list)):
                port_ret = portfolio_returns_list[j]
                core_ret = core_returns_list[j]
                active_return = port_ret - core_ret
                active_returns_final.append(active_return)
            
            if len(active_returns_final) >= 2:
                te_realized_final = np.std(active_returns_final, ddof=1) * np.sqrt(day_count)
        
        # Average core weight
        avg_core_weight = np.mean([bar['weights_json'].get('_core_weight', 1.0) for bar in portfolio_series]) * 100.0
        
        # V2 metrics
        te_realized_list = [bar['weights_json'].get('_te_realized') for bar in portfolio_series if bar['weights_json'].get('_te_realized') is not None]
        avg_realized_te = np.mean(te_realized_list) if te_realized_list else None
        
        te_pred_list = [bar['weights_json'].get('_te_pred') for bar in portfolio_series if bar['weights_json'].get('_te_pred') is not None]
        avg_predicted_te = np.mean(te_pred_list) if te_pred_list else None
        
        turnover_list = [bar['weights_json'].get('_portfolio_turnover', 0.0) for bar in portfolio_series if bar['weights_json'].get('_portfolio_turnover') is not None]
        avg_turnover = np.mean(turnover_list) if turnover_list else 0.0
        
        te_ratio = (te_realized_final / target_te) if te_realized_final is not None and target_te > 0 else None
        
        metrics = {
            'total_return': float(total_return),
            'annualized_return': float(annualized_return_pct),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe),
            'max_drawdown': float(max_drawdown),
            'realized_te': float(te_realized_final) if te_realized_final is not None else None,
            'avg_core_weight': float(avg_core_weight),
            'avg_realized_te': float(avg_realized_te) if avg_realized_te is not None else None,
            'avg_predicted_te': float(avg_predicted_te) if avg_predicted_te is not None else None,
            'avg_turnover': float(avg_turnover) * 100.0,  # In percentage
            'te_ratio': float(te_ratio) if te_ratio is not None else None,
        }
    else:
        metrics = {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'realized_te': None,
            'avg_core_weight': 100.0,
            'avg_realized_te': None,
            'avg_predicted_te': None,
            'avg_turnover': 0.0,
            'te_ratio': None,
        }
    
    return {
        'portfolio_series': portfolio_series,
        'instrument_series': instrument_series,
        'metrics': metrics,
        'debug_log': debug_log if debug else None,
    }


def compute_te_sat(w_unit: np.ndarray, cov_matrix: np.ndarray, day_count: int) -> float:
    """
    Compute predicted TE for unit satellite portfolio (annualized).
    
    Args:
        w_unit: Unit satellite weights (sums to 1)
        cov_matrix: Covariance matrix (annualized)
        day_count: Days per year for annualization
    
    Returns:
        TE_sat (annualized)
    """
    if len(w_unit) == 0 or cov_matrix.shape[0] == 0:
        return 0.0
    te_sat = np.sqrt(w_unit @ cov_matrix @ w_unit)
    return float(te_sat)


def compute_ir_sat(
    w_unit: np.ndarray,
    mu_sat: np.ndarray,
    mu_core: float,
    cov_matrix: np.ndarray,
    day_count: int,
    eps: float = 1e-6,
) -> Tuple[float, float]:
    """
    Compute Information Ratio for unit satellite portfolio.
    
    Args:
        w_unit: Unit satellite weights (sums to 1)
        mu_sat: Expected returns vector (daily)
        mu_core: Core daily return
        cov_matrix: Covariance matrix (annualized)
        day_count: Days per year
        eps: Small epsilon to avoid division by zero
    
    Returns:
        (IR_sat, TE_sat) where IR_sat = ER_sat / (TE_sat + eps)
    """
    if len(w_unit) == 0:
        return 0.0, 0.0
    
    # Excess return proxy (annualized approximation)
    er_sat = np.sum(mu_sat * w_unit) * day_count - mu_core * day_count
    
    # TE_sat
    te_sat = compute_te_sat(w_unit, cov_matrix, day_count)
    
    # IR_sat
    ir_sat = er_sat / (te_sat + eps) if (te_sat + eps) > 0 else 0.0
    
    return float(ir_sat), float(te_sat)


def build_unit_satellite_portfolio(
    hist_returns: pd.DataFrame,
    core_daily_return: float,
    lookback_risk_days: int,
    lookback_return_days: int,
    day_count: int,
    max_weight_per_asset: float,
    top_k_satellite: Optional[int],
    shrinkage: bool,
    turnover_penalty: float,
    stability_penalty: float,
    optimization_method: str,
    previous_satellite_weights: Optional[Dict[int, float]],
    instrument_ids: List[int],
) -> Dict:
    """
    Build unit satellite portfolio (w_unit that sums to 1).
    
    Returns dict with:
    - w_unit: Dict[instrument_id, float] (sums to 1.0)
    - mu_sat: pd.Series (expected returns)
    - cov_matrix: np.ndarray (covariance matrix, possibly shrunk)
    - cov_matrix_shrunk: np.ndarray (if shrinkage enabled)
    - te_sat: float (predicted TE for w_unit)
    - ir_sat: float (Information Ratio for w_unit)
    """
    # Compute expected returns (momentum: mean of returns)
    if len(hist_returns) < lookback_return_days:
        return_hist = hist_returns
    else:
        return_hist = hist_returns.iloc[-lookback_return_days:]
    
    mu_sat = return_hist.mean()  # Series: instrument_id -> mean return
    
    # Filter top-K if requested
    if top_k_satellite and top_k_satellite < len(instrument_ids):
        top_inst_ids = mu_sat.nlargest(top_k_satellite).index.tolist()
        instrument_ids = [inst_id for inst_id in instrument_ids if inst_id in top_inst_ids]
        mu_sat = mu_sat[instrument_ids]
    
    # Compute covariance matrix
    if len(hist_returns) < lookback_risk_days:
        risk_hist = hist_returns
    else:
        risk_hist = hist_returns.iloc[-lookback_risk_days:]
    
    # Filter to only instrument_ids that exist in risk_hist
    available_inst_ids = [inst_id for inst_id in instrument_ids if inst_id in risk_hist.columns]
    if not available_inst_ids:
        # Fallback: equal weight unit portfolio
        n = len(instrument_ids)
        w_unit = {inst_id: 1.0 / n if n > 0 else 0.0 for inst_id in instrument_ids}
        return {
            'w_unit': w_unit,
            'mu_sat': pd.Series(dtype=float),
            'cov_matrix': np.array([]),
            'cov_matrix_shrunk': None,
            'te_sat': 0.0,
            'ir_sat': 0.0,
        }
    
    instrument_ids = available_inst_ids
    risk_hist_filtered = risk_hist[instrument_ids]
    mu_sat = mu_sat[instrument_ids]
    
    # Compute covariance matrix (annualized)
    cov_matrix = risk_hist_filtered.cov().values * day_count  # Annualized, convert to numpy array
    
    # Apply shrinkage if enabled
    cov_matrix_shrunk = None
    if shrinkage:
        cov_matrix_shrunk, _ = _ledoit_wolf_shrinkage(cov_matrix)
        cov_matrix_use = cov_matrix_shrunk
    else:
        cov_matrix_use = cov_matrix
    
    # Build unit portfolio (budget = 1.0)
    previous_weights_dict = previous_satellite_weights if previous_satellite_weights else {inst_id: 0.0 for inst_id in instrument_ids}
    
    if optimization_method == "quadratic":
        # V2: Quadratic optimization
        w_unit_dict = _optimize_satellite_weights_quadratic(
            mu_sat=mu_sat.values,
            cov_matrix=cov_matrix_use,
            budget=1.0,  # Unit portfolio
            max_weight_per_asset=max_weight_per_asset,
            sat_min=0.0,  # Not used for unit portfolio
            turnover_penalty=turnover_penalty,
            stability_penalty=stability_penalty,
            previous_weights=previous_weights_dict,
            instrument_ids=instrument_ids,
        )
    else:
        # V1: Greedy allocation
        w_unit_dict = {inst_id: 0.0 for inst_id in instrument_ids}
        remaining_budget = 1.0
        
        # Sort by mu (descending)
        sorted_inst_ids = mu_sat.sort_values(ascending=False).index.tolist()
        
        for inst_id in sorted_inst_ids:
            if remaining_budget <= 0:
                break
            
            # Allocate up to max_weight_per_asset
            allocation = min(remaining_budget, max_weight_per_asset)
            w_unit_dict[inst_id] = allocation
            remaining_budget -= allocation
        
        # Normalize to sum = 1.0
        total = sum(w_unit_dict.values())
        if total > 0 and abs(total - 1.0) > 1e-6:
            scale = 1.0 / total
            w_unit_dict = {k: v * scale for k, v in w_unit_dict.items()}
    
    # Expand to include all instrument_ids (fill 0.0 for missing)
    full_w_unit = {inst_id: w_unit_dict.get(inst_id, 0.0) for inst_id in instrument_ids}
    
    # Compute TE_sat and IR_sat for unit portfolio
    w_unit_vector = np.array([full_w_unit.get(inst_id, 0.0) for inst_id in instrument_ids])
    te_sat = compute_te_sat(w_unit_vector, cov_matrix_use, day_count)
    ir_sat, _ = compute_ir_sat(w_unit_vector, mu_sat.values, core_daily_return, cov_matrix_use, day_count)
    
    return {
        'w_unit': full_w_unit,
        'mu_sat': mu_sat,
        'cov_matrix': cov_matrix,
        'cov_matrix_shrunk': cov_matrix_shrunk,
        'te_sat': te_sat,
        'ir_sat': ir_sat,
    }


def compute_scalar_satellite_weight(
    w_unit_result: Dict,
    allocation_mode: str,
    target_te: float,
    lambda_risk: float,
    multiplier: float,
    sat_min: float,
    sat_max: float,
    rel_index: float,
    rel_floor: float,
    core_daily_return: float,
    day_count: int,
    te_max_hard_mult: Optional[float] = None,
) -> Tuple[float, Dict]:
    """
    Compute scalar satellite weight w using EDHEC-style allocation mode.
    
    Args:
        w_unit_result: Result from build_unit_satellite_portfolio
        allocation_mode: "te_target", "utility_lambda", or "dynamic_cushion"
        target_te: Target TE (for te_target mode)
        lambda_risk: Risk aversion (for utility_lambda mode)
        multiplier: Multiplier (for dynamic_cushion mode)
        sat_min: Minimum satellite weight
        sat_max: Maximum satellite weight
        rel_index: Relative performance index (for dynamic_cushion)
        rel_floor: Relative floor (for dynamic_cushion)
        core_daily_return: Core daily return
        day_count: Days per year
        te_max_hard_mult: Optional hard cap multiplier for TE
    
    Returns:
        (w, metadata_dict) where w is the scalar satellite weight and metadata contains IR, TE, etc.
    """
    w_unit = w_unit_result['w_unit']
    te_sat = w_unit_result['te_sat']
    ir_sat = w_unit_result['ir_sat']
    mu_sat = w_unit_result['mu_sat']
    
    eps = 1e-6
    
    if allocation_mode == "te_target":
        # w = clamp(target_te / max(TE_sat, eps), sat_min, sat_max)
        if te_sat > eps:
            w = target_te / te_sat
        else:
            w = sat_max  # If TE_sat is very small, use max allocation
        
        w = max(sat_min, min(sat_max, w))
        
        # Optional: enforce hard TE cap
        if te_max_hard_mult is not None and target_te > 0:
            w_max_by_te = (target_te * te_max_hard_mult) / max(te_sat, eps)
            w = min(w, w_max_by_te)
            w = max(sat_min, w)  # Re-clamp after TE cap
        
        metadata = {
            'te_sat': te_sat,
            'ir_sat': ir_sat,
            'alloc_mode': 'te_target',
        }
    
    elif allocation_mode == "utility_lambda":
        # w* = IR_sat / (2*lambda_risk*max(TE_sat, eps))
        if te_sat > eps and lambda_risk > 0:
            w = ir_sat / (2 * lambda_risk * te_sat)
        else:
            w = sat_min  # Fallback to minimum
        
        w = max(sat_min, min(sat_max, w))
        
        # Optional: enforce hard TE cap if target_te provided
        if te_max_hard_mult is not None and target_te > 0:
            w_max_by_te = (target_te * te_max_hard_mult) / max(te_sat, eps)
            w = min(w, w_max_by_te)
            w = max(sat_min, w)
        
        metadata = {
            'te_sat': te_sat,
            'ir_sat': ir_sat,
            'lambda_risk': lambda_risk,
            'alloc_mode': 'utility_lambda',
        }
    
    elif allocation_mode == "dynamic_cushion":
        # Cushion = max(rel_index - rel_floor, 0)
        cushion = max(rel_index - rel_floor, 0.0)
        
        # w = clamp(multiplier * cushion, sat_min, sat_max)
        w = multiplier * cushion
        w = max(sat_min, min(sat_max, w))
        
        metadata = {
            'te_sat': te_sat,
            'ir_sat': ir_sat,
            'cushion': cushion,
            'rel_index': rel_index,
            'rel_floor': rel_floor,
            'multiplier': multiplier,
            'alloc_mode': 'dynamic_cushion',
        }
    
    else:
        raise ValueError(f"Unknown allocation_mode: {allocation_mode}")
    
    return float(w), metadata


def _ledoit_wolf_shrinkage(cov_matrix: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Ledoit-Wolf shrinkage estimator for covariance matrix.
    
    Returns (shrunk_cov_matrix, shrinkage_intensity)
    
    Reference: Ledoit & Wolf (2004) "A well-conditioned estimator for large-dimensional covariance matrices"
    Simplified implementation without external dependencies.
    """
    n = cov_matrix.shape[0]
    if n == 0:
        return cov_matrix, 0.0
    
    # Sample mean (target: constant correlation model)
    mu = np.trace(cov_matrix) / n
    F = mu * np.eye(n)
    
    # Compute shrinkage intensity (simplified version)
    # pi = sum of squared off-diagonal elements
    pi_hat = np.sum((cov_matrix - np.diag(np.diag(cov_matrix))) ** 2)
    
    # rho = sum of diagonal elements squared
    rho_hat = np.sum(np.diag(cov_matrix) ** 2)
    
    # gamma = ||F - S||^2
    gamma_hat = np.sum((F - cov_matrix) ** 2)
    
    # Shrinkage intensity
    kappa = (pi_hat - rho_hat) / gamma_hat if gamma_hat > 0 else 0.0
    shrinkage_intensity = max(0.0, min(1.0, kappa))
    
    # Shrunk covariance matrix
    shrunk_cov = (1 - shrinkage_intensity) * cov_matrix + shrinkage_intensity * F
    
    return shrunk_cov, shrinkage_intensity


def _optimize_satellite_weights_quadratic(
    mu_sat: np.ndarray,
    cov_matrix: np.ndarray,
    budget: float,
    max_weight_per_asset: float,
    sat_min: float,
    turnover_penalty: float,
    stability_penalty: float,
    previous_weights: Dict[int, float],
    instrument_ids: List[int],
) -> Dict[int, float]:
    """
    V2 quadratic optimization for satellite weights (gradient-based with projection).
    
    Uses gradient ascent with projection (simple, no scipy dependency).
    
    Objective: max mu^T w - penalty * (turnover + stability)
    Constraints:
    - sum(w) = budget
    - w >= 0
    - w <= max_weight_per_asset
    """
    n = len(mu_sat)
    if n == 0:
        return {inst_id: 0.0 for inst_id in instrument_ids}
    
    # Initialize weights (equal weight)
    w = np.ones(n) * (budget / n)
    
    # Previous weights vector
    w_prev = np.array([previous_weights.get(inst_id, 0.0) for inst_id in instrument_ids])
    
    # Gradient ascent with projection
    learning_rate = 0.01
    max_iterations = 100
    tolerance = 1e-6
    
    for iteration in range(max_iterations):
        # Gradient: mu - penalties
        grad_mu = mu_sat
        
        # Turnover penalty gradient (approximate: -penalty * sign(w))
        grad_turnover = -turnover_penalty * np.sign(w) if turnover_penalty > 0 else np.zeros(n)
        
        # Stability penalty gradient: -2 * penalty * (w - w_prev)
        grad_stability = -2 * stability_penalty * (w - w_prev) if stability_penalty > 0 else np.zeros(n)
        
        grad = grad_mu + grad_turnover + grad_stability
        
        # Update
        w_new = w + learning_rate * grad
        
        # Project onto constraints: sum(w) = budget, 0 <= w <= max_weight_per_asset
        # Step 1: Clip to [0, max_weight_per_asset]
        w_new = np.clip(w_new, 0.0, max_weight_per_asset)
        
        # Step 2: Normalize to sum = budget
        total = np.sum(w_new)
        if total > 0:
            w_new = w_new * (budget / total)
        
        # Check convergence
        if np.max(np.abs(w_new - w)) < tolerance:
            break
        
        w = w_new
    
    # Convert to dict
    satellite_weights = {instrument_ids[i]: float(w[i]) for i in range(n)}
    
    return satellite_weights


def _optimize_weights(
    hist_returns: pd.DataFrame,
    core_daily_return: float,
    target_te: float,
    te_tolerance: float,
    te_max_hard_mult: float,
    lookback_risk_days: int,
    lookback_return_days: int,
    day_count: int,
    core_min: float,
    max_weight_per_asset: float,
    core_grid_step: float,
    top_k_satellite: Optional[int],
    instrument_ids: List[int],  # Required parameter (must be before optional params)
    sat_min: float = 0.0,  # V2
    shrinkage: bool = False,  # V2
    turnover_penalty: float = 0.0,  # V2
    stability_penalty: float = 0.0,  # V2
    optimization_method: str = "grid",  # V2
    previous_satellite_weights: Optional[Dict[int, float]] = None,  # V2
) -> Dict:
    """
    Optimize core and satellite weights (V1 grid search or V2 quadratic).
    
    Returns dict with:
    - core_weight: float
    - satellite_weights: Dict[instrument_id, float]
    - te_pred: float (predicted TE)
    - te_pred_shrunk: float (V2, if shrinkage enabled)
    - optimization_score: float (V2, if available)
    """
    # Compute expected returns (momentum: mean of returns)
    if len(hist_returns) < lookback_return_days:
        return_hist = hist_returns
    else:
        return_hist = hist_returns.iloc[-lookback_return_days:]
    
    mu_sat = return_hist.mean()  # Series: instrument_id -> mean return
    mu_core = core_daily_return
    
    # Filter top-K if requested
    if top_k_satellite and top_k_satellite < len(instrument_ids):
        top_inst_ids = mu_sat.nlargest(top_k_satellite).index.tolist()
        instrument_ids = [inst_id for inst_id in instrument_ids if inst_id in top_inst_ids]
        mu_sat = mu_sat[instrument_ids]
    
    # Compute covariance matrix
    if len(hist_returns) < lookback_risk_days:
        risk_hist = hist_returns
    else:
        risk_hist = hist_returns.iloc[-lookback_risk_days:]
    
    # Filter to only instrument_ids that exist in risk_hist
    available_inst_ids = [inst_id for inst_id in instrument_ids if inst_id in risk_hist.columns]
    if not available_inst_ids:
        # Fallback: equal weight, 100% core
        return {
            'core_weight': 1.0,
            'satellite_weights': {inst_id: 0.0 for inst_id in instrument_ids},
            'te_pred': 0.0,
        }
    
    instrument_ids = available_inst_ids
    risk_hist_filtered = risk_hist[instrument_ids]
    mu_sat = mu_sat[instrument_ids]
    
    # Compute covariance matrix (annualized)
    cov_matrix = risk_hist_filtered.cov().values * day_count  # Annualized, convert to numpy array
    
    # Apply shrinkage if enabled (V2)
    cov_matrix_shrunk = None
    if shrinkage:
        cov_matrix_shrunk, shrinkage_intensity = _ledoit_wolf_shrinkage(cov_matrix)
        cov_matrix_use = cov_matrix_shrunk
    else:
        cov_matrix_use = cov_matrix
    
    # Grid search over core_weight
    best_candidate = None
    best_score = float('-inf')
    
    core_weight_candidates = np.arange(core_min, 1.0 + core_grid_step, core_grid_step)
    
    # Previous weights vector for stability penalty (V2)
    previous_weights_dict = previous_satellite_weights if previous_satellite_weights else {inst_id: 0.0 for inst_id in instrument_ids}
    
    for w_core in core_weight_candidates:
        budget = 1.0 - w_core
        if budget <= 0:
            continue
        
        # Ensure sat_min constraint (V2)
        if budget < sat_min:
            continue
        
        # Optimize satellite weights (V1 or V2)
        if optimization_method == "quadratic":
            # V2: Quadratic optimization
            satellite_weights_dict = _optimize_satellite_weights_quadratic(
                mu_sat=mu_sat.values,
                cov_matrix=cov_matrix_use,
                budget=budget,
                max_weight_per_asset=max_weight_per_asset,
                sat_min=sat_min,
                turnover_penalty=turnover_penalty,
                stability_penalty=stability_penalty,
                previous_weights=previous_weights_dict,
                instrument_ids=instrument_ids,
            )
        else:
            # V1: Greedy allocation
            satellite_weights_dict = {inst_id: 0.0 for inst_id in instrument_ids}
            remaining_budget = budget
            
            # Sort by mu (descending)
            sorted_inst_ids = mu_sat.sort_values(ascending=False).index.tolist()
            
            for inst_id in sorted_inst_ids:
                if remaining_budget <= 0:
                    break
                
                # Allocate up to max_weight_per_asset
                allocation = min(remaining_budget, max_weight_per_asset)
                satellite_weights_dict[inst_id] = allocation
                remaining_budget -= allocation
            
            # Normalize to use full budget
            total_sat = sum(satellite_weights_dict.values())
            if total_sat > 0 and abs(total_sat - budget) > 1e-6:
                scale = budget / total_sat
                satellite_weights_dict = {k: v * scale for k, v in satellite_weights_dict.items()}
        
        # Compute predicted TE
        w_sat_vector = np.array([satellite_weights_dict.get(inst_id, 0.0) for inst_id in instrument_ids])
        te_pred = np.sqrt(w_sat_vector @ cov_matrix_use @ w_sat_vector)
        
        # Compute TE with shrinkage if enabled (V2)
        te_pred_shrunk = None
        if shrinkage and cov_matrix_shrunk is not None:
            te_pred_shrunk = np.sqrt(w_sat_vector @ cov_matrix_shrunk @ w_sat_vector)
        
        # Check if TE is acceptable
        te_max_hard = target_te * te_max_hard_mult
        if te_pred > te_max_hard:
            continue
        
        # Compute optimization score (expected excess return - penalties) (V2)
        mu_portfolio = w_core * mu_core + np.sum(mu_sat.values * w_sat_vector)
        excess_return = mu_portfolio - mu_core
        
        # Penalties (V2)
        turnover_penalty_value = 0.0
        stability_penalty_value = 0.0
        
        if turnover_penalty > 0:
            turnover_penalty_value = turnover_penalty * np.sum(np.abs(w_sat_vector))
        
        if stability_penalty > 0:
            prev_vector = np.array([previous_weights_dict.get(inst_id, 0.0) for inst_id in instrument_ids])
            stability_penalty_value = stability_penalty * np.sum((w_sat_vector - prev_vector) ** 2)
        
        optimization_score = excess_return - turnover_penalty_value - stability_penalty_value
        
        # Prefer candidates within tolerance
        within_tolerance = abs(te_pred - target_te) <= te_tolerance
        
        if best_candidate is None:
            best_candidate = {
                'core_weight': w_core,
                'satellite_weights': satellite_weights_dict,
                'te_pred': te_pred,
                'te_pred_shrunk': te_pred_shrunk,
                'optimization_score': optimization_score,
                'within_tolerance': within_tolerance,
            }
            best_score = optimization_score
        else:
            # Prefer within tolerance
            if within_tolerance and not best_candidate['within_tolerance']:
                best_candidate = {
                    'core_weight': w_core,
                    'satellite_weights': satellite_weights_dict,
                    'te_pred': te_pred,
                    'te_pred_shrunk': te_pred_shrunk,
                    'optimization_score': optimization_score,
                    'within_tolerance': within_tolerance,
                }
                best_score = optimization_score
            elif within_tolerance == best_candidate['within_tolerance']:
                # Same tolerance status, prefer higher score (V2) or excess_return (V1)
                score_use = optimization_score if optimization_method == "quadratic" else excess_return
                best_score_use = best_candidate.get('optimization_score', best_candidate.get('excess_return', float('-inf')))
                if score_use > best_score_use:
                    best_candidate = {
                        'core_weight': w_core,
                        'satellite_weights': satellite_weights_dict,
                        'te_pred': te_pred,
                        'te_pred_shrunk': te_pred_shrunk,
                        'optimization_score': optimization_score,
                        'excess_return': excess_return,  # Keep for V1 compatibility
                        'within_tolerance': within_tolerance,
                    }
                    best_score = score_use
    
    if best_candidate is None:
        # Fallback: 100% core
        return {
            'core_weight': 1.0,
            'satellite_weights': {inst_id: 0.0 for inst_id in instrument_ids},
            'te_pred': 0.0,
        }
    
    # Expand satellite_weights to include all instrument_ids (fill 0.0 for missing)
    full_satellite_weights = {inst_id: best_candidate['satellite_weights'].get(inst_id, 0.0) for inst_id in instrument_ids}
    
    result = {
        'core_weight': best_candidate['core_weight'],
        'satellite_weights': full_satellite_weights,
        'te_pred': best_candidate['te_pred'],
    }
    
    # Add V2 fields if available
    if 'te_pred_shrunk' in best_candidate and best_candidate['te_pred_shrunk'] is not None:
        result['te_pred_shrunk'] = best_candidate['te_pred_shrunk']
    if 'optimization_score' in best_candidate:
        result['optimization_score'] = best_candidate['optimization_score']
    
    return result
