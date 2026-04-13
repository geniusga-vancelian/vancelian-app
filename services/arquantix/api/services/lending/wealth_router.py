"""Wealth & Lending visibility API — Phase 2A.5.

Provides read-only endpoints for the wealth management view:
  - Total portfolio value (spot + lending - borrowing)
  - Lending positions detail
  - Borrowing positions detail

Identité : le client est résolu via le JWT (``mobile_app_client``), pas via un
``client_id`` arbitraire en query (évite l’accès inter-clients).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio_engine.clients.models import Client as PeClient
from services.test_clients.mobile_identity import mobile_app_client

from .valuation import (
    compute_total_portfolio_value_v2,
    get_lending_positions,
    get_borrowing_positions,
)

router = APIRouter(prefix="/api/app", tags=["Wealth & Lending"])


@router.get("/portfolio/wealth")
def get_portfolio_wealth(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Wealth view: spot + lending - borrowing.

    Returns a structured breakdown of the client's total portfolio value
    across all position types. Uses the same pricing source as spot.
    """
    try:
        wealth = compute_total_portfolio_value_v2(db, client.id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wealth computation failed: {exc}",
        )

    return {
        "client_id": str(client.id),
        "currency": "EUR",
        "spot": {
            "value": wealth["spot_value_eur"],
            "count": wealth["spot_count"],
        },
        "lending": {
            "value": wealth["lending_value_eur"],
            "count": wealth["lending_count"],
            "positions": wealth["lending_positions"],
        },
        "borrowing": {
            "value": wealth["borrowing_value_eur"],
            "count": wealth["borrowing_count"],
            "positions": wealth["borrowing_positions"],
        },
        "net": {
            "value": wealth["net_value_eur"],
        },
    }


@router.get("/lending/positions")
def list_lending_positions(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """List all open lending positions with market values."""
    positions = get_lending_positions(db, client.id)
    return {
        "client_id": str(client.id),
        "count": len(positions),
        "positions": positions,
    }


@router.get("/borrowing/positions")
def list_borrowing_positions(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """List all open borrowing positions with market values."""
    positions = get_borrowing_positions(db, client.id)
    return {
        "client_id": str(client.id),
        "count": len(positions),
        "positions": positions,
    }
