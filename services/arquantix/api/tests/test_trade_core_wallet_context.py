"""Tests trade wallet context on swap audit (ADR 008 Phase 2)."""
import uuid

from services.trade_core.execute_trade import (
    WALLET_CONTEXT_EVENT,
    read_trade_wallet_context,
)


def test_read_trade_wallet_context_from_audit():
    swap_id = uuid.uuid4()
    wallet_from = uuid.uuid4()
    wallet_to = uuid.uuid4()
    correlation = uuid.uuid4()

    class FakeSwap:
        audit_log = [
            {"event": "bundle_leg_context", "batch_id": "abc"},
            {
                "event": WALLET_CONTEXT_EVENT,
                "wallet_from_id": str(wallet_from),
                "wallet_to_id": str(wallet_to),
                "correlation_id": str(correlation),
                "instrument_from_id": str(uuid.uuid4()),
                "instrument_to_id": str(uuid.uuid4()),
            },
        ]

    ctx = read_trade_wallet_context(FakeSwap())
    assert ctx is not None
    assert ctx["wallet_from_id"] == str(wallet_from)
    assert ctx["wallet_to_id"] == str(wallet_to)
    assert ctx["correlation_id"] == str(correlation)


def test_read_trade_wallet_context_missing():
    class EmptySwap:
        audit_log = []

    assert read_trade_wallet_context(EmptySwap()) is None
