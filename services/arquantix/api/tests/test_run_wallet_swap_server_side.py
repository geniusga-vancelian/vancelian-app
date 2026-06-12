"""Fonction unique d'exécution serveur ``run_virtual_wallet_swap_server_side`` (composition)."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.trade_core import run_wallet_swap as rws
from services.trade_core import server_execution as se
from services.trade_core.run_wallet_swap import (
    VirtualWalletSwapError,
    VirtualWalletSwapRequest,
    run_virtual_wallet_swap_server_side,
)

PERSON_ID = uuid4()
SWAP_ID = uuid4()


def _request(quantity_from: str = "10") -> VirtualWalletSwapRequest:
    return VirtualWalletSwapRequest(
        wallet_from_id=uuid4(),
        wallet_to_id=uuid4(),
        quantity_from=Decimal(quantity_from),
        estimated_quantity_to=Decimal("0.05"),
        side="buy",
        correlation_id=uuid4(),
        client_id=uuid4(),
        portfolio_id=uuid4(),
        leg_id="leg-1",
        batch_id="batch-1",
        bundle_action="rebalance",
        leg_action="rebalance_buy",
    )


def _fake_quote():
    return SimpleNamespace(
        swap_id=SWAP_ID,
        from_asset="USDC",
        to_asset="AAVE",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.05"),
        status="quote_received",
        review_snapshot=None,
        requires_client_signature=True,
        trade=None,
    )


def test_invalid_quantity_raises():
    with pytest.raises(VirtualWalletSwapError) as exc:
        run_virtual_wallet_swap_server_side(None, _request("0"), None, person_id=PERSON_ID)
    assert exc.value.code == "invalid_quantity"


def test_composition_signs_and_settles(monkeypatch):
    captured = {}
    monkeypatch.setattr(rws, "quote_virtual_wallet_swap", lambda db, req, actor: _fake_quote())

    def _fake_exec(db, *, person_id, swap_id):
        captured["person_id"] = person_id
        captured["swap_id"] = swap_id
        return se.ServerSwapExecutionResult(
            phase="confirmed", swap_id=swap_id, signed_server_side=True,
            tx_hash="0xfeed", settled=True,
        )

    monkeypatch.setattr(se, "execute_prepared_swap_server_side", _fake_exec)

    result = run_virtual_wallet_swap_server_side(None, _request(), None, person_id=PERSON_ID)

    assert captured == {"person_id": PERSON_ID, "swap_id": SWAP_ID}
    assert result.phase == "confirmed"
    assert result.quote.swap_id == SWAP_ID
    assert result.finalize is not None
    assert result.finalize.settled is True
    assert result.finalize.tx_hash == "0xfeed"
    assert result.finalize.error is None


def test_composition_propagates_fallback(monkeypatch):
    monkeypatch.setattr(rws, "quote_virtual_wallet_swap", lambda db, req, actor: _fake_quote())
    monkeypatch.setattr(
        se, "execute_prepared_swap_server_side",
        lambda db, *, person_id, swap_id: se.ServerSwapExecutionResult(
            phase="awaiting_signature", swap_id=swap_id, signed_server_side=False,
            fallback_reason="wallet_not_delegated",
        ),
    )

    result = run_virtual_wallet_swap_server_side(None, _request(), None, person_id=PERSON_ID)

    assert result.phase == "awaiting_signature"
    assert result.finalize.settled is False
    assert result.finalize.error == "wallet_not_delegated"
    # le swap reste quoté → signable côté client (zéro régression)
    assert result.quote.swap_id == SWAP_ID
