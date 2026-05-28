"""Compat — règlement mock swap via le ledger partagé."""
from __future__ import annotations

from sqlalchemy.orm import Session

from services.lifi.lifi_swap_settlement import apply_swap_settlement


def apply_mock_swap_settlement(db: Session, swap) -> None:
    apply_swap_settlement(db, swap, sync_source="lifi_mock_swap", allow_mock_quote_amount=True)
