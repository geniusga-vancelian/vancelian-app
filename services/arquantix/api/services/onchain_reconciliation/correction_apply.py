"""Apply contrôlé Phase 5B — deposit depuis raw event, lien metadata."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from database import PersonCryptoWallet
from services.privy_wallet.enums import (
    PersonWalletDepositStatus,
    PersonWalletDirection,
    PersonWalletTransactionKind,
)
from services.privy_wallet.repository import (
    PersonCryptoWalletRepository,
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
)

from .correction_policy import (
    CORRECTION_STATUS_APPLIED,
    CorrectionPolicyError,
    validate_discrepancy_applyable,
    validate_raw_event_for_discrepancy,
)
from .raw_event_consumption import (
    RawEventConsumptionError,
    lock_raw_event_for_apply,
    mark_raw_event_consumed,
)
from .discrepancy_models import ReconciliationCorrection, ReconciliationDiscrepancy
from .discrepancy_repository import DiscrepancyRepository, discrepancy_to_dict


class CorrectionApplyError(ValueError):
    pass


def apply_correction(
    db: Session,
    *,
    correction: ReconciliationCorrection,
    discrepancy: ReconciliationDiscrepancy,
    actor_id: str,
) -> dict[str, Any]:
    if correction.applied_at is not None or correction.status == CORRECTION_STATUS_APPLIED:
        raise CorrectionApplyError("correction_already_applied")
    if correction.status != "approved":
        raise CorrectionApplyError("correction_not_approved")

    validate_discrepancy_applyable(discrepancy)

    action = correction.action.strip().lower()
    meta = correction.metadata_json if isinstance(correction.metadata_json, dict) else {}
    raw_event_id = meta.get("raw_onchain_event_id")
    if not raw_event_id:
        raise CorrectionApplyError("missing_raw_onchain_event_id")

    try:
        raw_event = lock_raw_event_for_apply(db, UUID(str(raw_event_id)))
    except LookupError as exc:
        raise CorrectionApplyError("raw_onchain_event_not_found") from exc

    try:
        validate_raw_event_for_discrepancy(
            db,
            discrepancy,
            raw_event,
            for_correction_id=correction.id,
        )
    except RawEventConsumptionError as exc:
        raise CorrectionApplyError(str(exc)) from exc

    if action == "create_missing_deposit_from_raw_event":
        result = _apply_create_deposit_from_raw(db, discrepancy, raw_event, correction=correction)
    elif action == "link_raw_event_to_existing_ledger_entry":
        result = _apply_link_raw_to_deposit(db, discrepancy, raw_event, correction=correction)
    else:
        raise CorrectionApplyError(f"action_not_applyable:{action}")

    mark_raw_event_consumed(db, raw_event, correction_id=correction.id)

    correction.status = CORRECTION_STATUS_APPLIED
    correction.dry_run = False
    correction.applied_at = datetime.now(timezone.utc)
    if isinstance(correction.metadata_json, dict):
        correction.metadata_json = {**correction.metadata_json, "applied_by": actor_id}
    db.add(correction)

    DiscrepancyRepository.update_status(
        db,
        discrepancy,
        status="resolved",
        resolved=True,
        metadata_patch={
            "resolved_by_correction_id": str(correction.id),
            "resolution_action": action,
        },
    )
    db.flush()
    return {
        "correction_id": str(correction.id),
        "discrepancy": discrepancy_to_dict(discrepancy),
        "apply_result": result,
    }


def _apply_create_deposit_from_raw(
    db: Session,
    discrepancy: ReconciliationDiscrepancy,
    raw_event: Any,
    *,
    correction: ReconciliationCorrection,
) -> dict[str, Any]:
    amount = validate_raw_event_for_discrepancy(db, discrepancy, raw_event)

    wallet = (
        db.query(PersonCryptoWallet)
        .filter(
            PersonCryptoWallet.person_id == discrepancy.person_id,
            PersonCryptoWallet.revoked_at.is_(None),
        )
        .filter(PersonCryptoWallet.address.ilike(discrepancy.wallet_address or ""))
        .first()
    )
    if wallet is None:
        wallet = PersonCryptoWalletRepository.find_active_by_address(
            db,
            discrepancy.wallet_address or "",
        )
    if wallet is None:
        raise CorrectionPolicyError("wallet_not_found")

    existing = PersonWalletDepositRepository.find_by_chain_tx(
        db,
        chain_id=raw_event.chain_id,
        tx_hash=raw_event.tx_hash,
        log_index=raw_event.log_index,
    )
    if existing is not None:
        raise CorrectionApplyError("deposit_already_exists")

    idempotency_key = f"recon_raw_{raw_event.chain_id}_{raw_event.tx_hash}_{raw_event.log_index}"

    deposit = PersonWalletDepositRepository.create(
        db,
        data={
            "person_crypto_wallet_id": wallet.id,
            "person_id": wallet.person_id,
            "pe_client_id": wallet.pe_client_id,
            "transaction_kind": PersonWalletTransactionKind.PRIVY_DEPOSIT_IN.value,
            "direction": PersonWalletDirection.CREDIT.value,
            "asset": raw_event.asset.upper(),
            "amount": amount,
            "chain_type": "ethereum",
            "chain_id": raw_event.chain_id,
            "tx_hash": raw_event.tx_hash.lower(),
            "log_index": raw_event.log_index,
            "block_number": raw_event.block_number,
            "from_address": None,
            "to_address": raw_event.wallet_address.lower(),
            "status": PersonWalletDepositStatus.CONFIRMED.value,
            "idempotency_key": idempotency_key,
            "title": f"Dépôt {raw_event.asset} (réconciliation)",
            "subtitle": f"+{amount} {raw_event.asset}",
            "metadata_json": {
                "source": "onchain_reconciliation_apply",
                "correction_id": str(correction.id),
                "raw_onchain_event_id": str(raw_event.id),
            },
            "confirmed_at": datetime.now(timezone.utc),
        },
    )

    balance = PersonWalletBalanceRepository.get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=wallet.person_id,
        asset=raw_event.asset,
    )
    PersonWalletBalanceRepository.increment_balance(
        db,
        balance,
        delta=amount,
        sync_source="onchain_reconciliation_apply",
    )

    return {
        "deposit_id": str(deposit.id),
        "amount": str(amount),
        "raw_onchain_event_id": str(raw_event.id),
    }


def _apply_link_raw_to_deposit(
    db: Session,
    discrepancy: ReconciliationDiscrepancy,
    raw_event: Any,
    *,
    correction: ReconciliationCorrection,
) -> dict[str, Any]:
    meta = correction.metadata_json if isinstance(correction.metadata_json, dict) else {}
    deposit_id = meta.get("deposit_id")
    if not deposit_id:
        raise CorrectionApplyError("missing_deposit_id")

    deposit = PersonWalletDepositRepository.get_for_person(
        db, UUID(str(deposit_id)), discrepancy.person_id
    )
    if deposit is None:
        raise CorrectionApplyError("deposit_not_found")

    base_meta = deposit.metadata_json if isinstance(deposit.metadata_json, dict) else {}
    deposit.metadata_json = {
        **base_meta,
        "raw_onchain_event_id": str(raw_event.id),
        "linked_by": "onchain_reconciliation_apply",
        "correction_id": str(correction.id),
    }
    db.add(deposit)
    db.flush()

    return {
        "deposit_id": str(deposit.id),
        "raw_onchain_event_id": str(raw_event.id),
        "metadata_only": True,
    }
