"""S3 Controller v1 — réconciliation LI.FI standalone post LEDGER_SETTLED (lecture seule)."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.controller.constants import (
    CONTROLLER_ACTOR,
    RECONCILIATION_REPORT_METADATA_KEY,
)
from services.controller.result import ReconciliationOutcome, ReconciliationResult
from services.lifi.lifi_swap_reconciliation import detect_swap_ledger_legs
from services.lifi.lifi_swap_settlement import (
    swap_credit_idempotency_key,
    swap_debit_idempotency_key,
)
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.privy_wallet.enums import PersonWalletDepositStatus, PersonWalletDirection
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import (
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
)
from services.settlement.constants import SETTLEMENT_RECEIPT_METADATA_KEY
from services.settlement.lifi_ledger import is_lifi_standalone_intent
from services.settlement.preconditions import settlement_marker_present
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.repository import TransactionIntentTransitionRepository

logger = logging.getLogger(__name__)

_AMOUNT_RELATIVE_TOLERANCE = Decimal("0.02")
_AMOUNT_ABSOLUTE_TOLERANCE = Decimal("1e-12")


def _terminal(
    intent_id: UUID,
    code: str,
    message: str,
    *,
    projection: dict[str, Any] | None = None,
) -> ReconciliationResult:
    return ReconciliationResult(
        outcome=ReconciliationOutcome.RECONCILIATION_TERMINAL_FAILURE,
        intent_id=intent_id,
        error_code=code,
        error_message=message,
        projection=projection,
    )


def _retryable(
    intent_id: UUID,
    code: str,
    message: str,
    *,
    projection: dict[str, Any] | None = None,
) -> ReconciliationResult:
    return ReconciliationResult(
        outcome=ReconciliationOutcome.RECONCILIATION_RETRYABLE_FAILURE,
        intent_id=intent_id,
        error_code=code,
        error_message=message,
        projection=projection,
    )


def _amount_compatible(expected: Decimal, actual: Decimal) -> bool:
    if actual <= 0 and expected > 0:
        return False
    diff = abs(expected - actual)
    tolerance = max(
        _AMOUNT_ABSOLUTE_TOLERANCE,
        expected * _AMOUNT_RELATIVE_TOLERANCE,
    )
    return diff <= tolerance


def _resolve_amount_out(intent: TransactionIntent, swap: PersonWalletSwap) -> Decimal:
    assets = intent.assets_json if isinstance(intent.assets_json, dict) else {}
    to_block = assets.get("to")
    if isinstance(to_block, dict) and to_block.get("amount") is not None:
        amount = Decimal(str(to_block["amount"]))
        if amount > 0:
            return amount
    if swap.estimated_receive is not None:
        amount = Decimal(str(swap.estimated_receive))
        if amount > 0:
            return amount
    raise ValueError("amount_out_missing")


def _compute_report_hash(intent_id: UUID, projection: dict[str, Any]) -> str:
    payload = {
        "intent_id": str(intent_id),
        "controller": "s3-lifi-swap-v1",
        "projection": projection,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _reconciliation_report_hash(intent: TransactionIntent) -> str | None:
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    raw = meta.get(RECONCILIATION_REPORT_METADATA_KEY)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _persist_reconciliation_report(intent: TransactionIntent, report_hash: str) -> None:
    meta = dict(intent.metadata_json) if isinstance(intent.metadata_json, dict) else {}
    meta[RECONCILIATION_REPORT_METADATA_KEY] = report_hash
    intent.metadata_json = meta


def _deposit_linked_to_swap(deposit: PersonWalletDeposit, swap: PersonWalletSwap) -> bool:
    swap_id = str(swap.id)
    if deposit.idempotency_key in {
        swap_debit_idempotency_key(swap_id),
        swap_credit_idempotency_key(swap_id),
    }:
        return True
    meta = deposit.metadata_json if isinstance(deposit.metadata_json, dict) else {}
    if str(meta.get("swap_id") or "") == swap_id:
        return True
    tx_hash = str(swap.tx_hash or "").strip().lower()
    if not tx_hash:
        return False
    dep_tx = str(deposit.tx_hash or "").strip().lower()
    if dep_tx != tx_hash:
        return False
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    if deposit.direction == PersonWalletDirection.DEBIT.value and deposit.asset.upper() == from_asset:
        return True
    if deposit.direction == PersonWalletDirection.CREDIT.value and deposit.asset.upper() == to_asset:
        return True
    return False


def _enumerate_swap_ledger_deposits(
    db: Session,
    swap: PersonWalletSwap,
) -> tuple[list[PersonWalletDeposit], list[PersonWalletDeposit]]:
    """Liste déterministe des dépôts ledger rattachés au swap (débit / crédit)."""
    swap_id = str(swap.id)
    seen: set[UUID] = set()
    debits: list[PersonWalletDeposit] = []
    credits: list[PersonWalletDeposit] = []

    def _append(dep: PersonWalletDeposit) -> None:
        if dep.id in seen:
            return
        seen.add(dep.id)
        if dep.direction == PersonWalletDirection.DEBIT.value:
            debits.append(dep)
        elif dep.direction == PersonWalletDirection.CREDIT.value:
            credits.append(dep)

    deposit_repo = PersonWalletDepositRepository()
    for key in (swap_debit_idempotency_key(swap_id), swap_credit_idempotency_key(swap_id)):
        dep = deposit_repo.find_by_deposit_idempotency_key(db, key)
        if dep is not None:
            _append(dep)

    rows = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.person_id == swap.person_id,
            PersonWalletDeposit.metadata_json["swap_id"].astext == swap_id,
        )
        .all()
    )
    for dep in rows:
        _append(dep)

    tx_hash = str(swap.tx_hash or "").strip().lower()
    if tx_hash:
        for dep in deposit_repo.find_confirmed_by_tx_hash(
            db, tx_hash=tx_hash, person_id=swap.person_id
        ):
            if _deposit_linked_to_swap(dep, swap):
                _append(dep)

    return debits, credits


def _external_movements(
    db: Session,
    *,
    swap: PersonWalletSwap,
    asset: str,
    window_start: datetime,
    window_end: datetime,
) -> list[dict[str, str]]:
    asset_u = asset.upper()
    rows = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.person_id == swap.person_id,
            PersonWalletDeposit.asset == asset_u,
            PersonWalletDeposit.status == PersonWalletDepositStatus.CONFIRMED.value,
            PersonWalletDeposit.confirmed_at >= window_start,
            PersonWalletDeposit.confirmed_at <= window_end,
        )
        .order_by(PersonWalletDeposit.confirmed_at.asc())
        .all()
    )
    external: list[dict[str, str]] = []
    for dep in rows:
        if _deposit_linked_to_swap(dep, swap):
            continue
        external.append(
            {
                "deposit_id": str(dep.id),
                "direction": str(dep.direction),
                "asset": asset_u,
                "amount": str(dep.amount),
                "tx_hash": str(dep.tx_hash or ""),
                "idempotency_key": str(dep.idempotency_key or ""),
            }
        )
    return external


def _external_net(external: list[dict[str, str]]) -> Decimal:
    net = Decimal("0")
    for row in external:
        amount = Decimal(str(row["amount"]))
        if row["direction"] == PersonWalletDirection.CREDIT.value:
            net += amount
        elif row["direction"] == PersonWalletDirection.DEBIT.value:
            net -= amount
    return net


def _balance_variation_explained(
    db: Session,
    *,
    swap: PersonWalletSwap,
    intent: TransactionIntent,
    from_asset: str,
    swap_debit_amount: Decimal,
    window_start: datetime,
    window_end: datetime,
) -> tuple[bool, list[dict[str, str]], str | None]:
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    snapshot = meta.get("balance_snapshot")
    if not isinstance(snapshot, dict):
        return True, [], "balance_snapshot_missing_warning"

    snapshot_asset = str(snapshot.get("asset") or "").upper()
    if snapshot_asset and snapshot_asset != from_asset:
        return True, [], "balance_snapshot_asset_mismatch_warning"

    try:
        start_available = Decimal(str(snapshot.get("available") or "0"))
    except Exception:
        return False, [], "balance_snapshot_invalid"

    external = _external_movements(
        db,
        swap=swap,
        asset=from_asset,
        window_start=window_start,
        window_end=window_end,
    )
    external_net = _external_net(external)
    expected_end = start_available - swap_debit_amount + external_net

    wallet = None
    from services.lifi.lifi_swap_settlement import _resolve_swap_wallet

    try:
        wallet = _resolve_swap_wallet(db, swap)
    except Exception:
        return False, external, "wallet_unavailable_for_balance_check"

    balance_repo = PersonWalletBalanceRepository()
    row = balance_repo.get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=wallet.person_id,
        asset=from_asset,
    )
    actual_end = Decimal(str(row.available_balance))
    if not _amount_compatible(expected_end, actual_end):
        return False, external, "balance_variation_unexplained"
    return True, external, None


def _build_projection(
    db: Session,
    *,
    intent: TransactionIntent,
    swap: PersonWalletSwap,
    debits: list[PersonWalletDeposit],
    credits: list[PersonWalletDeposit],
    amount_in: Decimal,
    amount_out: Decimal,
    external_movements: list[dict[str, str]],
    warnings: list[str],
) -> dict[str, Any]:
    observed_debit = debits[0] if debits else None
    observed_credit = credits[0] if credits else None
    legs = detect_swap_ledger_legs(db, swap)
    return {
        "intent_id": str(intent.id),
        "swap_id": str(swap.id),
        "tx_hash": str(swap.tx_hash or ""),
        "settlement_receipt_hash": settlement_marker_present(intent),
        "expected_debit": {"asset": str(swap.from_asset).upper(), "amount": str(amount_in)},
        "expected_credit": {"asset": str(swap.to_asset).upper(), "amount": str(amount_out)},
        "observed_debit": (
            {
                "deposit_id": str(observed_debit.id),
                "asset": observed_debit.asset.upper(),
                "amount": str(observed_debit.amount),
                "tx_hash": str(observed_debit.tx_hash or ""),
            }
            if observed_debit
            else None
        ),
        "observed_credit": (
            {
                "deposit_id": str(observed_credit.id),
                "asset": observed_credit.asset.upper(),
                "amount": str(observed_credit.amount),
                "tx_hash": str(observed_credit.tx_hash or ""),
                "source": legs.credit_source,
            }
            if observed_credit
            else None
        ),
        "debit_count": len(debits),
        "credit_count": len(credits),
        "external_movements": external_movements,
        "warnings": warnings,
    }


def _apply_phase_transition(
    db: Session,
    *,
    intent: TransactionIntent,
    phase: IntentOrchestratorPhase,
    report_hash: str | None,
    outcome: ReconciliationOutcome,
    error_code: str | None = None,
) -> None:
    meta_patch: dict[str, Any] = {
        "controller": CONTROLLER_ACTOR,
        "outcome": outcome.value,
    }
    if report_hash:
        meta_patch[RECONCILIATION_REPORT_METADATA_KEY] = report_hash
    if error_code:
        meta_patch["error_code"] = error_code

    TransactionIntentTransitionRepository.insert_transition(
        db,
        intent_id=intent.id,
        from_status=intent.status,
        to_status=intent.status,
        phase=phase.value,
        actor=CONTROLLER_ACTOR,
        metadata_json=meta_patch,
    )
    intent.current_phase = phase.value
    if report_hash and outcome == ReconciliationOutcome.RECONCILED:
        _persist_reconciliation_report(intent, report_hash)


def reconcile_lifi_swap_intent(db: Session, intent_id: UUID) -> ReconciliationResult:
    """Relit ledger / webhook / DB et marque RECONCILED ou échec — sans écriture économique."""
    intent = db.query(TransactionIntent).filter(TransactionIntent.id == intent_id).first()
    if intent is None:
        return _terminal(intent_id, "intent.not_found", "Intent introuvable")

    phase = (intent.current_phase or "").strip().upper()
    if phase == IntentOrchestratorPhase.RECONCILED.value:
        existing = _reconciliation_report_hash(intent)
        return ReconciliationResult(
            outcome=ReconciliationOutcome.NOOP_ALREADY_RECONCILED,
            intent_id=intent.id,
            reconciliation_report_hash=existing,
        )

    if not is_lifi_standalone_intent(intent):
        return _terminal(
            intent.id,
            "controller.product_not_supported",
            "Produit hors périmètre Controller v1 (LI.FI standalone uniquement)",
        )

    if phase != IntentOrchestratorPhase.LEDGER_SETTLED.value:
        return _terminal(
            intent.id,
            "controller.phase_not_ready",
            f"Phase {phase or '?'} non autorisée pour réconciliation (attendu LEDGER_SETTLED)",
        )

    if not settlement_marker_present(intent):
        return _terminal(
            intent.id,
            "controller.missing_settlement_receipt",
            "settlement_receipt_hash requis avant réconciliation",
        )

    linked = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.id == intent.linked_id)
        .first()
    )
    if linked is None:
        return _terminal(intent.id, "controller.swap_not_found", "Swap lié introuvable")

    swap = linked
    if is_bundle_internal_swap(swap):
        return _terminal(
            intent.id,
            "controller.bundle_internal_swap",
            "Swap bundle interne exclu du Controller v1",
        )

    tx_hash = str(swap.tx_hash or "").strip()
    if not tx_hash:
        return _retryable(intent.id, "controller.missing_tx_hash", "tx_hash requis pour réconciliation")

    try:
        amount_in = Decimal(str(swap.amount_in))
        amount_out = _resolve_amount_out(intent, swap)
    except (ValueError, TypeError) as exc:
        return _terminal(intent.id, "controller.invalid_amounts", str(exc))

    if amount_in <= 0 or amount_out <= 0:
        return _terminal(intent.id, "controller.invalid_amounts", "Montants swap invalides")

    debits, credits = _enumerate_swap_ledger_deposits(db, swap)
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()

    warnings: list[str] = []
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    if meta.get("balance_snapshot") is None:
        warnings.append("balance_snapshot_missing_warning")

    window_start = swap.created_at or intent.created_at or datetime.now(timezone.utc)
    window_end = swap.confirmed_at or datetime.now(timezone.utc)
    external_for_projection = _external_movements(
        db,
        swap=swap,
        asset=from_asset,
        window_start=window_start,
        window_end=window_end,
    )

    projection = _build_projection(
        db,
        intent=intent,
        swap=swap,
        debits=debits,
        credits=credits,
        amount_in=amount_in,
        amount_out=amount_out,
        external_movements=external_for_projection,
        warnings=warnings,
    )

    if len(debits) == 0:
        result = _retryable(
            intent.id,
            "controller.debit_missing",
            "Débit source absent",
            projection=projection,
        )
        _apply_phase_transition(
            db,
            intent=intent,
            phase=IntentOrchestratorPhase.RECONCILIATION_RETRYABLE_FAILURE,
            report_hash=None,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return result

    if len(credits) == 0:
        result = _retryable(
            intent.id,
            "controller.credit_missing",
            "Crédit destination absent",
            projection=projection,
        )
        _apply_phase_transition(
            db,
            intent=intent,
            phase=IntentOrchestratorPhase.RECONCILIATION_RETRYABLE_FAILURE,
            report_hash=None,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return result

    if len(debits) > 1:
        result = _terminal(
            intent.id,
            "controller.double_debit",
            "Double débit détecté",
            projection=projection,
        )
        _apply_phase_transition(
            db,
            intent=intent,
            phase=IntentOrchestratorPhase.RECONCILIATION_TERMINAL_FAILURE,
            report_hash=None,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return result

    if len(credits) > 1:
        result = _terminal(
            intent.id,
            "controller.double_credit",
            "Double crédit détecté",
            projection=projection,
        )
        _apply_phase_transition(
            db,
            intent=intent,
            phase=IntentOrchestratorPhase.RECONCILIATION_TERMINAL_FAILURE,
            report_hash=None,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return result

    debit = debits[0]
    credit = credits[0]

    if debit.asset.upper() != from_asset:
        result = _terminal(
            intent.id,
            "controller.debit_asset_mismatch",
            f"Débit asset {debit.asset} ≠ {from_asset}",
            projection=projection,
        )
        _apply_phase_transition(
            db,
            intent=intent,
            phase=IntentOrchestratorPhase.RECONCILIATION_TERMINAL_FAILURE,
            report_hash=None,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return result

    if credit.asset.upper() != to_asset:
        result = _terminal(
            intent.id,
            "controller.credit_asset_mismatch",
            f"Crédit asset {credit.asset} ≠ {to_asset}",
            projection=projection,
        )
        _apply_phase_transition(
            db,
            intent=intent,
            phase=IntentOrchestratorPhase.RECONCILIATION_TERMINAL_FAILURE,
            report_hash=None,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return result

    debit_amount = Decimal(str(debit.amount))
    credit_amount = Decimal(str(credit.amount))
    if not _amount_compatible(amount_in, debit_amount):
        result = _terminal(
            intent.id,
            "controller.debit_amount_mismatch",
            "Montant débit incompatible avec amount_in",
            projection=projection,
        )
        _apply_phase_transition(
            db,
            intent=intent,
            phase=IntentOrchestratorPhase.RECONCILIATION_TERMINAL_FAILURE,
            report_hash=None,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return result

    if not _amount_compatible(amount_out, credit_amount):
        result = _terminal(
            intent.id,
            "controller.credit_amount_mismatch",
            "Montant crédit incompatible avec amount_out",
            projection=projection,
        )
        _apply_phase_transition(
            db,
            intent=intent,
            phase=IntentOrchestratorPhase.RECONCILIATION_TERMINAL_FAILURE,
            report_hash=None,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return result

    swap_tx = tx_hash.lower()
    for leg in (debit, credit):
        leg_tx = str(leg.tx_hash or "").strip().lower()
        if leg_tx and leg_tx != swap_tx:
            result = _terminal(
                intent.id,
                "controller.tx_hash_mismatch",
                "tx_hash incohérent entre swap et jambe ledger",
                projection=projection,
            )
            _apply_phase_transition(
                db,
                intent=intent,
                phase=IntentOrchestratorPhase.RECONCILIATION_TERMINAL_FAILURE,
                report_hash=None,
                outcome=result.outcome,
                error_code=result.error_code,
            )
            return result

    balance_ok, external_movements, balance_issue = _balance_variation_explained(
        db,
        swap=swap,
        intent=intent,
        from_asset=from_asset,
        swap_debit_amount=debit_amount,
        window_start=window_start,
        window_end=window_end,
    )
    projection["external_movements"] = external_movements
    if balance_issue == "balance_snapshot_missing_warning":
        if "balance_snapshot_missing_warning" not in projection["warnings"]:
            projection["warnings"].append(balance_issue)
    elif balance_issue:
        projection["balance_issue"] = balance_issue

    if not balance_ok:
        result = _terminal(
            intent.id,
            "controller.balance_unexplained",
            "Variation balance source non expliquée par swap + mouvements externes",
            projection=projection,
        )
        _apply_phase_transition(
            db,
            intent=intent,
            phase=IntentOrchestratorPhase.RECONCILIATION_TERMINAL_FAILURE,
            report_hash=None,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return result

    report_hash = _compute_report_hash(intent.id, projection)
    _apply_phase_transition(
        db,
        intent=intent,
        phase=IntentOrchestratorPhase.RECONCILED,
        report_hash=report_hash,
        outcome=ReconciliationOutcome.RECONCILED,
    )

    logger.info(
        "controller.lifi_swap_reconciled intent_id=%s swap_id=%s report_hash=%s",
        intent.id,
        swap.id,
        report_hash[:16],
    )

    return ReconciliationResult(
        outcome=ReconciliationOutcome.RECONCILED,
        intent_id=intent.id,
        reconciliation_report_hash=report_hash,
        projection=projection,
    )
