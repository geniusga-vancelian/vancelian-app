"""Post-deploy neutre Global User Transaction Lock V1 — flag OFF · aucun runtime."""
from __future__ import annotations

import inspect
import json
import os
import urllib.error
import urllib.request

from sqlalchemy import text

from database import SessionLocal
from services.product_locks.enums import ProductLockScope
from services.product_locks.global_user_transaction_lock_config import (
    global_user_transaction_lock_enabled,
)

MERGE_SHA = os.environ.get("GLOBAL_LOCK_MERGE_SHA", "pending")
BASELINE_PE_ATOMS = int(os.environ.get("BUNDLE_BASELINE_PE_ATOMS", "19"))
BASELINE_COST_BASIS = int(os.environ.get("BUNDLE_BASELINE_COST_BASIS", "67"))
BASELINE_LIFI_LEGS = int(os.environ.get("BUNDLE_BASELINE_LIFI_LEGS", "131"))
HEALTH_URL = os.environ.get("ARQUANTIX_HEALTH_URL", "https://arquantix.com/health")


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
    db = SessionLocal()
    try:
        alembic = db.execute(text("SELECT version_num FROM alembic_version")).scalar()

        financial_tx_locks = db.execute(
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

        flag_env = os.environ.get("GLOBAL_USER_TRANSACTION_LOCK_ENABLED", "").strip().lower()
        flag_bundle_funding = os.environ.get("BUNDLE_FUNDING_HANDLER_ENABLED", "").strip().lower()
        flag_bundle_settlement = os.environ.get("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED", "").strip().lower()
        health_ok, health_status, health_error = _health_ok()

        module_imported = False
        acquire_callable = False
        user_message_ok = False
        module_src = ""
        orchestrator_src = ""
        worker_src = ""
        try:
            from services.product_locks.global_user_transaction_lock import (  # noqa: F401
                acquire_global_user_transaction_lock,
            )
            from services.product_locks.exceptions import (
                TRANSACTION_IN_PROGRESS_USER_MESSAGE,
                TransactionInProgress409,
            )

            import services.product_locks.global_user_transaction_lock as glm

            module_imported = True
            acquire_callable = callable(acquire_global_user_transaction_lock)
            user_message_ok = (
                TRANSACTION_IN_PROGRESS_USER_MESSAGE
                == "A transaction is already in progress. Please wait until it is completed."
            )
            module_src = inspect.getsource(glm)
            try:
                from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

                orchestrator_src = inspect.getsource(BundleOrchestrator)
            except Exception:
                orchestrator_src = ""
            try:
                import services.transaction_outbox.settlement_worker as sw

                worker_src = inspect.getsource(sw)
            except Exception:
                worker_src = ""
        except Exception as exc:
            module_src = str(exc)

        runtime_wired = (
            "acquire_global_user_transaction_lock" in orchestrator_src
            or "global_user_transaction_lock" in orchestrator_src
            or "acquire_global_user_transaction_lock" in worker_src
        )

        git_sha = (
            os.environ.get("GIT_SHA")
            or os.environ.get("GIT_COMMIT")
            or os.environ.get("SOURCE_VERSION")
        )

        result = {
            "phase": "global_user_transaction_lock_post_deploy_verify",
            "merge_sha": MERGE_SHA,
            "deploy_git_sha": git_sha,
            "health": {
                "url": HEALTH_URL,
                "ok": health_ok,
                "status": health_status,
                "error": health_error,
            },
            "alembic_version": str(alembic),
            "flags": {
                "GLOBAL_USER_TRANSACTION_LOCK_ENABLED": flag_env or None,
                "global_user_transaction_lock_enabled()": global_user_transaction_lock_enabled(),
                "BUNDLE_FUNDING_HANDLER_ENABLED": flag_bundle_funding or None,
                "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED": flag_bundle_settlement or None,
            },
            "neutralite": {
                "active_financial_transaction_locks": financial_tx_locks,
                "pe_atoms": pe,
                "pe_atoms_expected": BASELINE_PE_ATOMS,
                "cost_basis": cb,
                "cost_basis_expected": BASELINE_COST_BASIS,
                "lifi_swap_legs": legs,
                "lifi_swap_legs_expected": BASELINE_LIFI_LEGS,
            },
            "runtime_wiring": {
                "global_lock_module_present": module_imported,
                "acquire_global_lock_callable": acquire_callable,
                "transaction_in_progress_user_message_ok": user_message_ok,
                "module_no_worker_settlement_imports": all(
                    token not in module_src.lower()
                    for token in (
                        "transaction_outbox",
                        "settlement_worker",
                        "bundle_leg_settlement_handler",
                        "services.settlement.settle",
                    )
                ),
                "orchestrator_worker_calls_global_lock": runtime_wired,
            },
            "all_checks_pass": (
                health_ok
                and str(alembic) == "176"
                and flag_env not in ("1", "true", "yes", "on")
                and not global_user_transaction_lock_enabled()
                and financial_tx_locks == 0
                and pe == BASELINE_PE_ATOMS
                and cb == BASELINE_COST_BASIS
                and legs == BASELINE_LIFI_LEGS
                and module_imported
                and acquire_callable
                and user_message_ok
                and not runtime_wired
            ),
        }
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
