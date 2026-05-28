"""Tests refresh statut LI.FI → CONFIRMED."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_client import LifiClient
from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.models import PersonWalletSwap


@pytest.fixture
def submitted_swap():
    return PersonWalletSwap(
        id=uuid4(),
        person_id=uuid4(),
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="ethereum",
        amount_in=Decimal("1000"),
        tx_hash="0xabc123",
        lifi_tool="stargateV2",
        lifi_quote_raw={
            "action": {"fromChainId": 8453, "toChainId": 1},
        },
        audit_log=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_refresh_lifi_status_confirmed(submitted_swap):
    from services.lifi.lifi_actual_receive import LifiActualReceiveResult

    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_status.return_value = {
        "status": "DONE",
        "substatus": "COMPLETED",
        "substatusMessage": "The transfer is complete.",
        "receiving": {
            "amount": "500000000000000000",
            "token": {"symbol": "ETH", "decimals": 18},
        },
    }
    svc = LifiExecuteService(lifi_client=mock_client)
    db = MagicMock()
    actual = LifiActualReceiveResult(amount=Decimal("0.5"), source="lifi_status_receiving")

    with patch(
        "services.lifi.lifi_execute_service.resolve_lifi_actual_receive_amount",
        return_value=actual,
    ):
        with patch("services.lifi.lifi_execute_service.apply_swap_settlement") as mock_settle:
            svc.refresh_lifi_status(db, submitted_swap)

    assert submitted_swap.status == SwapSessionStatus.CONFIRMED.value
    assert submitted_swap.confirmed_at is not None
    mock_settle.assert_called_once()
    mock_client.get_status.assert_called_once_with(
        tx_hash="0xabc123",
        bridge="stargateV2",
        from_chain=8453,
        to_chain=1,
    )
    db.commit.assert_called()


def test_refresh_lifi_status_stays_submitted_when_pending(submitted_swap):
    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_status.return_value = {"status": "PENDING", "substatus": "WAIT_DESTINATION_TRANSACTION"}
    svc = LifiExecuteService(lifi_client=mock_client)
    db = MagicMock()

    svc.refresh_lifi_status(db, submitted_swap)

    assert submitted_swap.status == SwapSessionStatus.SUBMITTED.value
    db.commit.assert_called()


def test_refresh_lifi_status_failed(submitted_swap):
    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_status.return_value = {
        "status": "FAILED",
        "substatus": "SLIPPAGE_EXCEEDED",
        "substatusMessage": "Slippage too high",
    }
    svc = LifiExecuteService(lifi_client=mock_client)
    db = MagicMock()

    svc.refresh_lifi_status(db, submitted_swap)

    assert submitted_swap.status == SwapSessionStatus.FAILED.value
    assert "Slippage" in (submitted_swap.error_message or "")
