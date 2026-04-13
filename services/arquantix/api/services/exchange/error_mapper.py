"""Centralized HTTP error mapping for Exchange module exceptions.

Provides consistent error responses across all exchange endpoints (admin + mobile).
"""
from __future__ import annotations

from fastapi import HTTPException, status

from .service import (
    AccountNotFoundError,
    DuplicateOrderError,
    ExchangeError,
    FxUnavailableError,
    InsufficientCryptoBalanceError,
    InsufficientFundsError,
    MarketQuoteStaleError,
    PriceUnavailableError,
    UnsupportedAssetError,
)
from services.portfolio_engine.provisioning.errors import ClientNotEligibleError

_ERROR_MAP: dict[type, tuple[int, str]] = {
    ClientNotEligibleError:        (status.HTTP_403_FORBIDDEN,                "CLIENT_NOT_ELIGIBLE"),
    UnsupportedAssetError:         (status.HTTP_400_BAD_REQUEST,              "UNSUPPORTED_ASSET"),
    InsufficientFundsError:        (status.HTTP_409_CONFLICT,                 "INSUFFICIENT_FUNDS"),
    InsufficientCryptoBalanceError:(status.HTTP_409_CONFLICT,                 "INSUFFICIENT_CRYPTO_BALANCE"),
    DuplicateOrderError:           (status.HTTP_409_CONFLICT,                 "DUPLICATE_ORDER"),
    AccountNotFoundError:          (status.HTTP_404_NOT_FOUND,                "ACCOUNT_NOT_FOUND"),
    MarketQuoteStaleError:         (status.HTTP_503_SERVICE_UNAVAILABLE,      "MARKET_QUOTE_STALE"),
    PriceUnavailableError:         (status.HTTP_503_SERVICE_UNAVAILABLE,      "PRICE_UNAVAILABLE"),
    FxUnavailableError:            (status.HTTP_503_SERVICE_UNAVAILABLE,      "FX_UNAVAILABLE"),
}


def raise_exchange_error(exc: ExchangeError) -> None:
    """Convert an ExchangeError subclass into an HTTPException with stable body."""
    for exc_type, (http_code, error_code) in _ERROR_MAP.items():
        if isinstance(exc, exc_type):
            raise HTTPException(
                status_code=http_code,
                detail={
                    "status": "failed",
                    "error_code": error_code,
                    "message": str(exc),
                },
            )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "status": "failed",
            "error_code": "EXCHANGE_ERROR",
            "message": str(exc),
        },
    )
