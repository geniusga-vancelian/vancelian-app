"""
CPPI (Constant Proportion Portfolio Insurance) Strategy

Implements CPPI strategy with:
- Risky sleeve (market-priced instruments)
- Core sleeve (synthetic fixed-yield assets with liquidity constraints)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
from datetime import date, timedelta
from decimal import Decimal

# Core asset definitions
CORE_DEFI = {
    'code': 'CORE_DEFI',
    'annual_yield': 0.035,
    'liquidity': 1.0,  # 100%
    'lockup_days': 0,
}

CORE_FLEX = {
    'code': 'CORE_FLEX',
    'annual_yield': 0.06,
    'liquidity': 0.10,  # 10% redeemable
    'lockup_days': 0,
}

CORE_AVENIR = {
    'code': 'CORE_AVENIR',
    'annual_yield': 0.08,
    'liquidity': 0.10,  # 10% after lockup
    'lockup_days': 365,  # 1 year
}

CORE_EXCLUSIVE = {
    'code': 'CORE_EXCLUSIVE',
    'annual_yield': 0.10,
    'liquidity': 1.0,  # 100% after lockup
    'lockup_days': 1095,  # 3 years
}

CORE_ASSETS = [CORE_DEFI, CORE_FLEX, CORE_AVENIR, CORE_EXCLUSIVE]


class CorePolicy:
    """Core allocation policy"""
    
    @staticmethod
    def v1_default_allocate_increase(amount: float) -> Dict[str, float]:
        """
        Allocate new money to core assets (when increasing core allocation)
        Returns dict mapping core_code to allocation amount
        """
        return {
            'CORE_DEFI': amount * 0.70,
            'CORE_FLEX': amount * 0.20,
            'CORE_AVENIR': amount * 0.10,
            'CORE_EXCLUSIVE': 0.0,
        }
    
    @staticmethod
    def v1_default_redeem(
        positions: Dict[str, float],
        target_redeem: float,
        current_date: date,
        start_date: date
    ) -> Tuple[Dict[str, float], float]:
        """
        Redeem from core assets (when decreasing core allocation)
        Returns: (updated_positions, actual_redeemed)
        """
        updated_positions = positions.copy()
        remaining = target_redeem
        actual_redeemed = 0.0
        days_since_start = (current_date - start_date).days
        
        # 1. Redeem from CORE_DEFI first (100% liquidity)
        if remaining > 0 and 'CORE_DEFI' in updated_positions:
            redeem_from_defi = min(remaining, updated_positions['CORE_DEFI'])
            updated_positions['CORE_DEFI'] -= redeem_from_defi
            actual_redeemed += redeem_from_defi
            remaining -= redeem_from_defi
        
        # 2. Redeem from CORE_FLEX (10% liquidity)
        if remaining > 0 and 'CORE_FLEX' in updated_positions:
            max_redeem_flex = updated_positions['CORE_FLEX'] * CORE_FLEX['liquidity']
            redeem_from_flex = min(remaining, max_redeem_flex)
            updated_positions['CORE_FLEX'] -= redeem_from_flex
            actual_redeemed += redeem_from_flex
            remaining -= redeem_from_flex
        
        # 3. Redeem from CORE_AVENIR (if unlocked, 10% liquidity)
        if remaining > 0 and days_since_start >= CORE_AVENIR['lockup_days']:
            if 'CORE_AVENIR' in updated_positions:
                max_redeem_avenir = updated_positions['CORE_AVENIR'] * CORE_AVENIR['liquidity']
                redeem_from_avenir = min(remaining, max_redeem_avenir)
                updated_positions['CORE_AVENIR'] -= redeem_from_avenir
                actual_redeemed += redeem_from_avenir
                remaining -= redeem_from_avenir
        
        # 4. Redeem from CORE_EXCLUSIVE (if unlocked, 100% liquidity)
        if remaining > 0 and days_since_start >= CORE_EXCLUSIVE['lockup_days']:
            if 'CORE_EXCLUSIVE' in updated_positions:
                redeem_from_exclusive = min(remaining, updated_positions['CORE_EXCLUSIVE'])
                updated_positions['CORE_EXCLUSIVE'] -= redeem_from_exclusive
                actual_redeemed += redeem_from_exclusive
                remaining -= redeem_from_exclusive
        
        return updated_positions, actual_redeemed


def accrue_core_positions(
    positions: Dict[str, float],
    days: int,
    day_count: int = 365
) -> Dict[str, float]:
    """
    Accrue core positions over N days
    Returns updated positions dict
    """
    updated = {}
    for core_code, value in positions.items():
        core_asset = next((c for c in CORE_ASSETS if c['code'] == core_code), None)
        if core_asset and value > 0:
            daily_rate = core_asset['annual_yield'] / day_count
            updated[core_code] = value * (1 + daily_rate) ** days
        else:
            updated[core_code] = value
    return updated


def compute_core_value(positions: Dict[str, float]) -> float:
    """Compute total core sleeve value"""
    return sum(positions.values())


def run_cppi_backtest(
    price_matrix_close: pd.DataFrame,  # Index: date, Columns: instrument_id (or code)
    weights_resolver: Callable[[date], Dict[int, float]],  # date -> {instrument_id: weight}
    start_date: date,
    end_date: date,
    initial_capital: float,
    rebalance_frequency: str,  # "daily", "weekly", "monthly"
    fees_bps: float,
    slippage_bps: float,
    floor_ratio: float,  # e.g. 0.90
    multiplier: float,  # e.g. 4.0
    risky_cap: float,  # e.g. 1.0
    core_min: float,  # e.g. 0.0
    day_count: int = 365,
    core_policy: str = "v1_default"
) -> Dict:
    """
    Run CPPI backtest
    
    Returns dict with:
    - portfolio_series: List[Dict] with nav, cushion, risky_weight, core_weight, etc.
    - instrument_series: Dict[instrument_id, List[Dict]]
    - metrics: Dict with computed metrics
    - liquidity_shortfall_count: int
    - liquidity_shortfall_dates: List[date]
    """
    # Initialize
    V0 = initial_capital
    F = floor_ratio * V0  # Static floor
    
    # Core positions (initially 100% core)
    core_positions = CorePolicy.v1_default_allocate_increase(V0)
    
    # Risky positions (initially 0)
    risky_positions = {inst_id: 0.0 for inst_id in price_matrix_close.columns}
    
    # Calendar
    calendar = price_matrix_close.index.to_list()
    calendar = [d.date() if isinstance(d, pd.Timestamp) else d for d in calendar]
    calendar = sorted([d for d in calendar if start_date <= d <= end_date])
    
    # Rebalance dates
    if rebalance_frequency == "daily":
        rebalance_dates = set(calendar)
    elif rebalance_frequency == "weekly":
        # Monday of each week
        rebalance_dates = set()
        for d in calendar:
            if d.weekday() == 0:  # Monday
                rebalance_dates.add(d)
        # Include first date if not Monday
        if calendar and calendar[0] not in rebalance_dates:
            rebalance_dates.add(calendar[0])
    elif rebalance_frequency == "monthly":
        # First trading day of each month
        rebalance_dates = set()
        current_month = None
        for d in calendar:
            if current_month is None or d.month != current_month:
                rebalance_dates.add(d)
                current_month = d.month
    else:
        rebalance_dates = set(calendar)
    
    rebalance_dates = sorted(rebalance_dates)
    
    # Storage
    portfolio_series = []
    instrument_series = {inst_id: [] for inst_id in price_matrix_close.columns}
    liquidity_shortfall_dates = []
    
    # Track last rebalance date
    last_rebalance_date = None
    last_risky_weights = None
    
    # Daily loop
    for i, current_date in enumerate(calendar):
        # Accrue core positions (1 day)
        if i > 0:
            days_since_last = (current_date - calendar[i-1]).days
            if days_since_last > 0:
                core_positions = accrue_core_positions(core_positions, days_since_last, day_count)
        
        # Compute current values
        C_t = compute_core_value(core_positions)
        
        # Compute risky value
        R_t = 0.0
        risky_weights = {}
        if last_risky_weights is not None:
            # Use last rebalanced weights to compute current risky value
            current_prices = price_matrix_close.loc[pd.Timestamp(current_date)]
            for inst_id, weight in last_risky_weights.items():
                if inst_id in current_prices.index:
                    price = float(current_prices[inst_id])
                    if not np.isnan(price) and price > 0:
                        # Value = position * price
                        # Position = weight * total_risky_value_last
                        # So value = weight * total_risky_value_last * price / price_last
                        # Simplified: track positions directly
                        if inst_id in risky_positions:
                            R_t += risky_positions[inst_id] * price
                        risky_weights[inst_id] = weight
        
        # If no risky positions yet, try to compute from initial
        if R_t == 0.0 and last_risky_weights is None:
            # First date: no risky yet
            R_t = 0.0
        
        V_t = R_t + C_t
        
        # Check if rebalance date and prices available
        should_rebalance = current_date in rebalance_dates
        
        # Check if prices available for risky assets
        prices_available = True
        if should_rebalance:
            current_prices = price_matrix_close.loc[pd.Timestamp(current_date)]
            for inst_id in price_matrix_close.columns:
                if inst_id not in current_prices.index or pd.isna(current_prices[inst_id]):
                    prices_available = False
                    break
        
        # Rebalance logic
        if should_rebalance and prices_available and i > 0:
            # Compute targets
            K_t = max(V_t - F, 0.0)  # Cushion
            risky_target_value = min(multiplier * K_t, risky_cap * V_t)
            core_target_value = V_t - risky_target_value
            
            # Enforce core_min
            core_target_value = max(core_target_value, core_min * V_t)
            risky_target_value = V_t - core_target_value
            
            # Get risky weights from resolver
            risky_weights_target = weights_resolver(current_date)
            if not risky_weights_target:
                # Fallback to equal weight
                n_instruments = len(price_matrix_close.columns)
                if n_instruments > 0:
                    equal_weight = 1.0 / n_instruments
                    risky_weights_target = {inst_id: equal_weight for inst_id in price_matrix_close.columns}
            
            # Normalize weights
            total_weight = sum(risky_weights_target.values())
            if total_weight > 0:
                risky_weights_target = {k: v / total_weight for k, v in risky_weights_target.items()}
            else:
                risky_weights_target = {}
            
            # Adjust core allocation
            core_current_value = C_t
            core_delta = core_target_value - core_current_value
            
            if core_delta > 0:
                # Increase core: allocate new money
                allocations = CorePolicy.v1_default_allocate_increase(core_delta)
                for core_code, amount in allocations.items():
                    core_positions[core_code] = core_positions.get(core_code, 0.0) + amount
            elif core_delta < 0:
                # Decrease core: redeem
                target_redeem = abs(core_delta)
                core_positions, actual_redeemed = CorePolicy.v1_default_redeem(
                    core_positions, target_redeem, current_date, start_date
                )
                
                # Check liquidity shortfall
                if actual_redeemed < target_redeem:
                    liquidity_shortfall_dates.append(current_date)
                    # Cap risky target to what can be funded
                    risky_target_value = R_t + actual_redeemed
            
            # Adjust risky allocation
            risky_current_value = R_t
            risky_delta = risky_target_value - risky_current_value
            
            # Get current prices
            current_prices_dict = {}
            for inst_id in price_matrix_close.columns:
                price = float(price_matrix_close.loc[pd.Timestamp(current_date), inst_id])
                if not np.isnan(price) and price > 0:
                    current_prices_dict[inst_id] = price
            
            # Rebalance risky positions
            if risky_target_value > 0 and current_prices_dict:
                for inst_id, target_weight in risky_weights_target.items():
                    if inst_id in current_prices_dict:
                        target_position_value = risky_target_value * target_weight
                        current_price = current_prices_dict[inst_id]
                        risky_positions[inst_id] = target_position_value / current_price if current_price > 0 else 0.0
                last_risky_weights = risky_weights_target.copy()
            else:
                last_risky_weights = risky_weights_target.copy() if risky_weights_target else last_risky_weights
            
            # Apply transaction costs (on risky trades only)
            if abs(risky_delta) > 0:
                fees_per_trade = fees_bps / 10000.0
                slippage_per_trade = slippage_bps / 10000.0
                costs = abs(risky_delta) * (fees_per_trade + slippage_per_trade)
                V_t -= costs
                # Adjust core to absorb costs
                if C_t > costs:
                    # Deduct from CORE_DEFI first
                    if 'CORE_DEFI' in core_positions:
                        core_positions['CORE_DEFI'] -= min(costs, core_positions['CORE_DEFI'])
            
            last_rebalance_date = current_date
        
        # Recompute values after rebalance
        C_t = compute_core_value(core_positions)
        R_t = 0.0
        if last_risky_weights:
            current_prices = price_matrix_close.loc[pd.Timestamp(current_date)]
            for inst_id, weight in last_risky_weights.items():
                if inst_id in current_prices.index:
                    price = float(current_prices[inst_id])
                    if not np.isnan(price) and price > 0 and inst_id in risky_positions:
                        R_t += risky_positions[inst_id] * price
        V_t = R_t + C_t
        
        # Store portfolio series
        K_t = max(V_t - F, 0.0)
        risky_weight = R_t / V_t if V_t > 0 else 0.0
        core_weight = C_t / V_t if V_t > 0 else 0.0
        
        portfolio_series.append({
            'date': current_date,
            'nav_base100': (V_t / V0 * 100.0) if V0 > 0 else 100.0,
            'portfolio_return': 0.0,  # Will be computed from nav series
            'drawdown': 0.0,  # Will be computed from nav series
            'turnover': 0.0,  # Will be computed
            'costs': 0.0,  # Will be computed
            'weights_json': {
                # Store risky weights
                **{str(k): float(v) for k, v in last_risky_weights.items()} if last_risky_weights else {},
                # Store CPPI metrics
                '_cppi_cushion': float(K_t),
                '_cppi_risky_weight': float(risky_weight),
                '_cppi_core_weight': float(core_weight),
                '_cppi_floor': float(F),
                '_cppi_risky_value': float(R_t),
                '_cppi_core_value': float(C_t),
            },
            'tradable_json': {str(k): True for k in price_matrix_close.columns},
        })
        
        # Store instrument series
        current_prices = price_matrix_close.loc[pd.Timestamp(current_date)]
        for inst_id in price_matrix_close.columns:
            if inst_id in current_prices.index:
                price = float(current_prices[inst_id])
                if not np.isnan(price) and price > 0:
                    # Base100 from first date
                    first_price = float(price_matrix_close.iloc[0][inst_id])
                    base100 = (price / first_price * 100.0) if first_price > 0 else 100.0
                    instrument_series[inst_id].append({
                        'date': current_date,
                        'base100': base100,
                        'instrument_return': 0.0,  # Will be computed
                    })
    
    # Post-process: compute returns, drawdown, turnover
    nav_series = pd.Series([s['nav_base100'] for s in portfolio_series], index=pd.DatetimeIndex([s['date'] for s in portfolio_series]))
    
    # Compute returns
    returns = nav_series.pct_change().fillna(0.0)
    
    # Compute drawdown
    running_max = nav_series.cummax()
    drawdown = ((nav_series - running_max) / running_max * 100.0).fillna(0.0)
    
    # Compute turnover (simplified: track weight changes)
    turnover = pd.Series(0.0, index=nav_series.index)
    
    # Update portfolio series with computed values
    for i, ps in enumerate(portfolio_series):
        date_idx = pd.Timestamp(ps['date'])
        if date_idx in returns.index:
            ps['portfolio_return'] = float(returns[date_idx]) * 100.0
        if date_idx in drawdown.index:
            ps['drawdown'] = float(drawdown[date_idx])
        if date_idx in turnover.index:
            ps['turnover'] = float(turnover[date_idx])
    
    # Compute metrics
    total_return = (nav_series.iloc[-1] / nav_series.iloc[0] - 1) * 100.0 if len(nav_series) > 0 else 0.0
    annualized_return = (1 + total_return / 100.0) ** (365.0 / len(calendar)) - 1 if len(calendar) > 0 else 0.0
    annualized_return_pct = annualized_return * 100.0
    
    volatility = returns.std() * np.sqrt(365) * 100.0  # Annualized
    sharpe = (annualized_return_pct / volatility) if volatility > 0 else 0.0
    max_drawdown = float(drawdown.min())
    
    metrics = {
        'portfolio': {
            'total_return': total_return,
            'annualized_return': annualized_return_pct,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'liquidity_shortfall_count': len(liquidity_shortfall_dates),
        },
        'instruments': {}
    }
    
    return {
        'portfolio_series': portfolio_series,
        'instrument_series': instrument_series,
        'metrics': metrics,
        'liquidity_shortfall_count': len(liquidity_shortfall_dates),
        'liquidity_shortfall_dates': liquidity_shortfall_dates,
    }

