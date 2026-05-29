"""Tests Phase 3.5 — filtres self-trading sur privy deposits et wallet statistics."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from services.exchange.models import ExchangeOrder
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.self_trading_transactions import (
    filter_self_trading_exchange_orders,
    filter_self_trading_privy_deposits,
)
from services.privy_wallet.service import PrivyWalletLedgerService
from services.wallet_statistics.service import build_wallet_statistics
from conftest import make_linked_client


def _bundle_swap_audit(*, portfolio_id: str, batch_id: str):
    return [
        {
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "portfolio_id": portfolio_id,
            "batch_id": batch_id,
            "bundle_action": "allocation",
        }
    ]


def test_filter_self_trading_privy_deposits_excludes_bundle_linked(db):
    pe = make_linked_client(db)
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.0001"),
        audit_log=_bundle_swap_audit(portfolio_id=str(uuid.uuid4()), batch_id="b1"),
    )
    db.add(swap)
    db.commit()

    bundle_deposit = SimpleNamespace(
        metadata_json={"swap_id": str(swap.id)},
        title="Bundle internal",
    )
    plain_deposit = SimpleNamespace(metadata_json={}, title="Plain deposit")

    filtered = filter_self_trading_privy_deposits(
        db, [bundle_deposit, plain_deposit],
    )
    assert [d.title for d in filtered] == ["Plain deposit"]


def test_privy_deposits_list_excludes_bundle_internal(db):
    pe = make_linked_client(db)
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.0001"),
        audit_log=_bundle_swap_audit(portfolio_id=str(uuid.uuid4()), batch_id="b1"),
    )
    db.add(swap)
    db.commit()

    rows = [
        SimpleNamespace(
            id=uuid.uuid4(),
            transaction_kind="crypto_swap",
            direction="credit",
            asset="CBBTC",
            amount=Decimal("0.0001"),
            status="confirmed",
            chain_type="evm",
            chain_id=8453,
            tx_hash="0xabc",
            from_address="0xfrom",
            to_address="0xto",
            confirmations=1,
            title="Bundle internal",
            subtitle=None,
            person_crypto_wallet_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            confirmed_at=datetime.now(timezone.utc),
            metadata_json={"swap_id": str(swap.id)},
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            transaction_kind="deposit",
            direction="credit",
            asset="USDC",
            amount=Decimal("50"),
            status="confirmed",
            chain_type="evm",
            chain_id=8453,
            tx_hash="0xdef",
            from_address="0xfrom",
            to_address="0xto",
            confirmations=1,
            title="Plain deposit",
            subtitle=None,
            person_crypto_wallet_id=uuid.uuid4(),
            created_at=datetime.now(timezone.utc),
            confirmed_at=datetime.now(timezone.utc),
            metadata_json={},
        ),
    ]

    svc = PrivyWalletLedgerService()
    with patch.object(svc._wallet_repo, "list_active_for_person", return_value=[]):
        with patch.object(svc._deposit_repo, "list_for_person", return_value=rows):
            result = svc.list_deposits(db, person_id=pe.person_id, limit=50)

    titles = [d.title for d in result.deposits]
    assert titles == ["Plain deposit"]


def test_wallet_statistics_excludes_bundle_exchange_orders(db):
    pe = make_linked_client(db)
    bundle_order = ExchangeOrder(
        id=uuid.uuid4(),
        client_id=pe.id,
        side="buy",
        asset="USDC",
        currency="EUR",
        amount_crypto=Decimal("100"),
        amount_fiat=Decimal("100"),
        price=Decimal("1"),
        status="completed",
        external_reference=f"stats-bundle-{uuid.uuid4()}",
        metadata_={"portfolio_scope": "bundle", "portfolio_id": str(uuid.uuid4())},
        created_at=datetime.now(timezone.utc),
    )
    direct_order = ExchangeOrder(
        id=uuid.uuid4(),
        client_id=pe.id,
        side="buy",
        asset="USDC",
        currency="EUR",
        amount_crypto=Decimal("25"),
        amount_fiat=Decimal("25"),
        price=Decimal("1"),
        status="completed",
        external_reference=f"stats-direct-{uuid.uuid4()}",
        metadata_={"portfolio_scope": "direct"},
        created_at=datetime.now(timezone.utc),
    )
    db.add_all([bundle_order, direct_order])
    db.commit()

    stats = build_wallet_statistics(db, pe.id, "USDC", portfolio_scope=None)
    assert stats.get("trade_count", 0) == 1
    assert Decimal(str(stats.get("total_bought", 0))) == Decimal("25")

    filtered = filter_self_trading_exchange_orders([bundle_order, direct_order])
    assert len(filtered) == 1
