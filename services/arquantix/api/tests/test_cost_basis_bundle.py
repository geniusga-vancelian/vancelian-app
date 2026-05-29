"""Cost basis bundle Li.FI + wallet_history charts."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.cost_basis.backfill_bundle_lifi import run_bundle_lifi_cost_basis_backfill
from services.cost_basis.ingest_bundle_lifi import ingest_bundle_lifi_swap_settlement
from services.cost_basis.models import CostBasisExecution
from services.cost_basis.repository import CostBasisExecutionRepository
from services.cost_basis.wac import compute_wac_from_executions
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.wallet_history.service import build_wallet_history

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
        metadata_json={"privy_wallet_id": "w-bundle-cb-test"},
    )
    db.flush()


def _bundle_swap_audit(*, portfolio_id: str, batch_id: str) -> list[dict]:
    return [
        {
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "portfolio_id": portfolio_id,
            "batch_id": batch_id,
            "bundle_action": "allocation",
            "leg_action": "allocation",
        },
    ]


def _seed_confirmed_bundle_swap(
    db: Session,
    pe,
    *,
    portfolio_id: uuid.UUID,
    from_asset: str = "USDC",
    to_asset: str = "AAVE",
) -> PersonWalletSwap:
    batch_id = str(uuid.uuid4())
    swap = PersonWalletSwap(
        id=uuid.uuid4(),
        person_id=pe.person_id,
        from_asset=from_asset,
        to_asset=to_asset,
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("100"),
        estimated_receive=Decimal("1.2"),
        status=SwapSessionStatus.CONFIRMED.value,
        tx_hash="0x" + uuid.uuid4().hex,
        confirmed_at=datetime.now(timezone.utc),
        audit_log=[
            *_bundle_swap_audit(portfolio_id=str(portfolio_id), batch_id=batch_id),
            {"event": "swap_settled", "actual_receive_amount": "1.2", "source": "test"},
        ],
    )
    db.add(swap)
    db.flush()
    return swap


class _Wallet:
    pe_client_id = None
    person_id = None

    def __init__(self, pe):
        self.pe_client_id = pe.id
        self.person_id = pe.person_id


def test_bundle_lifi_ingest_scoped(db: Session):
    pe = make_linked_client(db)
    _seed_privy_wallet(db, pe)
    portfolio_id = uuid.uuid4()
    swap = _seed_confirmed_bundle_swap(db, pe, portfolio_id=portfolio_id)
    db.commit()

    created = ingest_bundle_lifi_swap_settlement(
        db,
        swap,
        wallet=_Wallet(pe),
        amount_out=Decimal("1.2"),
        portfolio_id=portfolio_id,
    )
    assert created >= 1

    row = (
        db.query(CostBasisExecution)
        .filter(
            CostBasisExecution.provider_source == "bundle_lifi",
            CostBasisExecution.portfolio_scope == "bundle",
            CostBasisExecution.portfolio_id == portfolio_id,
        )
        .first()
    )
    assert row is not None
    assert row.position_asset == "AAVE"


def test_bundle_backfill_idempotent(db: Session):
    pe = make_linked_client(db)
    _seed_privy_wallet(db, pe)
    portfolio_id = uuid.uuid4()
    _seed_confirmed_bundle_swap(db, pe, portfolio_id=portfolio_id)
    db.commit()

    first = run_bundle_lifi_cost_basis_backfill(
        db, dry_run=False, person_id=pe.person_id, portfolio_id=portfolio_id
    )
    assert first.eligible >= 1
    db.commit()

    second = run_bundle_lifi_cost_basis_backfill(
        db, dry_run=False, person_id=pe.person_id, portfolio_id=portfolio_id
    )
    assert second.ignored >= 1


def test_wallet_history_bundle_uses_cost_basis(db: Session):
    pe = make_linked_client(db)
    _seed_privy_wallet(db, pe)
    portfolio_id = uuid.uuid4()
    swap = _seed_confirmed_bundle_swap(db, pe, portfolio_id=portfolio_id)
    ingest_bundle_lifi_swap_settlement(
        db,
        swap,
        wallet=_Wallet(pe),
        amount_out=Decimal("1.2"),
        portfolio_id=portfolio_id,
    )
    db.commit()

    history = build_wallet_history(
        db,
        pe.id,
        mode="performance_value",
        portfolio_scope="bundle",
        portfolio_id=str(portfolio_id),
        asset="AAVE",
    )
    assert len(history["points"]) >= 1
