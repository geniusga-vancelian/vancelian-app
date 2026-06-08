"""Test contrôlé Global User Transaction Lock V1 — flag ON job only · TD flags OFF."""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from database import SessionLocal
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.onchain_indexer.models import TransactionIntent
from services.product_locks.enums import ProductLockScope
from services.product_locks.exceptions import (
    TRANSACTION_IN_PROGRESS_USER_MESSAGE,
    ProductLockConflict,
)
from services.product_locks.global_user_transaction_lock import (
    acquire_global_user_transaction_lock,
    release_global_user_transaction_lock,
    transaction_in_progress_409_from_conflict,
)

PILOT_EMAIL = os.environ.get("GLOBAL_LOCK_PILOT_EMAIL", "gaelitier@gmail.com")
# Compte pilote prod (aligné GO_BUNDLE_B3C / GO_PILOT)
PERSON_ID = uuid.UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
PE_CLIENT_ID = uuid.UUID("080358a8-4519-4acf-b5da-25485446c967")
BASELINE_PE = int(os.environ.get("BUNDLE_BASELINE_PE_ATOMS", "19"))
BASELINE_CB = int(os.environ.get("BUNDLE_BASELINE_COST_BASIS", "67"))
BASELINE_LEGS = int(os.environ.get("BUNDLE_BASELINE_LIFI_LEGS", "131"))


def _expires_in(seconds: int = 3600) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _resolve_pilot(db):
    env_person = (os.environ.get("GLOBAL_LOCK_PERSON_ID") or "").strip()
    env_client = (os.environ.get("GLOBAL_LOCK_PE_CLIENT_ID") or "").strip()
    person_id = uuid.UUID(env_person) if env_person else PERSON_ID
    pe_client_id = uuid.UUID(env_client) if env_client else PE_CLIENT_ID
    row = db.execute(
        text("SELECT 1 FROM pe_clients WHERE id = :cid AND person_id = :pid LIMIT 1"),
        {"cid": pe_client_id, "pid": person_id},
    ).fetchone()
    if row is None:
        raise RuntimeError(
            f"pilot_not_found person_id={person_id} pe_client_id={pe_client_id} email={PILOT_EMAIL}"
        )
    return person_id, pe_client_id


def _ensure_wallet(db, person_id, pe_client_id):
    row = db.execute(
        text(
            """
            SELECT id FROM person_crypto_wallets
            WHERE person_id = :pid
            ORDER BY created_at ASC
            LIMIT 1
            """
        ),
        {"pid": person_id},
    ).fetchone()
    if row is not None:
        return row[0]
    return upsert_person_crypto_wallet(
        db,
        person_id=person_id,
        pe_client_id=pe_client_id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=f"0x{uuid.uuid4().hex[:40]}",
    )


def _intent(db, person_id: uuid.UUID) -> TransactionIntent:
    row = TransactionIntent(
        person_id=person_id,
        product_type="lifi_swap",
        operation_type="swap",
        idempotency_key=f"global-lock-pilot:{uuid.uuid4()}",
        status="created",
    )
    db.add(row)
    db.flush()
    return row


def _baseline(db) -> dict:
    pe = db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
    cb = db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
    legs = db.execute(
        text(
            "SELECT COUNT(*) FROM person_wallet_deposits WHERE idempotency_key LIKE 'lifi-swap:%'"
        )
    ).scalar()
    active = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM transaction_product_locks
            WHERE scope = :scope AND asset = 'GLOBAL' AND status = 'active'
              AND released_at IS NULL
            """
        ),
        {"scope": ProductLockScope.FINANCIAL_TRANSACTION.value},
    ).scalar()
    dead_letter = db.execute(
        text("SELECT COUNT(*) FROM transaction_outbox WHERE status = 'dead_letter'")
    ).scalar()
    completed = db.execute(
        text(
            """
            SELECT COUNT(*) FROM transaction_intents
            WHERE LOWER(status) = 'completed' OR current_phase = 'COMPLETED'
            """
        )
    ).scalar()
    return {
        "pe_atoms": pe,
        "cost_basis": cb,
        "lifi_swap_legs": legs,
        "active_financial_transaction_locks": active,
        "dead_letter": dead_letter,
        "completed": completed,
    }


def main() -> None:
    mode = (os.environ.get("GLOBAL_LOCK_TEST_MODE") or "full").strip().lower()
    test_run_id = os.environ.get("GLOBAL_LOCK_TEST_RUN_ID") or uuid.uuid4().hex
    os.environ["GLOBAL_USER_TRANSACTION_LOCK_ENABLED"] = "true"

    db = SessionLocal()
    try:
        person_id, pe_client_id = _resolve_pilot(db)
        _ensure_wallet(db, person_id, pe_client_id)
        before = _baseline(db)

        intent_a_id = os.environ.get("GLOBAL_LOCK_INTENT_A_ID")
        intent_b_id = os.environ.get("GLOBAL_LOCK_INTENT_B_ID")

        result: dict = {
            "phase": "global_user_transaction_lock_controlled_test",
            "test_run_id": test_run_id,
            "mode": mode,
            "pilot_email": PILOT_EMAIL,
            "person_id": str(person_id),
            "baseline_before": before,
        }

        if mode in ("full", "acquire_a", "setup"):
            intent_a = _intent(db, person_id) if not intent_a_id else db.get(
                TransactionIntent, uuid.UUID(intent_a_id)
            )
            acquire_a = acquire_global_user_transaction_lock(
                db,
                person_id=person_id,
                intent_id=intent_a.id,
                expires_at=_expires_in(),
                reason="controlled_test_acquire_a",
            )
            db.commit()
            result["intent_a_id"] = str(intent_a.id)
            result["acquire_a"] = {
                "acquired": acquire_a.acquired,
                "idempotent": acquire_a.idempotent,
            }

        if mode in ("full", "acquire_b_conflict"):
            intent_a = db.get(TransactionIntent, uuid.UUID(result.get("intent_a_id") or intent_a_id))
            if intent_a is None:
                raise RuntimeError("intent_a_required_for_acquire_b_conflict")
            intent_b = _intent(db, person_id)
            conflict_ok = False
            mapped_ok = False
            try:
                acquire_global_user_transaction_lock(
                    db,
                    person_id=person_id,
                    intent_id=intent_b.id,
                    expires_at=_expires_in(),
                    reason="controlled_test_acquire_b",
                )
            except ProductLockConflict as exc:
                mapped = transaction_in_progress_409_from_conflict(
                    exc,
                    existing_reason="controlled_test_acquire_a",
                    requested_reason="controlled_test_acquire_b",
                )
                conflict_ok = True
                mapped_ok = (
                    mapped.error_code == "transaction_in_progress"
                    and str(mapped) == TRANSACTION_IN_PROGRESS_USER_MESSAGE
                    and mapped.existing_intent_id == intent_a.id
                    and mapped.requested_intent_id == intent_b.id
                )
                result["intent_b_id"] = str(intent_b.id)
                result["acquire_b_conflict"] = {
                    "conflict_raised": conflict_ok,
                    "error_code": mapped.error_code,
                    "user_message": str(mapped),
                    "mapped_ok": mapped_ok,
                }
            db.rollback()

        if mode in ("full", "release_a"):
            iid = result.get("intent_a_id") or intent_a_id
            if not iid:
                raise RuntimeError("intent_a_required_for_release")
            release = release_global_user_transaction_lock(
                db,
                intent_id=uuid.UUID(iid),
                reason="controlled_test_release_a",
            )
            db.commit()
            result["release_a"] = {
                "released": release.released,
                "idempotent": release.idempotent,
            }

        if mode in ("full", "acquire_b_ok"):
            intent_b = _intent(db, person_id) if not intent_b_id else db.get(
                TransactionIntent, uuid.UUID(intent_b_id)
            )
            acquire_b = acquire_global_user_transaction_lock(
                db,
                person_id=person_id,
                intent_id=intent_b.id,
                expires_at=_expires_in(),
                reason="controlled_test_acquire_b_after_release",
            )
            db.commit()
            result["intent_b_id"] = str(intent_b.id)
            result["acquire_b_ok"] = {
                "acquired": acquire_b.acquired,
                "idempotent": acquire_b.idempotent,
            }
            release_cleanup = release_global_user_transaction_lock(
                db,
                intent_id=intent_b.id,
                reason="controlled_test_cleanup",
            )
            db.commit()
            result["cleanup_release_b"] = {
                "released": release_cleanup.released,
            }

        after = _baseline(db)
        result["baseline_after"] = after
        result["checks"] = {
            "acquire_a_success": result.get("acquire_a", {}).get("acquired") is True,
            "acquire_b_conflict": result.get("acquire_b_conflict", {}).get("conflict_raised") is True,
            "error_code_transaction_in_progress": (
                result.get("acquire_b_conflict", {}).get("error_code") == "transaction_in_progress"
            ),
            "release_a_success": result.get("release_a", {}).get("released") is True,
            "acquire_b_after_release_success": result.get("acquire_b_ok", {}).get("acquired") is True,
            "active_locks_zero_end": after["active_financial_transaction_locks"] == 0,
            "pe_unchanged": after["pe_atoms"] == BASELINE_PE,
            "cb_unchanged": after["cost_basis"] == BASELINE_CB,
            "legs_unchanged": after["lifi_swap_legs"] == BASELINE_LEGS,
            "dead_letter_zero": after["dead_letter"] == 0,
            "completed_zero": after["completed"] == 0,
        }
        result["all_checks_pass"] = (
            before["pe_atoms"] == BASELINE_PE
            and after["pe_atoms"] == BASELINE_PE
            and before["cost_basis"] == BASELINE_CB
            and after["cost_basis"] == BASELINE_CB
            and before["lifi_swap_legs"] == BASELINE_LEGS
            and after["lifi_swap_legs"] == BASELINE_LEGS
            and after["dead_letter"] == 0
            and after["completed"] == 0
            and (
                mode != "full"
                or all(result["checks"].values())
            )
        )
        print(json.dumps(result, indent=2, default=str))
        if not result["all_checks_pass"]:
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
