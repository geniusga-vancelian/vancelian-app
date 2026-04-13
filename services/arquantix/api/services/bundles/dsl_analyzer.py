"""
DSL Analyzer for dynamic bundles
Infers requirements (lookback, price usage) from rule JSON
"""
from typing import Dict, Any, Tuple


def infer_dynamic_requirements(rule_json: Dict[str, Any]) -> Tuple[int, bool]:
    """
    Infer requirements from dynamic rule JSON
    
    Args:
        rule_json: DSL rule JSON
    
    Returns:
        Tuple of (lookback_days, uses_prices)
        - lookback_days: Minimum number of days needed for calculations
        - uses_prices: Whether rule requires price data from database
    """
    max_window = 0
    uses_prices = False
    
    def analyze_expression(expr: Any, depth: int = 0) -> None:
        """Recursively analyze expression tree"""
        nonlocal max_window, uses_prices
        
        if depth > 50:  # Prevent infinite recursion
            return
        
        if not isinstance(expr, dict):
            return
        
        op = expr.get('op')
        
        if op == 'sma':
            window = expr.get('window', 20)
            max_window = max(max_window, window)
            uses_prices = True
        
        elif op == 'price':
            uses_prices = True
            lag = expr.get('lag', 0)
            # Need at least lag+1 days
            max_window = max(max_window, lag + 1)
        
        elif op == 'returns':
            window = expr.get('window', 20)
            max_window = max(max_window, window + 1)  # Need window+1 for returns
            uses_prices = True
        
        elif op in ('add', 'sub', 'mul', 'div', 'ratio'):
            if 'a' in expr:
                analyze_expression(expr['a'], depth + 1)
            if 'b' in expr:
                analyze_expression(expr['b'], depth + 1)
        
        elif op == 'clip':
            if 'value' in expr:
                analyze_expression(expr['value'], depth + 1)
        
        elif op == 'if':
            if 'cond' in expr:
                analyze_expression(expr['cond'], depth + 1)
            if 'then' in expr:
                analyze_expression(expr['then'], depth + 1)
            if 'else' in expr:
                analyze_expression(expr['else'], depth + 1)
        
        # const, normalize_to_one don't require prices
    
    # Analyze all items in the rule
    items = rule_json.get('items', [])
    for item in items:
        expr = item.get('expr', {})
        analyze_expression(expr)
    
    # Add buffer: need extra days for stability
    lookback_days = max_window + 10 if max_window > 0 else 0
    
    return lookback_days, uses_prices

