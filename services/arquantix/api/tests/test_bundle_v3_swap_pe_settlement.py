"""Tests settlement PE bundle V3 — confirmation async + validation montants."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import (
    BundleLifiLegService,
)
from services.portfolio_engine.bundle_execution.bundle_swap_pe_settlement import (
    SETTLEMENT_RECEIPT_EVENT,
    swap_needs_pe_settlement,
    try_settle_confirmed_bundle_swap,
)
from services.portfolio_engine.bundle_execution.pe_settlement import BundlePeSettlementError
from services.portfolio_engine.bundle_execution.types import ExecutionLeg


def _swap(*, status: str, audit: list | None = None) -> PersonWalletSwap:
    return PersonWalletSwap(
        id=uuid.uuid4(),
        person_id=uuid.uuid4(),
        from_asset="USDC",
        to_asset="CBETH",
        amount_in=Decimal("3.5"),
        estimated_receive=Decimal("0.002"),
        status=status,
        audit_log=audit or [],
    )


def _leg() -> ExecutionLeg:
    return ExecutionLeg(
        leg_id="v3-rebal-test-ETH-a1",
        portfolio_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        action="rebalance_buy",
        from_asset="USDC",
        to_asset="CBETH",
        amount_from=Decimal("3.5"),
        batch_id=str(uuid.uuid4()),
        bundle_action="rebalance_v3",
        chain="base",
        metadata={
            "entry_instrument_id": str(uuid.uuid4()),
            "target_instrument_id": str(uuid.uuid4()),
        },
    )


def test_swap_needs_pe_settlement_when_confirmed_without_receipt():
    swap = _swap(
        status=SwapSessionStatus.CONFIRMED.value,
        audit=[{"event": "bundle_leg_context", "bundle_execution": True, "batch_id": "b1",
                "portfolio_id": str(uuid.uuid4()), "client_id": str(uuid.uuid4()),
                "bundle_action": "rebalance_v3", "leg_action": "rebalance_buy",
                "entry_instrument_id": str(uuid.uuid4()),
                "target_instrument_id": str(uuid.uuid4())}],
    )
    assert swap_needs_pe_settlement(swap) is True


def test_swap_needs_pe_settlement_false_when_receipt_present():
    swap = _swap(
        status=SwapSessionStatus.CONFIRMED.value,
        audit=[{"event": SETTLEMENT_RECEIPT_EVENT}],
    )
    assert swap_needs_pe_settlement(swap) is False


def test_validate_settlement_rejects_zero_amount_out():
    svc = BundleLifiLegService()
    leg = _leg()
    with pytest.raises(BundlePeSettlementError, match="settlement_amount_out_invalid"):
        svc._validate_settlement_amounts(
            leg=leg, amount_in=Decimal("3.5"), amount_out=Decimal("0"),
        )


@patch.object(BundleLifiLegService, "_apply_post_confirmation")
def test_try_settle_calls_apply_for_confirmed_bundle_swap(
    mock_apply: MagicMock,
):
    leg = _leg()
    swap = _swap(
        status=SwapSessionStatus.CONFIRMED.value,
        audit=[{
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "batch_id": leg.batch_id,
            "portfolio_id": str(leg.portfolio_id),
            "client_id": str(leg.client_id),
            "bundle_action": "rebalance_v3",
            "leg_action": "rebalance_buy",
            "leg_id": leg.leg_id,
            "entry_instrument_id": leg.metadata["entry_instrument_id"],
            "target_instrument_id": leg.metadata["target_instrument_id"],
        }],
    )
    db = MagicMock()
    assert try_settle_confirmed_bundle_swap(db, swap) is True
    mock_apply.assert_called_once()
