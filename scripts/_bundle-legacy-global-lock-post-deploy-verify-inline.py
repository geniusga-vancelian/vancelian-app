"""Post-deploy neutre — Global Lock legacy Bundle · flag OFF · aucun lock actif."""
from __future__ import annotations

import json
import os

from sqlalchemy import text

from database import SessionLocal
from services.product_locks.enums import ProductLockScope

BASELINE_PE_ATOMS = int(os.environ.get("BUNDLE_BASELINE_PE_ATOMS", "19"))
BASELINE_COST_BASIS = int(os.environ.get("BUNDLE_BASELINE_COST_BASIS", "67"))
BASELINE_LIFI_LEGS = int(os.environ.get("BUNDLE_BASELINE_LIFI_LEGS", "131"))


def _flag_on(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def main() -> None:
    db = SessionLocal()
    try:
        financial_tx_active = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_product_locks
                WHERE scope = :scope
                  AND asset = 'GLOBAL'
                  AND status = 'active'
                  AND released_at IS NULL
                """
            ),
            {"scope": ProductLockScope.FINANCIAL_TRANSACTION.value},
        ).scalar()

        pe = db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
        cb = db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
        legs = db.execute(
            text(
                "SELECT COUNT(*) FROM person_wallet_deposits WHERE idempotency_key LIKE 'lifi-swap:%'"
            )
        ).scalar()

        out = {
            "phase": "bundle_legacy_global_lock_post_deploy_verify",
            "flags": {
                "GLOBAL_USER_TRANSACTION_LOCK_ENABLED": os.environ.get(
                    "GLOBAL_USER_TRANSACTION_LOCK_ENABLED"
                ),
            },
            "flag_global_lock_off": not _flag_on("GLOBAL_USER_TRANSACTION_LOCK_ENABLED"),
            "financial_transaction_global_locks_active": financial_tx_active,
            "pe_atoms": pe,
            "cost_basis_entries": cb,
            "bundle_lifi_legs": legs,
            "baseline_pe_atoms": BASELINE_PE_ATOMS,
            "baseline_cost_basis": BASELINE_COST_BASIS,
            "baseline_lifi_legs": BASELINE_LIFI_LEGS,
            "all_checks_pass": (
                not _flag_on("GLOBAL_USER_TRANSACTION_LOCK_ENABLED")
                and financial_tx_active == 0
                and pe == BASELINE_PE_ATOMS
                and cb == BASELINE_COST_BASIS
                and legs == BASELINE_LIFI_LEGS
            ),
        }
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
