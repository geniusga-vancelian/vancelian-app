"""Politique Phase 5B — actions whitelistées et garde-fous apply."""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import RawOnChainEvent
from services.privy_wallet.asset_mapping import normalize_evm_address, parse_amount_to_decimal
from services.security.security_env import is_production_env

from .discrepancy_models import ReconciliationDiscrepancy

CORRECTION_STATUS_PREVIEW = "preview"
CORRECTION_STATUS_REQUESTED = "requested"
CORRECTION_STATUS_APPROVED = "approved"
CORRECTION_STATUS_APPLIED = "applied"
CORRECTION_STATUS_REJECTED = "rejected"

APPLY_WHITELIST_ACTIONS = frozenset(
    {
        "link_raw_event_to_existing_ledger_entry",
        "create_missing_deposit_from_raw_event",
    }
)

FORBIDDEN_APPLY_ACTIONS = frozenset(
    {
        "void_deposit",
        "adjust_balance",
        "rebuild_balance",
        "delete_deposit",
        "force_settlement",
        "increment_balance",
    }
)

FINANCIAL_APPLY_ACTIONS = frozenset({"create_missing_deposit_from_raw_event"})

ALLOWED_RAW_EVENT_TYPES = frozenset({"erc20_transfer", "native_transfer"})

APPLY_ALLOWED_DISCREPANCY_STATUSES = frozenset({"open", "acknowledged"})


class CorrectionPolicyError(ValueError):
    """Violation des règles Phase 5B."""


def allow_single_approver_dev() -> bool:
    return os.getenv("ONCHAIN_RECONCILIATION_ALLOW_SINGLE_APPROVER_DEV", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def validate_approver_separation(*, requested_by: str | None, approved_by: str | None) -> None:
    if not requested_by or not approved_by:
        raise CorrectionPolicyError("requested_by et approved_by requis")
    if requested_by.strip().lower() == approved_by.strip().lower():
        if is_production_env():
            raise CorrectionPolicyError("approver_must_differ_from_requester_in_production")
        if not allow_single_approver_dev():
            raise CorrectionPolicyError("approver_must_differ_from_requester")


def load_raw_event(db: Session, raw_event_id: UUID) -> RawOnChainEvent | None:
    return db.query(RawOnChainEvent).filter(RawOnChainEvent.id == raw_event_id).first()


def discrepancy_has_verified_raw_event(
    db: Session,
    discrepancy: ReconciliationDiscrepancy,
    *,
    raw_event_id: UUID | None = None,
) -> tuple[bool, RawOnChainEvent | None]:
    if raw_event_id:
        row = load_raw_event(db, raw_event_id)
        return row is not None, row

    meta = discrepancy.metadata_json if isinstance(discrepancy.metadata_json, dict) else {}
    chain_id = meta.get("chain_id")
    tx_hash = meta.get("tx_hash") or discrepancy.reference_id
    log_index = meta.get("log_index", 0)
    if chain_id is not None and tx_hash:
        from services.onchain_indexer.repository import RawOnChainEventRepository

        row = RawOnChainEventRepository.find_by_chain_tx_log(
            db,
            chain_id=int(chain_id),
            tx_hash=str(tx_hash),
            log_index=int(log_index),
        )
        if row is not None:
            return True, row

    if not discrepancy.wallet_address or not discrepancy.asset:
        return False, None
    row = (
        db.query(RawOnChainEvent)
        .filter(
            RawOnChainEvent.wallet_address == discrepancy.wallet_address.lower(),
            RawOnChainEvent.asset == discrepancy.asset.upper(),
        )
        .order_by(RawOnChainEvent.parsed_at.desc())
        .first()
    )
    return row is not None, row


def validate_discrepancy_applyable(discrepancy: ReconciliationDiscrepancy) -> None:
    status = (discrepancy.status or "").strip().lower()
    if status not in APPLY_ALLOWED_DISCREPANCY_STATUSES:
        raise CorrectionPolicyError(f"discrepancy_status_not_applyable:{status}")


def compute_allowed_to_apply(
    db: Session,
    discrepancy: ReconciliationDiscrepancy,
    *,
    action: str,
    raw_event_id: UUID | None = None,
    deposit_id: UUID | None = None,
) -> bool:
    normalized = action.strip().lower()
    if normalized not in APPLY_WHITELIST_ACTIONS:
        return False
    if (discrepancy.status or "").strip().lower() not in APPLY_ALLOWED_DISCREPANCY_STATUSES:
        return False
    has_raw, raw_row = discrepancy_has_verified_raw_event(db, discrepancy, raw_event_id=raw_event_id)
    if not has_raw or raw_row is None:
        return False
    from .raw_event_consumption import get_consumed_correction_id

    if get_consumed_correction_id(db, raw_row) is not None:
        return False
    if normalized == "link_raw_event_to_existing_ledger_entry":
        return deposit_id is not None
    return True


def validate_raw_event_for_discrepancy(
    db: Session,
    discrepancy: ReconciliationDiscrepancy,
    raw_event: RawOnChainEvent,
    *,
    for_correction_id: UUID | None = None,
) -> Decimal:
    validate_discrepancy_applyable(discrepancy)
    from .raw_event_consumption import assert_raw_event_available

    assert_raw_event_available(db, raw_event, for_correction_id=for_correction_id)

    if raw_event.event_type.lower() not in ALLOWED_RAW_EVENT_TYPES:
        raise CorrectionPolicyError(f"unsupported_event_type:{raw_event.event_type}")

    disc_wallet = normalize_evm_address(discrepancy.wallet_address)
    event_wallet = normalize_evm_address(raw_event.wallet_address)
    if not disc_wallet or not event_wallet or disc_wallet.lower() != event_wallet.lower():
        raise CorrectionPolicyError("wallet_mismatch")

    if discrepancy.asset and raw_event.asset.upper() != discrepancy.asset.upper():
        raise CorrectionPolicyError("asset_mismatch")

    amount = parse_amount_to_decimal(raw_event.amount_raw, raw_event.asset)
    if amount <= 0:
        raise CorrectionPolicyError("invalid_amount")

    if discrepancy.delta is not None:
        delta = Decimal(str(discrepancy.delta))
        if delta > 0 and amount > delta:
            raise CorrectionPolicyError("amount_exceeds_discrepancy_delta")

    return amount
