"""Bundle scope movements — dry-run from PE atoms + audit events (read-only)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

from .enums import InternalMovementType, InternalScope
from .types import CurrentPeScopeSnapshot, ScopeMovement, ScopeMovementSet
from .utils import (
    TOLERANCE,
    accumulate_movement_net,
    normalize_asset,
    resolve_client_id,
)

AUDIT_FUND = "bundle.fund_cash_leg"
AUDIT_RELEASE = "bundle.release_cash_leg"


def _asset_symbol_for_instrument(db: Session, instrument_id: UUID) -> str:
    from services.portfolio_engine.instruments.models import Instrument
    from services.portfolio_engine.assets.models import Asset

    row = (
        db.query(Asset.symbol)
        .join(Instrument, Instrument.asset_id == Asset.id)
        .filter(Instrument.id == instrument_id)
        .first()
    )
    return normalize_asset(row[0]) if row else "UNKNOWN"


def read_current_bundle_pe_scopes(
    db: Session,
    *,
    person_id: UUID,
    client_id: UUID,
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """Retourne (bundle_cash, bundle_position) depuis les atoms PE ouverts."""
    bundle_pf_ids = [
        r[0]
        for r in db.query(Portfolio.id)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type == "bundle_portfolio",
            Portfolio.status == "active",
        )
        .all()
    ]
    cash: dict[str, Decimal] = {}
    spot: dict[str, Decimal] = {}
    if not bundle_pf_ids:
        return cash, spot

    atoms = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id.in_(bundle_pf_ids),
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
        if atom.position_type == PositionType.CASH.value or meta.get("role") == "bundle_cash_leg":
            cash[asset] = cash.get(asset, Decimal("0")) + qty
        elif atom.position_type == PositionType.SPOT.value:
            spot[asset] = spot.get(asset, Decimal("0")) + qty
    return cash, spot


def compute_expected_bundle_scope_movements(
    db: Session,
    person_id: UUID,
    *,
    audit_limit: int = 500,
) -> ScopeMovementSet:
    """
    Reconstruit les mouvements bundle depuis les audit events PE (fund/release).

    Vérifie aussi que les atoms PE actuels sont cohérents avec la somme nette attendue.
    """
    result = ScopeMovementSet(person_id=person_id, product="bundle")
    client_id = resolve_client_id(db, person_id)
    if client_id is None:
        result.notes.append("Aucun pe_client pour cette personne.")
        return result

    portfolio_ids = [
        str(r[0])
        for r in db.query(Portfolio.id)
        .filter(
            Portfolio.client_id == client_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .all()
    ]

    q = db.query(AuditEvent).filter(
        AuditEvent.action.in_([AUDIT_FUND, AUDIT_RELEASE]),
    )
    if portfolio_ids:
        q = q.filter(AuditEvent.entity_id.in_(portfolio_ids))
    else:
        q = q.filter(AuditEvent.entity_id == "__none__")

    audits = q.order_by(AuditEvent.created_at.asc()).limit(audit_limit).all()

    for row in audits:
        meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
        meta_client = str(meta.get("client_id") or "")
        if meta_client and meta_client != str(client_id):
            continue

        asset = normalize_asset(meta.get("entry_asset") or meta.get("asset"))
        try:
            qty = Decimal(str(meta.get("amount") or "0"))
        except Exception:
            continue
        if qty <= 0:
            continue

        batch_id = str(meta.get("batch_id") or row.id)
        if row.action == AUDIT_FUND:
            movement = ScopeMovement(
                movement_type=InternalMovementType.FUND.value,
                source_scope=InternalScope.TRADING_AVAILABLE.value,
                destination_scope=InternalScope.BUNDLE_CASH.value,
                asset=asset,
                quantity=qty,
                reference_id=batch_id,
                source_system="pe_audit_events",
                metadata={"audit_event_id": str(row.id), "action": row.action},
            )
        else:
            movement = ScopeMovement(
                movement_type=InternalMovementType.RELEASE.value,
                source_scope=InternalScope.BUNDLE_CASH.value,
                destination_scope=InternalScope.TRADING_AVAILABLE.value,
                asset=asset,
                quantity=qty,
                reference_id=batch_id,
                source_system="pe_audit_events",
                metadata={"audit_event_id": str(row.id), "action": row.action},
            )
        result.movements.append(movement)
        accumulate_movement_net(result.net_by_scope, movement)

    bundle_cash, bundle_spot = read_current_bundle_pe_scopes(
        db, person_id=person_id, client_id=client_id
    )
    expected_cash: dict[str, Decimal] = {}
    for (_scope, asset), qty in result.net_by_scope.items():
        if _scope == InternalScope.BUNDLE_CASH.value:
            expected_cash[asset] = expected_cash.get(asset, Decimal("0")) + qty

    for asset, pe_qty in bundle_cash.items():
        exp_qty = expected_cash.get(asset, Decimal("0"))
        if abs(pe_qty - exp_qty) > TOLERANCE and result.movements:
            result.notes.append(
                f"Bundle cash {asset}: PE atom={pe_qty} vs net audit fund/release={exp_qty} "
                "(allocation legs consomment le cash — écart attendu si invest confirmé)."
            )

    if bundle_cash or bundle_spot:
        result.notes.append(
            f"PE bundle snapshot: cash={ {k: str(v) for k, v in bundle_cash.items()} }, "
            f"spot={ {k: str(v) for k, v in bundle_spot.items()} }"
        )
    elif not result.movements:
        result.notes.append("Aucun audit bundle.fund/release ni atom bundle PE.")

    return result
