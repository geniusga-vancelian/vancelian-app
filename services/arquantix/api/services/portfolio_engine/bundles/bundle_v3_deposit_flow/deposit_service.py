"""Bundle V3 Deposit Flow — request (fund + queue) et worker (rebalance V3)."""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.bundle_funding import (
    BundleFundingError,
    fund_bundle_cash_leg_from_self_trading,
)
from services.portfolio_engine.bundles.bundle_v3_deposit_flow.config import (
    bundle_v3_deposit_flow_enabled,
)
from services.portfolio_engine.bundles.drift_engine import compute_bundle_drift_snapshot
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator, BundleOrchestratorError
from services.portfolio_engine.bundles.rebalance_executor import (
    BundleRebalanceExecutorError,
    execute_v3_bundle_rebalance,
)
from services.portfolio_engine.bundles.rebalance_planner import plan_bundle_rebalance_from_drift
from services.portfolio_engine.financial_operations.wiring import (
    acquire_bundle_invest_portfolio_operation,
    release_bundle_invest_portfolio_operation,
)
from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
from services.transaction_outbox.models import TransactionOutbox
from services.transaction_outbox.repository import TransactionOutboxRepository

logger = logging.getLogger(__name__)

V3_DEPOSIT_INTENT_PRODUCT = "bundle_deposit_v3"
V3_DEPOSIT_FLOW_VERSION = "bundle_v3_deposit_flow_v1"

_TERMINAL_V3 = frozenset({
    "COMPLETED",
    "COMPLETED_WITH_RESIDUAL_CASH",
    "FAILED",
    "NO_ACTION",
})


class V3DepositFlowError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _ensure_v3_deposit_flow_active() -> None:
    if not bundle_v3_deposit_flow_enabled():
        raise V3DepositFlowError("v3_deposit_flow_disabled", "BUNDLE_V3_DEPOSIT_FLOW_ENABLED is off")


def _create_deposit_intent(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    deposit_execution_id: UUID,
    funding_amount: Decimal,
    entry_asset: str,
    batch_id: str,
) -> TransactionIntent:
    intent = TransactionIntent(
        person_id=person_id,
        product_type=V3_DEPOSIT_INTENT_PRODUCT,
        operation_type="deposit",
        idempotency_key=f"v3-deposit-{deposit_execution_id}",
        status="created",
        metadata_json={
            "flow_version": V3_DEPOSIT_FLOW_VERSION,
            "portfolio_id": str(portfolio_id),
            "deposit_execution_id": str(deposit_execution_id),
            "batch_id": batch_id,
            "funding_asset": entry_asset.upper(),
            "funding_amount": str(funding_amount),
        },
    )
    db.add(intent)
    db.flush()
    return intent


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

    acquire_bundle_invest_portfolio_operation(
        db,
        portfolio_id=portfolio_id,
        batch_id=batch_id,
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
        release_bundle_invest_portfolio_operation(
            db,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            failed=True,
        )
        raise V3DepositFlowError(str(exc).split(":")[0] if ":" in str(exc) else "bundle_funding_failed", str(exc)) from exc

    intent = _create_deposit_intent(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
        deposit_execution_id=deposit_execution_id,
        funding_amount=funding_amount,
        entry_asset=entry_asset,
        batch_id=batch_id,
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

    return {
        "status": "queued",
        "flow": "bundle_v3_deposit",
        "deposit_execution_id": str(deposit_execution_id),
        "batch_id": batch_id,
        "portfolio_id": str(portfolio_id),
        "intent_id": str(intent.id),
        "outbox_id": str(outbox_row.id),
        "outbox_created": created,
        "funding": funding_result,
        "message": "Deposit funded; V3 rebalance queued",
    }


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

    try:
        result = execute_v3_bundle_rebalance(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            drift_rebalance_plan=plan,
            trigger="deposit",
        )
    except BundleRebalanceExecutorError as exc:
        release_bundle_invest_portfolio_operation(
            db,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            failed=True,
        )
        outbox.status = OutboxEventStatus.DEAD_LETTER.value
        outbox.last_error = str(exc)
        db.flush()
        raise

    v3_status = str(result.get("v3_status") or "")
    if v3_status in _TERMINAL_V3:
        release_bundle_invest_portfolio_operation(
            db,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            failed=v3_status == "FAILED",
        )
        outbox.status = OutboxEventStatus.PROCESSED.value
        db.flush()

    return {
        "deposit_execution_id": deposit_execution_id,
        "v3_status": v3_status,
        "rebalance_execution_id": result.get("rebalance_execution_id"),
        "plan_hash": result.get("plan_hash"),
        "terminal": v3_status in _TERMINAL_V3,
        "result": result,
    }


def resume_disabled_for_v3_deposit_flow() -> bool:
    return bundle_v3_deposit_flow_enabled()
