"""Tests maintenance sessions swap — expiration + réconciliation SUBMITTED."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from database import Person
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.lifi.swap_session_maintenance import (
    expire_stale_swap_sessions,
    reconcile_stuck_submitted_swaps,
)


def _migration_159_applied() -> bool:
    try:
        from sqlalchemy import inspect

        from database import engine

        return inspect(engine).has_table("person_wallet_swaps")
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_159_applied(),
    reason="Appliquer `alembic upgrade head` (159) pour les tests swap LI.FI.",
)


def _person_id(db: Session):
    row = db.query(Person).first()
    if row is None:
        pytest.skip("Aucune personne en base")
    return row.id


def test_expire_stale_quote_received(db: Session):
    person_id = _person_id(db)
    swap = PersonWalletSwap(
        id=uuid4(),
        person_id=person_id,
        status=SwapSessionStatus.QUOTE_RECEIVED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        slippage_bps=50,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        audit_log=[],
    )
    db.add(swap)
    db.commit()

    report = expire_stale_swap_sessions(db, dry_run=False, limit=10)
    db.refresh(swap)
    assert str(swap.id) in report["swap_ids"]
    assert swap.status == SwapSessionStatus.EXPIRED.value


def test_reconcile_submitted_stuck_dry_run(db: Session):
    person_id = _person_id(db)
    swap = PersonWalletSwap(
        id=uuid4(),
        person_id=person_id,
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        slippage_bps=50,
        tx_hash="0xabc123def4567890abc123def4567890abc123def4567890abc123def4567890",
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=15),
        audit_log=[],
    )
    db.add(swap)
    db.commit()

    mock_svc = MagicMock()
    report = reconcile_stuck_submitted_swaps(db, dry_run=True, execute_service=mock_svc, limit=10)
    assert report["polled"] == 1
    mock_svc.refresh_lifi_status.assert_not_called()
