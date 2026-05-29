"""Tests — périmètre et dédup transactions bundle."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from services.portfolio_engine.bundle_execution.bundle_pe_transactions import (
    list_bundle_pe_asset_transactions,
)
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.privy_wallet.transaction_merge import merge_crypto_transactions
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.enums import IntentProductType
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc
from conftest import make_linked_client


def _bundle_swap_audit(*, portfolio_id: str, batch_id: str, action: str = "allocation"):
    return [
        {
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "portfolio_id": portfolio_id,
            "batch_id": batch_id,
            "bundle_action": action,
            "leg_action": action,
        }
    ]


class _SwapStub:
    def __init__(self, audit_log):
        self.audit_log = audit_log


def test_is_bundle_internal_swap():
    pid = str(uuid.uuid4())
    assert is_bundle_internal_swap(_SwapStub(_bundle_swap_audit(portfolio_id=pid, batch_id="b1")))
    assert not is_bundle_internal_swap(_SwapStub([]))
    assert not is_bundle_internal_swap(_SwapStub([{"event": "other"}]))
    # batch_id seul sans bundle_execution — pas interne
    assert not is_bundle_internal_swap(
        _SwapStub([
            {
                "event": "bundle_leg_context",
                "batch_id": "b1",
                "bundle_action": "allocation",
            }
        ])
    )


def test_is_bundle_internal_swap_withdraw_sell_and_rebalance():
    pid = str(uuid.uuid4())
    for action in ("withdraw_sell", "rebalance_sell", "rebalance_buy", "allocation"):
        assert is_bundle_internal_swap(
            _SwapStub(_bundle_swap_audit(portfolio_id=pid, batch_id="b1", action=action))
        )


def test_list_bundle_pe_asset_transactions_dedupes_audit_and_intent(db):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())

    audit = AuditEvent(
        id=uuid.uuid4(),
        action="bundle.fund_cash_leg",
        entity_type="portfolio",
        entity_id=portfolio.id,
        metadata_={
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": batch_id,
            "entry_asset": "USDC",
            "amount": "25",
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit)

    intent = TransactionIntent(
        id=uuid.uuid4(),
        person_id=pe.person_id,
        product_type=IntentProductType.BUNDLE_INVEST.value,
        operation_type="bundle_invest",
        idempotency_key=f"test-{batch_id}",
        status="confirmed",
        linked_reference_id=batch_id,
        metadata_json={
            "batch_id": batch_id,
            "bundle_id": str(portfolio.id),
            "funding_asset": "USDC",
            "funding_amount": "25",
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(intent)
    db.commit()

    txs = list_bundle_pe_asset_transactions(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
    )
    debits = [t for t in txs if t.get("direction") == "debit"]
    assert len(debits) == 1
    assert debits[0]["amount_crypto"] == "25"


def test_merge_crypto_transactions_dedupes_lifi_and_privy_by_hash():
    tx_hash = "0xabc"
    lifi = {
        "id": uuid.uuid4(),
        "created_at": datetime.now(timezone.utc),
        "transaction_kind": "crypto_swap",
        "source_system": "lifi_swap",
        "tx_hash": tx_hash,
        "title": "Échange USDC → CBBTC",
    }
    privy = {
        "id": uuid.uuid4(),
        "created_at": datetime.now(timezone.utc),
        "transaction_kind": "crypto_swap",
        "source_system": "privy",
        "tx_hash": tx_hash,
        "title": "Échange USDC → CBBTC",
        "metadata_json": {"swap_id": str(lifi["id"])},
    }
    merged = merge_crypto_transactions([], [], extra_txs=[privy, lifi])
    assert len(merged) == 1
    assert merged[0]["source_system"] == "lifi_swap"
