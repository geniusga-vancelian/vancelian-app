"""
Minimal Binance REST client for latest quote (ticker) data.
Uses public market data only; no API key required.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .config import BINANCE_REST_BASE_URL, BINANCE_TIMEOUT_SECONDS

# Normalized quote structure returned to callers
QUOTE_KEYS = ("provider_symbol", "last_price", "bid_price", "ask_price", "volume", "quote_time")


def _parse_quote_time(close_time_ms: Optional[int]) -> Optional[datetime]:
    if close_time_ms is None:
        return None
    try:
        return datetime.fromtimestamp(close_time_ms / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def fetch_ticker(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch 24h ticker for one symbol from Binance public API.
    Returns a normalized dict or None on failure.

    Normalized fields:
      provider_symbol, last_price, bid_price, ask_price, volume, quote_time
    """
    base = (BINANCE_REST_BASE_URL or "https://api.binance.com").rstrip("/")
    url = f"{base}/api/v3/ticker/24hr"
    params = {"symbol": symbol.upper()}
    try:
        with httpx.Client(timeout=BINANCE_TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        return None

    if not isinstance(data, dict) or "lastPrice" not in data:
        return None

    last = float(data.get("lastPrice", 0))
    bid = data.get("bidPrice")
    ask = data.get("askPrice")
    vol = data.get("volume")
    close_time_ms = data.get("closeTime")
    try:
        bid_price = float(bid) if bid is not None else None
    except (TypeError, ValueError):
        bid_price = None
    try:
        ask_price = float(ask) if ask is not None else None
    except (TypeError, ValueError):
        ask_price = None
    try:
        volume = float(vol) if vol is not None else None
    except (TypeError, ValueError):
        volume = None
    quote_time = _parse_quote_time(close_time_ms)

    return {
        "provider_symbol": data.get("symbol") or symbol,
        "last_price": last,
        "bid_price": bid_price,
        "ask_price": ask_price,
        "volume": volume,
        "quote_time": quote_time,
    }


def _klines_open_time_ms(candle: list) -> Optional[datetime]:
    """Parse open_time from Binance kline array (index 0, ms)."""
    try:
        ms = candle[0]
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    except (IndexError, TypeError, ValueError, OSError):
        return None


def fetch_klines_1m(
    symbol: str,
    limit: int = 500,
    start_time_ms: Optional[int] = None,
    end_time_ms: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Fetch 1-minute klines from Binance REST."""
    base = (BINANCE_REST_BASE_URL or "https://api.binance.com").rstrip("/")
    url = f"{base}/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": "1m", "limit": min(limit, 1000)}
    if start_time_ms is not None:
        params["startTime"] = start_time_ms
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    try:
        with httpx.Client(timeout=BINANCE_TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    out = []
    for candle in data:
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            continue
        open_time = _klines_open_time_ms(candle)
        if open_time is None:
            continue
        try:
            o = float(candle[1])
            h = float(candle[2])
            l = float(candle[3])
            c = float(candle[4])
            v = float(candle[5])
        except (TypeError, ValueError, IndexError):
            continue
        out.append({
            "open_time": open_time,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        })
    return out


def fetch_klines_5m(
    symbol: str,
    limit: int = 500,
    start_time_ms: Optional[int] = None,
    end_time_ms: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch 5-minute klines from Binance REST.
    Returns list of normalized candles or None on failure.

    Normalized candle: open_time (datetime tz utc), open, high, low, close, volume (all float).
    """
    base = (BINANCE_REST_BASE_URL or "https://api.binance.com").rstrip("/")
    url = f"{base}/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": "5m", "limit": min(limit, 1000)}
    if start_time_ms is not None:
        params["startTime"] = start_time_ms
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    try:
        with httpx.Client(timeout=BINANCE_TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    out = []
    for candle in data:
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            continue
        open_time = _klines_open_time_ms(candle)
        if open_time is None:
            continue
        try:
            o = float(candle[1])
            h = float(candle[2])
            l = float(candle[3])
            c = float(candle[4])
            v = float(candle[5])
        except (TypeError, ValueError, IndexError):
            continue
        out.append({
            "open_time": open_time,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        })
    return out


def fetch_klines_1h(
    symbol: str,
    limit: int = 500,
    start_time_ms: Optional[int] = None,
    end_time_ms: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch 1-hour klines from Binance REST.
    Returns list of normalized candles or None on failure.

    Normalized candle: open_time (datetime tz utc), open, high, low, close, volume (all float).
    """
    base = (BINANCE_REST_BASE_URL or "https://api.binance.com").rstrip("/")
    url = f"{base}/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": "1h", "limit": min(limit, 1000)}
    if start_time_ms is not None:
        params["startTime"] = start_time_ms
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    try:
        with httpx.Client(timeout=BINANCE_TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    out = []
    for candle in data:
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            continue
        open_time = _klines_open_time_ms(candle)
        if open_time is None:
            continue
        try:
            o = float(candle[1])
            h = float(candle[2])
            l = float(candle[3])
            c = float(candle[4])
            v = float(candle[5])
        except (TypeError, ValueError, IndexError):
            continue
        out.append({
            "open_time": open_time,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        })
    return out


def fetch_klines_4h(
    symbol: str,
    limit: int = 500,
    start_time_ms: Optional[int] = None,
    end_time_ms: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch 4-hour klines from Binance REST.
    Returns list of normalized candles or None on failure.

    Normalized candle: open_time (datetime tz utc), open, high, low, close, volume (all float).
    """
    base = (BINANCE_REST_BASE_URL or "https://api.binance.com").rstrip("/")
    url = f"{base}/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": "4h", "limit": min(limit, 1000)}
    if start_time_ms is not None:
        params["startTime"] = start_time_ms
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    try:
        with httpx.Client(timeout=BINANCE_TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    out = []
    for candle in data:
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            continue
        open_time = _klines_open_time_ms(candle)
        if open_time is None:
            continue
        try:
            o = float(candle[1])
            h = float(candle[2])
            l = float(candle[3])
            c = float(candle[4])
            v = float(candle[5])
        except (TypeError, ValueError, IndexError):
            continue
        out.append({
            "open_time": open_time,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        })
    return out


def fetch_klines_1d(
    symbol: str,
    limit: int = 500,
    start_time_ms: Optional[int] = None,
    end_time_ms: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch 1-day klines from Binance REST.
    Returns list of normalized candles or None on failure.

    Normalized candle: open_time (datetime tz utc), open, high, low, close, volume (all float).
    """
    base = (BINANCE_REST_BASE_URL or "https://api.binance.com").rstrip("/")
    url = f"{base}/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": "1d", "limit": min(limit, 1000)}
    if start_time_ms is not None:
        params["startTime"] = start_time_ms
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    try:
        with httpx.Client(timeout=BINANCE_TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    out = []
    for candle in data:
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            continue
        open_time = _klines_open_time_ms(candle)
        if open_time is None:
            continue
        try:
            o = float(candle[1])
            h = float(candle[2])
            l = float(candle[3])
            c = float(candle[4])
            v = float(candle[5])
        except (TypeError, ValueError, IndexError):
            continue
        out.append({
            "open_time": open_time,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        })
    return out


def fetch_klines_1w(
    symbol: str,
    limit: int = 500,
    start_time_ms: Optional[int] = None,
    end_time_ms: Optional[int] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch 1-week klines from Binance REST.
    Returns list of normalized candles or None on failure.

    Normalized candle: open_time (datetime tz utc), open, high, low, close, volume (all float).
    """
    base = (BINANCE_REST_BASE_URL or "https://api.binance.com").rstrip("/")
    url = f"{base}/api/v3/klines"
    params = {"symbol": symbol.upper(), "interval": "1w", "limit": min(limit, 1000)}
    if start_time_ms is not None:
        params["startTime"] = start_time_ms
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    try:
        with httpx.Client(timeout=BINANCE_TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not isinstance(data, list):
        return None
    out = []
    for candle in data:
        if not isinstance(candle, (list, tuple)) or len(candle) < 6:
            continue
        open_time = _klines_open_time_ms(candle)
        if open_time is None:
            continue
        try:
            o = float(candle[1])
            h = float(candle[2])
            l = float(candle[3])
            c = float(candle[4])
            v = float(candle[5])
        except (TypeError, ValueError, IndexError):
            continue
        out.append({
            "open_time": open_time,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": v,
        })
    return out
