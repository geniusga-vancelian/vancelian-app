"""Cleanup ops contrôlé pour batches bundle invest legacy zombies — R4.5-E.2-C.

Strictement limité à un ``batch_id`` explicite. Aucune mutation PE / cash / spot.
Par défaut ``dry_run=True`` — ``--apply`` uniquement après validation humaine.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_ledger.reconciliation import reconcile_bundle_ledger_shadow
from services.portfolio_engine.bundles.bundle_invest_lock import clear_invest_lock
from services.portfolio_engine.bundles.bundle_reconciliation_read_model import (
    STATUS_RECONCILIATION_REQUIRED,
    build_bundle_reconciliation_state,
    invest_lock_ttl_minutes,
    list_batch_allocation_swaps,
    read_raw_invest_lock,
)
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.hardening.audit_repository import AuditRepository
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.assets.models import Asset
from services.transaction_intents.bundle_intent_sync import LEG_FAILED, _normalize_legs
from services.transaction_intents.enums import IntentStatus
from services.transaction_intents.repository import TransactionIntentRepository

logger = logging.getLogger(__name__)

TERMINAL_OUTCOME_COMPLETED_PARTIAL = "completed_partial_allocation"
AUDIT_ACTION_OPS_COMPLETED_PARTIAL = "ops.bundle_invest.completed_partial_allocation"
SKIP_REASON_AWAITING_SIGNATURE_STALE = "awaiting_signature_stale"
ENTITY_TYPE_BUNDLE_INVEST = "bundle_invest"

PENDING_SWAP_STATUSES = frozenset({
    SwapSessionStatus.PENDING.value,
    SwapSessionStatus.QUOTE_RECEIVED.value,
    SwapSessionStatus.AWAITING_SIGNATURE.value,
    SwapSessionStatus.SUBMITTED.value,
})


class BundleLegacyCleanupError(Exception):
    """Erreur générique cleanup legacy."""


class BundleLegacyCleanupRejected(BundleLegacyCleanupError):
    """Préconditions non satisfaites — aucune mutation."""

    def __init__(self, code: str, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        self.code = code
        self.details = details or {}
        super().__init__(message)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_client(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
) -> Client:
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .first()
    )
    if portfolio is None:
        raise BundleLegacyCleanupRejected("portfolio_not_found", f"portfolio {portfolio_id} introuvable")

    client = db.query(Client).filter(Client.id == portfolio.client_id).first()
    if client is None or client.person_id != person_id:
        raise BundleLegacyCleanupRejected(
            "person_portfolio_mismatch",
            f"person_id {person_id} ne correspond pas au portfolio {portfolio_id}",
        )
    return client


def snapshot_pe_bundle_positions(
    db: Session,
    *,
    portfolio_id: UUID,
) -> dict[str, Any]:
    """Quantités PE cash + spot — pour vérifier zéro mouvement lors du cleanup."""
    rows = (
        db.query(PositionAtom, Instrument, Asset)
        .join(Instrument, Instrument.id == PositionAtom.instrument_id)
        .join(Asset, Asset.id == Instrument.asset_id)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.status == "open",
        )
        .all()
    )
    cash: list[dict[str, Any]] = []
    spots: list[dict[str, Any]] = []
    for atom, _instr, asset in rows:
        qty = Decimal(str(atom.quantity or 0))
        if qty <= 0:
            continue
        row = {
            "atom_id": str(atom.id),
            "asset": asset.symbol,
            "position_type": atom.position_type,
            "quantity": str(qty),
            "cost_basis": str(atom.cost_basis or 0),
        }
        if atom.position_type == PositionType.CASH.value:
            cash.append(row)
        elif atom.position_type == PositionType.SPOT.value:
            spots.append(row)
    return {"cash": cash, "spots": spots}


def _allocation_swaps_have_live_onchain_tx(
    swaps: list[PersonWalletSwap],
) -> list[dict[str, Any]]:
    """Swap allocation du batch avec tx soumise on-chain (bloquant)."""
    blocking: list[dict[str, Any]] = []
    for swap in swaps:
        if str(swap.status) != SwapSessionStatus.SUBMITTED.value:
            continue
        tx = (swap.tx_hash or "").strip()
        if tx:
            blocking.append({
                "swap_id": str(swap.id),
                "asset": str(swap.to_asset or ""),
                "status": swap.status,
                "tx_hash": tx,
            })
    return blocking


def _stale_pending_swaps_for_skip(
    swaps: list[PersonWalletSwap],
) -> list[PersonWalletSwap]:
    out: list[PersonWalletSwap] = []
    for swap in swaps:
        if str(swap.status) not in PENDING_SWAP_STATUSES:
            continue
        if (swap.tx_hash or "").strip():
            continue
        out.append(swap)
    return out


def _find_cleanup_audit(
    db: Session,
    *,
    batch_id: str,
    idempotency_key: str,
) -> bool:
    from services.portfolio_engine.hardening.audit_models import AuditEvent

    by_request = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.action == AUDIT_ACTION_OPS_COMPLETED_PARTIAL,
            AuditEvent.request_id == idempotency_key,
        )
        .first()
    )
    if by_request is not None:
        return True

    rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.action == AUDIT_ACTION_OPS_COMPLETED_PARTIAL)
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
        .all()
    )
    for row in rows:
        meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
        if (
            str(meta.get("batch_id") or "") == batch_id
            and str(meta.get("idempotency_key") or "") == idempotency_key
        ):
            return True
    return False


def audit_legacy_bundle_cleanup(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Audit read-only agrégé (read model E.2-A + PE + ledger shadow)."""
    batch_id = str(batch_id).strip()
    client = _resolve_client(db, person_id=person_id, portfolio_id=portfolio_id)

    now = now or datetime.now(timezone.utc)
    read_model = build_bundle_reconciliation_state(
        db,
        client_id=client.id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
        now=now,
    )
    swaps = list_batch_allocation_swaps(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    )
    pe_before = snapshot_pe_bundle_positions(db, portfolio_id=portfolio_id)

    ledger: dict[str, Any] | None = None
    ledger_error: str | None = None
    try:
        ledger = reconcile_bundle_ledger_shadow(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
    except Exception as exc:
        ledger_error = str(exc)

    portfolio_row = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    raw_lock = read_raw_invest_lock(portfolio_row.metadata_ if portfolio_row else None)

    intent_row = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=person_id,
        bundle_id=str(portfolio_id),
        batch_id=batch_id,
    )
    intent_snapshot = None
    if intent_row is not None:
        intent_snapshot = {
            "intent_id": str(intent_row.id),
            "status": str(intent_row.status or ""),
            "metadata_keys": sorted((intent_row.metadata_json or {}).keys())
            if isinstance(intent_row.metadata_json, dict)
            else [],
        }

    return {
        "read_only": True,
        "audited_at": _utc_now_iso(),
        "person_id": str(person_id),
        "portfolio_id": str(portfolio_id),
        "batch_id": batch_id,
        "client_id": str(client.id),
        "read_model": read_model,
        "allocation_swap_count": len(swaps),
        "live_onchain_submitted": _allocation_swaps_have_live_onchain_tx(swaps),
        "stale_pending_swaps": [
            {
                "swap_id": str(s.id),
                "asset": str(s.to_asset or "").upper(),
                "status": s.status,
                "amount_in": float(s.amount_in or 0),
            }
            for s in _stale_pending_swaps_for_skip(swaps)
        ],
        "pe_positions": pe_before,
        "ledger_shadow": ledger,
        "ledger_shadow_error": ledger_error,
        "raw_invest_lock": raw_lock,
        "intent": intent_snapshot,
    }


def validate_legacy_cleanup_preconditions(
    audit: dict[str, Any],
) -> None:
    """Lève ``BundleLegacyCleanupRejected`` si le batch n'est pas éligible."""
    read_model = audit.get("read_model") or {}
    status = str(read_model.get("status") or "")
    lock = read_model.get("lock") or {}
    intent_status = str(read_model.get("intent_status") or "").lower()

    if status != STATUS_RECONCILIATION_REQUIRED:
        raise BundleLegacyCleanupRejected(
            "invalid_read_model_status",
            f"status attendu {STATUS_RECONCILIATION_REQUIRED}, reçu {status!r}",
            details={"status": status},
        )
    lock_eligible = bool(lock.get("zombie"))
    if not lock_eligible:
        age = lock.get("age_minutes")
        ttl = lock.get("ttl_minutes") or invest_lock_ttl_minutes()
        confirmed = read_model.get("confirmed_allocations") or []
        lock_eligible = (
            status == STATUS_RECONCILIATION_REQUIRED
            and len(confirmed) > 0
            and age is not None
            and ttl is not None
            and float(age) >= float(ttl)
        )
    raw_lock = audit.get("raw_invest_lock")
    if not lock_eligible and raw_lock and str(raw_lock.get("batch_id") or "") == str(
        audit.get("batch_id") or "",
    ):
        lock_eligible = str(raw_lock.get("status") or "") in {
            "signature_requested",
            "pending_signature",
            "partial_pending",
            "submitted",
            "pending_confirmation",
            "finalizing",
        }

    if not lock_eligible:
        raise BundleLegacyCleanupRejected(
            "lock_not_zombie",
            "lock zombie ou stale (TTL dépassé + allocation confirmée) requis",
            details={"lock": lock, "raw_lock_status": (raw_lock or {}).get("status")},
        )
    if intent_status != IntentStatus.PARTIAL.value:
        raise BundleLegacyCleanupRejected(
            "invalid_intent_status",
            f"intent_status attendu partial, reçu {intent_status!r}",
            details={"intent_status": intent_status},
        )

    confirmed = read_model.get("confirmed_allocations") or []
    cash = float(read_model.get("cash_residual_usdc") or 0)
    if not confirmed and cash <= 0:
        raise BundleLegacyCleanupRejected(
            "no_confirmed_allocation_or_cash",
            "au moins une allocation confirmée ou cash_residual_usdc > 0 requis",
        )

    raw_lock = audit.get("raw_invest_lock")
    batch_id = str(audit.get("batch_id") or "")
    if raw_lock is None or str(raw_lock.get("batch_id") or "") != batch_id:
        raise BundleLegacyCleanupRejected(
            "lock_batch_mismatch",
            "bundle_invest_lock absent ou batch_id incohérent",
            details={"raw_lock": raw_lock},
        )

    live = audit.get("live_onchain_submitted") or []
    if live:
        raise BundleLegacyCleanupRejected(
            "live_onchain_submitted",
            "swap SUBMITTED avec tx_hash — cleanup interdit",
            details={"swaps": live},
        )

    ledger = audit.get("ledger_shadow")
    if ledger is not None and str(ledger.get("verdict") or "") == "DIFF":
        raise BundleLegacyCleanupRejected(
            "ledger_shadow_diff",
            "ledger shadow verdict DIFF — cleanup interdit",
            details={"verdict": ledger.get("verdict")},
        )


def plan_legacy_cleanup_writes(
    audit: dict[str, Any],
    *,
    idempotency_key: str,
    actor_id: str,
) -> dict[str, Any]:
    """État cible et champs qui seraient écrits (dry-run / apply)."""
    read_model = audit.get("read_model") or {}
    batch_id = str(audit.get("batch_id") or "")
    portfolio_id = str(audit.get("portfolio_id") or "")
    person_id = str(audit.get("person_id") or "")
    client_id = str(audit.get("client_id") or "")

    skipped_legs = [
        {
            "asset": row["asset"],
            "swap_id": row["swap_id"],
            "reason": SKIP_REASON_AWAITING_SIGNATURE_STALE,
            "prior_status": row["status"],
            "target_swap_status": SwapSessionStatus.EXPIRED.value,
        }
        for row in audit.get("stale_pending_swaps") or []
    ]

    intent_meta_patch = {
        "terminal_outcome": TERMINAL_OUTCOME_COMPLETED_PARTIAL,
        "cash_residual_usdc": read_model.get("cash_residual_usdc"),
        "legacy_cleanup": True,
        "legacy_cleanup_at": _utc_now_iso(),
        "skipped_legs": skipped_legs,
        "ops_idempotency_key": idempotency_key,
        "ops_actor_id": actor_id,
    }

    return {
        "target": {
            "batch_status": TERMINAL_OUTCOME_COMPLETED_PARTIAL,
            "intent_status": IntentStatus.PARTIAL.value,
            "intent_note": (
                "Intent reste partial — terminal_outcome dans metadata_json "
                "(pas de statut schema completed_partial_allocation)."
            ),
            "lock_action": "clear_invest_lock",
            "lock_after": None,
            "cash_residual_preserved_in_bundle": True,
            "pe_positions_mutated": False,
            "spot_sell": False,
            "trading_release": False,
        },
        "would_write": {
            "person_wallet_swaps": [
                {
                    "swap_id": s["swap_id"],
                    "field": "status",
                    "from": s["prior_status"],
                    "to": SwapSessionStatus.EXPIRED.value,
                }
                for s in skipped_legs
            ],
            "transaction_intents": {
                "batch_id": batch_id,
                "status": IntentStatus.PARTIAL.value,
                "metadata_json_patch": intent_meta_patch,
                "legs_reconcile": "stale pending → failed via bundle_invest_lock helper",
            },
            "pe_portfolios.metadata": {
                "bundle_invest_lock": "remove (clear_invest_lock)",
                "batch_id": batch_id,
                "client_id": client_id,
            },
            "pe_audit_events": {
                "action": AUDIT_ACTION_OPS_COMPLETED_PARTIAL,
                "entity_type": ENTITY_TYPE_BUNDLE_INVEST,
                "entity_id": batch_id,
                "metadata": {
                    "batch_id": batch_id,
                    "portfolio_id": portfolio_id,
                    "person_id": person_id,
                    "idempotency_key": idempotency_key,
                    "actor_id": actor_id,
                    "terminal_outcome": TERMINAL_OUTCOME_COMPLETED_PARTIAL,
                },
            },
        },
        "preserved": {
            "confirmed_allocations": read_model.get("confirmed_allocations") or [],
            "cash_residual_usdc": read_model.get("cash_residual_usdc"),
        },
    }


def complete_legacy_bundle_with_cash_residual(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str,
    idempotency_key: str,
    actor_id: str,
    dry_run: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Cleanup legacy zombie — ``dry_run=True`` par défaut (aucune mutation)."""
    batch_id = str(batch_id).strip()
    if not batch_id:
        raise BundleLegacyCleanupError("batch_id_required")
    if not idempotency_key.strip():
        raise BundleLegacyCleanupError("idempotency_key_required")

    now = now or datetime.now(timezone.utc)
    if _find_cleanup_audit(db, batch_id=batch_id, idempotency_key=idempotency_key):
        audit = audit_legacy_bundle_cleanup(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            now=now,
        )
        plan = plan_legacy_cleanup_writes(
            audit,
            idempotency_key=idempotency_key,
            actor_id=actor_id,
        )
        return {
            "dry_run": dry_run,
            "already_applied": True,
            "batch_id": batch_id,
            "idempotency_key": idempotency_key,
            "audit": audit,
            "plan": plan,
            "mutations_applied": False,
            "message": "Cleanup déjà appliqué (idempotency_key).",
        }

    audit = audit_legacy_bundle_cleanup(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
        now=now,
    )
    validate_legacy_cleanup_preconditions(audit)
    plan = plan_legacy_cleanup_writes(
        audit,
        idempotency_key=idempotency_key,
        actor_id=actor_id,
    )

    if dry_run:
        return {
            "dry_run": True,
            "already_applied": False,
            "batch_id": batch_id,
            "idempotency_key": idempotency_key,
            "audit": audit,
            "plan": plan,
            "mutations_applied": False,
            "message": "Dry-run — aucune écriture DB.",
        }

    client = _resolve_client(db, person_id=person_id, portfolio_id=portfolio_id)
    pe_before = snapshot_pe_bundle_positions(db, portfolio_id=portfolio_id)

    swaps = list_batch_allocation_swaps(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    )
    for swap in _stale_pending_swaps_for_skip(swaps):
        swap.status = SwapSessionStatus.EXPIRED.value
        db.add(swap)

    from services.portfolio_engine.bundles.bundle_invest_lock import (
        _reconcile_stale_intent_legs_for_batch,
    )

    _reconcile_stale_intent_legs_for_batch(
        db,
        person_id=person_id,
        bundle_id=str(portfolio_id),
        batch_id=batch_id,
    )

    intent_row = TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=person_id,
        bundle_id=str(portfolio_id),
        batch_id=batch_id,
    )
    if intent_row is not None:
        meta = dict(intent_row.metadata_json or {})
        patch = plan["would_write"]["transaction_intents"]["metadata_json_patch"]
        legs = _normalize_legs(meta.get("legs"))
        for leg in legs:
            swap_id = str(leg.get("swap_id") or "")
            for skipped in patch.get("skipped_legs") or []:
                if swap_id and swap_id == skipped.get("swap_id"):
                    leg["status"] = LEG_FAILED
                    leg["failure_reason"] = skipped.get("reason")
        meta.update(patch)
        meta["legs"] = legs
        intent_row.metadata_json = meta
        intent_row.status = IntentStatus.PARTIAL.value
        db.add(intent_row)

    clear_invest_lock(
        db,
        client_id=client.id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    )

    AuditRepository.create(
        db,
        data={
            "entity_type": ENTITY_TYPE_BUNDLE_INVEST,
            "entity_id": batch_id,
            "action": AUDIT_ACTION_OPS_COMPLETED_PARTIAL,
            "actor_type": "admin",
            "actor_id": actor_id,
            "request_id": idempotency_key,
            "metadata": {
                "batch_id": batch_id,
                "portfolio_id": str(portfolio_id),
                "person_id": str(person_id),
                "idempotency_key": idempotency_key,
                "terminal_outcome": TERMINAL_OUTCOME_COMPLETED_PARTIAL,
                "dry_run": False,
            },
        },
    )

    pe_after = snapshot_pe_bundle_positions(db, portfolio_id=portfolio_id)
    if pe_before != pe_after:
        raise BundleLegacyCleanupError(
            "pe_positions_changed_unexpectedly — rollback requis",
        )

    read_model_after = build_bundle_reconciliation_state(
        db,
        client_id=client.id,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
        now=now,
    )

    return {
        "dry_run": False,
        "already_applied": False,
        "batch_id": batch_id,
        "idempotency_key": idempotency_key,
        "audit": audit,
        "plan": plan,
        "mutations_applied": True,
        "read_model_after": read_model_after,
        "pe_unchanged": pe_before == pe_after,
    }
