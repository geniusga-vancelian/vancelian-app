"""Backfill Li.FI historique → cost_basis_executions."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from services.cost_basis.backfill_lifi import run_lifi_cost_basis_backfill
from services.cost_basis.ingest_lifi import ingest_lifi_swap_settlement
from services.cost_basis.models import CostBasisExecution
from services.cost_basis.repository import CostBasisExecutionRepository
from services.lifi.models import PersonWalletSwap

from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet

from conftest import make_linked_client

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"


def _seed_privy_wallet(db: Session, pe) -> None:
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-backfill-test"},
    )
    db.flush()


def _seed_usdc_aave_swap(
    db: Session,
    pe,
    *,
    amount_in: str = "3.33335",
    amount_out: str = "0.04140135",
    audit_receive: bool = True,
) -> PersonWalletSwap:
    swap_id = uuid.uuid4()
    audit = []
    if audit_receive:
        audit.append(
            {
                "event": "swap_settled",
                "actual_receive_amount": amount_out,
                "source": "test",
            }
        )
    swap = PersonWalletSwap(
        id=swap_id,
        person_id=pe.person_id,
        status="CONFIRMED",
        from_asset="USDC",
        to_asset="AAVE",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal(amount_in),
        estimated_receive=Decimal(amount_out),
        tx_hash="0xbackfilltest",
        confirmed_at=datetime.now(timezone.utc),
        audit_log=audit,
    )
    db.add(swap)
    db.flush()
    return swap


def test_backfill_usdc_aave_historical(db: Session):
    pe = make_linked_client(db, email=f"bf-lifi-{uuid.uuid4().hex[:8]}@test.local")
    _seed_privy_wallet(db, pe)
    swap = _seed_usdc_aave_swap(db, pe)

    result = run_lifi_cost_basis_backfill(
        db,
        dry_run=False,
        person_id=pe.person_id,
        asset="AAVE",
    )
    assert result.scanned >= 1
    assert result.ingested >= 1
    assert result.rows_created >= 1

    row = CostBasisExecutionRepository().find_by_provider(
        db,
        provider_source="lifi",
        provider_execution_id=f"lifi:{swap.id}:acquisition:AAVE",
    )
    assert row is not None
    price = Decimal(str(row.execution_price_usdc))
    assert abs(price - Decimal("80.51")) < Decimal("0.1")


def test_backfill_idempotent_rerun(db: Session):
    pe = make_linked_client(db, email=f"bf-idem-{uuid.uuid4().hex[:8]}@test.local")
    _seed_privy_wallet(db, pe)
    _seed_usdc_aave_swap(db, pe)

    first = run_lifi_cost_basis_backfill(db, dry_run=False, person_id=pe.person_id)
    assert first.rows_created >= 1

    second = run_lifi_cost_basis_backfill(db, dry_run=False, person_id=pe.person_id)
    assert second.ignored >= 1
    assert second.rows_created == 0
    assert any(o.reason == "already_ingested" for o in second.outcomes)


def test_backfill_dry_run_writes_nothing(db: Session):
    pe = make_linked_client(db, email=f"bf-dry-{uuid.uuid4().hex[:8]}@test.local")
    _seed_privy_wallet(db, pe)
    swap = _seed_usdc_aave_swap(db, pe)

    result = run_lifi_cost_basis_backfill(
        db,
        dry_run=True,
        person_id=pe.person_id,
    )
    assert result.dry_run is True
    assert result.eligible >= 1
    assert any(o.status == "would_ingest" for o in result.outcomes)

    row = CostBasisExecutionRepository().find_by_provider(
        db,
        provider_source="lifi",
        provider_execution_id=f"lifi:{swap.id}:acquisition:AAVE",
    )
    assert row is None


def test_backfill_skips_already_ingested(db: Session):
    pe = make_linked_client(db, email=f"bf-skip-{uuid.uuid4().hex[:8]}@test.local")
    _seed_privy_wallet(db, pe)
    swap = _seed_usdc_aave_swap(db, pe)

    from services.lifi.lifi_actual_receive import _resolve_swap_wallet

    wallet = _resolve_swap_wallet(db, swap)
    ingest_lifi_swap_settlement(
        db,
        swap,
        wallet=wallet,
        amount_out=Decimal("0.04140135"),
    )

    result = run_lifi_cost_basis_backfill(db, dry_run=False, person_id=pe.person_id)
    assert result.ignored >= 1
    assert result.rows_created == 0

    count = (
        db.query(CostBasisExecution)
        .filter(
            CostBasisExecution.provider_source == "lifi",
            CostBasisExecution.client_id == pe.id,
        )
        .count()
    )
    assert count == 1
