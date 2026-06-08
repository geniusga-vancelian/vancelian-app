"""B3c — Bundle leg settlement handler (child-only · BUY USDC→AAVE · Base)."""
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.bundle_funding import sum_bundle_cash_leg_quantity
from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (
    BUNDLE_LEG_BUY_TO_ASSET,
    BundleLegSettlementHandlerError,
    compute_bundle_leg_settlement_receipt_hash,
    compute_child_report_hash,
    settle_bundle_leg_idempotently,
)
from services.portfolio_engine.bundles.orchestrator import POSITION_TYPE_CASH, POSITION_TYPE_SPOT
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.privy_wallet.repository import PersonWalletBalanceRepository
from services.transaction_intents.bundle_parent_child_repository import bundle_child_idempotency_key
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

PLAN_HASH = "sha256:plan-test-b3c"
PLANNER_VERSION = "v1"
EVM_ADDR = f"0x{uuid.uuid4().hex[:40]}"


@pytest.fixture
def leg_settlement_handler_on(monkeypatch):
    monkeypatch.setenv("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED", "true")


def _instrument_aave(db: Session) -> Instrument:
    asset = db.query(Asset).filter(Asset.symbol == "AAVE").first()
    if asset is None:
        asset = Asset(symbol="AAVE", name="Aave", asset_type="crypto")
        db.add(asset)
        db.flush()
    instr = (
        db.query(Instrument)
        .filter(Instrument.asset_id == asset.id, Instrument.instrument_type == "spot")
        .first()
    )
    if instr is None:
        instr = Instrument(
            asset_id=asset.id,
            code="AAVE_SPOT",
            name="AAVE Spot",
            instrument_type="spot",
        )
        db.add(instr)
        db.flush()
    return instr


def _seed_bundle_cash(db: Session, portfolio_id: uuid.UUID, usdc_instr_id: uuid.UUID, amount: str):
    BundleOrchestrator._credit_cash_leg(
        db,
        portfolio_id,
        usdc_instr_id,
        Decimal(amount),
        Decimal("0"),
    )


def _insert_child_with_swap(
    db: Session,
    *,
    person_id: uuid.UUID,
    parent_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    usdc_instr: Instrument,
    aave_instr: Instrument,
    leg_direction: str = "buy",
    from_asset: str = "USDC",
    to_asset: str = "AAVE",
    wallet_address: str = EVM_ADDR,
) -> tuple[TransactionIntent, PersonWalletSwap]:
    swap_id = uuid.uuid4()
    swap = PersonWalletSwap(
        id=swap_id,
        person_id=person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset=from_asset,
        to_asset=to_asset,
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("50"),
        estimated_receive=Decimal("0.5"),
        tx_hash=f"0x{uuid.uuid4().hex}",
        audit_log=[
            {
                "event": "bundle_leg_context",
                "bundle_execution": True,
                "batch_id": "batch-b3c",
                "leg_id": "leg-0",
                "portfolio_id": str(portfolio_id),
                "bundle_action": "invest",
                "leg_action": "rebalance_buy",
            },
            {"event": "quote_requested", "signing_wallet_address": wallet_address},
        ],
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(swap)
    db.flush()

    child = TransactionIntent(
        person_id=person_id,
        product_type=IntentProductType.BUNDLE_LEG.value,
        operation_type=IntentOperationType.BUNDLE_LEG.value,
        idempotency_key=bundle_child_idempotency_key(parent_intent_id=parent_id, leg_index=0),
        status=IntentStatus.SUBMITTED.value,
        intent_role=IntentRole.CHILD.value,
        parent_intent_id=parent_id,
        leg_index=0,
        linked_table="person_wallet_swaps",
        linked_id=swap_id,
        metadata_json={
            "plan_hash": PLAN_HASH,
            "planner_version": PLANNER_VERSION,
            "leg_index": 0,
            "leg_direction": leg_direction,
            "from_asset": from_asset,
            "to_asset": to_asset,
            "portfolio_id": str(portfolio_id),
            "entry_instrument_id": str(usdc_instr.id),
            "target_instrument_id": str(aave_instr.id),
            "planned_amount_in": "50",
        },
    )
    db.add(child)
    db.flush()
    return child, swap


def _setup_child_rail(db: Session):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    aave = _instrument_aave(db)
    portfolio = _bundle_portfolio(db, pe.id)
    _seed_bundle_cash(db, portfolio.id, usdc.id, "200")

    from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet

    wallet = upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=EVM_ADDR,
    )
    _seed_privy_usdc(db, pe.person_id, wallet.id, "500")

    parent_id = uuid.uuid4()
    child, swap = _insert_child_with_swap(
        db,
        person_id=pe.person_id,
        parent_id=parent_id,
        portfolio_id=portfolio.id,
        usdc_instr=usdc,
        aave_instr=aave,
        wallet_address=wallet.address,
    )
    db.commit()
    return pe, usdc, aave, portfolio, child, swap, wallet


@pytestmark_db
def test_flag_off_no_settlement(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED", "false")
    _, usdc, _, portfolio, child, swap, _ = _setup_child_rail(db)

    cash_before = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)
    result = settle_bundle_leg_idempotently(db, child_intent_id=child.id)
    db.commit()

    assert result.skipped is True
    assert result.settled is False
    assert result.reason == "bundle_leg_settlement_handler_disabled"
    assert sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id) == cash_before
    assert not swap_settlement_applied(swap)


def swap_settlement_applied(swap: PersonWalletSwap) -> bool:
    from services.lifi.lifi_swap_settlement import swap_settlement_already_applied

    return swap_settlement_already_applied(swap)


@pytestmark_db
def test_nominal_buy_usdc_aave_settlement(db: Session, leg_settlement_handler_on):
    pe, usdc, aave, portfolio, child, swap, wallet = _setup_child_rail(db)

    privy_before = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=pe.person_id, asset="USDC",
    )
    bal_before = Decimal(str(privy_before.balance))
    cash_before = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)

    result = settle_bundle_leg_idempotently(db, child_intent_id=child.id)
    db.commit()

    assert result.settled is True
    assert result.skipped is False
    assert result.settlement_receipt_hash and result.settlement_receipt_hash.startswith("sha256:")
    assert result.child_report_hash and result.child_report_hash.startswith("sha256:")
    assert result.plan_hash == PLAN_HASH
    assert result.planner_version == PLANNER_VERSION
    assert result.leg_index == 0

    db.refresh(child)
    meta = child.metadata_json or {}
    assert meta.get("settlement_receipt_hash") == result.settlement_receipt_hash
    assert meta.get("child_report_hash") == result.child_report_hash
    assert (meta.get("bundle_leg_settlement") or {}).get("phase") == "SETTLED"

    privy_after = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=pe.person_id, asset="USDC",
    )
    assert Decimal(str(privy_after.balance)) < bal_before
    assert sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id) < cash_before

    aave_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == aave.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    assert aave_atom is not None and Decimal(str(aave_atom.quantity)) > 0


@pytestmark_db
def test_idempotent_second_call_no_op(db: Session, leg_settlement_handler_on):
    _, usdc, _, portfolio, child, _, _ = _setup_child_rail(db)

    first = settle_bundle_leg_idempotently(db, child_intent_id=child.id)
    db.commit()
    cash_mid = sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id)

    second = settle_bundle_leg_idempotently(db, child_intent_id=child.id)
    db.commit()

    assert second.idempotent is True
    assert second.settlement_receipt_hash == first.settlement_receipt_hash
    assert second.child_report_hash == first.child_report_hash
    assert sum_bundle_cash_leg_quantity(db, portfolio.id, usdc.id) == cash_mid


@pytestmark_db
def test_sell_direction_rejected(db: Session, leg_settlement_handler_on):
    pe, usdc, aave, portfolio, _, _, _ = _setup_child_rail(db)
    parent_id = uuid.uuid4()
    child, _ = _insert_child_with_swap(
        db,
        person_id=pe.person_id,
        parent_id=parent_id,
        portfolio_id=portfolio.id,
        usdc_instr=usdc,
        aave_instr=aave,
        leg_direction="sell",
        from_asset="AAVE",
        to_asset="USDC",
    )
    db.commit()

    with pytest.raises(BundleLegSettlementHandlerError) as exc:
        settle_bundle_leg_idempotently(db, child_intent_id=child.id)
    assert exc.value.code == "bundle.leg.sell_not_allowed_b3c"


@pytestmark_db
def test_invalid_asset_pair_rejected(db: Session, leg_settlement_handler_on):
    pe, usdc, aave, portfolio, _, _, _ = _setup_child_rail(db)
    parent_id = uuid.uuid4()
    child, _ = _insert_child_with_swap(
        db,
        person_id=pe.person_id,
        parent_id=parent_id,
        portfolio_id=portfolio.id,
        usdc_instr=usdc,
        aave_instr=aave,
        from_asset="USDC",
        to_asset="UNI",
    )
    db.commit()

    with pytest.raises(BundleLegSettlementHandlerError) as exc:
        settle_bundle_leg_idempotently(db, child_intent_id=child.id)
    assert exc.value.code == "bundle.leg.invalid_asset_pair_b3c"


@pytestmark_db
def test_missing_plan_hash_rejected(db: Session, leg_settlement_handler_on):
    _, _, _, _, child, _, _ = _setup_child_rail(db)
    meta = dict(child.metadata_json or {})
    meta.pop("plan_hash", None)
    child.metadata_json = meta
    db.add(child)
    db.commit()

    with pytest.raises(BundleLegSettlementHandlerError) as exc:
        settle_bundle_leg_idempotently(db, child_intent_id=child.id)
    assert exc.value.code == "bundle.leg.missing_plan_hash"


@pytestmark_db
def test_no_cost_basis_executions(db: Session, leg_settlement_handler_on):
    _, _, _, _, child, _, _ = _setup_child_rail(db)
    try:
        cb_before = db.execute(sa.text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
    except Exception:
        pytest.skip("Table cost_basis_executions absente")

    settle_bundle_leg_idempotently(db, child_intent_id=child.id)
    db.commit()

    cb_after = db.execute(sa.text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
    assert cb_after == cb_before


@pytestmark_db
def test_child_report_hash_stable(db: Session, leg_settlement_handler_on):
    _, _, _, _, child, swap, _ = _setup_child_rail(db)

    receipt = compute_bundle_leg_settlement_receipt_hash(
        child_intent_id=child.id,
        swap_id=swap.id,
        plan_hash=PLAN_HASH,
        planner_version=PLANNER_VERSION,
        leg_index=0,
    )
    report = compute_child_report_hash(
        child_intent_id=child.id,
        settlement_receipt_hash=receipt,
        plan_hash=PLAN_HASH,
        planner_version=PLANNER_VERSION,
        leg_index=0,
    )

    result = settle_bundle_leg_idempotently(db, child_intent_id=child.id)
    db.commit()

    assert result.settlement_receipt_hash == receipt
    assert result.child_report_hash == report


def test_api_accepts_only_child_intent_id():
    import inspect as ins

    sig = ins.signature(settle_bundle_leg_idempotently)
    params = [p for p in sig.parameters if p != "db"]
    assert params == ["child_intent_id"]


def test_no_parent_query_in_handler_source():
    import services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler as mod

    text = ins_getsource(mod).lower()
    forbidden = (
        "find_parent",
        "parent_intent_id=",
        "recompute_bundle_parent",
        "transaction_outbox",
        "settlement_worker",
        "lifi_swap_controller",
        "reconcile_lifi_swap",
        "services.settlement.settle",
    )
    for token in forbidden:
        assert token not in text, token


def ins_getsource(mod):
    return inspect.getsource(mod)


def test_legacy_bundle_lifi_leg_service_still_present():
    from services.portfolio_engine.bundle_execution import bundle_lifi_leg_service as legacy

    assert hasattr(legacy.BundleLifiLegService, "_apply_post_confirmation")
