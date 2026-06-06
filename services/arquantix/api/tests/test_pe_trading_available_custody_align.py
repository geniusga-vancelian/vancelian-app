"""Tests alignement PE trading_available ← ledger Privy liquide (EURC gap)."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from services.portfolio_engine.direct_overlay import align_pe_trading_available_from_ledger_liquid
from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
from services.portfolio_engine.portfolio_breakdown import build_asset_breakdown_row
from services.portfolio_engine.internal_scope_movements.types import CurrentPeScopeSnapshot
from services.privy_wallet.repository import PersonWalletBalanceRepository
from tests.conftest import make_linked_client


def _seed_privy_balance(db: Session, pe, asset: str, balance: str) -> None:
    from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet

    wallet = upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"[:42],
        chain_id=8453,
        metadata_json={"privy_wallet_id": f"w-align-{uuid.uuid4().hex[:8]}"},
    )
    row = PersonWalletBalanceRepository.get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        asset=asset,
    )
    row.balance = Decimal(balance)
    row.available_balance = Decimal(balance)
    db.flush()


def test_eurc_privy_only_aligns_trading_available(db: Session):
    pe = make_linked_client(db)
    _seed_privy_balance(db, pe, "EURC", "91.414272")

    aligned = align_pe_trading_available_from_ledger_liquid(db, pe.person_id)
    assert len(aligned) == 1
    assert aligned[0]["asset"] == "EURC"
    assert Decimal(aligned[0]["expected_trading_available"]) == Decimal("91.414272")

    snap = read_current_pe_scope_snapshot(db, pe.person_id)
    assert snap.trading_available["EURC"] == Decimal("91.414272")


def test_usdc_vault_split_not_double_counted(db: Session):
    pe = make_linked_client(db)
    _seed_privy_balance(db, pe, "USDC", "176.74")

    from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom, _resolve_or_create_instrument
    from services.portfolio_engine.portfolios.models import Portfolio

    direct_pf = ensure_direct_portfolio(db, pe.id)
    usdc_instr = _resolve_or_create_instrument(db, "USDC")
    sync_direct_atom(db, direct_pf.id, usdc_instr.id, Decimal("62.64"), Decimal("62.64"))

    vault_pf = Portfolio(
        client_id=pe.id,
        portfolio_type="vault_portfolio",
        name="Vault",
        base_currency="USD",
        status="active",
    )
    db.add(vault_pf)
    db.flush()
    from services.portfolio_engine.positions.models import PositionAtom

    db.add(
        PositionAtom(
            portfolio_id=vault_pf.id,
            instrument_id=usdc_instr.id,
            position_type="spot",
            status="open",
            quantity=Decimal("114.10"),
            available_quantity=Decimal("114.10"),
            metadata_={"scope": "vault_position"},
        )
    )
    db.flush()

    aligned = align_pe_trading_available_from_ledger_liquid(db, pe.person_id)
    assert aligned == []

    snap = read_current_pe_scope_snapshot(db, pe.person_id)
    assert snap.trading_available["USDC"] == Decimal("62.64")


def test_collateral_asset_skipped(db: Session):
    pe = make_linked_client(db)
    _seed_privy_balance(db, pe, "CBBTC", "0.00237")

    from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, _resolve_or_create_instrument
    from services.portfolio_engine.positions.enums import PositionType
    from services.portfolio_engine.positions.models import PositionAtom

    direct_pf = ensure_direct_portfolio(db, pe.id)
    instr = _resolve_or_create_instrument(db, "CBBTC")
    db.add(
        PositionAtom(
            portfolio_id=direct_pf.id,
            instrument_id=instr.id,
            position_type=PositionType.COLLATERAL.value,
            status="open",
            quantity=Decimal("0.00031643"),
            available_quantity=Decimal("0"),
            metadata_={"scope": "trading_locked_collateral"},
        )
    )
    db.flush()

    aligned = align_pe_trading_available_from_ledger_liquid(db, pe.person_id)
    assert aligned == []


def test_breakdown_row_eurc_after_align_logic():
    """Après alignement, available = total_holdings pour EURC pur."""
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.trading_available["EURC"] = Decimal("91.414272")
    row = build_asset_breakdown_row(
        "EURC",
        pe=pe,
        ledger={"EURC": Decimal("91.414272")},
        on_chain_base={"EURC": Decimal("91.414272")},
        pending_by_asset={},
    )
    assert row["available"] == row["total_holdings"]
    assert Decimal(row["swappable_balance"]) == Decimal("91.414272")
