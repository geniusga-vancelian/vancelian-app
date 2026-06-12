"""Bundle V3 Deposit Flow — request (fund + queue) et worker (rebalance V3)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution.bundle_funding import (
    BundleFundingError,
    fund_bundle_cash_leg_from_self_trading,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.config import (
    bundle_v3_deposit_flow_enabled,
    bundle_v3_deposit_immediate_kick_enabled,
)
from services.portfolio_engine.bundles.drift_engine import compute_bundle_drift_snapshot
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator, BundleOrchestratorError
from services.portfolio_engine.bundles.rebalance_executor import (
    BundleRebalanceExecutorError,
    execute_v3_bundle_rebalance,
)
from services.portfolio_engine.bundles.bundle_transaction_global_lock import (
    acquire_bundle_transaction_global_lock_or_raise,
    release_bundle_transaction_global_lock_on_v3_terminal,
)
from services.portfolio_engine.bundles.bundle_transaction_intent import (
    BUNDLE_TRANSACTION_INTENT_PRODUCT,
    BUNDLE_TRANSACTION_OPERATION_DEPOSIT_REBALANCE,
    LEGACY_DEPOSIT_INTENT_PRODUCT,
    PHASE_FUNDING,
    PHASE_REBALANCING,
    create_bundle_transaction_intent,
    set_bundle_transaction_phase,
    sync_bundle_transaction_rebalancing,
)
from services.portfolio_engine.bundles.rebalance_planner import plan_bundle_rebalance_from_drift
from services.portfolio_engine.financial_operations.wiring import (
    acquire_bundle_transaction_v3_portfolio_operation,
    release_bundle_transaction_v3_portfolio_operation,
)
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import TransactionOutboxRepository

logger = logging.getLogger(__name__)

V3_DEPOSIT_INTENT_PRODUCT = LEGACY_DEPOSIT_INTENT_PRODUCT
V3_DEPOSIT_FLOW_VERSION = "bundle_v3_deposit_flow_v1"

_TERMINAL_V3 = frozenset({
    "COMPLETED",
    "COMPLETED_WITH_RESIDUAL_CASH",
    "FAILED",
    "NO_ACTION",
})

_STATUS_BY_V3_TERMINAL = {
    "COMPLETED": "completed",
    "COMPLETED_WITH_RESIDUAL_CASH": "completed_with_residual_cash",
    "FAILED": "failed",
    "NO_ACTION": "completed",
}


def _deposit_status_from_v3(v3_status: str | None) -> str:
    if not v3_status:
        return "queued"
    return _STATUS_BY_V3_TERMINAL.get(str(v3_status), "queued")


def _record_immediate_kick_failure(db: Session, outbox: TransactionOutbox, exc: Exception) -> None:
    """Outbox repasse PENDING — retry immédiat possible via cron/worker."""
    outbox.attempt_count = int(outbox.attempt_count or 0) + 1
    outbox.last_error = str(exc)[:2000]
    outbox.locked_by = None
    outbox.locked_at = None
    if outbox.attempt_count >= int(outbox.max_attempts or 10):
        outbox.status = OutboxEventStatus.DEAD_LETTER.value
        finalize_v3_deposit_outbox_dead_letter(
            db,
            outbox=outbox,
            reason=f"immediate_kick_max_attempts:{exc}",
        )
    else:
        outbox.status = OutboxEventStatus.PENDING.value
        # Pas de délai : le cron (ou un 2e appel worker) peut reprendre tout de suite.
        outbox.next_retry_at = datetime.now(timezone.utc)
    db.flush()


def finalize_v3_deposit_outbox_dead_letter(
    db: Session,
    *,
    outbox: TransactionOutbox,
    reason: str,
) -> dict[str, Any]:
    """Clôture forcée V3 + libère intent/locks quand l'outbox dépôt est DEAD_LETTER."""
    from services.portfolio_engine.bundles.bundle_transaction_intent import (
        finalize_bundle_transaction_after_v3_terminal,
    )
    from services.portfolio_engine.bundles.rebalance_executor import (
        ENTITY_TYPE_V3_REBALANCE,
        ACTION_V3_TERMINAL,
        find_running_v3_rebalance_execution,
        terminalize_stale_v3_rebalance_execution,
    )
    from services.portfolio_engine.hardening.audit_models import AuditEvent

    payload = outbox.payload_json if isinstance(outbox.payload_json, dict) else {}
    client_id = UUID(str(payload.get("client_id") or "00000000-0000-0000-0000-000000000000"))
    portfolio_id = UUID(str(payload.get("portfolio_id") or "00000000-0000-0000-0000-000000000000"))
    deposit_execution_id = str(payload.get("deposit_execution_id") or "")
    batch_id = str(payload.get("batch_id") or deposit_execution_id).strip()
    pid = str(portfolio_id)

    terminal_payload: dict[str, Any] | None = None
    stale = terminalize_stale_v3_rebalance_execution(db, portfolio_id=pid)
    if stale is not None:
        terminal_payload = dict(stale)
    else:
        running = find_running_v3_rebalance_execution(db, portfolio_id=pid)
        if running is not None:
            from services.portfolio_engine.bundles.rebalance_executor import (
                _force_terminalize_running_snapshot,
            )

            terminal_payload = _force_terminalize_running_snapshot(
                db,
                running=running,
                actor_id="bundle-v3-dead-letter",
                extra={
                    "dead_letter_finalized": True,
                    "dead_letter_reason": reason,
                    "forced_v3_status": "FAILED",
                },
            )
            terminal_payload["v3_status"] = "FAILED"

    if terminal_payload is None and batch_id:
        rows = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
                AuditEvent.action == ACTION_V3_TERMINAL,
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(50)
            .all()
        )
        for row in rows:
            meta = row.metadata_ or {}
            if str(meta.get("portfolio_id") or "") != pid:
                continue
            audit_batch = str(
                meta.get("batch_id") or meta.get("rebalance_execution_id") or "",
            )
            if audit_batch == batch_id:
                terminal_payload = dict(meta)
                break

    if terminal_payload is None:
        terminal_payload = {
            "v3_status": "FAILED",
            "rebalance_execution_id": batch_id or None,
            "batch_id": batch_id or None,
            "portfolio_id": pid,
            "dead_letter_finalized": True,
            "dead_letter_reason": reason,
        }

    if str(terminal_payload.get("v3_status") or "") not in _TERMINAL_V3:
        terminal_payload["v3_status"] = "FAILED"

    finalized = finalize_bundle_transaction_after_v3_terminal(
        db,
        portfolio_id=portfolio_id,
        terminal=terminal_payload,
    )
    try:
        release_bundle_transaction_v3_portfolio_operation(
            db,
            portfolio_id=portfolio_id,
            execution_id=batch_id or deposit_execution_id,
            failed=True,
        )
    except Exception:
        logger.warning(
            "bundle_v3_deposit.dead_letter_portfolio_guard_release_failed portfolio=%s batch=%s",
            portfolio_id,
            batch_id,
            exc_info=True,
        )

    return {
        "portfolio_id": pid,
        "batch_id": batch_id or None,
        "intent_id": str(finalized.id) if finalized is not None else None,
        "v3_status": terminal_payload.get("v3_status"),
        "reason": reason,
    }


def kick_v3_deposit_rebalance_immediately(
    db: Session,
    *,
    outbox: TransactionOutbox,
) -> dict[str, Any]:
    """Exécute drift+rebalance V3 dès l'enqueue — filet cron si échec."""
    if not bundle_v3_deposit_immediate_kick_enabled():
        return {"worker_immediate_kick": "skipped"}

    try:
        result = process_v3_deposit_rebalance_outbox_event(db, outbox=outbox)
    except Exception as exc:
        logger.warning(
            "bundle_v3_deposit_immediate_kick_failed outbox=%s error=%s",
            outbox.id,
            exc,
            exc_info=True,
        )
        _record_immediate_kick_failure(db, outbox, exc)
        return {
            "worker_immediate_kick": "failed",
            "worker_error": str(exc)[:500],
        }

    v3_status = str(result.get("v3_status") or "")
    terminal = bool(result.get("terminal"))
    return {
        "worker_immediate_kick": "success" if terminal else "deferred",
        "v3_status": v3_status or None,
        "rebalance_execution_id": result.get("rebalance_execution_id"),
        "plan_hash": result.get("plan_hash"),
        "terminal": terminal,
    }


class V3DepositFlowError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _ensure_v3_deposit_flow_active() -> None:
    if not bundle_v3_deposit_flow_enabled():
        raise V3DepositFlowError("v3_deposit_flow_disabled", "BUNDLE_V3_DEPOSIT_FLOW_ENABLED is off")


def request_v3_bundle_deposit(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
    funding_asset: str,
    funding_amount: Decimal,
) -> dict[str, Any]:
    """Phase HTTP — guard + fund cash leg + enqueue rebalance V3 (pas d'allocation legacy)."""
    _ensure_v3_deposit_flow_active()

    orchestrator = BundleOrchestrator()
    portfolio = orchestrator._load_and_validate_portfolio(db, portfolio_id, client_id)
    product = orchestrator._load_product(db, portfolio)
    entry_config = orchestrator._resolve_entry_config(product)
    entry_asset = entry_config["entry_asset_default"]
    orchestrator._validate_funding_asset(funding_asset, entry_config)
    orchestrator._validate_funding_amount(funding_asset, funding_amount)

    if funding_asset.upper() != entry_asset.upper():
        raise V3DepositFlowError(
            "v3_deposit_entry_asset_only",
            f"V3 deposit flow requires direct {entry_asset} funding",
        )

    from services.portfolio_engine.clients.models import Client as _Client

    client_row = db.query(_Client).filter(_Client.id == client_id).first()
    person_id = client_row.person_id if client_row is not None else None
    if person_id is None:
        raise V3DepositFlowError("client_has_no_person_id", "client_has_no_person_id")

    deposit_execution_id = uuid.uuid4()
    batch_id = str(deposit_execution_id)

    acquire_bundle_transaction_v3_portfolio_operation(
        db,
        portfolio_id=portfolio_id,
        execution_id=deposit_execution_id,
    )

    entry_instrument = orchestrator._resolve_or_create_instrument(db, entry_asset)
    try:
        funding_result = fund_bundle_cash_leg_from_self_trading(
            db,
            client_id=client_id,
            person_id=person_id,
            portfolio_id=portfolio_id,
            entry_asset=entry_asset,
            entry_instrument_id=entry_instrument.id,
            amount=funding_amount,
            batch_id=batch_id,
        )
    except BundleFundingError as exc:
        release_bundle_transaction_v3_portfolio_operation(
            db,
            portfolio_id=portfolio_id,
            execution_id=deposit_execution_id,
            failed=True,
        )
        raise V3DepositFlowError(exc.code, str(exc)) from exc

    intent = create_bundle_transaction_intent(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        transaction_execution_id=deposit_execution_id,
        operation_type=BUNDLE_TRANSACTION_OPERATION_DEPOSIT_REBALANCE,
        phase=PHASE_FUNDING,
        idempotency_suffix=f"deposit-{deposit_execution_id}",
        extra_metadata={
            "flow_version": V3_DEPOSIT_FLOW_VERSION,
            "deposit_execution_id": str(deposit_execution_id),
            "funding_asset": entry_asset.upper(),
            "funding_amount": str(funding_amount),
            "funding_status": "completed",
        },
    )
    acquire_bundle_transaction_global_lock_or_raise(
        db,
        person_id=person_id,
        intent_id=intent.id,
    )
    set_bundle_transaction_phase(
        intent,
        phase=PHASE_REBALANCING,
        extra={"funding_status": "completed"},
    )

    outbox_payload = {
        "flow_version": V3_DEPOSIT_FLOW_VERSION,
        "client_id": str(client_id),
        "portfolio_id": str(portfolio_id),
        "person_id": str(person_id),
        "deposit_execution_id": str(deposit_execution_id),
        "batch_id": batch_id,
        "funding_amount": str(funding_amount),
        "entry_asset": entry_asset.upper(),
    }
    outbox_row, created = TransactionOutboxRepository.insert_event_idempotent_per_intent_type(
        db,
        intent_id=intent.id,
        event_type=OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
        payload_json=outbox_payload,
        correlation_id=deposit_execution_id,
    )

    kick = kick_v3_deposit_rebalance_immediately(db, outbox=outbox_row)
    v3_status = kick.get("v3_status")
    status = _deposit_status_from_v3(v3_status) if kick.get("worker_immediate_kick") == "success" else "queued"
    if kick.get("worker_immediate_kick") == "skipped":
        message = "Deposit funded; V3 rebalance queued"
    elif kick.get("worker_immediate_kick") == "success":
        message = f"Deposit funded; V3 rebalance terminal ({v3_status})"
    elif kick.get("worker_immediate_kick") == "deferred":
        message = "Deposit funded; V3 rebalance in progress"
        status = "processing"
    else:
        message = "Deposit funded; V3 rebalance queued (immediate kick failed, cron retry)"

    response: dict[str, Any] = {
        "status": status,
        "flow": "bundle_v3_deposit",
        "deposit_execution_id": str(deposit_execution_id),
        "batch_id": batch_id,
        "portfolio_id": str(portfolio_id),
        "intent_id": str(intent.id),
        "outbox_id": str(outbox_row.id),
        "outbox_created": created,
        "funding": funding_result,
        "message": message,
        **kick,
    }
    return response


def _resolve_deposit_rebalance_trigger(db: Session, person_raw: Any) -> str:
    """``server`` si la personne est éligible au worker de rééquilibrage, sinon ``deposit``.

    Fail-closed : flag OFF / allowlist vide / personne inconnue → ``deposit`` (signature
    client historique). Aucune exception ne remonte (robustesse worker).
    """
    if not person_raw:
        return "deposit"
    from services.lifi.orchestrator_allowlist import (
        lifi_rebalance_worker_enabled_for_person,
    )

    try:
        if lifi_rebalance_worker_enabled_for_person(db, UUID(str(person_raw))):
            return "server"
    except (ValueError, TypeError):
        return "deposit"
    return "deposit"


def process_v3_deposit_rebalance_outbox_event(
    db: Session,
    *,
    outbox: TransactionOutbox,
) -> dict[str, Any]:
    """Worker — drift + execute_v3_bundle_rebalance(trigger=deposit) + release guard."""
    payload = outbox.payload_json if isinstance(outbox.payload_json, dict) else {}
    client_id = UUID(str(payload["client_id"]))
    portfolio_id = UUID(str(payload["portfolio_id"]))
    deposit_execution_id = str(payload.get("deposit_execution_id") or "")
    batch_id = str(payload.get("batch_id") or deposit_execution_id)

    snap = compute_bundle_drift_snapshot(db, client_id=client_id, portfolio_id=portfolio_id)
    plan = plan_bundle_rebalance_from_drift(snap)

    # Signature serveur (Privy déléguée, sans navigateur) si la personne est allowlistée :
    # le rééquilibrage s'exécute entièrement côté serveur, leg par leg. Sinon trigger
    # ``deposit`` historique (signature client) — défaut fail-closed, zéro régression.
    trigger = _resolve_deposit_rebalance_trigger(db, payload.get("person_id"))

    try:
        result = execute_v3_bundle_rebalance(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            drift_rebalance_plan=plan,
            trigger=trigger,  # type: ignore[arg-type]
        )
    except BundleRebalanceExecutorError as exc:
        outbox.status = OutboxEventStatus.DEAD_LETTER.value
        outbox.last_error = str(exc)
        finalize_v3_deposit_outbox_dead_letter(
            db,
            outbox=outbox,
            reason=f"executor_error:{exc}",
        )
        db.flush()
        raise

    intent_id = outbox.intent_id
    if intent_id is not None:
        from services.onchain_indexer.models import TransactionIntent

        intent = db.query(TransactionIntent).filter(TransactionIntent.id == intent_id).first()
        if intent is not None:
            sync_bundle_transaction_rebalancing(intent, result=result)
            release_bundle_transaction_global_lock_on_v3_terminal(
                db,
                intent_id=intent.id,
                v3_status=str(result.get("v3_status") or ""),
            )
            db.add(intent)

    v3_status = str(result.get("v3_status") or "")
    if v3_status in _TERMINAL_V3:
        release_bundle_transaction_v3_portfolio_operation(
            db,
            portfolio_id=portfolio_id,
            execution_id=batch_id,
            failed=v3_status == "FAILED",
        )
        outbox.status = OutboxEventStatus.PROCESSED.value
        db.flush()
    elif v3_status == "RUNNING":
        # Reprise worker/cron — legs en cours (wallet ou confirmation on-chain).
        TransactionOutboxRepository.release_processing_lock(db, outbox)
        outbox.status = OutboxEventStatus.PENDING.value
        outbox.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        outbox.last_error = None
        db.flush()

    return {
        "deposit_execution_id": deposit_execution_id,
        "v3_status": v3_status,
        "rebalance_execution_id": result.get("rebalance_execution_id"),
        "plan_hash": result.get("plan_hash"),
        "terminal": v3_status in _TERMINAL_V3,
        "awaiting_wallet_signature": v3_status == "RUNNING",
        "result": result,
    }


def is_v3_deposit_batch(
    db: Session,
    *,
    portfolio_id: UUID,
    batch_id: str,
) -> bool:
    """True si le batch provient du flux V3 deposit (intent ou outbox), pas legacy LI.FI."""
    from sqlalchemy import text

    bid = str(batch_id or "").strip()
    if not bid:
        return False
    pid = str(portfolio_id)
    intent_row = db.execute(
        text(
            """
            SELECT 1 FROM transaction_intents
            WHERE product_type IN (:product_legacy, :product_unified)
              AND metadata_json->>'batch_id' = :batch
              AND metadata_json->>'portfolio_id' = :portfolio
            LIMIT 1
            """
        ),
        {
            "product_legacy": V3_DEPOSIT_INTENT_PRODUCT,
            "product_unified": BUNDLE_TRANSACTION_INTENT_PRODUCT,
            "batch": bid,
            "portfolio": pid,
        },
    ).fetchone()
    if intent_row is not None:
        return True
    outbox_row = db.execute(
        text(
            """
            SELECT 1 FROM transaction_outbox
            WHERE event_type = :event_type
              AND payload_json->>'batch_id' = :batch
              AND payload_json->>'portfolio_id' = :portfolio
            LIMIT 1
            """
        ),
        {
            "event_type": OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
            "batch": bid,
            "portfolio": pid,
        },
    ).fetchone()
    return outbox_row is not None


def legacy_resume_available_for_batch(
    db: Session,
    *,
    portfolio_id: UUID,
    batch_id: str,
) -> bool:
    """Legacy LI.FI resume autorisé pour les batches non-V3 même si le flag V3 est ON."""
    if not bundle_v3_deposit_flow_enabled():
        return True
    return not is_v3_deposit_batch(db, portfolio_id=portfolio_id, batch_id=batch_id)


def resume_disabled_for_v3_deposit_flow(
    db: Session,
    *,
    client_id: UUID,
    portfolio_id: UUID,
) -> bool:
    """Bloque legacy resume seulement pour les dépôts V3 — pas les batches legacy (ex. Majors)."""
    if not bundle_v3_deposit_flow_enabled():
        return False
    from services.portfolio_engine.bundles.bundle_invest_lock import peek_bundle_invest_lock_state

    state = peek_bundle_invest_lock_state(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
    )
    if state.get("status") != "active":
        return True
    lock = state.get("lock") or {}
    batch_id = str(lock.get("batch_id") or "").strip()
    if not batch_id:
        return True
    return not legacy_resume_available_for_batch(
        db,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
    )
