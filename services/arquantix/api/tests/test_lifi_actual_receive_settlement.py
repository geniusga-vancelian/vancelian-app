"""Tests settlement LI.FI Phase 2 — montant réel (pas estimated_receive)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_actual_receive import (
    LifiActualReceiveResult,
    resolve_lifi_actual_receive_amount,
)
from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.lifi_swap_settlement import (
    SwapSettlementBlocked,
    apply_swap_settlement,
    swap_settlement_already_applied,
)
from services.lifi.models import PersonWalletSwap
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from services.privy_wallet.service import PrivyWalletLedgerService
from tests.conftest import make_linked_client

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
PRIVY_USER = "did:privy:testlifiactual001"


def _seed_wallet(db: Session, pe):
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=PRIVY_USER,
        external_email="lifi-actual@test.local",
    )
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-actual"},
    )
    db.commit()


def _make_confirmed_swap(person_id, *, estimated: str = "0.01", to_asset: str = "ETH") -> PersonWalletSwap:
    return PersonWalletSwap(
        id=uuid4(),
        person_id=person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset=to_asset,
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("12"),
        estimated_receive=Decimal(estimated),
        tx_hash="0xswapbaseeth1234567890abcdef1234567890abcdef1234567890abcdef12",
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        confirmed_at=datetime.now(timezone.utc),
    )


def test_apply_swap_settlement_credits_amount_actual_not_estimate(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="25",
            chain_id=8453,
        ),
    )
    db.commit()

    swap = _make_confirmed_swap(pe.person_id, estimated="0.01")
    db.add(swap)
    db.flush()

    actual = Decimal("0.00475")
    apply_swap_settlement(
        db,
        swap,
        sync_source="lifi_swap",
        amount_actual=actual,
    )
    db.commit()

    balances = PrivyWalletLedgerService().get_balances(db, person_id=pe.person_id).balances
    eth = next(b for b in balances if b.asset == "ETH")
    assert Decimal(eth.balance) == actual
    assert Decimal(eth.balance) != Decimal("0.01")


def test_apply_swap_settlement_blocked_when_amount_actual_missing(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap = _make_confirmed_swap(pe.person_id)
    db.add(swap)
    db.flush()

    with patch(
        "services.lifi.lifi_swap_settlement.resolve_lifi_actual_receive_amount",
        return_value=None,
    ):
        with pytest.raises(SwapSettlementBlocked) as exc_info:
            apply_swap_settlement(db, swap, sync_source="lifi_swap")
        assert exc_info.value.code == "actual_amount_missing"


def test_apply_swap_settlement_idempotent(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="20",
            chain_id=8453,
        ),
    )
    db.commit()

    swap = _make_confirmed_swap(pe.person_id)
    db.add(swap)
    db.flush()

    apply_swap_settlement(db, swap, sync_source="lifi_swap", amount_actual=Decimal("0.00475"))
    swap.audit_log = [{"event": "swap_settled"}]
    db.commit()
    assert swap_settlement_already_applied(swap) is True

    balances_before = PrivyWalletLedgerService().get_balances(db, person_id=pe.person_id).balances
    eth_before = next(b for b in balances_before if b.asset == "ETH").balance

    apply_swap_settlement(db, swap, sync_source="lifi_swap", amount_actual=Decimal("99"))
    db.commit()

    eth_after = next(
        b for b in PrivyWalletLedgerService().get_balances(db, person_id=pe.person_id).balances if b.asset == "ETH"
    ).balance
    assert eth_after == eth_before


def test_resolve_prefers_lifi_status_receiving_amount():
    payload = {
        "status": "DONE",
        "substatus": "COMPLETED",
        "receiving": {
            "amount": "4750000000000000",
            "token": {"symbol": "ETH", "decimals": 18},
            "txHash": "0xrecv1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        },
    }
    swap = MagicMock()
    swap.to_asset = "ETH"
    swap.estimated_receive = Decimal("0.01")

    with patch(
        "services.lifi.lifi_actual_receive._amount_from_on_chain_receive",
        return_value=None,
    ):
        result = resolve_lifi_actual_receive_amount(MagicMock(), swap, lifi_status_payload=payload)

    assert result is not None
    assert result.amount == Decimal("0.00475")
    assert result.source == "lifi_status_receiving"


def test_refresh_lifi_status_partial_does_not_confirm(submitted_swap):
    mock_client = MagicMock()
    mock_client.get_status.return_value = {
        "status": "DONE",
        "substatus": "PARTIAL",
        "substatusMessage": "Received different token",
    }
    svc = LifiExecuteService(lifi_client=mock_client)
    db = MagicMock()

    with patch("services.lifi.lifi_execute_service.apply_swap_settlement") as mock_settle:
        svc.refresh_lifi_status(db, submitted_swap)

    assert submitted_swap.status == SwapSessionStatus.SUBMITTED.value
    assert submitted_swap.confirmed_at is None
    mock_settle.assert_not_called()
    audit_events = [e.get("event") for e in submitted_swap.audit_log if isinstance(e, dict)]
    assert "partial_confirmed" in audit_events


def test_refresh_lifi_status_completed_without_amount_blocks_settlement(submitted_swap):
    mock_client = MagicMock()
    mock_client.get_status.return_value = {
        "status": "DONE",
        "substatus": "COMPLETED",
        "substatusMessage": "Complete",
    }
    svc = LifiExecuteService(lifi_client=mock_client)
    db = MagicMock()

    with patch(
        "services.lifi.lifi_execute_service.resolve_lifi_actual_receive_amount",
        return_value=None,
    ):
        with patch("services.lifi.lifi_execute_service.apply_swap_settlement") as mock_settle:
            svc.refresh_lifi_status(db, submitted_swap)

    assert submitted_swap.status == SwapSessionStatus.CONFIRMED.value
    mock_settle.assert_not_called()
    assert any(
        isinstance(e, dict) and e.get("event") == "settlement_blocked" and e.get("reason") == "actual_amount_missing"
        for e in submitted_swap.audit_log
    )


def test_refresh_lifi_status_completed_settles_actual_amount(submitted_swap):
    mock_client = MagicMock()
    mock_client.get_status.return_value = {
        "status": "DONE",
        "substatus": "COMPLETED",
        "receiving": {"amount": "1000000000000000000", "token": {"symbol": "ETH", "decimals": 18}},
    }
    svc = LifiExecuteService(lifi_client=mock_client)
    db = MagicMock()
    actual = LifiActualReceiveResult(amount=Decimal("1"), source="lifi_status_receiving")

    with patch(
        "services.lifi.lifi_execute_service.resolve_lifi_actual_receive_amount",
        return_value=actual,
    ):
        with patch("services.lifi.lifi_execute_service.apply_swap_settlement") as mock_settle:
            svc.refresh_lifi_status(db, submitted_swap)

    assert submitted_swap.status == SwapSessionStatus.CONFIRMED.value
    mock_settle.assert_called_once()
    kwargs = mock_settle.call_args.kwargs
    assert kwargs["actual_receive"] == actual


def test_refresh_lifi_status_failed_no_settlement(submitted_swap):
    mock_client = MagicMock()
    mock_client.get_status.return_value = {
        "status": "FAILED",
        "substatus": "SLIPPAGE_EXCEEDED",
        "substatusMessage": "Slippage too high",
    }
    svc = LifiExecuteService(lifi_client=mock_client)
    db = MagicMock()

    with patch("services.lifi.lifi_execute_service.apply_swap_settlement") as mock_settle:
        svc.refresh_lifi_status(db, submitted_swap)

    assert submitted_swap.status == SwapSessionStatus.FAILED.value
    mock_settle.assert_not_called()


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
        estimated_receive=Decimal("0.5"),
        tx_hash="0xabc123",
        lifi_tool="stargateV2",
        lifi_quote_raw={"action": {"fromChainId": 8453, "toChainId": 1}},
        audit_log=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
