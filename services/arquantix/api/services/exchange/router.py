"""FastAPI router for Exchange Engine v1."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

from .schemas import (
    ExchangeBuyRequest,
    ExchangeBuyResponse,
    ExchangeSellRequest,
    ExchangeSellResponse,
    SettlementRunResponse,
)
from .service import (
    AccountNotFoundError,
    DuplicateOrderError,
    ExchangeError,
    ExchangeService,
    FxUnavailableError,
    InsufficientCryptoBalanceError,
    InsufficientFundsError,
    MarketQuoteStaleError,
    PriceUnavailableError,
    UnsupportedAssetError,
)
from services.portfolio_engine.provisioning.errors import ClientNotEligibleError

exchange_router = APIRouter(tags=["exchange"])
_guard = require_admin_or_ops()
_svc = ExchangeService()


@exchange_router.post("/api/exchange/buy", response_model=ExchangeBuyResponse)
def exchange_buy(
    payload: ExchangeBuyRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = _svc.buy(db, payload, actor)
        db.commit()
        return ExchangeBuyResponse(**result)
    except ClientNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except UnsupportedAssetError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except MarketQuoteStaleError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except (PriceUnavailableError, FxUnavailableError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InsufficientFundsError:
        return ExchangeBuyResponse(status="failed", error="insufficient_funds")
    except DuplicateOrderError:
        return ExchangeBuyResponse(status="ignored", reason="duplicate_external_reference")


@exchange_router.post("/api/exchange/sell", response_model=ExchangeSellResponse)
def exchange_sell(
    payload: ExchangeSellRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = _svc.sell(db, payload, actor)
        db.commit()
        return ExchangeSellResponse(**result)
    except ClientNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except UnsupportedAssetError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except MarketQuoteStaleError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except (PriceUnavailableError, FxUnavailableError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InsufficientCryptoBalanceError:
        return ExchangeSellResponse(status="failed", error="insufficient_crypto_balance")
    except InsufficientFundsError:
        return ExchangeSellResponse(status="failed", error="insufficient_settlement_eur")
    except ExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@exchange_router.post("/api/exchange/settlement", response_model=SettlementRunResponse)
def run_settlement(
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    result = _svc.run_settlement(db, actor)
    db.commit()
    return SettlementRunResponse(**result)
