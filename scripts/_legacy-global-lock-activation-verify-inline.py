"""Vérification pré/post activation GLOBAL_USER_TRANSACTION_LOCK_ENABLED (lecture seule)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from sqlalchemy import text

from database import SessionLocal
from services.product_locks.enums import ProductLockScope

PERSON_ID = os.environ.get(
    "VERIFY_PERSON_ID",
    "8b0e0044-f1ef-47a5-99d4-370598a77492",
)
HEALTH_URL = os.environ.get("ARQUANTIX_HEALTH_URL", "https://arquantix.com/health")
PE_BASELINE = int(os.environ.get("INCIDENT_PE_BASELINE", "19"))
CB_BASELINE = int(os.environ.get("INCIDENT_CB_BASELINE", "76"))
LEGS_BASELINE = int(os.environ.get("INCIDENT_LEGS_BASELINE", "131"))


def _flag_on(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _health_ok() -> tuple[bool, int | None, str | None]:
    try:
        req = urllib.request.Request(HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200, resp.status, None
    except urllib.error.HTTPError as exc:
        return False, exc.code, str(exc)
    except Exception as exc:
        return False, None, str(exc)


def main() -> None:
    mode = (os.environ.get("LEGACY_GLOBAL_LOCK_VERIFY_MODE") or "pre_activation").strip()
    db = SessionLocal()
    try:
        health_ok, health_status, health_error = _health_ok()
        financial_tx_active = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_product_locks
                WHERE person_id = :pid
                  AND scope = :scope
                  AND asset = 'GLOBAL'
                  AND status = 'active'
                  AND released_at IS NULL
                """
            ),
            {"pid": PERSON_ID, "scope": ProductLockScope.FINANCIAL_TRANSACTION.value},
        ).scalar()

        stuck_parents = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE person_id = :pid
                  AND product_type = 'bundle_invest'
                  AND LOWER(status) IN (
                    'partial', 'awaiting_signature', 'submitted', 'partial_pending', 'pending_signature'
                  )
                """
            ),
            {"pid": PERSON_ID},
        ).scalar()

        dead_letter = db.execute(
            text("SELECT COUNT(*) FROM transaction_outbox WHERE status = 'dead_letter'")
        ).scalar()
        pe = db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
        cb = db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
        legs = db.execute(
            text(
                "SELECT COUNT(*) FROM person_wallet_deposits WHERE idempotency_key LIKE 'lifi-swap:%'"
            )
        ).scalar()

        flag_on = _flag_on("GLOBAL_USER_TRANSACTION_LOCK_ENABLED")
        pre_ready = (
            not flag_on
            and financial_tx_active == 0
            and stuck_parents == 0
            and dead_letter == 0
        )
        post_ready = (
            flag_on
            and health_ok
            and financial_tx_active == 0
            and dead_letter == 0
        )

        out = {
            "phase": "legacy_global_lock_activation_verify",
            "mode": mode,
            "person_id": PERSON_ID,
            "health_ok": health_ok,
            "health_status": health_status,
            "health_error": health_error,
            "flags": {
                "GLOBAL_USER_TRANSACTION_LOCK_ENABLED": os.environ.get(
                    "GLOBAL_USER_TRANSACTION_LOCK_ENABLED"
                ),
            },
            "flag_global_lock_on": flag_on,
            "financial_transaction_global_locks_active": financial_tx_active,
            "stuck_bundle_parents": stuck_parents,
            "dead_letter_count": dead_letter,
            "pe_atoms": pe,
            "cost_basis_executions": cb,
            "lifi_swap_deposits": legs,
            "baseline_pe": PE_BASELINE,
            "baseline_cb": CB_BASELINE,
            "baseline_legs": LEGS_BASELINE,
            "pre_activation_ready": pre_ready,
            "post_activation_stable": post_ready,
            "go_activation": pre_ready if mode == "pre_activation" else None,
            "go_post_activation_audit": post_ready if mode == "post_activation" else None,
        }
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
