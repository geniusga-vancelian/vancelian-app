"""
CPPI (Constant Proportion Portfolio Insurance) Strategy v1.1

Simplified implementation:
- Risky sleeve: basket of instruments (bundle or equal-weight)
- Core sleeve: synthetic cash-like accrual at constant yield
- Floor: grows daily with the same core_yield (indexed floor)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Optional
from datetime import date


def run_cppi_backtest(
    prices_df: pd.DataFrame,  # Index: date, Columns: instrument_id
    weights_resolver: Callable[[date], Dict[int, float]],  # date -> {instrument_id: weight}
    start_date: date,
    end_date: date,
    initial_capital: float,
    rebalance_frequency: str,  # "daily", "weekly", "monthly"
    fees_bps: float,
    slippage_bps: float,
    floor_ratio: float = 0.90,
    multiplier: float = 4.0,
    risky_cap: float = 1.0,
    core_min: float = 0.0,
    core_yield: float = 0.035,
    day_count: int = 365,
    debug: bool = False,
) -> Dict:
    """
    Run CPPI backtest
    
    Returns dict with:
    - portfolio_series: List[Dict] with nav, cushion, risky_weight, core_weight
    - instrument_series: Dict[instrument_id, List[Dict]]
    - metrics: Dict
    """
    # Initialize
    V0 = initial_capital
    F = floor_ratio * V0  # Initial floor (grows daily with core_yield)
    
    # Calendar
    calendar = sorted([d.date() if isinstance(d, pd.Timestamp) else d for d in prices_df.index if start_date <= (d.date() if isinstance(d, pd.Timestamp) else d) <= end_date])
    
    if not calendar:
        raise ValueError("No dates in calendar")
    
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
    
    # State
    risky_positions = {inst_id: 0.0 for inst_id in prices_df.columns}  # instrument_id -> shares
    risky_weights = None  # Last rebalanced weights
    core_value = V0  # Start 100% core
    
    # Storage
    portfolio_series = []
    instrument_series = {inst_id: [] for inst_id in prices_df.columns}
    debug_log = []  # Debug output for rebalances
    
    # Daily loop
    for i, current_date in enumerate(calendar):
        date_ts = pd.Timestamp(current_date)
        
        # Accrue core (daily)
        if i > 0:
            days_since_last = (current_date - calendar[i-1]).days
            if days_since_last > 0:
                daily_rate = core_yield / day_count
                core_value = core_value * (1 + daily_rate) ** days_since_last
                
                # Accrue floor with same yield (CPPI v1.1: indexed floor)
                F = F * (1 + daily_rate) ** days_since_last
        
        # Compute risky value
        risky_value = 0.0
        if risky_weights is not None:
            current_prices = prices_df.loc[date_ts]
            for inst_id in prices_df.columns:
                if inst_id in current_prices.index and not pd.isna(current_prices[inst_id]):
                    price = float(current_prices[inst_id])
                    if price > 0 and inst_id in risky_positions:
                        risky_value += risky_positions[inst_id] * price
        
        V_t = risky_value + core_value
        
        # Rebalance logic
        should_rebalance = current_date in rebalance_dates
        prices_available = True
        missing_instruments = []
        
        if should_rebalance and i > 0:
            # Check prices available
            current_prices = prices_df.loc[date_ts]
            for inst_id in prices_df.columns:
                if inst_id not in current_prices.index or pd.isna(current_prices[inst_id]):
                    prices_available = False
                    missing_instruments.append(inst_id)
            
            if not prices_available:
                # Log skip explicitly
                if debug:
                    debug_log.append({
                        'date': current_date.isoformat(),
                        'event': 'rebalance_skipped',
                        'reason': 'missing_prices',
                        'missing_instruments': missing_instruments,
                        'V_t': float(V_t),
                    })
            
            if prices_available:
                # Compute targets
                K_t = max(V_t - F, 0.0)  # Cushion
                risky_target_value = min(multiplier * K_t, risky_cap * V_t)
                core_target_value = V_t - risky_target_value
                
                # Enforce core_min
                if core_target_value < core_min * V_t:
                    core_target_value = core_min * V_t
                    risky_target_value = V_t - core_target_value
                
                # Get risky weights (must be valid: all > 0, sum == 1.0)
                target_weights = weights_resolver(current_date)
                if not target_weights:
                    raise ValueError(f"weights_resolver returned empty weights at date {current_date}")
                
                # Validate weights: all > 0
                if not all(w > 0 for w in target_weights.values()):
                    raise ValueError(f"weights_resolver returned non-positive weights at date {current_date}: {target_weights}")
                
                # Validate weights: sum == 1.0 (strict, no normalization)
                total_w = sum(target_weights.values())
                if abs(total_w - 1.0) > 1e-4:
                    raise ValueError(f"weights_resolver returned weights summing to {total_w:.6f} at date {current_date}, expected 1.0: {target_weights}")
                
                # Trade risky
                risky_current_value = risky_value
                risky_delta = risky_target_value - risky_current_value
                
                # Compute target positions
                current_prices_dict = {}
                for inst_id in prices_df.columns:
                    if inst_id in current_prices.index and not pd.isna(current_prices[inst_id]):
                        current_prices_dict[inst_id] = float(current_prices[inst_id])
                
                # Rebalance risky positions
                if risky_target_value > 0 and current_prices_dict:
                    for inst_id, weight in target_weights.items():
                        if inst_id in current_prices_dict:
                            target_position_value = risky_target_value * weight
                            price = current_prices_dict[inst_id]
                            risky_positions[inst_id] = target_position_value / price if price > 0 else 0.0
                    risky_weights = target_weights.copy()
                
                # Apply costs (on risky trades only)
                if abs(risky_delta) > 0:
                    fees_per_trade = fees_bps / 10000.0
                    slippage_per_trade = slippage_bps / 10000.0
                    costs = abs(risky_delta) * (fees_per_trade + slippage_per_trade)
                    core_value -= costs  # Deduct from core
                    # Recompute V_t after costs
                    V_t_after_costs = risky_value + core_value
                    # Adjust targets proportionally to maintain allocation ratios
                    if V_t_after_costs > 0:
                        risky_target_value = risky_target_value * (V_t_after_costs / V_t)
                        core_target_value = V_t_after_costs - risky_target_value
                    else:
                        core_target_value = V_t_after_costs
                        risky_target_value = 0.0
                
                # Update core to match target (residual after risky)
                core_value = core_target_value
                
                # Debug output for rebalance
                if debug:
                    debug_log.append({
                        'date': current_date.isoformat(),
                        'event': 'rebalance',
                        'V_t': float(V_t),
                        'floor': float(F),
                        'cushion': float(K_t),
                        'risky_target_value': float(risky_target_value),
                        'core_target_value': float(core_target_value),
                        'risky_weight': float(risky_target_value / V_t) if V_t > 0 else 0.0,
                        'core_weight': float(core_target_value / V_t) if V_t > 0 else 0.0,
                        'risky_instrument_weights': {str(k): float(v) for k, v in target_weights.items()},
                        'costs': float(costs) if abs(risky_delta) > 0 else 0.0,
                    })
                
        # Recompute after rebalance
        risky_value = 0.0
        if risky_weights is not None:
            current_prices = prices_df.loc[date_ts]
            for inst_id, weight in risky_weights.items():
                if inst_id in current_prices.index and not pd.isna(current_prices[inst_id]):
                    price = float(current_prices[inst_id])
                    if price > 0 and inst_id in risky_positions:
                        risky_value += risky_positions[inst_id] * price
        
        V_t = risky_value + core_value
        
        # Store portfolio series
        K_t = max(V_t - F, 0.0)
        risky_weight = risky_value / V_t if V_t > 0 else 0.0
        core_weight = core_value / V_t if V_t > 0 else 0.0
        
        weights_dict = {}
        if risky_weights:
            weights_dict.update({str(k): float(v) for k, v in risky_weights.items()})
        weights_dict['_cppi_cushion'] = float(K_t)
        weights_dict['_cppi_risky_weight'] = float(risky_weight)
        weights_dict['_cppi_core_weight'] = float(core_weight)
        weights_dict['_cppi_floor'] = float(F)
        
        portfolio_series.append({
            'date': current_date,
            'nav_base100': (V_t / V0 * 100.0) if V0 > 0 else 100.0,
            'portfolio_return': 0.0,  # Computed later
            'drawdown': 0.0,  # Computed later
            'turnover': 0.0,  # Computed later
            'costs': 0.0,  # Computed later
            'weights_json': weights_dict,
            'tradable_json': {str(k): True for k in prices_df.columns},
        })
        
        # Store instrument series
        current_prices = prices_df.loc[date_ts]
        first_prices = prices_df.iloc[0]
        for inst_id in prices_df.columns:
            if inst_id in current_prices.index and not pd.isna(current_prices[inst_id]):
                price = float(current_prices[inst_id])
                first_price = float(first_prices[inst_id]) if inst_id in first_prices.index else price
                base100 = (price / first_price * 100.0) if first_price > 0 else 100.0
                instrument_series[inst_id].append({
                    'date': current_date,
                    'base100': base100,
                    'instrument_return': 0.0,  # Computed later
                })
    
    # Post-process: compute returns, drawdown
    nav_series = pd.Series([s['nav_base100'] for s in portfolio_series], index=pd.DatetimeIndex([s['date'] for s in portfolio_series]))
    returns = nav_series.pct_change().fillna(0.0)
    running_max = nav_series.cummax()
    drawdown = ((nav_series - running_max) / running_max * 100.0).fillna(0.0)
    
    # Update portfolio series
    for i, ps in enumerate(portfolio_series):
        date_idx = pd.Timestamp(ps['date'])
        if date_idx in returns.index:
            ps['portfolio_return'] = float(returns[date_idx]) * 100.0
        if date_idx in drawdown.index:
            ps['drawdown'] = float(drawdown[date_idx])
    
    # Metrics
    total_return = (nav_series.iloc[-1] / nav_series.iloc[0] - 1) * 100.0 if len(nav_series) > 0 else 0.0
    annualized_return = (1 + total_return / 100.0) ** (365.0 / len(calendar)) - 1 if len(calendar) > 0 else 0.0
    annualized_return_pct = annualized_return * 100.0
    volatility = returns.std() * np.sqrt(365) * 100.0
    sharpe = (annualized_return_pct / volatility) if volatility > 0 else 0.0
    max_drawdown = float(drawdown.min())
    
    metrics = {
        'portfolio': {
            'total_return': total_return,
            'annualized_return': annualized_return_pct,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
        },
        'instruments': {}
    }
    
    result = {
        'portfolio_series': portfolio_series,
        'instrument_series': instrument_series,
        'metrics': metrics,
    }
    
    # Add debug log if enabled
    if debug:
        result['debug_log'] = debug_log
    
    return result
