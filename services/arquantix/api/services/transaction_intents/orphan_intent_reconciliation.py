"""PR 1 — Réconciliation read/repair-only des intents orchestrateur orphelins.

Problème : sur le chemin orchestrateur LI.FI, ``lifi_intent_sync`` est no-op, donc un
swap qui devient terminal (``FAILED``/``EXPIRED``/``CONFIRMED``) ne propage jamais son
état à l'intent lié → l'intent reste indéfiniment en ``created``/``queued``.

Ce module **ne touche pas** au chemin d'exécution (quote/prepare/sign/broadcast), ni au
lock, ni à l'execution worker serveur. Il se contente de :
  - détecter les intents non terminaux dont le swap lié est déjà terminal (lecture) ;
  - réparer ``intent.status`` pour refléter l'état terminal du swap (repair).

``current_phase`` est laissé inchangé (pas de phase FAILED dans l'enum avant PR 5).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.enums import IntentProductType, IntentStatus
from services.transaction_intents.lifi_intent_sync import LINKED_TABLE
from services.transaction_outbox.repository import TransactionIntentTransitionRepository

logger = logging.getLogger(__name__)

RECONCILER_ACTOR = "intent_swap_reconciler"

# Statuts intent considérés terminaux (ne plus réconcilier).
TERMINAL_INTENT_STATUSES = frozenset(
    {
        IntentStatus.CONFIRMED.value,
        IntentStatus.FAILED.value,
        IntentStatus.FAILED_FINAL.value,
        IntentStatus.SUPERSEDED.value,
    }
)

# Swap terminal échoué → intent failed.
_SWAP_TERMINAL_FAILED = frozenset(
    {SwapSessionStatus.FAILED.value, SwapSessionStatus.EXPIRED.value}
)


@dataclass(frozen=True)
class IntentReconcileResult:
    action: str  # "repaired" | "noop"
    intent_id: str
    reason: str
    from_status: str | None = None
    to_status: str | None = None
    swap_id: str | None = None
    swap_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "intent_id": self.intent_id,
            "reason": self.reason,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "swap_id": self.swap_id,
            "swap_status": self.swap_status,
        }


def _is_orchestrator_lifi_intent(intent: TransactionIntent) -> bool:
    if (intent.product_type or "") != IntentProductType.LIFI_SWAP.value:
        return False
    if (intent.linked_table or "").strip() != LINKED_TABLE or not intent.linked_id:
        return False
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    return bool(meta.get("phase2_orchestrator"))


def _target_intent_status_for_swap(swap: PersonWalletSwap) -> tuple[str | None, str]:
    """Retourne (target_status, reason) ou (None, reason) si pas de réconciliation."""
    swap_status = (swap.status or "").upper()
    if swap_status in _SWAP_TERMINAL_FAILED:
        return IntentStatus.FAILED.value, "linked_swap_terminal_failed"
    if swap_status == SwapSessionStatus.CONFIRMED.value:
        # Promotion confirmé uniquement si le ledger est déjà posé (sinon : laisser le
        # settlement worker faire son travail — on ne crée pas de confirmé sans compta).
        if swap_settlement_already_applied(swap):
            return IntentStatus.CONFIRMED.value, "linked_swap_confirmed_settled"
        return None, "swap_confirmed_pending_settlement"
    return None, f"swap_not_terminal:{swap_status or '?'}"


def reconcile_intent_from_linked_swap(
    db: Session,
    intent: TransactionIntent,
    *,
    swap: PersonWalletSwap | None = None,
    dry_run: bool = False,
) -> IntentReconcileResult:
    """Réconcilie un intent orchestrateur depuis l'état terminal de son swap lié.

    Idempotent : no-op si l'intent est déjà terminal ou si le swap n'est pas terminal.
    N'effectue **aucun** commit (laissé à l'appelant).
    """
    intent_id = str(intent.id)

    if not _is_orchestrator_lifi_intent(intent):
        return IntentReconcileResult("noop", intent_id, "not_orchestrator_lifi_intent")

    if (intent.status or "") in TERMINAL_INTENT_STATUSES:
        return IntentReconcileResult(
            "noop", intent_id, "intent_already_terminal", from_status=intent.status
        )

    if swap is None:
        swap = (
            db.query(PersonWalletSwap)
            .filter(PersonWalletSwap.id == intent.linked_id)
            .first()
        )
    if swap is None:
        return IntentReconcileResult("noop", intent_id, "linked_swap_not_found")

    target_status, reason = _target_intent_status_for_swap(swap)
    if target_status is None:
        return IntentReconcileResult(
            "noop",
            intent_id,
            reason,
            from_status=intent.status,
            swap_id=str(swap.id),
            swap_status=swap.status,
        )

    from_status = intent.status
    if not dry_run:
        intent.status = target_status
        TransactionIntentTransitionRepository.insert_transition(
            db,
            intent_id=intent.id,
            from_status=from_status,
            to_status=target_status,
            phase=intent.current_phase,
            actor=RECONCILER_ACTOR,
            metadata_json={
                "reason": reason,
                "swap_id": str(swap.id),
                "swap_status": swap.status,
            },
        )
        db.flush()
        # Libère les product locks orchestrateur si l'intent devient terminal-échec.
        if target_status == IntentStatus.FAILED.value:
            try:
                from services.transaction_outbox.orchestrator_product_locks import (
                    release_orchestrator_product_locks_for_intent,
                )

                release_orchestrator_product_locks_for_intent(
                    db, intent, reason="reconciled_intent_failed"
                )
            except Exception:  # noqa: BLE001 — la réconciliation ne doit jamais casser le flow
                logger.exception("reconcile_release_locks_failed intent_id=%s", intent_id)

        logger.info(
            "intent_reconciled_from_swap intent_id=%s from=%s to=%s reason=%s swap_id=%s",
            intent_id,
            from_status,
            target_status,
            reason,
            str(swap.id),
        )

    return IntentReconcileResult(
        "repaired",
        intent_id,
        reason,
        from_status=from_status,
        to_status=target_status,
        swap_id=str(swap.id),
        swap_status=swap.status,
    )


def find_orphaned_lifi_intents(
    db: Session,
    *,
    older_than_minutes: int = 10,
    limit: int = 200,
    person_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Lecture seule — intents orchestrateur non terminaux dont le swap lié est terminal."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
    q = (
        db.query(TransactionIntent, PersonWalletSwap)
        .join(PersonWalletSwap, PersonWalletSwap.id == TransactionIntent.linked_id)
        .filter(
            TransactionIntent.product_type == IntentProductType.LIFI_SWAP.value,
            TransactionIntent.linked_table == LINKED_TABLE,
            TransactionIntent.status.notin_(list(TERMINAL_INTENT_STATUSES)),
            PersonWalletSwap.status.in_(
                [
                    SwapSessionStatus.FAILED.value,
                    SwapSessionStatus.EXPIRED.value,
                    SwapSessionStatus.CONFIRMED.value,
                ]
            ),
            TransactionIntent.updated_at < cutoff,
        )
    )
    if person_id is not None:
        q = q.filter(TransactionIntent.person_id == person_id)
    rows = q.order_by(TransactionIntent.updated_at.asc()).limit(limit).all()

    out: list[dict[str, Any]] = []
    for intent, swap in rows:
        if not _is_orchestrator_lifi_intent(intent):
            continue
        target_status, reason = _target_intent_status_for_swap(swap)
        out.append(
            {
                "intent_id": str(intent.id),
                "person_id": str(intent.person_id) if intent.person_id else None,
                "intent_status": intent.status,
                "intent_phase": intent.current_phase,
                "swap_id": str(swap.id),
                "swap_status": swap.status,
                "would_set_status": target_status,
                "reason": reason,
                "intent_updated_at": (intent.updated_at.isoformat() if intent.updated_at else None),
            }
        )
    return out


def reconcile_orphaned_lifi_intents(
    db: Session,
    *,
    dry_run: bool = True,
    older_than_minutes: int = 10,
    limit: int = 200,
    person_id: UUID | None = None,
) -> dict[str, Any]:
    """Balayage repair (idempotent). ``dry_run=True`` par défaut : aucune écriture."""
    candidates = find_orphaned_lifi_intents(
        db, older_than_minutes=older_than_minutes, limit=limit, person_id=person_id
    )
    repaired: list[dict[str, Any]] = []
    for row in candidates:
        if row.get("would_set_status") is None:
            continue
        intent = (
            db.query(TransactionIntent)
            .filter(TransactionIntent.id == UUID(row["intent_id"]))
            .first()
        )
        if intent is None:
            continue
        result = reconcile_intent_from_linked_swap(db, intent, dry_run=dry_run)
        if result.action == "repaired":
            repaired.append(result.to_dict())
    if not dry_run and repaired:
        db.commit()

    return {
        "dry_run": dry_run,
        "older_than_minutes": older_than_minutes,
        "candidates": len(candidates),
        "repaired": len(repaired),
        "items": (repaired if not dry_run else candidates)[:100],
    }
