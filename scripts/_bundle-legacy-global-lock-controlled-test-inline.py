"""Controlled test — Global Lock legacy Bundle (flag ON · job ECS only)."""
from __future__ import annotations

import json
import os
import uuid

from sqlalchemy.orm import Session

from database import PersonCryptoWallet, SessionLocal
from services.auth.person_identity_bridge import PROVIDER_PRIVY, upsert_person_crypto_wallet
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.legacy_bundle_global_lock import (
    acquire_legacy_bundle_global_lock_or_raise,
    release_legacy_bundle_global_lock,
    transaction_in_progress_response_body,
)
from services.product_locks.exceptions import TransactionInProgress409
from services.product_locks.global_user_transaction_lock import (
    find_active_global_user_transaction_lock,
)

PERSON_ID = os.environ.get(
    "CONTROLLED_TEST_PERSON_ID",
    "8b0e0044-f1ef-47a5-99d4-370598a77492",
)


def _intent(db: Session, person_id: uuid.UUID) -> TransactionIntent:
    row = TransactionIntent(
        person_id=person_id,
        product_type="bundle_invest",
        operation_type="invest",
        idempotency_key=f"legacy-global-lock-ctrl-{uuid.uuid4()}",
        status="created",
    )
    db.add(row)
    db.flush()
    return row


def main() -> None:
    os.environ["GLOBAL_USER_TRANSACTION_LOCK_ENABLED"] = "true"
    person_id = uuid.UUID(PERSON_ID)
    db: Session = SessionLocal()
    try:
        wallet = (
            db.query(PersonCryptoWallet)
            .filter(PersonCryptoWallet.person_id == person_id)
            .first()
        )
        if wallet is None:
            raise RuntimeError(f"no wallet for person_id={person_id}")

        intent_a = _intent(db, person_id)
        intent_b = _intent(db, person_id)

        first = acquire_legacy_bundle_global_lock_or_raise(
            db, person_id=person_id, intent_id=intent_a.id,
        )
        db.flush()

        conflict_body = None
        try:
            acquire_legacy_bundle_global_lock_or_raise(
                db, person_id=person_id, intent_id=intent_b.id,
            )
            got_409 = False
        except TransactionInProgress409 as exc:
            got_409 = True
            conflict_body = transaction_in_progress_response_body(exc)

        resume = acquire_legacy_bundle_global_lock_or_raise(
            db, person_id=person_id, intent_id=intent_a.id,
        )
        db.flush()

        release_legacy_bundle_global_lock(db, intent_id=intent_a.id)
        db.flush()

        second = acquire_legacy_bundle_global_lock_or_raise(
            db, person_id=person_id, intent_id=intent_b.id,
        )
        db.flush()
        release_legacy_bundle_global_lock(db, intent_id=intent_b.id)
        db.commit()

        out = {
            "phase": "bundle_legacy_global_lock_controlled_test",
            "person_id": str(person_id),
            "first_acquire": {
                "acquired": first.acquired if first else None,
                "intent_id": str(intent_a.id),
            },
            "second_different_intent_409": got_409,
            "conflict_body": conflict_body,
            "resume_idempotent": resume.idempotent if resume else None,
            "after_release_second_allowed": second.acquired if second else None,
            "active_lock_after_cleanup": find_active_global_user_transaction_lock(
                db, person_id=person_id,
            ),
            "go": got_409 and (resume.idempotent if resume else False),
        }
        print(json.dumps(out, indent=2, default=str))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
