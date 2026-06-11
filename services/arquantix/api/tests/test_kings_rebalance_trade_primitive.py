"""Gate pilote Kings — trade primitive wiring (ADR 008)."""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from services.trade_core.types import TradeRequest


def test_trade_request_carries_wallet_ids():
    wallet_from = uuid.uuid4()
    wallet_to = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    client_id = uuid.uuid4()
    correlation = uuid.uuid4()

    req = TradeRequest(
        wallet_from_id=wallet_from,
        wallet_to_id=wallet_to,
        instrument_from_id=uuid.uuid4(),
        instrument_to_id=uuid.uuid4(),
        quantity_from=Decimal("42.38"),
        correlation_id=correlation,
        client_id=client_id,
        portfolio_id=portfolio_id,
        from_asset="USDC",
        to_asset="BTC",
        leg_id="v3-rebal-test-rebalance_buy-BTC-a1",
        batch_id=str(uuid.uuid4()),
        bundle_action="rebalance_v3",
        leg_action="rebalance_buy",
    )
    assert req.wallet_from_id == wallet_from
    assert req.wallet_to_id == wallet_to
    assert req.metadata == {}


@patch(
    "services.portfolio_engine.bundle_execution.bundle_lifi_leg_service.BundleLifiLegService",
)
def test_execute_trade_delegates_to_bundle_leg_service(mock_svc_cls):
    from services.trade_core.execute_trade import execute_trade

    swap_id = uuid.uuid4()
    mock_svc = MagicMock()
    mock_svc_cls.return_value = mock_svc
    mock_svc._person_id_for_client.return_value = uuid.uuid4()
    mock_svc.execute_leg.return_value = MagicMock(
        leg_id="leg-1",
        status="pending",
        from_asset="USDC",
        to_asset="BTC",
        amount_from=Decimal("42"),
        amount_to=Decimal("0.001"),
        tx_hash=None,
        provider_order_id=str(swap_id),
        raw={"requires_client_signature": True, "swap_id": str(swap_id)},
    )

    mock_db = MagicMock()
    mock_swap = MagicMock()
    mock_swap.audit_log = []

    with patch("services.trade_core.execute_trade.PersonWalletSwapRepository") as mock_repo_cls:
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.get_for_person.return_value = mock_swap

        req = TradeRequest(
            wallet_from_id=uuid.uuid4(),
            wallet_to_id=uuid.uuid4(),
            instrument_from_id=uuid.uuid4(),
            instrument_to_id=uuid.uuid4(),
            quantity_from=Decimal("42"),
            correlation_id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            portfolio_id=uuid.uuid4(),
            from_asset="USDC",
            to_asset="BTC",
            leg_id="leg-1",
            batch_id="batch-1",
            bundle_action="rebalance_v3",
            leg_action="rebalance_buy",
        )
        result = execute_trade(mock_db, req, actor=MagicMock())

    assert result.swap_id == swap_id
    assert result.status == "awaiting_signature"
    assert result.requires_client_signature is True
    mock_repo.append_audit.assert_called()
