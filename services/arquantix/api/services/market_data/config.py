"""
Market Data configuration
Loads environment variables following audit pattern (os.getenv, no Pydantic Settings)
"""
import os

MARKET_DATA_PROVIDER = os.getenv("MARKET_DATA_PROVIDER", "binance")

# Binance (latest quote ingestion)
BINANCE_REST_BASE_URL = os.getenv("BINANCE_REST_BASE_URL", "https://api.binance.com")
_t = os.getenv("BINANCE_TIMEOUT_SECONDS", "10")
BINANCE_TIMEOUT_SECONDS = int(_t) if (_t and _t.strip()) else 10
BINANCE_INGESTION_ENABLED = (os.getenv("BINANCE_INGESTION_ENABLED", "true").lower() in ("true", "1", "yes"))

# Binance WebSocket (Spot combined stream)
BINANCE_WS_BASE_URL = os.getenv("BINANCE_WS_BASE_URL", "wss://stream.binance.com:9443")
BINANCE_WS_INGESTION_COMMIT_BATCH_SIZE = int(os.getenv("BINANCE_WS_INGESTION_COMMIT_BATCH_SIZE", "20") or "20")
BINANCE_WS_INGESTION_COMMIT_INTERVAL_SEC = float(os.getenv("BINANCE_WS_INGESTION_COMMIT_INTERVAL_SEC", "2.0") or "2.0")
BINANCE_WS_RECONNECT_BASE_DELAY_SEC = float(os.getenv("BINANCE_WS_RECONNECT_BASE_DELAY_SEC", "1.0") or "1.0")
BINANCE_WS_RECONNECT_MAX_DELAY_SEC = float(os.getenv("BINANCE_WS_RECONNECT_MAX_DELAY_SEC", "60.0") or "60.0")





