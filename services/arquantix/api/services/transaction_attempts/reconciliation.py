"""Backfill dry-run et gap audit onchain_transaction_attempts (Phase 2)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from config.supported_swap_assets import SUPPORTED_SWAP_CHAINS, normalize_chain_key
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_intents.lifi_intent_sync import LINKED_TABLE as LIFI_LINKED_TABLE

from .dual_write import LINKED_SWAPS, LINKED_VAULT
from .tx_hash_canonical import swap_covered_by_attempt
from .enums import AttemptProtocol, AttemptStepType
from .models import OnchainTransactionAttempt
from .repository import OnchainTransactionAttemptRepository

VAULT_INTEGRATION_MODES = frozenset(
    {"direct_morpho", "ledgity_vault", "lombard_v1", "morpho_vault"}
)

LOMBARD_VAULT_STEP_TYPES = frozenset(
    {
        AttemptStepType.APPROVE.value,
        AttemptStepType.AUTHORIZE.value,
        AttemptStepType.OPEN_LOAN.value,
    }
)


def migration_171_ready(db: Session | None = None) -> bool:
    try:
        if db is not None:
            r = db.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'onchain_transaction_attempts'"
                )
            )
            return r.fetchone() is not None
        from database import engine

        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'onchain_transaction_attempts'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


def tx_hash_backfill_idempotency_key(*, chain_id: int, tx_hash: str) -> str:
    from .tx_hash_canonical import tx_hash_canonical_idempotency_key

    return tx_hash_canonical_idempotency_key(chain_id=chain_id, tx_hash=tx_hash)


def _chain_id_from_swap(swap: PersonWalletSwap) -> int:
    try:
        meta = SUPPORTED_SWAP_CHAINS.get(normalize_chain_key(swap.from_chain), {})
        return int(meta.get("lifi_chain_id") or 8453)
    except Exception:
        return 8453


def _swap_protocol(swap: PersonWalletSwap) -> str:
    if is_bundle_internal_swap(swap):
        return AttemptProtocol.INTERNAL_BUNDLE.value
    return AttemptProtocol.LIFI.value


def _approval_hash_from_swap(swap: PersonWalletSwap) -> str | None:
    audit = swap.audit_log if isinstance(swap.audit_log, list) else []
    for entry in reversed(audit):
        if not isinstance(entry, dict):
            continue
        if entry.get("event") == "approval_submitted" and entry.get("tx_hash"):
            return str(entry["tx_hash"]).strip().lower()
    return None


def _attempt_exists(db: Session, *, idempotency_key: str, step_type: str) -> bool:
    return (
        OnchainTransactionAttemptRepository.find_by_composite_key(
            db,
            idempotency_key=idempotency_key,
            step_type=step_type,
        )
        is not None
    )


def _attempt_exists_for_chain_tx(
    db: Session,
    *,
    chain_id: int,
    tx_hash: str | None,
    step_type: str | None = None,
) -> bool:
    if not tx_hash:
        return False
    norm = tx_hash.strip().lower()
    q = db.query(OnchainTransactionAttempt).filter(
        OnchainTransactionAttempt.chain_id == chain_id,
        OnchainTransactionAttempt.tx_hash == norm,
    )
    if step_type:
        q = q.filter(OnchainTransactionAttempt.step_type == step_type)
    return q.first() is not None


def _attempt_exists_by_linked_reference(
    db: Session,
    *,
    linked_reference_id: str,
    step_type: str,
) -> bool:
    return (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.linked_reference_id == linked_reference_id,
            OnchainTransactionAttempt.step_type == step_type,
        )
        .first()
        is not None
    )


def _vault_metadata_dict(metadata_json: Any) -> dict[str, Any]:
    if isinstance(metadata_json, dict):
        return metadata_json
    if isinstance(metadata_json, str) and metadata_json.strip():
        try:
            parsed = json.loads(metadata_json)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _expected_vault_attempt_step_type(
    *,
    integration_mode: str | None,
    operation: str,
    metadata_json: Any = None,
) -> str:
    """Map OVT operation (+ Lombard metadata) → expected onchain_transaction_attempt step_type."""
    op = str(operation or "").strip().lower()
    mode = str(integration_mode or "").strip().lower()
    if mode != "lombard_v1":
        return op

    if op in (
        AttemptStepType.APPROVE.value,
        AttemptStepType.AUTHORIZE.value,
        AttemptStepType.OPEN_LOAN.value,
    ):
        return op

    if op == AttemptStepType.DEPOSIT.value:
        meta = _vault_metadata_dict(metadata_json)
        lombard_op = str(meta.get("lombard_operation") or "").strip().lower()
        if lombard_op in LOMBARD_VAULT_STEP_TYPES:
            return lombard_op
        return AttemptStepType.OPEN_LOAN.value

    return op


def _vault_legacy_covered_by_attempt(
    db: Session,
    *,
    row: sa.RowMapping,
    expected_step_type: str,
) -> bool:
    legacy = _legacy_record_from_vault(row, expected_step_type=expected_step_type)
    idem = legacy["legacy_idempotency_key"]
    if _attempt_exists(db, idempotency_key=idem, step_type=expected_step_type):
        return True
    if legacy.get("tx_hash") and _attempt_exists_for_chain_tx(
        db,
        chain_id=int(legacy["chain_id"]),
        tx_hash=str(legacy["tx_hash"]),
        step_type=expected_step_type,
    ):
        return True
    return _attempt_exists_by_linked_reference(
        db,
        linked_reference_id=str(row["id"]),
        step_type=expected_step_type,
    )


def _integration_mode_to_protocol(mode: str | None) -> str | None:
    norm = (mode or "").strip().lower()
    if norm in ("direct_morpho", "morpho_vault"):
        return AttemptProtocol.MORPHO.value
    if norm == "ledgity_vault":
        return AttemptProtocol.LEDGITY.value
    if norm == "lombard_v1":
        return AttemptProtocol.LOMBARD.value
    return None


def _vault_attempt_key(
    *,
    protocol: str,
    person_id: UUID,
    group_key: str,
    step_type: str,
    step_index: int,
) -> str:
    return f"{protocol}:{person_id}:{group_key}:{step_type}:{step_index}"


def select_canonical_legacy_record(
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Choix déterministe : intent > plus ancien > amount_in > reference_id."""
    if not records:
        raise ValueError("records must not be empty")
    if len(records) == 1:
        return records[0], []

    def _sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
        has_intent = 0 if record.get("intent_id") else 1
        created = record.get("created_at") or ""
        try:
            amount = Decimal(str(record.get("amount_in") or "0"))
        except Exception:
            amount = Decimal("0")
        ref = str(record.get("reference_id") or "")
        return (has_intent, created, -amount, ref)

    ordered = sorted(records, key=_sort_key)
    return ordered[0], ordered[1:]


def build_grouped_attempt_candidate(
    canonical: dict[str, Any],
    secondaries: list[dict[str, Any]],
    *,
    chain_id: int,
    tx_hash: str,
) -> dict[str, Any]:
    norm_hash = tx_hash.strip().lower()
    idem = tx_hash_backfill_idempotency_key(chain_id=chain_id, tx_hash=norm_hash)
    return {
        "source": canonical["source"],
        "reference_id": canonical["reference_id"],
        "person_id": canonical["person_id"],
        "chain_id": chain_id,
        "tx_hash": norm_hash,
        "step_type": canonical["step_type"],
        "protocol": canonical["protocol"],
        "idempotency_key": idem,
        "intent_id": canonical.get("intent_id"),
        "swap_status": canonical.get("swap_status"),
        "vault_status": canonical.get("vault_status"),
        "grouping": {
            "backfill_grouped_by_tx_hash": True,
            "legacy_records_in_group": 1 + len(secondaries),
            "secondary_count": len(secondaries),
        },
        "raw_submission_json": {
            "backfill_grouped_by_tx_hash": True,
            "canonical_legacy_record": canonical,
            "secondary_legacy_records": secondaries,
        },
    }


def group_legacy_records_by_chain_tx(
    raw_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Regroupe les records avec tx_hash par (chain_id, tx_hash).

    Returns:
        grouped_attempts, ungrouped_records, duplicate_tx_hash_groups
    """
    with_hash: list[dict[str, Any]] = []
    without_hash: list[dict[str, Any]] = []
    for record in raw_records:
        tx = record.get("tx_hash")
        if tx and str(tx).strip():
            with_hash.append(record)
        else:
            without_hash.append(record)

    buckets: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for record in with_hash:
        key = (int(record["chain_id"]), str(record["tx_hash"]).strip().lower())
        buckets.setdefault(key, []).append(record)

    grouped: list[dict[str, Any]] = []
    duplicate_groups: list[dict[str, Any]] = []
    for (chain_id, tx_hash), records in buckets.items():
        canonical, secondaries = select_canonical_legacy_record(records)
        if len(records) > 1:
            duplicate_groups.append(
                {
                    "chain_id": chain_id,
                    "tx_hash": tx_hash,
                    "record_count": len(records),
                    "sources": sorted({r.get("source") for r in records}),
                    "canonical_reference_id": canonical["reference_id"],
                    "secondary_reference_ids": [s["reference_id"] for s in secondaries],
                }
            )
        grouped.append(
            build_grouped_attempt_candidate(
                canonical,
                secondaries,
                chain_id=chain_id,
                tx_hash=tx_hash,
            )
        )
    return grouped, without_hash, duplicate_groups


def _legacy_record_from_swap(
    db: Session,
    swap: PersonWalletSwap,
    *,
    step_type: str,
    tx_hash: str,
    protocol: str,
) -> dict[str, Any]:
    intent = TransactionIntentRepository.find_by_linked(
        db,
        linked_table=LIFI_LINKED_TABLE,
        linked_id=swap.id,
    )
    step_suffix = "approve" if step_type == AttemptStepType.APPROVE.value else "swap"
    return {
        "source": "person_wallet_swaps",
        "reference_id": str(swap.id),
        "person_id": str(swap.person_id),
        "chain_id": _chain_id_from_swap(swap),
        "tx_hash": tx_hash.strip().lower(),
        "step_type": step_type,
        "protocol": protocol,
        "intent_id": str(intent.id) if intent else None,
        "created_at": swap.created_at.isoformat() if swap.created_at else None,
        "amount_in": str(swap.amount_in) if swap.amount_in is not None else None,
        "swap_status": swap.status,
        "legacy_idempotency_key": f"lifi:{swap.id}:{step_suffix}",
    }


def _scan_swap_backfill_raw_records(
    db: Session,
    *,
    person_id: UUID | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    q = db.query(PersonWalletSwap).order_by(PersonWalletSwap.created_at.desc())
    if person_id is not None:
        q = q.filter(PersonWalletSwap.person_id == person_id)
    swaps = q.limit(limit).all()

    records: list[dict[str, Any]] = []
    for swap in swaps:
        protocol = _swap_protocol(swap)
        approval_hash = _approval_hash_from_swap(swap)
        if approval_hash:
            approve_key = f"lifi:{swap.id}:approve"
            if not _attempt_exists(
                db, idempotency_key=approve_key, step_type=AttemptStepType.APPROVE.value
            ) and not _attempt_exists_for_chain_tx(
                db,
                chain_id=_chain_id_from_swap(swap),
                tx_hash=approval_hash,
                step_type=AttemptStepType.APPROVE.value,
            ):
                records.append(
                    _legacy_record_from_swap(
                        db,
                        swap,
                        step_type=AttemptStepType.APPROVE.value,
                        tx_hash=approval_hash,
                        protocol=protocol,
                    )
                )

        if swap.tx_hash and swap.status not in {
            SwapSessionStatus.PENDING.value,
            SwapSessionStatus.QUOTE_RECEIVED.value,
            SwapSessionStatus.AWAITING_SIGNATURE.value,
        }:
            swap_key = f"lifi:{swap.id}:swap"
            chain_id = _chain_id_from_swap(swap)
            if not swap_covered_by_attempt(
                db,
                swap,
                chain_id=chain_id,
                tx_hash=str(swap.tx_hash),
                step_type=AttemptStepType.SWAP.value,
                swap_idempotency_key=swap_key,
            ):
                records.append(
                    _legacy_record_from_swap(
                        db,
                        swap,
                        step_type=AttemptStepType.SWAP.value,
                        tx_hash=str(swap.tx_hash),
                        protocol=protocol,
                    )
                )
    return records


def _legacy_record_from_vault(
    row: sa.RowMapping,
    *,
    expected_step_type: str | None = None,
) -> dict[str, Any]:
    protocol = _integration_mode_to_protocol(row["integration_mode"])
    operation = str(row["operation"] or "").strip().lower()
    step_type = expected_step_type or _expected_vault_attempt_step_type(
        integration_mode=str(row.get("integration_mode") or ""),
        operation=operation,
        metadata_json=row.get("metadata_json"),
    )
    group_key = str(row["idempotency_key"] or row["id"])
    step_index = int(row["tx_index"] or 0)
    person_uuid = UUID(str(row["person_id"]))
    return {
        "source": "onchain_vault_transactions",
        "reference_id": str(row["id"]),
        "person_id": str(row["person_id"]),
        "chain_id": int(row["chain_id"] or 8453),
        "tx_hash": str(row["tx_hash"]).strip().lower() if row.get("tx_hash") else None,
        "step_type": step_type,
        "vault_operation": operation,
        "protocol": protocol,
        "intent_id": None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "amount_in": str(row["amount_raw"]) if row.get("amount_raw") is not None else None,
        "vault_status": row["status"],
        "legacy_idempotency_key": _vault_attempt_key(
            protocol=str(protocol),
            person_id=person_uuid,
            group_key=group_key,
            step_type=step_type,
            step_index=step_index,
        ),
    }


def _scan_vault_backfill_raw_records(
    db: Session,
    *,
    person_id: UUID | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    sql = """
        SELECT id, person_id, operation, status, tx_hash, chain_id, wallet_address,
               idempotency_key, integration_mode, tx_index, asset_symbol, amount_raw,
               metadata_json, created_at
        FROM onchain_vault_transactions
        WHERE integration_mode = ANY(:modes)
    """
    params: dict[str, Any] = {"modes": list(VAULT_INTEGRATION_MODES), "limit": limit}
    if person_id is not None:
        sql += " AND person_id = :person_id"
        params["person_id"] = str(person_id)
    sql += " ORDER BY created_at DESC LIMIT :limit"

    rows = db.execute(sa.text(sql), params).mappings().all()
    records: list[dict[str, Any]] = []
    for row in rows:
        protocol = _integration_mode_to_protocol(row["integration_mode"])
        if protocol is None:
            continue
        operation = str(row["operation"] or "").strip().lower()
        if operation not in {
            AttemptStepType.APPROVE.value,
            AttemptStepType.DEPOSIT.value,
            AttemptStepType.WITHDRAW.value,
            AttemptStepType.AUTHORIZE.value,
            AttemptStepType.OPEN_LOAN.value,
            AttemptStepType.COLLATERAL_SUPPLY.value,
        }:
            continue
        expected_step = _expected_vault_attempt_step_type(
            integration_mode=str(row.get("integration_mode") or ""),
            operation=operation,
            metadata_json=row.get("metadata_json"),
        )
        if _vault_legacy_covered_by_attempt(db, row=row, expected_step_type=expected_step):
            continue
        legacy = _legacy_record_from_vault(row, expected_step_type=expected_step)
        if not legacy.get("tx_hash") and str(row["status"] or "").lower() not in (
            "success",
            "failed",
            "reverted",
        ):
            continue
        records.append(legacy)
    return records


def _ungrouped_to_attempt_candidate(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": record["source"],
        "reference_id": record["reference_id"],
        "person_id": record["person_id"],
        "chain_id": record["chain_id"],
        "tx_hash": record.get("tx_hash"),
        "step_type": record["step_type"],
        "protocol": record["protocol"],
        "idempotency_key": record["legacy_idempotency_key"],
        "intent_id": record.get("intent_id"),
        "swap_status": record.get("swap_status"),
        "vault_status": record.get("vault_status"),
        "grouping": {
            "backfill_grouped_by_tx_hash": False,
            "legacy_records_in_group": 1,
            "secondary_count": 0,
        },
        "raw_submission_json": {
            "backfill_grouped_by_tx_hash": False,
            "canonical_legacy_record": record,
            "secondary_legacy_records": [],
        },
    }


def build_backfill_plan(
    db: Session,
    *,
    person_id: UUID | None = None,
    swap_limit: int = 500,
    vault_limit: int = 500,
) -> dict[str, Any]:
    swap_raw = _scan_swap_backfill_raw_records(db, person_id=person_id, limit=swap_limit)
    vault_raw = _scan_vault_backfill_raw_records(db, person_id=person_id, limit=vault_limit)
    all_raw = swap_raw + vault_raw

    grouped, ungrouped, duplicate_groups = group_legacy_records_by_chain_tx(all_raw)
    ungrouped_attempts = [_ungrouped_to_attempt_candidate(r) for r in ungrouped]
    all_attempts = grouped + ungrouped_attempts

    grouped_secondary = sum(a["grouping"]["secondary_count"] for a in grouped)
    legacy_covered = sum(a["grouping"]["legacy_records_in_group"] for a in all_attempts)

    def _count_by_protocol(attempts: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for attempt in attempts:
            protocol = str(attempt.get("protocol") or "unknown")
            counts[protocol] = counts.get(protocol, 0) + 1
        return counts

    by_protocol = _count_by_protocol(all_attempts)
    grouped_under_single = [
        {
            "detector": "legacy_records_grouped_under_single_attempt",
            "severity": "info",
            **group,
        }
        for group in duplicate_groups
    ]

    return {
        "raw_legacy_records": len(all_raw),
        "attempts_to_create": len(all_attempts),
        "legacy_records_covered": legacy_covered,
        "grouped_secondary_records": grouped_secondary,
        "duplicate_tx_hash_groups": duplicate_groups,
        "legacy_records_grouped_under_single_attempt": grouped_under_single,
        "attempts": all_attempts,
        "by_source": {
            "lifi": by_protocol.get(AttemptProtocol.LIFI.value, 0),
            "internal_bundle": by_protocol.get(AttemptProtocol.INTERNAL_BUNDLE.value, 0),
            "morpho": by_protocol.get(AttemptProtocol.MORPHO.value, 0),
            "ledgity": by_protocol.get(AttemptProtocol.LEDGITY.value, 0),
            "lombard": by_protocol.get(AttemptProtocol.LOMBARD.value, 0),
        },
        "by_protocol": by_protocol,
    }


def build_backfill_report(
    db: Session,
    *,
    person_id: UUID | None = None,
    swap_limit: int = 500,
    vault_limit: int = 500,
) -> dict[str, Any]:
    if not migration_171_ready(db):
        return {
            "ready": False,
            "message": "Table onchain_transaction_attempts absente (migration 171 requise).",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    plan = build_backfill_plan(
        db,
        person_id=person_id,
        swap_limit=swap_limit,
        vault_limit=vault_limit,
    )
    report = {
        "ready": True,
        "dry_run": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "person_id": str(person_id) if person_id else None,
        "summary": {
            "raw_legacy_records": plan["raw_legacy_records"],
            "attempts_to_create": plan["attempts_to_create"],
            "legacy_records_covered": plan["legacy_records_covered"],
            "grouped_secondary_records": plan["grouped_secondary_records"],
            "duplicate_tx_hash_groups_count": len(plan["duplicate_tx_hash_groups"]),
            "by_source": plan["by_source"],
            "by_protocol": plan["by_protocol"],
            "doctrine_ok": plan["attempts_to_create"] <= plan["legacy_records_covered"],
        },
        "duplicate_tx_hash_groups": plan["duplicate_tx_hash_groups"][:50],
        "legacy_records_grouped_under_single_attempt": plan[
            "legacy_records_grouped_under_single_attempt"
        ][:50],
        "attempt_candidates": plan["attempts"][:100],
        "notes": [
            "Doctrine: 1 tx_hash on-chain = 1 onchain_transaction_attempt.",
            "Privy inbound deposits exclus du backfill Phase 2 (person_wallet_deposits).",
            "Backfill n'altère pas les tables legacy.",
            "Ne pas lancer --apply tant que duplicate_tx_hash_groups est résolu en dry-run.",
        ],
    }
    try:
        from services.transaction_trace.enums import TraceEventType
        from services.transaction_trace.transaction_trace_logger import log_transaction_trace

        log_transaction_trace(
            TraceEventType.REPLAY_BACKFILL_CANDIDATE,
            db=db,
            person_id=person_id,
            source="transaction_attempts.reconciliation.build_backfill_report",
            message="backfill dry-run candidates computed",
            metadata_json={
                "summary": report["summary"],
                "duplicate_tx_hash_groups_count": len(plan["duplicate_tx_hash_groups"]),
            },
        )
    except Exception:
        pass
    return report


def apply_backfill(
    db: Session,
    *,
    person_id: UUID | None = None,
    swap_limit: int = 500,
    vault_limit: int = 500,
) -> dict[str, Any]:
    report = build_backfill_report(
        db,
        person_id=person_id,
        swap_limit=swap_limit,
        vault_limit=vault_limit,
    )
    if not report.get("ready"):
        return report

    plan = build_backfill_plan(
        db,
        person_id=person_id,
        swap_limit=swap_limit,
        vault_limit=vault_limit,
    )
    applied = {"attempts": 0, "errors": []}

    from .schemas import AttemptCreateInput, AttemptTransitionInput
    from .service import OnchainTransactionAttemptService

    for cand in plan["attempts"]:
        try:
            meta = cand.get("raw_submission_json") if isinstance(cand.get("raw_submission_json"), dict) else {}
            OnchainTransactionAttemptService.create_prepared_attempt(
                db,
                AttemptCreateInput(
                    person_id=UUID(cand["person_id"]),
                    chain_id=int(cand["chain_id"]),
                    protocol=str(cand["protocol"]),
                    operation_type=_operation_type_for_step(str(cand["step_type"])),
                    step_type=str(cand["step_type"]),
                    idempotency_key=str(cand["idempotency_key"]),
                    intent_id=UUID(cand["intent_id"]) if cand.get("intent_id") else None,
                    linked_table=LINKED_SWAPS if cand["source"] == "person_wallet_swaps" else LINKED_VAULT,
                    linked_id=UUID(cand["reference_id"])
                    if cand["source"] == "person_wallet_swaps"
                    else None,
                    linked_reference_id=cand["reference_id"]
                    if cand["source"] == "onchain_vault_transactions"
                    else None,
                    metadata_patch={
                        "backfill": True,
                        **(cand.get("grouping") or {}),
                    },
                    raw_submission_json=meta,
                ),
            )
            if cand.get("tx_hash"):
                status = _status_from_legacy_candidate(cand)
                transition = AttemptTransitionInput(tx_hash=str(cand["tx_hash"]))
                if status == "confirmed":
                    OnchainTransactionAttemptService.mark_confirmed(
                        db,
                        idempotency_key=str(cand["idempotency_key"]),
                        step_type=str(cand["step_type"]),
                        transition=transition,
                    )
                elif status == "failed":
                    OnchainTransactionAttemptService.mark_failed(
                        db,
                        idempotency_key=str(cand["idempotency_key"]),
                        step_type=str(cand["step_type"]),
                        transition=transition,
                    )
                else:
                    OnchainTransactionAttemptService.mark_submitted(
                        db,
                        idempotency_key=str(cand["idempotency_key"]),
                        step_type=str(cand["step_type"]),
                        transition=transition,
                    )
            applied["attempts"] += 1
            try:
                from services.transaction_trace.enums import TraceEventType
                from services.transaction_trace.transaction_trace_logger import log_transaction_trace

                log_transaction_trace(
                    TraceEventType.REPLAY_BACKFILL_APPLIED,
                    db=db,
                    person_id=UUID(cand["person_id"]),
                    idempotency_key=str(cand["idempotency_key"]),
                    protocol=str(cand.get("protocol")),
                    operation_type=_operation_type_for_step(str(cand["step_type"])),
                    step_type=str(cand["step_type"]),
                    status_to=_status_from_legacy_candidate(cand),
                    tx_hash=str(cand["tx_hash"]) if cand.get("tx_hash") else None,
                    chain_id=int(cand["chain_id"]),
                    linked_table=LINKED_SWAPS if cand["source"] == "person_wallet_swaps" else LINKED_VAULT,
                    linked_id=UUID(cand["reference_id"])
                    if cand["source"] == "person_wallet_swaps"
                    else None,
                    linked_reference_id=cand["reference_id"]
                    if cand["source"] == "onchain_vault_transactions"
                    else None,
                    source="transaction_attempts.reconciliation.apply_backfill",
                    message="backfill attempt applied from legacy",
                    metadata_json=cand.get("grouping"),
                )
            except Exception:
                pass
        except Exception as exc:
            applied["errors"].append({"reference_id": cand["reference_id"], "error": str(exc)})

    db.flush()
    report["dry_run"] = False
    report["applied"] = applied
    return report


def _operation_type_for_step(step_type: str) -> str:
    if step_type in (AttemptStepType.APPROVE.value, AttemptStepType.AUTHORIZE.value):
        return AttemptStepType.APPROVE.value
    if step_type == AttemptStepType.WITHDRAW.value:
        return AttemptStepType.WITHDRAW.value
    if step_type == AttemptStepType.OPEN_LOAN.value:
        return "borrow"
    if step_type == AttemptStepType.SWAP.value:
        return AttemptStepType.SWAP.value
    return AttemptStepType.DEPOSIT.value


def _status_from_legacy_candidate(cand: dict[str, Any]) -> str:
    swap_status = str(cand.get("swap_status") or "").upper()
    if swap_status == SwapSessionStatus.CONFIRMED.value:
        return "confirmed"
    if swap_status == SwapSessionStatus.FAILED.value:
        return "failed"
    vault_status = str(cand.get("vault_status") or "").lower()
    if vault_status == "success":
        return "confirmed"
    if vault_status in ("failed", "reverted"):
        return "failed"
    return "submitted"


def _anomaly(gap_type: str, *, severity: str = "gap", **fields: Any) -> dict[str, Any]:
    return {"gap_type": gap_type, "severity": severity, **fields}


def _swap_missing_covered_by_chain_tx(
    db: Session,
    *,
    swap,
    chain_id: int,
    tx_hash: str,
    step_type: str,
) -> bool:
    swap_idem = (
        f"lifi:{swap.id}:{'approve' if step_type == AttemptStepType.APPROVE.value else 'swap'}"
    )
    return swap_covered_by_attempt(
        db,
        swap,
        chain_id=chain_id,
        tx_hash=tx_hash,
        step_type=step_type,
        swap_idempotency_key=swap_idem,
    )


def scan_attempt_gaps_for_person(
    db: Session,
    person_id: UUID,
    *,
    swap_limit: int = 200,
    vault_limit: int = 200,
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []

    swaps = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == person_id)
        .order_by(PersonWalletSwap.created_at.desc())
        .limit(swap_limit)
        .all()
    )

    swap_swap_records: list[dict[str, Any]] = []
    for swap in swaps:
        if swap.tx_hash and swap.status not in {
            SwapSessionStatus.PENDING.value,
            SwapSessionStatus.QUOTE_RECEIVED.value,
        }:
            chain_id = _chain_id_from_swap(swap)
            tx = str(swap.tx_hash).strip().lower()
            if not _swap_missing_covered_by_chain_tx(
                db,
                swap=swap,
                chain_id=chain_id,
                tx_hash=tx,
                step_type=AttemptStepType.SWAP.value,
            ):
                swap_swap_records.append(
                    _legacy_record_from_swap(
                        db,
                        swap,
                        step_type=AttemptStepType.SWAP.value,
                        tx_hash=tx,
                        protocol=_swap_protocol(swap),
                    )
                )

        approve_hash = _approval_hash_from_swap(swap)
        if approve_hash and not _swap_missing_covered_by_chain_tx(
            db,
            swap=swap,
            chain_id=_chain_id_from_swap(swap),
            tx_hash=approve_hash,
            step_type=AttemptStepType.APPROVE.value,
        ):
            gaps.append(
                _anomaly(
                    "swap_missing_approval_attempt",
                    person_id=str(person_id),
                    reference_id=str(swap.id),
                )
            )

        intent = TransactionIntentRepository.find_by_linked(
            db,
            linked_table=LIFI_LINKED_TABLE,
            linked_id=swap.id,
        )
        if intent is not None:
            for step in (AttemptStepType.APPROVE.value, AttemptStepType.SWAP.value):
                idem = f"lifi:{swap.id}:{step if step != AttemptStepType.APPROVE.value else 'approve'}"
                attempt = OnchainTransactionAttemptRepository.find_by_composite_key(
                    db,
                    idempotency_key=idem,
                    step_type=step,
                )
                if attempt is not None and attempt.intent_id and attempt.intent_id != intent.id:
                    gaps.append(
                        _anomaly(
                            "lifi_attempt_intent_mismatch",
                            person_id=str(person_id),
                            reference_id=str(swap.id),
                            metadata={
                                "step_type": step,
                                "expected_intent_id": str(intent.id),
                                "attempt_intent_id": str(attempt.intent_id),
                            },
                        )
                    )

    grouped_swaps, _, duplicate_swap_groups = group_legacy_records_by_chain_tx(swap_swap_records)
    for group in duplicate_swap_groups:
        gaps.append(
            _anomaly(
                "legacy_records_grouped_under_single_attempt",
                severity="info",
                person_id=str(person_id),
                reference_id=group["canonical_reference_id"],
                metadata=group,
            )
        )
    for attempt in grouped_swaps:
        gaps.append(
            _anomaly(
                "swap_missing_swap_attempt",
                person_id=str(person_id),
                reference_id=attempt["reference_id"],
                metadata={
                    "tx_hash": attempt["tx_hash"],
                    "grouped_secondary_count": attempt["grouping"]["secondary_count"],
                    "legacy_records_in_group": attempt["grouping"]["legacy_records_in_group"],
                },
            )
        )

    vault_rows = db.execute(
        sa.text(
            """
            SELECT id, person_id, operation, status, tx_hash, idempotency_key,
                   integration_mode, tx_index, amount_raw, metadata_json, created_at, chain_id
            FROM onchain_vault_transactions
            WHERE person_id = :person_id
              AND integration_mode = ANY(:modes)
              AND status IN ('success', 'failed', 'reverted', 'pending')
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {
            "person_id": str(person_id),
            "modes": list(VAULT_INTEGRATION_MODES),
            "limit": vault_limit,
        },
    ).mappings().all()

    vault_missing_records: list[dict[str, Any]] = []
    for row in vault_rows:
        protocol = _integration_mode_to_protocol(row["integration_mode"])
        if protocol is None:
            continue
        operation = str(row["operation"] or "").strip().lower()
        if operation not in {
            AttemptStepType.APPROVE.value,
            AttemptStepType.DEPOSIT.value,
            AttemptStepType.WITHDRAW.value,
            AttemptStepType.AUTHORIZE.value,
            AttemptStepType.OPEN_LOAN.value,
        }:
            continue
        expected_step = _expected_vault_attempt_step_type(
            integration_mode=str(row.get("integration_mode") or ""),
            operation=operation,
            metadata_json=row.get("metadata_json"),
        )
        if _vault_legacy_covered_by_attempt(db, row=row, expected_step_type=expected_step):
            continue
        legacy = _legacy_record_from_vault(row, expected_step_type=expected_step)
        vault_missing_records.append(legacy)

    grouped_vaults, ungrouped_vaults, duplicate_vault_groups = group_legacy_records_by_chain_tx(
        vault_missing_records
    )
    for group in duplicate_vault_groups:
        gaps.append(
            _anomaly(
                "legacy_records_grouped_under_single_attempt",
                severity="info",
                person_id=str(person_id),
                reference_id=group["canonical_reference_id"],
                metadata=group,
            )
        )
    for attempt in grouped_vaults + [_ungrouped_to_attempt_candidate(r) for r in ungrouped_vaults]:
        gaps.append(
            _anomaly(
                "vault_tx_missing_attempt",
                person_id=str(person_id),
                reference_id=attempt["reference_id"],
                metadata={
                    "operation": attempt["step_type"],
                    "tx_hash": attempt.get("tx_hash"),
                    "grouped_secondary_count": attempt["grouping"]["secondary_count"],
                },
            )
        )

    for row in vault_rows:
        if str(row.get("status") or "").strip().lower() != "success":
            continue
        legacy_tx = str(row.get("tx_hash") or "").strip().lower()
        if not legacy_tx:
            continue
        operation = str(row["operation"] or "").strip().lower()
        if operation not in {
            AttemptStepType.APPROVE.value,
            AttemptStepType.DEPOSIT.value,
            AttemptStepType.WITHDRAW.value,
            AttemptStepType.AUTHORIZE.value,
            AttemptStepType.OPEN_LOAN.value,
        }:
            continue
        expected_step = _expected_vault_attempt_step_type(
            integration_mode=str(row.get("integration_mode") or ""),
            operation=operation,
            metadata_json=row.get("metadata_json"),
        )
        attempt = (
            db.query(OnchainTransactionAttempt)
            .filter(
                OnchainTransactionAttempt.linked_reference_id == row["id"],
                OnchainTransactionAttempt.step_type == expected_step,
            )
            .first()
        )
        if attempt is None:
            continue
        att_status = (attempt.status or "").strip().lower()
        att_tx = (attempt.tx_hash or "").strip().lower()
        if att_status != "confirmed" or att_tx != legacy_tx:
            gaps.append(
                _anomaly(
                    "vault_attempt_inconsistent_with_legacy",
                    person_id=str(person_id),
                    reference_id=str(row["id"]),
                    metadata={
                        "operation": operation,
                        "expected_step_type": expected_step,
                        "legacy_tx_hash": legacy_tx,
                        "attempt_id": str(attempt.id),
                        "attempt_status": attempt.status,
                        "attempt_tx_hash": attempt.tx_hash,
                    },
                )
            )

    attempts = (
        db.query(OnchainTransactionAttempt)
        .filter(OnchainTransactionAttempt.person_id == person_id)
        .order_by(OnchainTransactionAttempt.created_at.desc())
        .limit(200)
        .all()
    )
    for attempt in attempts:
        if attempt.protocol == AttemptProtocol.PRIVY.value:
            continue
        if attempt.linked_table == LINKED_SWAPS and attempt.linked_id:
            swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == attempt.linked_id).first()
            if swap is None:
                gaps.append(
                    _anomaly(
                        "attempt_orphan_swap",
                        person_id=str(person_id),
                        reference_id=str(attempt.id),
                        metadata={"linked_id": str(attempt.linked_id)},
                    )
                )
        elif attempt.linked_table == LINKED_VAULT and attempt.linked_reference_id:
            exists = db.execute(
                sa.text("SELECT 1 FROM onchain_vault_transactions WHERE id = :id"),
                {"id": attempt.linked_reference_id},
            ).fetchone()
            if exists is None:
                gaps.append(
                    _anomaly(
                        "attempt_orphan_vault_tx",
                        person_id=str(person_id),
                        reference_id=str(attempt.id),
                        metadata={"linked_reference_id": attempt.linked_reference_id},
                    )
                )

    return gaps


def _emit_reconciliation_gap_traces(
    db: Session,
    gaps: list[dict[str, Any]],
    *,
    source: str = "transaction_attempts.reconciliation.build_gap_report",
) -> None:
    if not gaps:
        return
    try:
        from services.transaction_trace.enums import TraceEventType
        from services.transaction_trace.transaction_trace_logger import log_transaction_trace

        for gap in gaps[:200]:
            meta = gap.get("metadata") if isinstance(gap.get("metadata"), dict) else {}
            log_transaction_trace(
                TraceEventType.RECONCILIATION_GAP_DETECTED,
                db=db,
                person_id=UUID(str(gap["person_id"])) if gap.get("person_id") else None,
                linked_reference_id=str(gap["reference_id"]) if gap.get("reference_id") else None,
                source=source,
                message=f"reconciliation gap: {gap.get('gap_type')}",
                metadata_json={
                    "gap_type": gap.get("gap_type"),
                    "severity": gap.get("severity", "gap"),
                    **meta,
                },
            )
    except Exception:
        pass


def build_gap_report(
    db: Session,
    *,
    person_id: UUID | None = None,
    person_limit: int = 100,
    swap_limit: int = 200,
    vault_limit: int = 200,
) -> dict[str, Any]:
    if not migration_171_ready(db):
        return {
            "ready": False,
            "dry_run": True,
            "message": "Table onchain_transaction_attempts absente (migration 171 requise).",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _summarize(gaps: list[dict[str, Any]]) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        blocking = 0
        informational = 0
        for gap in gaps:
            by_type[gap["gap_type"]] = by_type.get(gap["gap_type"], 0) + 1
            if gap.get("severity") == "info":
                informational += 1
            else:
                blocking += 1
        return {
            "total_entries": len(gaps),
            "blocking_gaps": blocking,
            "informational": informational,
            "by_type": by_type,
        }

    if person_id is not None:
        gaps = scan_attempt_gaps_for_person(
            db,
            person_id,
            swap_limit=swap_limit,
            vault_limit=vault_limit,
        )
        _emit_reconciliation_gap_traces(db, gaps)
        return {
            "ready": True,
            "dry_run": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "person_id": str(person_id),
            "summary": _summarize(gaps),
            "gaps": gaps,
            "excluded_from_phase2": [
                "privy_inbound_deposit (pas d'intent, attempt optionnel non requis)",
            ],
        }

    person_rows = db.execute(
        sa.text(
            """
            SELECT DISTINCT person_id FROM (
                SELECT person_id FROM person_wallet_swaps
                UNION
                SELECT person_id FROM onchain_vault_transactions
                WHERE integration_mode = ANY(:modes)
            ) t
            LIMIT :limit
            """
        ),
        {"modes": list(VAULT_INTEGRATION_MODES), "limit": person_limit},
    ).scalars().all()

    all_gaps: list[dict[str, Any]] = []
    for pid in person_rows:
        all_gaps.extend(
            scan_attempt_gaps_for_person(
                db,
                UUID(str(pid)),
                swap_limit=swap_limit,
                vault_limit=vault_limit,
            )
        )

    _emit_reconciliation_gap_traces(db, all_gaps)
    return {
        "ready": True,
        "dry_run": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "persons_scanned": len(person_rows),
        "summary": _summarize(all_gaps),
        "gaps": all_gaps[:500],
        "excluded_from_phase2": [
            "privy_inbound_deposit (pas d'intent, attempt optionnel non requis)",
        ],
    }
