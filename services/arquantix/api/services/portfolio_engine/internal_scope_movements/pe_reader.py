"""Read current PE scope balances — read-only."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

from .bundle import _asset_symbol_for_instrument
from .types import CurrentPeScopeSnapshot
from .utils import normalize_asset, resolve_client_id

PORTFOLIO_DIRECT = "direct_portfolio"


def read_current_pe_scope_snapshot(db: Session, person_id: UUID) -> CurrentPeScopeSnapshot:
    """Lit les scopes PE actuels sans mutation."""
    snap = CurrentPeScopeSnapshot(person_id=person_id, client_id=resolve_client_id(db, person_id))
    if snap.client_id is None:
        return snap

    direct_pf = (
        db.query(Portfolio.id)
        .filter(
            Portfolio.client_id == snap.client_id,
            Portfolio.portfolio_type == PORTFOLIO_DIRECT,
            Portfolio.status == "active",
        )
        .first()
    )
    bundle_pf_ids = [
        r[0]
        for r in db.query(Portfolio.id)
        .filter(
            Portfolio.client_id == snap.client_id,
            Portfolio.portfolio_type == "bundle_portfolio",
            Portfolio.status == "active",
        )
        .all()
    ]
    vault_pf_ids = [
        r[0]
        for r in db.query(Portfolio.id)
        .filter(
            Portfolio.client_id == snap.client_id,
            Portfolio.portfolio_type == "vault_portfolio",
            Portfolio.status == "active",
        )
        .all()
    ]

    portfolio_ids = []
    if direct_pf:
        portfolio_ids.append(direct_pf[0])
    portfolio_ids.extend(bundle_pf_ids)
    portfolio_ids.extend(vault_pf_ids)

    if not portfolio_ids:
        return snap

    atoms = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id.in_(portfolio_ids),
            PositionAtom.status == "open",
        )
        .all()
    )

    for atom in atoms:
        asset = _asset_symbol_for_instrument(db, atom.instrument_id)
        qty = Decimal(str(atom.quantity or 0))
        if qty == 0:
            continue
        meta = atom.metadata_ if isinstance(atom.metadata_, dict) else {}
        scope_hint = str(meta.get("scope") or "").strip().lower()

        if atom.position_type == PositionType.COLLATERAL.value or scope_hint == "trading_locked_collateral":
            snap.trading_locked_collateral[asset] = (
                snap.trading_locked_collateral.get(asset, Decimal("0")) + qty
            )
            continue
        if atom.position_type == PositionType.BORROWING.value or scope_hint == "liability":
            snap.liability[asset] = snap.liability.get(asset, Decimal("0")) + qty
            continue
        if scope_hint == "vault_position" or meta.get("role") == "vault_position":
            snap.vault_position[asset] = snap.vault_position.get(asset, Decimal("0")) + qty
            continue

        if atom.portfolio_id in vault_pf_ids:
            if atom.position_type == PositionType.SPOT.value:
                snap.vault_position[asset] = snap.vault_position.get(asset, Decimal("0")) + qty
            continue

        if atom.portfolio_id == direct_pf[0] if direct_pf else None:
            if atom.position_type == PositionType.SPOT.value:
                snap.trading_available[asset] = snap.trading_available.get(asset, Decimal("0")) + qty
            continue

        if atom.portfolio_id in bundle_pf_ids:
            if atom.position_type == PositionType.CASH.value or meta.get("role") == "bundle_cash_leg":
                snap.bundle_cash[asset] = snap.bundle_cash.get(asset, Decimal("0")) + qty
            elif atom.position_type == PositionType.SPOT.value:
                snap.bundle_position[asset] = snap.bundle_position.get(asset, Decimal("0")) + qty

    return snap
