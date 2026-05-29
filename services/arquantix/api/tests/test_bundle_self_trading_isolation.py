"""Tests — isolation bundle / self-trading (Phase 1 anti-fuite + Phase 2 recovery)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.exchange.models import ExchangeOrder
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundles.bundle_invest_lock import (
    acquire_invest_lock,
    expire_stale_invest_lock_if_safe,
    get_invest_lock,
    invest_lock_ttl_minutes,
    reconcile_idle_invest_lock,
    reconcile_or_expire_idle_invest_lock,
)
from services.portfolio_engine.bundles.bundle_withdraw_lock import (
    acquire_withdraw_lock,
    expire_stale_withdraw_lock_if_safe,
    get_withdraw_lock,
    WITHDRAW_PHASE_UNWINDING,
)
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.bundles.withdraw import BundleWithdrawOrchestrator
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.test_clients.service import TestClientService
from services.transaction_intents.enums import IntentProductType
from services.transaction_intents.lifi_intent_sync import sync_lifi_swap_intent
from services.transaction_intents.repository import TransactionIntentRepository
from services.wallet_history.service import build_wallet_history
from services.portfolio_engine.bundle_execution.self_trading_transactions import (
    filter_self_trading_exchange_orders,
)
from tests.test_bundle_lifi_funding import (
    _bundle_portfolio,
    _instrument_usdc,
)
from services.portfolio_engine.bundle_execution.bundle_funding import (
    fund_bundle_cash_leg_from_self_trading,
)
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


def _seed_confirmed_swap(
    db: Session,
    pe,
    *,
    audit_log: list,
    from_asset: str = "USDC",
    to_asset: str = "CBBTC",
) -> PersonWalletSwap:
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset=from_asset,
        to_asset=to_asset,
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.0001"),
        tx_hash=f"0x{uuid.uuid4().hex}",
        confirmed_at=datetime.now(timezone.utc),
        audit_log=audit_log,
    )
    db.add(swap)
    db.flush()
    return swap


def _seed_self_trading_swap(db: Session, pe) -> PersonWalletSwap:
    return _seed_confirmed_swap(
        db,
        pe,
        audit_log=[],
        from_asset="USDC",
        to_asset="EURC",
    )


def test_bundle_leg_does_not_create_lifi_swap_intent(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    batch_id = str(uuid.uuid4())
    swap = _seed_confirmed_swap(
        db,
        pe,
        audit_log=_bundle_swap_audit(portfolio_id=str(portfolio.id), batch_id=batch_id),
    )
    sync_lifi_swap_intent(db, swap)
    db.commit()

    intent = TransactionIntentRepository.find_by_linked(
        db,
        linked_table="person_wallet_swaps",
        linked_id=swap.id,
    )
    assert intent is None


def test_self_trading_lifi_swap_still_creates_intent(db: Session):
    pytest.importorskip("sqlalchemy")
    from tests.test_phase7_transaction_intents import _migration_166_ready

    if not _migration_166_ready():
        pytest.skip("Migration 166 requise.")

    pe = make_linked_client(db)
    swap = _seed_self_trading_swap(db, pe)
    sync_lifi_swap_intent(db, swap)
    db.commit()

    intent = TransactionIntentRepository.find_by_linked(
        db,
        linked_table="person_wallet_swaps",
        linked_id=swap.id,
    )
    assert intent is not None
    assert intent.product_type == IntentProductType.LIFI_SWAP.value


def test_bundle_internal_swap_excluded_from_get_crypto_transactions(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    batch_id = str(uuid.uuid4())
    from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom

    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("100"), Decimal("100"))

    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("50"),
        batch_id=batch_id,
    )
    _seed_confirmed_swap(
        db,
        pe,
        audit_log=_bundle_swap_audit(portfolio_id=str(portfolio.id), batch_id=batch_id),
    )
    _seed_self_trading_swap(db, pe)
    db.commit()

    svc = TestClientService()
    result = svc.get_crypto_transactions(db, "USDC", client=pe)
    txs = result["transactions"]

    swap_titles = [t.get("title") for t in txs if t.get("source_system") == "lifi_swap"]
    assert len(swap_titles) == 1
    assert "EURC" in (swap_titles[0] or "")
    assert not any(t.get("transaction_kind") == "bundle_internal_swap" for t in txs)

    pe_transfers = [t for t in txs if t.get("transaction_kind") == "bundle_pe_transfer"]
    assert len(pe_transfers) >= 1
    assert any(t.get("direction") == "debit" for t in pe_transfers)


def test_bundle_pe_transfer_visible_in_self_trading_but_swap_not(db: Session):
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
    _seed_confirmed_swap(
        db,
        pe,
        audit_log=_bundle_swap_audit(portfolio_id=str(portfolio.id), batch_id=batch_id),
    )
    db.commit()

    svc = TestClientService()
    txs = svc.get_crypto_transactions(db, "USDC", client=pe)["transactions"]
    assert any(t.get("transaction_kind") == "bundle_pe_transfer" for t in txs)
    assert not any(
        t.get("source_system") == "lifi_swap" and "CBBTC" in str(t.get("title") or "")
        for t in txs
    )


def test_bundle_internal_swap_excluded_from_wallet_history(db: Session):
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
        external_reference=f"test-bundle-{uuid.uuid4()}",
        metadata_={"portfolio_scope": "bundle", "portfolio_id": str(uuid.uuid4())},
        created_at=datetime.now(timezone.utc),
    )
    direct_order = ExchangeOrder(
        id=uuid.uuid4(),
        client_id=pe.id,
        side="buy",
        asset="USDC",
        currency="EUR",
        amount_crypto=Decimal("50"),
        amount_fiat=Decimal("50"),
        price=Decimal("1"),
        status="completed",
        external_reference=f"test-direct-{uuid.uuid4()}",
        metadata_={"portfolio_scope": "direct"},
        created_at=datetime.now(timezone.utc),
    )
    db.add_all([bundle_order, direct_order])
    db.commit()

    filtered = filter_self_trading_exchange_orders([bundle_order, direct_order])
    assert len(filtered) == 1
    assert filtered[0].id == direct_order.id

    history = build_wallet_history(
        db,
        pe.id,
        portfolio_scope="direct",
        asset="USDC",
    )
    assert len(history["points"]) >= 1


def test_partial_allocation_preserves_cash_leg_and_lock_status(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom

    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("100"), Decimal("100"))

    batch_id = str(uuid.uuid4())
    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
        amount=Decimal("100"),
        batch_id=batch_id,
    )
    db.commit()

    cash = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.position_type == PositionType.CASH,
        )
        .first()
    )
    assert cash is not None
    assert Decimal(str(cash.quantity)) == Decimal("100")

    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    acquire_invest_lock(
        db,
        p,
        client_id=pe.id,
        batch_id=batch_id,
        status="partial_pending",
    )
    release = __import__(
        "services.portfolio_engine.bundles.bundle_invest_lock",
        fromlist=["release_invest_lock"],
    ).release_invest_lock
    release(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
        terminal_status="failed",
    )
    db.commit()
    db.refresh(p)

    cash_after = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.position_type == PositionType.CASH,
        )
        .first()
    )
    assert Decimal(str(cash_after.quantity)) == Decimal("100")
    assert get_invest_lock(p.metadata_) is None


def test_invest_lock_expires_after_stale_pending_signature(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    batch_id = str(uuid.uuid4())
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=invest_lock_ttl_minutes() + 5)).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": batch_id,
            "status": "pending_signature",
            "created_at": stale_time,
            "updated_at": stale_time,
        }
    }
    db.add(p)
    db.commit()

    with patch.dict("os.environ", {"BUNDLE_INVEST_LOCK_TTL_MINUTES": "120"}):
        assert expire_stale_invest_lock_if_safe(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            portfolio=p,
        )
    db.commit()
    db.refresh(p)
    assert get_invest_lock(p.metadata_) is None
    meta_lock = (p.metadata_ or {}).get("bundle_invest_lock") or {}
    assert meta_lock.get("status") == "expired"


def test_invest_lock_not_expired_while_submitted_swap_alive(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    batch_id = str(uuid.uuid4())
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=invest_lock_ttl_minutes() + 5)).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": batch_id,
            "status": "submitted",
            "created_at": stale_time,
            "updated_at": stale_time,
        }
    }
    db.add(p)
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.0001"),
        audit_log=_bundle_swap_audit(portfolio_id=str(portfolio.id), batch_id=batch_id),
    )
    db.add(swap)
    db.commit()

    with patch.dict("os.environ", {"BUNDLE_INVEST_LOCK_TTL_MINUTES": "120"}):
        assert not expire_stale_invest_lock_if_safe(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            portfolio=p,
        )
    assert get_invest_lock(p.metadata_) is not None


def test_invest_lock_cleared_by_reconcile_when_swaps_terminal(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    batch_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    p.metadata_ = {
        "bundle_invest_lock": {
            "bundle_action": "invest",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": batch_id,
            "status": "partial_pending",
            "created_at": now,
            "updated_at": now,
        }
    }
    db.add(p)
    db.commit()

    assert reconcile_idle_invest_lock(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        portfolio=p,
    )
    db.refresh(p)
    assert get_invest_lock(p.metadata_) is None


def test_withdraw_lock_expires_when_no_live_sell(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    batch_id = str(uuid.uuid4())
    stale_time = (datetime.now(timezone.utc) - timedelta(minutes=200)).isoformat()
    usdc = _instrument_usdc(db)

    p.metadata_ = {
        "bundle_withdraw_lock": {
            "bundle_action": "withdraw",
            "client_id": str(pe.id),
            "portfolio_id": str(portfolio.id),
            "batch_id": batch_id,
            "status": "pending_signature",
            "withdraw_phase": WITHDRAW_PHASE_UNWINDING,
            "entry_instrument_id": str(usdc.id),
            "entry_asset": "USDC",
            "requested_release_amount": "50",
            "full_withdraw": False,
            "released_amount": "0",
            "sell_legs_total": 1,
            "sell_legs_confirmed": 0,
            "sell_legs_failed": 0,
            "created_at": stale_time,
            "updated_at": stale_time,
        }
    }
    db.add(p)
    db.commit()
    db.refresh(p)

    with patch.dict("os.environ", {"BUNDLE_WITHDRAW_LOCK_TTL_MINUTES": "120"}):
        assert expire_stale_withdraw_lock_if_safe(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            portfolio=p,
        )
    db.commit()
    db.refresh(p)
    assert get_withdraw_lock(p.metadata_) is None
    meta_lock = (p.metadata_ or {}).get("bundle_withdraw_lock") or {}
    assert meta_lock.get("status") == "expired"


def test_withdraw_failed_partial_does_not_release_to_self_trading(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    batch_id = str(uuid.uuid4())

    cash_atom = PositionAtom(
        portfolio_id=portfolio.id,
        instrument_id=usdc.id,
        position_type=PositionType.CASH,
        quantity=Decimal("30"),
        cost_basis=Decimal("30"),
        status="open",
    )
    db.add(cash_atom)
    acquire_withdraw_lock(
        db,
        p,
        client_id=pe.id,
        batch_id=batch_id,
        entry_instrument_id=str(usdc.id),
        entry_asset="USDC",
        requested_release_amount="30",
        full_withdraw=False,
    )
    update = __import__(
        "services.portfolio_engine.bundles.bundle_withdraw_lock",
        fromlist=["update_withdraw_lock"],
    ).update_withdraw_lock
    update(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
        status="failed_partial",
        withdraw_phase="FAILED_PARTIAL",
        extra={"sell_legs_total": 2, "sell_legs_confirmed": 0, "sell_legs_failed": 2},
    )
    db.commit()

    direct_before = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id
            == __import__(
                "services.portfolio_engine.direct_overlay",
                fromlist=["ensure_direct_portfolio"],
            ).ensure_direct_portfolio(db, pe.id).id,
            PositionAtom.instrument_id == usdc.id,
        )
        .first()
    )
    qty_before = Decimal(str(direct_before.quantity)) if direct_before else Decimal("0")

    result = BundleWithdrawOrchestrator.try_release_if_ready(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
    )
    assert result.get("released") is False
    assert result.get("reason") == "all_sells_failed"

    direct_after = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id
            == __import__(
                "services.portfolio_engine.direct_overlay",
                fromlist=["ensure_direct_portfolio"],
            ).ensure_direct_portfolio(db, pe.id).id,
            PositionAtom.instrument_id == usdc.id,
        )
        .first()
    )
    qty_after = Decimal(str(direct_after.quantity)) if direct_after else Decimal("0")
    assert qty_after == qty_before


def test_withdraw_finalize_releases_only_confirmed_cash(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    usdc = _instrument_usdc(db)
    from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom

    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    batch_id = str(uuid.uuid4())

    cash_atom = PositionAtom(
        portfolio_id=portfolio.id,
        instrument_id=usdc.id,
        position_type=PositionType.CASH,
        quantity=Decimal("25"),
        cost_basis=Decimal("25"),
        status="open",
    )
    db.add(cash_atom)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("5"), Decimal("5"))

    acquire_withdraw_lock(
        db,
        p,
        client_id=pe.id,
        batch_id=batch_id,
        entry_instrument_id=str(usdc.id),
        entry_asset="USDC",
        requested_release_amount="25",
        full_withdraw=False,
    )
    from services.portfolio_engine.bundles.bundle_withdraw_lock import update_withdraw_lock

    update_withdraw_lock(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
        status="ready_to_release",
        withdraw_phase="READY_TO_RELEASE",
        extra={"sell_legs_total": 0, "sell_legs_confirmed": 0, "sell_legs_failed": 0},
    )
    db.commit()

    result = BundleWithdrawOrchestrator().finalize_withdraw_batch(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
    )
    assert result.get("released") is True
    assert float(result.get("amount") or 0) == pytest.approx(25.0, rel=1e-6)

    direct_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == usdc.id,
            PositionAtom.position_type == PositionType.SPOT,
        )
        .first()
    )
    assert direct_atom is not None
    assert Decimal(str(direct_atom.quantity)) == Decimal("30")


def test_resume_invest_rebuilds_pending_legs_from_lock(db: Session):
    pe = make_linked_client(db)
    portfolio = _bundle_portfolio(db, pe.id)
    p = db.query(Portfolio).filter(Portfolio.id == portfolio.id).first()
    batch_id = str(uuid.uuid4())
    usdc = _instrument_usdc(db)

    acquire_invest_lock(
        db,
        p,
        client_id=pe.id,
        batch_id=batch_id,
        entry_instrument_id=str(usdc.id),
        status="partial_pending",
        funding_asset="USDC",
        funding_amount="100",
    )
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("40"),
        estimated_receive=Decimal("0.0001"),
        audit_log=_bundle_swap_audit(portfolio_id=str(portfolio.id), batch_id=batch_id),
    )
    db.add(swap)
    db.commit()

    result = BundleOrchestrator().resume_lifi_invest_batch(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
    )
    assert result.get("batch_id") == batch_id
    alloc = result.get("allocation_details") or []
    assert len(alloc) >= 1
    assert alloc[0].get("status") == "pending"
