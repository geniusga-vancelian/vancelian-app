"""
Alpha Vantage API client
Handles rate limiting and errors
"""
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal
import time
from .config import ALPHAVANTAGE_API_KEY

ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"

# Rate limit: 5 calls per minute (free tier), 75 calls per minute (premium)
# We'll use 4 calls per minute to be safe
RATE_LIMIT_CALLS = 4
RATE_LIMIT_WINDOW = 60  # seconds
_last_call_times: List[float] = []


def _rate_limit():
    """Simple rate limiter: wait if we've made too many calls recently"""
    global _last_call_times
    now = time.time()
    # Remove calls older than the window
    _last_call_times = [t for t in _last_call_times if now - t < RATE_LIMIT_WINDOW]
    
    if len(_last_call_times) >= RATE_LIMIT_CALLS:
        # Wait until the oldest call is outside the window
        wait_time = RATE_LIMIT_WINDOW - (now - _last_call_times[0]) + 1
        if wait_time > 0:
            time.sleep(wait_time)
            _last_call_times = []
    
    _last_call_times.append(time.time())


class AlphaVantageClient:
    """Client for Alpha Vantage API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ALPHAVANTAGE_API_KEY
        if not self.api_key:
            raise ValueError("ALPHAVANTAGE_API_KEY not set")
        self.base_url = ALPHAVANTAGE_BASE_URL
    
    def _request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Make a request to Alpha Vantage API with rate limiting"""
        _rate_limit()
        
        params["apikey"] = self.api_key
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Check for API errors
                if "Error Message" in data:
                    raise ValueError(f"Alpha Vantage API error: {data['Error Message']}")
                if "Note" in data:
                    raise ValueError(f"Alpha Vantage rate limit: {data['Note']}")
                
                return data
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Alpha Vantage HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise ValueError(f"Alpha Vantage request failed: {str(e)}")
    
    def get_daily_equity(self, symbol: str, outputsize: str = "full") -> Dict[str, Any]:
        """
        Get daily equity data (TIME_SERIES_DAILY)
        Returns: { "Time Series (Daily)": { "2024-01-01": { "1. open": "...", ... } } }
        """
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,  # "compact" (100 days) or "full" (20+ years)
        }
        return self._request(params)
    
    def get_daily_equity_adjusted(self, symbol: str, outputsize: str = "full") -> Dict[str, Any]:
        """
        Get daily equity data with adjustments (TIME_SERIES_DAILY_ADJUSTED)
        Recommended for ETFs and equities
        Returns: { "Time Series (Daily)": { "2024-01-01": { "1. open": "...", ... } } }
        """
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": outputsize,  # "compact" (100 days) or "full" (20+ years)
        }
        return self._request(params)
    
    def get_daily_crypto(self, symbol: str, market: str = "USD") -> Dict[str, Any]:
        """
        Get daily crypto data (DIGITAL_CURRENCY_DAILY)
        Returns: { "Time Series (Digital Currency Daily)": { "2024-01-01": { "1a. open (USD)": "...", ... } } }
        """
        params = {
            "function": "DIGITAL_CURRENCY_DAILY",
            "symbol": symbol,
            "market": market,
        }
        return self._request(params)
    
    def parse_daily_equity(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse TIME_SERIES_DAILY or TIME_SERIES_DAILY_ADJUSTED response into list of bars"""
        # Both functions return "Time Series (Daily)"
        time_series = data.get("Time Series (Daily)", {})
        bars = []
        
        for date_str, values in time_series.items():
            bars.append({
                "date": datetime.strptime(date_str, "%Y-%m-%d").date(),
                "open": Decimal(values["1. open"]),
                "high": Decimal(values["2. high"]),
                "low": Decimal(values["3. low"]),
                "close": Decimal(values["4. close"]),
                "volume": int(values["5. volume"]),
            })
        
        # Sort by date ascending
        bars.sort(key=lambda x: x["date"])
        return bars
    
    def parse_daily_crypto(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse DIGITAL_CURRENCY_DAILY response into list of bars"""
        time_series = data.get("Time Series (Digital Currency Daily)", {})
        bars = []
        
        def _get_price_value(values: Dict[str, Any], field: str) -> Decimal:
            """
            Robust key lookup for crypto prices with fallbacks.
            Tries: "1a. open (USD)", "1. open", "open" (and similar for high/low/close)
            """
            # Define candidate keys in order of preference
            if field == "open":
                candidates = ["1a. open (USD)", "1. open", "open"]
            elif field == "high":
                candidates = ["2a. high (USD)", "2. high", "high"]
            elif field == "low":
                candidates = ["3a. low (USD)", "3. low", "low"]
            elif field == "close":
                candidates = ["4a. close (USD)", "4. close", "close"]
            else:
                candidates = [f"{field}"]
            
            # Try each candidate key
            for key in candidates:
                if key in values:
                    try:
                        return Decimal(str(values[key]))
                    except (ValueError, TypeError):
                        continue
            
            # If none found, raise error with available keys for debugging
            available_keys = list(values.keys())[:10]  # Sample first 10 keys
            raise ValueError(
                f"Crypto {field} not found. Tried: {candidates}. "
                f"Available keys (sample): {available_keys}"
            )
        
        for date_str, values in time_series.items():
            try:
                bars.append({
                    "date": datetime.strptime(date_str, "%Y-%m-%d").date(),
                    "open": _get_price_value(values, "open"),
                    "high": _get_price_value(values, "high"),
                    "low": _get_price_value(values, "low"),
                    "close": _get_price_value(values, "close"),
                    "volume": int(float(values.get("5. volume", 0) or 0)),
                })
            except (ValueError, KeyError) as e:
                # Log error but continue with other dates
                print(f"[AlphaVantage] Warning: Failed to parse {date_str}: {str(e)}")
                continue
        
        # Sort by date ascending
        bars.sort(key=lambda x: x["date"])
        return bars
    
    def get_latest_quote_equity(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest quote for equity (GLOBAL_QUOTE)
        Returns: { "Global Quote": { "05. price": "...", "07. latest trading day": "..." } }
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
        }
        return self._request(params)
    
    def parse_quote_equity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse GLOBAL_QUOTE response"""
        quote = data.get("Global Quote", {})
        if not quote:
            raise ValueError("No quote data in response")
        
        price = Decimal(quote.get("05. price", "0"))
        prev_close = Decimal(quote.get("08. previous close", "0"))
        change = price - prev_close if prev_close > 0 else None
        change_percent = (change / prev_close * 100) if change and prev_close > 0 else None
        
        return {
            "latest_price": price,
            "latest_date": datetime.strptime(quote.get("07. latest trading day", "2000-01-01"), "%Y-%m-%d"),
            "change": change,
            "change_percent": change_percent,
        }

