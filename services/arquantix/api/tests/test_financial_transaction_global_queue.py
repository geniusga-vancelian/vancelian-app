"""File transactionnelle globale — swap LI.FI · bundle rebalance · mutual exclusion."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_confirm_service import LifiConfirmService
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_transaction_global_lock import (
    acquire_bundle_transaction_global_lock_or_raise,
)
from services.portfolio_engine.bundles.bundle_transaction_intent import (
    BUNDLE_TRANSACTION_OPERATION_REBALANCE,
    PHASE_REBALANCING,
    create_bundle_transaction_intent,
)
from services.portfolio_engine.bundles.rebalancing_portfolio import rebalancing_portfolio
from services.product_locks.exceptions import TransactionInProgress409
from services.transaction_intents.enums import IntentOperationType, IntentProductType
from tests.test_bundle_lifi_funding import _bundle_portfolio
from conftest import make_linked_client
from tests.test_product_locks_l2_engine import _migration_175_ready


pytestmark = pytest.mark.skipif(
    not _migration_175_ready(),
    reason="Migration 175 requise (transaction_product_locks).",
)


def _wallet(db: Session, pe_client):
    return upsert_person_crypto_wallet(
        db,
        person_id=pe_client.person_id,
        pe_client_id=pe_client.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=f"0x{uuid.uuid4().hex[:40]}",
    )


def _standalone_swap(db: Session, person_id: uuid.UUID) -> PersonWalletSwap:
    swap = PersonWalletSwap(
        person_id=person_id,
        status=SwapSessionStatus.QUOTE_RECEIVED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        slippage_bps=50,
        estimated_receive=Decimal("0.003"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        audit_log=[],
    )
    db.add(swap)
    db.flush()
    intent = TransactionIntent(
        person_id=person_id,
        product_type=IntentProductType.LIFI_SWAP.value,
        operation_type=IntentOperationType.SWAP.value,
        idempotency_key=f"lifi_swap:{swap.id}",
        status="created",
        linked_table="person_wallet_swaps",
        linked_id=swap.id,
    )
    db.add(intent)
    db.flush()
    return swap


@pytest.fixture
def global_lock_on(monkeypatch):
    monkeypatch.setenv("GLOBAL_USER_TRANSACTION_LOCK_ENABLED", "true")
    monkeypatch.setenv("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED", "true")


def test_swap_confirm_blocked_when_bundle_lock_active(
    db: Session,
    global_lock_on,
    monkeypatch,
):
    pe = make_linked_client(db)
    _wallet(db, pe)
    swap = _standalone_swap(db, pe.person_id)
    bundle_intent = create_bundle_transaction_intent(
        db,
        person_id=pe.person_id,
        portfolio_id=uuid.uuid4(),
        transaction_execution_id=uuid.uuid4(),
        operation_type=BUNDLE_TRANSACTION_OPERATION_REBALANCE,
        phase=PHASE_REBALANCING,
    )
    acquire_bundle_transaction_global_lock_or_raise(
        db,
        person_id=pe.person_id,
        intent_id=bundle_intent.id,
    )
    db.commit()

    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "false")

    fresh_quote = type(
        "Q",
        (),
        {
            "estimated_receive": "0.003",
            "slippage_bps": 50,
            "amount_in": "10",
        },
    )()

    with patch.object(
        LifiConfirmService,
        "_quote",
        create=True,
    ), patch(
        "services.lifi.lifi_confirm_service.LifiQuoteService.refresh_quote",
        return_value=fresh_quote,
    ), patch(
        "services.lifi.lifi_confirm_service.compare_receive_against_review",
        return_value=type("C", (), {"acceptable": True, "delta_bps": 0})(),
    ), patch(
        "services.lifi.lifi_confirm_service.lifi_intent_orchestrator_enabled_for_person",
        return_value=False,
    ):
        svc = LifiConfirmService()
        with pytest.raises(TransactionInProgress409):
            svc.confirm_execute(
                db,
                person_id=pe.person_id,
                swap_id=swap.id,
                review_estimated_receive="0.003",
            )


def test_bundle_rebalance_blocked_when_swap_lock_active(
    db: Session,
    global_lock_on,
):
    pe = make_linked_client(db)
    _wallet(db, pe)
    portfolio = _bundle_portfolio(db, pe.id)
    swap = _standalone_swap(db, pe.person_id)
    swap_intent = (
        db.query(TransactionIntent)
        .filter(TransactionIntent.linked_id == swap.id)
        .first()
    )
    from services.lifi.lifi_swap_global_lock import acquire_lifi_swap_global_lock_or_raise

    acquire_lifi_swap_global_lock_or_raise(
        db,
        person_id=pe.person_id,
        swap_id=swap.id,
    )
    db.commit()

    with patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.compute_bundle_drift_snapshot",
        return_value={"snapshot_hash": "h1", "entry_asset": "USDC"},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.plan_bundle_rebalance_from_drift",
        return_value={"status": "ok", "plan_hash": "p1", "sell_plan": [], "buy_plan": []},
    ), patch(
        "services.portfolio_engine.bundles.rebalancing_portfolio.abandon_legacy_invest_lock_for_rebalancing",
        return_value={"abandoned": False},
    ):
        with pytest.raises(TransactionInProgress409):
            rebalancing_portfolio(db, client_id=pe.id, portfolio_id=portfolio.id)

    assert swap_intent is not None
