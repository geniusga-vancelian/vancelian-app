"""Vérification prod post-deploy W3/W4 (#38 · migration 174)."""
import json
import os

from sqlalchemy import text

from database import SessionLocal

PERSON_ID = "8b0e0044-f1ef-47a5-99d4-370598a77492"
BASELINE = {"pe": 19, "cb": 66, "legs": 116}


def main() -> None:
    db = SessionLocal()
    try:
        alembic = db.execute(text("SELECT version_num FROM alembic_version")).scalar()

        index_row = db.execute(
            text(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename = 'transaction_outbox'
                  AND indexname = 'uq_outbox_intent_event_type'
                """
            )
        ).fetchone()

        outbox_pending = db.execute(
            text("SELECT COUNT(*) FROM transaction_outbox WHERE status = 'pending'")
        ).scalar()
        intent_settle = db.execute(
            text("SELECT COUNT(*) FROM transaction_outbox WHERE event_type = 'intent.settle'")
        ).scalar()
        intent_settle_pending = db.execute(
            text(
                "SELECT COUNT(*) FROM transaction_outbox "
                "WHERE event_type = 'intent.settle' AND status = 'pending'"
            )
        ).scalar()

        econ = {
            "pe": db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar(),
            "cb": db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar(),
            "legs": db.execute(
                text(
                    "SELECT COUNT(*) FROM person_wallet_deposits "
                    "WHERE idempotency_key LIKE 'lifi-swap:%'"
                )
            ).scalar(),
        }

        other_users = db.execute(
            text(
                """
                SELECT COUNT(*) FROM transaction_intents
                WHERE metadata_json->>'phase2_orchestrator' = 'true'
                  AND person_id <> :pid
                """
            ),
            {"pid": PERSON_ID},
        ).scalar()

        orchestrator_intents = db.execute(
            text(
                """
                SELECT COUNT(*) FROM transaction_intents
                WHERE metadata_json->>'phase2_orchestrator' = 'true'
                  AND person_id = :pid
                """
            ),
            {"pid": PERSON_ID},
        ).scalar()

        dead_letter = db.execute(
            text("SELECT COUNT(*) FROM transaction_outbox WHERE status = 'dead_letter'")
        ).scalar()

        result = {
            "alembic_version": alembic,
            "migration_174_ok": int(str(alembic)) >= 174 if alembic and str(alembic).isdigit() else False,
            "unique_index": {
                "present": index_row is not None,
                "indexname": index_row[0] if index_row else None,
                "indexdef": index_row[1] if index_row else None,
            },
            "outbox": {
                "pending_total": outbox_pending,
                "intent_settle_total": intent_settle,
                "intent_settle_pending": intent_settle_pending,
                "dead_letter": dead_letter,
            },
            "economic": econ,
            "economic_baseline_match": econ == BASELINE,
            "orchestrator_intents_pilot": orchestrator_intents,
            "other_users_orchestrator": other_users,
            "flags_runtime_note": "read from ECS task definition (not DB)",
        }
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
