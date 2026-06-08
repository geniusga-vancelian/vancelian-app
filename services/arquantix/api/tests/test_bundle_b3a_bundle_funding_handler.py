"""B3a — Bundle funding handler (trading_available USDC → bundle_cash_leg)."""
from __future__ import annotations

import inspect
import uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.bundle_funding import (
    resolve_self_trading_available,
    sum_bundle_cash_leg_quantity,
)
from services.portfolio_engine.bundles.event_driven.bundle_funding_handler import (
    BundleFundingHandlerError,
    compute_bundle_funding_receipt_hash,
    settle_bundle_funding_idempotently,
)
from services.portfolio_engine.bundles.orchestrator import (
    POSITION_TYPE_CASH,
    POSITION_TYPE_SPOT,
)
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.positions.models import PositionAtom
from services.privy_wallet.repository import PersonWalletBalanceRepository
from services.transaction_intents.enums import (
    IntentOperationType,
    IntentProductType,
    IntentRole,
    IntentStatus,
)
from tests.test_bundle_lifi_funding import (
    _bundle_portfolio,
    _instrument_usdc,
    _seed_privy_usdc,
)

from conftest import make_linked_client


def _migration_176_ready() -> bool:
    try:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'transaction_intents'
                      AND column_name = 'parent_intent_id'
                    """
                )
            ).fetchone()
            return row is not None
    except Exception:
        return False


pytestmark_db = pytest.mark.skipif(
    not _migration_176_ready(),
    reason="Migration 176 requise (transaction_intents parent/child B1).",
)


@pytest.fixture
def funding_handler_on(monkeypatch):
    monkeypatch.setenv("BUNDLE_FUNDING_HANDLER_ENABLED", "true")


def _insert_parent(
    db: Session,
    *,
    person_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    bundle_execution_id: uuid.UUID | None = None,
    product_type: str = IntentProductType.BUNDLE_INVEST.value,
    intent_role: str = IntentRole.PARENT.value,
) -> TransactionIntent:
    bex = bundle_execution_id or uuid.uuid4()
    row = TransactionIntent(
        person_id=person_id,
        product_type=product_type,
        operation_type=IntentOperationType.INVEST.value,
        idempotency_key=f"bundle-b3a-{uuid.uuid4().hex}",
        status=IntentStatus.CREATED.value,
        intent_role=intent_role,
        bundle_execution_id=bex,
        linked_table="bundle_invest_lock",
        linked_reference_id=str(bex),
        metadata_json={
            "bundle_execution_group_id": str(bex),
            "bundle_id": str(portfolio_id),
        },
    )
    db.add(row)
    db.flush()
    return row


def _seed_trading_available(
    db: Session,
    client_id: uuid.UUID,
    instrument_id: uuid.UUID,
    amount: str,
) -> None:
    direct_pf = ensure_direct_portfolio(db, client_id)
    sync_direct_atom(db, direct_pf.id, instrument_id, Decimal(amount), Decimal("0"))


def _setup_pe_and_parent(db: Session, *, trading_amount: str = "500"):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    _seed_trading_available(db, pe.id, usdc.id, trading_amount)

    from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet

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
    _seed_privy_usdc(db, pe.person_id, wallet.id, "1000")
    parent = _insert_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
    )
    db.commit()
    return pe, usdc, portfolio, wallet, parent


@pytestmark_db
def test_flag_off_no_pe_change(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_FUNDING_HANDLER_ENABLED", "false")
    pe, usdc, portfolio, wallet, parent = _setup_pe_and_parent(db)

    trading_before = resolve_self_trading_available(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
    )
    cash_before = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)

    result = settle_bundle_funding_idempotently(
        db,
        parent_intent_id=parent.id,
        amount_usdc=Decimal("100"),
        portfolio_id=portfolio.id,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        bundle_execution_id=parent.bundle_execution_id,
    )
    db.commit()

    assert result.skipped is True
    assert result.settled is False
    assert result.reason == "bundle_funding_handler_disabled"

    trading_after = resolve_self_trading_available(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
    )
    cash_after = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)
    assert trading_after == trading_before
    assert cash_after == cash_before


@pytestmark_db
def test_nominal_trading_debit_bundle_cash_credit(db: Session, funding_handler_on):
    pe, usdc, portfolio, wallet, parent = _setup_pe_and_parent(db)

    result = settle_bundle_funding_idempotently(
        db,
        parent_intent_id=parent.id,
        amount_usdc=Decimal("100"),
        portfolio_id=portfolio.id,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        bundle_execution_id=parent.bundle_execution_id,
    )
    db.commit()

    assert result.settled is True
    assert result.skipped is False
    assert result.idempotent is False
    assert result.trading_debit_usdc == Decimal("100")
    assert result.bundle_cash_credit_usdc == Decimal("100")
    assert result.receipt_hash and result.receipt_hash.startswith("sha256:")

    trading_after = resolve_self_trading_available(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
    )
    cash_after = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)
    assert trading_after == Decimal("400")
    assert cash_after == Decimal("100")

    direct_pf = ensure_direct_portfolio(db, pe.id)
    direct_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == usdc.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    cash_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == usdc.id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
        )
        .first()
    )
    assert direct_atom is not None and Decimal(str(direct_atom.quantity)) == Decimal("-100")
    assert cash_atom is not None and Decimal(str(cash_atom.quantity)) == Decimal("100")

    db.refresh(parent)
    meta = parent.metadata_json or {}
    assert meta.get("bundle_funding_receipt_hash") == result.receipt_hash
    assert (meta.get("bundle_funding") or {}).get("funding_settled") is True
    assert (meta.get("bundle_funding") or {}).get("phase") == "FUNDED"


@pytestmark_db
def test_idempotent_second_call_no_op(db: Session, funding_handler_on):
    pe, usdc, portfolio, wallet, parent = _setup_pe_and_parent(db)

    first = settle_bundle_funding_idempotently(
        db,
        parent_intent_id=parent.id,
        amount_usdc=Decimal("100"),
        portfolio_id=portfolio.id,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        bundle_execution_id=parent.bundle_execution_id,
    )
    db.commit()

    trading_mid = resolve_self_trading_available(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
    )
    cash_mid = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)

    second = settle_bundle_funding_idempotently(
        db,
        parent_intent_id=parent.id,
        amount_usdc=Decimal("100"),
        portfolio_id=portfolio.id,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        bundle_execution_id=parent.bundle_execution_id,
    )
    db.commit()

    assert second.idempotent is True
    assert second.settled is True
    assert second.receipt_hash == first.receipt_hash

    trading_after = resolve_self_trading_available(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        entry_asset="USDC",
        entry_instrument_id=usdc.id,
    )
    cash_after = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)
    assert trading_after == trading_mid
    assert cash_after == cash_mid


@pytestmark_db
def test_no_privy_ledger_write(db: Session, funding_handler_on):
    pe, usdc, portfolio, wallet, parent = _setup_pe_and_parent(db)

    privy_before = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=pe.person_id, asset="USDC",
    )
    bal_before = Decimal(str(privy_before.balance))

    deposits_before = db.execute(sa.text("SELECT COUNT(*) FROM person_wallet_deposits")).scalar()

    settle_bundle_funding_idempotently(
        db,
        parent_intent_id=parent.id,
        amount_usdc=Decimal("50"),
        portfolio_id=portfolio.id,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        bundle_execution_id=parent.bundle_execution_id,
    )
    db.commit()

    privy_after = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=pe.person_id, asset="USDC",
    )
    bal_after = Decimal(str(privy_after.balance))
    deposits_after = db.execute(sa.text("SELECT COUNT(*) FROM person_wallet_deposits")).scalar()

    assert bal_after == bal_before
    assert deposits_after == deposits_before


@pytestmark_db
def test_no_cost_basis_executions(db: Session, funding_handler_on):
    pe, usdc, portfolio, wallet, parent = _setup_pe_and_parent(db)

    try:
        cb_before = db.execute(sa.text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
    except Exception:
        pytest.skip("Table cost_basis_executions absente")

    settle_bundle_funding_idempotently(
        db,
        parent_intent_id=parent.id,
        amount_usdc=Decimal("25"),
        portfolio_id=portfolio.id,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        bundle_execution_id=parent.bundle_execution_id,
    )
    db.commit()

    cb_after = db.execute(sa.text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
    assert cb_after == cb_before


@pytestmark_db
def test_wrong_product_type_rejected(db: Session, funding_handler_on):
    pe, usdc, portfolio, wallet, _ = _setup_pe_and_parent(db)
    wrong = _insert_parent(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        product_type=IntentProductType.LIFI_SWAP.value,
    )
    db.commit()

    with pytest.raises(BundleFundingHandlerError) as exc:
        settle_bundle_funding_idempotently(
            db,
            parent_intent_id=wrong.id,
            amount_usdc=Decimal("10"),
            portfolio_id=portfolio.id,
            wallet_id=wallet.id,
            person_id=pe.person_id,
        )
    assert exc.value.code == "bundle.funding.invalid_product_type"


@pytestmark_db
def test_non_parent_intent_rejected(db: Session, funding_handler_on):
    pe, usdc, portfolio, wallet, parent = _setup_pe_and_parent(db)
    child = TransactionIntent(
        person_id=pe.person_id,
        product_type=IntentProductType.BUNDLE_LEG.value,
        operation_type=IntentOperationType.BUNDLE_LEG.value,
        idempotency_key=f"child-{uuid.uuid4().hex}",
        status=IntentStatus.CREATED.value,
        intent_role=IntentRole.CHILD.value,
        parent_intent_id=parent.id,
        bundle_execution_id=parent.bundle_execution_id,
        metadata_json={"bundle_id": str(portfolio.id)},
    )
    db.add(child)
    db.commit()

    with pytest.raises(BundleFundingHandlerError) as exc:
        settle_bundle_funding_idempotently(
            db,
            parent_intent_id=child.id,
            amount_usdc=Decimal("10"),
            portfolio_id=portfolio.id,
            wallet_id=wallet.id,
            person_id=pe.person_id,
        )
    assert exc.value.code == "bundle.funding.invalid_intent_role"


@pytestmark_db
def test_amount_zero_or_negative_rejected(db: Session, funding_handler_on):
    pe, usdc, portfolio, wallet, parent = _setup_pe_and_parent(db)
    db.commit()

    for bad in (Decimal("0"), Decimal("-1")):
        with pytest.raises(BundleFundingHandlerError) as exc:
            settle_bundle_funding_idempotently(
                db,
                parent_intent_id=parent.id,
                amount_usdc=bad,
                portfolio_id=portfolio.id,
                wallet_id=wallet.id,
                person_id=pe.person_id,
            )
        assert exc.value.code == "bundle.funding.invalid_amount"


@pytestmark_db
def test_insufficient_trading_available_rejected(db: Session, funding_handler_on):
    pe, usdc, portfolio, wallet, parent = _setup_pe_and_parent(db, trading_amount="50")
    db.commit()

    with pytest.raises(BundleFundingHandlerError) as exc:
        settle_bundle_funding_idempotently(
            db,
            parent_intent_id=parent.id,
            amount_usdc=Decimal("100"),
            portfolio_id=portfolio.id,
            wallet_id=wallet.id,
            person_id=pe.person_id,
        )
    assert exc.value.code == "bundle.funding.insufficient_trading_available"


@pytestmark_db
def test_receipt_hash_stable(db: Session, funding_handler_on):
    pe, _, portfolio, wallet, parent = _setup_pe_and_parent(db)

    expected = compute_bundle_funding_receipt_hash(
        parent_intent_id=parent.id,
        portfolio_id=portfolio.id,
        person_id=pe.person_id,
        amount_usdc=Decimal("77"),
        bundle_execution_id=parent.bundle_execution_id,
    )

    result = settle_bundle_funding_idempotently(
        db,
        parent_intent_id=parent.id,
        amount_usdc=Decimal("77"),
        portfolio_id=portfolio.id,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        bundle_execution_id=parent.bundle_execution_id,
    )
    db.commit()

    assert result.receipt_hash == expected
    second = compute_bundle_funding_receipt_hash(
        parent_intent_id=parent.id,
        portfolio_id=portfolio.id,
        person_id=pe.person_id,
        amount_usdc=Decimal("77"),
        bundle_execution_id=parent.bundle_execution_id,
    )
    assert second == expected


def test_no_settlement_worker_controller_lifi_imports():
    import services.portfolio_engine.bundles.event_driven.bundle_funding_handler as mod

    text = inspect.getsource(mod).lower()
    for token in (
        "transaction_outbox",
        "settlement_worker",
        "lifi_swap_controller",
        "apply_swap_settlement",
        "reconcile_lifi_swap",
        "services.settlement.settle",
    ):
        assert token not in text, token


def test_legacy_fund_bundle_cash_leg_still_present():
    """B3a ne remplace pas le runtime legacy."""
    import services.portfolio_engine.bundle_execution.bundle_funding as legacy

    assert hasattr(legacy, "fund_bundle_cash_leg_from_self_trading")
