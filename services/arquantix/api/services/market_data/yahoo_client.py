"""
Yahoo Finance client using yfinance
Handles historical data fetching for market data instruments
"""
import yfinance as yf
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
import time
import pandas as pd


class YahooFinanceClient:
    """Client for Yahoo Finance using yfinance library"""
    
    def __init__(self):
        pass
    
    def get_symbol_for_yahoo(self, symbol: str, asset_class: str, provider_symbol: Optional[str] = None) -> str:
        """
        Convert internal symbol to Yahoo Finance symbol format
        - Crypto: BTC-USD, ETH-USD, etc.
        - ETFs/Equities: Use symbol directly (QQQ, SPY, etc.)
        - Forex: EURUSD=X, GBPUSD=X, etc.
        - Indices: May need special handling (^GSPC for S&P 500, etc.)
        """
        if provider_symbol:
            return provider_symbol
        
        symbol_upper = symbol.upper()
        
        # Crypto symbols: add -USD suffix if not present
        if asset_class == "crypto":
            if not "-USD" in symbol_upper and not "-EUR" in symbol_upper:
                # Remove USD suffix if present and add -USD
                if symbol_upper.endswith("USD"):
                    base = symbol_upper[:-3]
                    return f"{base}-USD"
                return f"{symbol_upper}-USD"
            return symbol_upper
        
        # Forex: add =X suffix if not present
        if asset_class == "forex":
            if not "=X" in symbol_upper:
                return f"{symbol_upper}=X"
            return symbol_upper
        
        # For indices and ETFs, try common mappings
        index_mappings = {
            "S&P 500": "^GSPC",
            "S&P500": "^GSPC",
            "SP500": "^GSPC",
            "DOW JONES": "^DJI",
            "NASDAQ 100": "^NDX",
            "NASDAQ100": "^NDX",
            "DAX": "^GDAXI",
            "CAC 40": "^FCHI",
            "CAC40": "^FCHI",
        }
        
        if symbol_upper in index_mappings:
            return index_mappings[symbol_upper]
        
        # Default: use symbol as-is
        return symbol_upper
    
    def get_historical_data(
        self,
        symbol: str,
        asset_class: str,
        provider_symbol: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        period: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical daily data from Yahoo Finance
        
        Args:
            symbol: Internal symbol (e.g., "BTCUSD")
            asset_class: Asset class (crypto, etf, equity, forex, index, etc.)
            provider_symbol: Yahoo Finance symbol (e.g., "BTC-USD")
            start_date: Start date (optional, if None uses period)
            end_date: End date (optional, defaults to today)
            period: Period string for yfinance (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        
        Returns:
            List of bars: [{"date": date, "open": Decimal, "high": Decimal, "low": Decimal, "close": Decimal, "volume": int}, ...]
        """
        if end_date is None:
            end_date = date.today()
        
        # Get Yahoo Finance symbol
        yahoo_symbol = self.get_symbol_for_yahoo(symbol, asset_class, provider_symbol)
        
        try:
            ticker = yf.Ticker(yahoo_symbol)
            
            # Fetch data
            if start_date and end_date:
                # Use date range
                hist = ticker.history(start=start_date, end=end_date + timedelta(days=1))  # +1 to include end_date
            elif period:
                # Use period string
                hist = ticker.history(period=period)
            else:
                # Default: last 5 years for equities/ETFs, 2 years for crypto
                if asset_class == "crypto":
                    hist = ticker.history(period="2y")
                else:
                    hist = ticker.history(period="5y")
            
            if hist.empty:
                raise ValueError(f"No data returned for symbol {yahoo_symbol}")
            
            # Convert to list of bars
            bars = []
            for date_idx, row in hist.iterrows():
                # yfinance returns datetime index
                bar_date = date_idx.date() if hasattr(date_idx, 'date') else pd.Timestamp(date_idx).date()
                
                # Skip if outside date range
                if start_date and bar_date < start_date:
                    continue
                if end_date and bar_date > end_date:
                    continue
                
                bars.append({
                    "date": bar_date,
                    "open": Decimal(str(row['Open'])),
                    "high": Decimal(str(row['High'])),
                    "low": Decimal(str(row['Low'])),
                    "close": Decimal(str(row['Close'])),
                    "volume": int(row['Volume']) if pd.notna(row['Volume']) else 0,
                })
            
            # Sort by date ascending
            bars.sort(key=lambda x: x["date"])
            return bars
        
        except Exception as e:
            raise ValueError(f"Failed to fetch data for {yahoo_symbol} ({symbol}): {str(e)}")
    
    def get_daily_data_full_history(
        self,
        symbol: str,
        asset_class: str,
        provider_symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get full historical data using max period"""
        return self.get_historical_data(
            symbol=symbol,
            asset_class=asset_class,
            provider_symbol=provider_symbol,
            period="max"
        )
    
    def get_daily_data_recent(
        self,
        symbol: str,
        asset_class: str,
        provider_symbol: Optional[str] = None,
        days: int = 120
    ) -> List[Dict[str, Any]]:
        """Get recent data (last N days)"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        return self.get_historical_data(
            symbol=symbol,
            asset_class=asset_class,
            provider_symbol=provider_symbol,
            start_date=start_date,
            end_date=end_date
        )


