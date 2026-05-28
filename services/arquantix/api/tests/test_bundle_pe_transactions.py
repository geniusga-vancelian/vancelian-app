"""Tests — historique transferts PE bundle dans l'historique crypto."""
from __future__ import annotations

import uuid
from decimal import Decimal

from services.portfolio_engine.bundle_execution.bundle_funding import (
    fund_bundle_cash_leg_from_self_trading,
)
from services.portfolio_engine.bundle_execution.bundle_pe_transactions import (
    list_bundle_pe_asset_transactions,
)
from services.portfolio_engine.hardening.audit_models import AuditEvent
from tests.test_bundle_lifi_funding import (
    _bundle_portfolio,
    _instrument_usdc,
    _seed_privy_usdc,
)
from conftest import make_linked_client


def test_fund_creates_audit_and_crypto_transaction(db):
    pe = make_linked_client(db)
    entry = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)

    from services.auth.person_identity_bridge import upsert_person_crypto_wallet, PROVIDER_PRIVY

    wallet = upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=f"0x{uuid.uuid4().hex[:40]}",
    )
    _seed_privy_usdc(db, pe.person_id, wallet.id, "100")
    db.commit()
    batch_id = str(uuid.uuid4())

    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=entry.id,
        amount=Decimal("10"),
        batch_id=batch_id,
    )
    db.commit()

    audit_count = (
        db.query(AuditEvent)
        .filter(AuditEvent.action == "bundle.fund_cash_leg")
        .count()
    )
    assert audit_count >= 1

    txs = list_bundle_pe_asset_transactions(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
    )
    fund_tx = next((t for t in txs if t.get("direction") == "debit"), None)
    assert fund_tx is not None
    assert fund_tx["amount_crypto"] == "10"
    assert fund_tx["source_system"] == "bundle_pe"
    assert fund_tx["transaction_kind"] == "bundle_pe_transfer"
    assert "Bundle" in fund_tx["title"]
