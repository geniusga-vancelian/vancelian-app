"""Tests — ADR 007 S1 Settlement Router."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.settlement.swap_router import (
    SCOPE_BUNDLE_PORTFOLIO,
    SCOPE_SELF_TRADING,
    SCOPE_SKIPPED,
    resolve_settlement_scope,
    settle_confirmed_swap,
)
from conftest import make_linked_client


def _swap_stub(*, person_id: uuid.UUID, bundle_internal: bool, confirmed: bool) -> PersonWalletSwap:
    audit = []
    if bundle_internal:
        audit.append({
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "bundle_action": "rebalance_buy",
            "batch_id": str(uuid.uuid4()),
        })
    status = SwapSessionStatus.CONFIRMED.value if confirmed else SwapSessionStatus.QUOTE_RECEIVED.value
    return PersonWalletSwap(
        person_id=person_id,
        status=status,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        audit_log=audit,
    )


def test_resolve_scope_bundle_internal():
    swap = _swap_stub(person_id=uuid.uuid4(), bundle_internal=True, confirmed=True)
    assert resolve_settlement_scope(swap) == SCOPE_BUNDLE_PORTFOLIO


def test_resolve_scope_standalone():
    swap = _swap_stub(person_id=uuid.uuid4(), bundle_internal=False, confirmed=True)
    assert resolve_settlement_scope(swap) == SCOPE_SELF_TRADING


def test_settle_skips_when_not_confirmed(db: Session):
    pe = make_linked_client(db)
    swap = _swap_stub(person_id=pe.person_id, bundle_internal=False, confirmed=False)
    db.add(swap)
    db.flush()

    result = settle_confirmed_swap(db, swap)
    assert result.skipped is True
    assert result.scope == SCOPE_SKIPPED


def test_settle_routes_bundle_to_pe_handler(db: Session):
    pe = make_linked_client(db)
    swap = _swap_stub(person_id=pe.person_id, bundle_internal=True, confirmed=True)
    db.add(swap)
    db.flush()

    with patch(
        "services.portfolio_engine.bundle_execution.bundle_swap_pe_settlement.try_settle_confirmed_bundle_swap",
        return_value=True,
    ) as bundle_mock:
        result = settle_confirmed_swap(db, swap)

    bundle_mock.assert_called_once()
    assert result.settled is True
    assert result.scope == SCOPE_BUNDLE_PORTFOLIO


def test_settle_routes_standalone_to_apply_swap_settlement(db: Session):
    pe = make_linked_client(db)
    swap = _swap_stub(person_id=pe.person_id, bundle_internal=False, confirmed=True)
    swap.tx_hash = "0xabc"
    db.add(swap)
    db.flush()

    with patch(
        "services.settlement.swap_router.apply_swap_settlement",
    ) as apply_mock:
        result = settle_confirmed_swap(db, swap)

    apply_mock.assert_called_once()
    assert result.settled is True
    assert result.scope == SCOPE_SELF_TRADING
