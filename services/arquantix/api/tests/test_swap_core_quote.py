"""Tests — ADR 007 S2 Swap Core quote."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.schemas import SwapQuoteResponse
from services.swap_core import QuotePolicy, SwapCore, SwapQuoteContext
from conftest import make_linked_client


def _mock_quote_response(swap_id: uuid.UUID) -> SwapQuoteResponse:
    return SwapQuoteResponse(
        swap_id=swap_id,
        status="QUOTE_RECEIVED",
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in="10",
        vancelian_fee="0",
        vancelian_fee_bps=0,
        network_fee="0",
        network_fee_asset=None,
        estimated_receive="0.003",
        estimated_receive_min="0.0029",
        route_steps=[],
        expires_at="2026-06-10T12:00:00Z",
        slippage_bps=50,
    )


def test_lifi_quote_service_delegates_to_swap_core(db: Session, monkeypatch):
    pe = make_linked_client(db)
    swap_id = uuid.uuid4()
    expected = _mock_quote_response(swap_id)

    with patch.object(SwapCore, "quote", return_value=expected) as quote_mock:
        from services.lifi.lifi_quote_service import LifiQuoteService

        out = LifiQuoteService().create_quote(
            db,
            person_id=pe.person_id,
            from_asset="USDC",
            to_asset="ETH",
            amount="10",
            from_chain="base",
            to_chain="base",
        )

    quote_mock.assert_called_once()
    ctx = quote_mock.call_args[0][1]
    assert ctx.policy == QuotePolicy.STANDALONE
    assert out.swap_id == swap_id


def test_bundle_lifi_quote_service_delegates_to_swap_core(db: Session):
    pe = make_linked_client(db)
    swap_id = uuid.uuid4()
    expected = _mock_quote_response(swap_id)

    with patch.object(SwapCore, "quote", return_value=expected) as quote_mock:
        from services.portfolio_engine.bundle_execution.bundle_lifi_quote_service import (
            BundleLifiQuoteService,
        )

        out = BundleLifiQuoteService().create_bundle_quote(
            db,
            person_id=pe.person_id,
            from_asset="USDC",
            to_asset="ETH",
            amount="10",
            leg_action="rebalance_buy",
        )

    quote_mock.assert_called_once()
    ctx = quote_mock.call_args[0][1]
    assert ctx.policy == QuotePolicy.BUNDLE_BASE
    assert ctx.leg_action == "rebalance_buy"
    assert out.swap_id == swap_id


def test_lifi_confirm_service_delegates_to_swap_core_confirm_poll(db: Session):
    pe = make_linked_client(db)
    swap_id = uuid.uuid4()
    mock_response = MagicMock()

    with patch(
        "services.swap_core.confirm_poll.SwapCoreConfirmPoll.confirm_and_execute",
        return_value=mock_response,
    ) as confirm_mock:
        from services.lifi.lifi_confirm_service import LifiConfirmService

        out = LifiConfirmService().confirm_execute(
            db,
            person_id=pe.person_id,
            swap_id=swap_id,
            review_estimated_receive="0.003",
        )

    confirm_mock.assert_called_once()
    assert out is mock_response
