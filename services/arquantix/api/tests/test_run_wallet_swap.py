"""Tests — run_virtual_wallet_swap (ADR 008)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from services.trade_core.run_wallet_swap import (
    VirtualWalletSwapError,
    VirtualWalletSwapRequest,
    build_trade_request_from_wallets,
    quote_virtual_wallet_swap,
)


def _wallet(*, wallet_id, portfolio_id, instrument_id, wallet_type):
    w = MagicMock()
    w.id = wallet_id
    w.portfolio_id = portfolio_id
    w.instrument_id = instrument_id
    w.wallet_type = wallet_type
    w.status = "active"
    return w


def _instrument(instrument_id, symbol):
    inst = MagicMock()
    inst.id = instrument_id
    asset = MagicMock()
    asset.symbol = symbol
    inst.asset = asset
    return inst


@patch("services.trade_core.run_wallet_swap._asset_symbol_for_wallet")
@patch("services.trade_core.run_wallet_swap._load_wallet")
def test_build_trade_request_buy_maps_wallets(mock_load, mock_symbol):
    portfolio_id = uuid.uuid4()
    client_id = uuid.uuid4()
    cash_inst = uuid.uuid4()
    spot_inst = uuid.uuid4()
    wallet_from = _wallet(
        wallet_id=uuid.uuid4(),
        portfolio_id=portfolio_id,
        instrument_id=cash_inst,
        wallet_type="cash_wallet",
    )
    wallet_to = _wallet(
        wallet_id=uuid.uuid4(),
        portfolio_id=portfolio_id,
        instrument_id=spot_inst,
        wallet_type="spot_wallet",
    )
    mock_load.side_effect = [wallet_from, wallet_to]
    mock_symbol.side_effect = ["USDC", "ETH"]

    req = VirtualWalletSwapRequest(
        wallet_from_id=wallet_from.id,
        wallet_to_id=wallet_to.id,
        quantity_from=Decimal("30"),
        estimated_quantity_to=Decimal("0.01"),
        side="buy",
        correlation_id=uuid.uuid4(),
        client_id=client_id,
        portfolio_id=portfolio_id,
        leg_id="leg-1",
        batch_id="batch-1",
        bundle_action="rebalance_v3",
        leg_action="rebalance_buy",
    )
    trade_req = build_trade_request_from_wallets(MagicMock(), req)
    assert trade_req.from_asset == "USDC"
    assert trade_req.to_asset == "ETH"
    assert trade_req.quantity_from == Decimal("30")


def test_build_trade_request_rejects_sell_with_wrong_wallets():
    portfolio_id = uuid.uuid4()
    wallet_from = _wallet(
        wallet_id=uuid.uuid4(),
        portfolio_id=portfolio_id,
        instrument_id=uuid.uuid4(),
        wallet_type="cash_wallet",
    )
    wallet_to = _wallet(
        wallet_id=uuid.uuid4(),
        portfolio_id=portfolio_id,
        instrument_id=uuid.uuid4(),
        wallet_type="spot_wallet",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [wallet_from, wallet_to]

    req = VirtualWalletSwapRequest(
        wallet_from_id=wallet_from.id,
        wallet_to_id=wallet_to.id,
        quantity_from=Decimal("1"),
        estimated_quantity_to=Decimal("4"),
        side="sell",
        correlation_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_id=portfolio_id,
        leg_id="leg-1",
        batch_id="batch-1",
        bundle_action="rebalance_v3",
        leg_action="rebalance_sell",
    )
    with pytest.raises(VirtualWalletSwapError) as exc:
        build_trade_request_from_wallets(db, req)
    assert exc.value.code == "side_wallet_mismatch"


@patch("services.trade_core.run_wallet_swap.execute_trade")
@patch("services.trade_core.run_wallet_swap.build_trade_request_from_wallets")
def test_quote_virtual_wallet_swap_returns_review_snapshot(mock_build, mock_execute):
    swap_id = uuid.uuid4()
    mock_build.return_value = MagicMock()
    mock_execute.return_value = MagicMock(
        swap_id=swap_id,
        status="awaiting_signature",
        from_asset="AAVE",
        to_asset="USDC",
        amount_from=Decimal("0.068"),
        amount_to=Decimal("4.31"),
        requires_client_signature=True,
    )

    req = VirtualWalletSwapRequest(
        wallet_from_id=uuid.uuid4(),
        wallet_to_id=uuid.uuid4(),
        quantity_from=Decimal("0.068"),
        estimated_quantity_to=Decimal("4.31"),
        side="sell",
        correlation_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_id=uuid.uuid4(),
        leg_id="leg-1",
        batch_id="batch-1",
        bundle_action="rebalance_v3",
        leg_action="rebalance_sell",
    )
    result = quote_virtual_wallet_swap(MagicMock(), req, MagicMock())

    assert result.swap_id == swap_id
    assert result.review_snapshot.review_amount_in == "0.068"
    assert result.review_snapshot.review_estimated_receive == "4.31"
    assert result.from_asset == "AAVE"
