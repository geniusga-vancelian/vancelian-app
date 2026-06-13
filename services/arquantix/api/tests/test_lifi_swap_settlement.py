"""Tests règlement ledger swap LI.FI (ETH visible sur Base après swap)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import apply_swap_settlement, swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from services.privy_wallet.service import PrivyWalletLedgerService
from tests.conftest import make_linked_client


EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
PRIVY_USER = "did:privy:testswapsettle001"


def _seed_wallet(db: Session, pe):
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=PRIVY_USER,
        external_email="swap-settle@test.local",
    )
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-settle"},
    )
    db.commit()


def _make_confirmed_base_swap(person_id) -> PersonWalletSwap:
    return PersonWalletSwap(
        id=uuid4(),
        person_id=person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("12"),
        estimated_receive=Decimal("0.00475"),
        tx_hash="0xswapbaseeth1234567890abcdef1234567890abcdef1234567890abcdef12",
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        confirmed_at=datetime.now(timezone.utc),
    )


def test_apply_swap_settlement_credits_eth_on_base_chain(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)

    admin = PrivyWalletAdminService()
    admin.simulate_deposit(
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

    swap = _make_confirmed_base_swap(pe.person_id)
    db.add(swap)
    db.flush()

    apply_swap_settlement(
        db,
        swap,
        sync_source="lifi_swap",
        amount_actual=Decimal("0.00475"),
    )
    db.commit()

    svc = PrivyWalletLedgerService()
    balances = svc.get_balances(db, person_id=pe.person_id).balances
    by_asset = {row.asset: row for row in balances}

    assert "ETH" in by_asset
    assert Decimal(by_asset["ETH"].balance) > 0
    assert by_asset["ETH"].chain_id == 8453
    assert Decimal(by_asset["USDC"].balance) == Decimal("13")


def test_swap_settlement_is_idempotent(db: Session):
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

    swap = _make_confirmed_base_swap(pe.person_id)
    db.add(swap)
    db.flush()

    apply_swap_settlement(db, swap, sync_source="lifi_swap", amount_actual=Decimal("0.00475"))
    swap.audit_log = [{"event": "swap_settled"}]
    db.commit()

    assert swap_settlement_already_applied(swap) is True


def test_legacy_settlement_atomic_debit_rolls_back_when_credit_fails(db: Session, monkeypatch):
    """D2 — un échec de la jambe CRÉDIT annule la jambe DÉBIT (savepoint) : jamais de débit
    orphelin sur le rail legacy. Le solde source reste intact."""
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

    swap = _make_confirmed_base_swap(pe.person_id)
    db.add(swap)
    db.flush()

    import services.lifi.lifi_swap_settlement as settle_mod

    real_create = settle_mod._create_swap_ledger_entry
    calls = {"n": 0}

    def _patched(db, **kw):
        calls["n"] += 1
        if calls["n"] == 1:  # 1ʳᵉ jambe = DÉBIT : écriture réelle
            return real_create(db, **kw)
        raise RuntimeError("credit boom")  # 2ᵉ jambe = CRÉDIT : échec

    monkeypatch.setattr(settle_mod, "_create_swap_ledger_entry", _patched)

    with pytest.raises(RuntimeError, match="credit boom"):
        apply_swap_settlement(db, swap, sync_source="lifi_swap", amount_actual=Decimal("0.00475"))

    assert calls["n"] == 2  # débit puis crédit tentés

    # Savepoint rollback : le débit USDC est annulé → solde inchangé, pas de crédit ETH.
    svc = PrivyWalletLedgerService()
    by_asset = {row.asset: row for row in svc.get_balances(db, person_id=pe.person_id).balances}
    assert Decimal(by_asset["USDC"].balance) == Decimal("25")
    assert "ETH" not in by_asset or Decimal(by_asset["ETH"].balance) == Decimal("0")
