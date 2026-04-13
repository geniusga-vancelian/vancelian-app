"""Address lookup (Google Places proxy) — API key server-only."""
from .routes import router as address_router

__all__ = ["address_router"]
