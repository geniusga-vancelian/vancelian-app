"""Snapshots API — placeholder. See docs/portfolio_engine/PRD_MULTI_ASSET_WALLET.md."""
from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_snapshots_placeholder():
    """Placeholder: list portfolio/position snapshots. TODO: implement with repository + schemas."""
    return {"module": "snapshots", "status": "placeholder"}
