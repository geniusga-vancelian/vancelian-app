"""Post-deploy neutre B5 — bundle parent controller · flags OFF · aucun runtime."""
from __future__ import annotations

import inspect
import json
import os
import urllib.error
import urllib.request

from sqlalchemy import text

from database import SessionLocal
from services.product_locks.enums import ProductLockScope
from services.transaction_intents.enums import IntentProductType, IntentRole

MERGE_SHA = os.environ.get("BUNDLE_B5_MERGE_SHA", "pending")
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

        b5_auto_reconciled = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE product_type = :product
                  AND intent_role = :role
                  AND metadata_json->>'phase' = 'RECONCILED'
                  AND metadata_json ? 'bundle_parent_controller'
                """
            ),
            {
                "product": IntentProductType.BUNDLE_INVEST.value,
                "role": IntentRole.PARENT.value,
            },
        ).scalar()

        pe = db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
        cb = db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
        legs = db.execute(
            text(
                "SELECT COUNT(*) FROM person_wallet_deposits WHERE idempotency_key LIKE 'lifi-swap:%'"
            )
        ).scalar()
        dead_letter = db.execute(
            text("SELECT COUNT(*) FROM transaction_outbox WHERE status = 'dead_letter'")
        ).scalar()
        completed = db.execute(
            text(
                """
                SELECT COUNT(*) FROM transaction_intents
                WHERE LOWER(status) = 'completed' OR current_phase = 'COMPLETED'
                   OR metadata_json->>'phase' = 'COMPLETED'
                """
            )
        ).scalar()

        health_ok, health_status, health_error = _health_ok()

        module_imported = False
        reconcile_callable = False
        module_src = ""
        orchestrator_src = ""
        worker_src = ""
        try:
            from services.portfolio_engine.bundles.event_driven.bundle_parent_controller import (  # noqa: F401
                reconcile_bundle_parent_idempotently,
            )

            import services.portfolio_engine.bundles.event_driven.bundle_parent_controller as b5

            module_imported = True
            reconcile_callable = callable(reconcile_bundle_parent_idempotently)
            module_src = inspect.getsource(b5)
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
            "reconcile_bundle_parent_idempotently" in orchestrator_src
            or "bundle_parent_controller" in orchestrator_src
            or "reconcile_bundle_parent_idempotently" in worker_src
            or "bundle_parent_controller" in worker_src
        )

        flags = {
            "BUNDLE_PARENT_CONTROLLER_ENABLED": os.environ.get("BUNDLE_PARENT_CONTROLLER_ENABLED"),
            "BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED": os.environ.get("BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED"),
            "GLOBAL_USER_TRANSACTION_LOCK_ENABLED": os.environ.get("GLOBAL_USER_TRANSACTION_LOCK_ENABLED"),
            "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED": os.environ.get("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED"),
        }

        forbidden_in_module = [
            token
            for token in (
                "settle_bundle_leg_idempotently",
                "apply_rebalance_buy_atoms",
                "release_global_user_transaction_lock",
                "PersonWalletSwap",
            )
            if token in module_src
        ]

        checks = {
            "health_ok": health_ok,
            "flag_b5_off": not (os.environ.get("BUNDLE_PARENT_CONTROLLER_ENABLED") or "").strip(),
            "module_present": module_imported,
            "reconcile_callable": reconcile_callable,
            "no_runtime_wiring": not runtime_wired,
            "no_forbidden_settlement_calls": len(forbidden_in_module) == 0,
            "b5_auto_reconciled_zero": b5_auto_reconciled == 0,
            "pe_baseline": pe == BASELINE_PE_ATOMS,
            "cb_baseline": cb == BASELINE_COST_BASIS,
            "legs_baseline": legs == BASELINE_LIFI_LEGS,
            "active_financial_locks_zero": financial_tx_locks == 0,
            "dead_letter_zero": dead_letter == 0,
            "completed_zero": completed == 0,
        }

        result = {
            "phase": "bundle_b5_post_deploy_verify",
            "merge_sha": MERGE_SHA,
            "health": {
                "url": HEALTH_URL,
                "ok": health_ok,
                "status": health_status,
                "error": health_error,
            },
            "alembic_version": str(alembic),
            "flags": flags,
            "neutralite": {
                "financial_transaction_locks_active": financial_tx_locks,
                "b5_auto_reconciled_parents": b5_auto_reconciled,
                "pe_atoms": pe,
                "cost_basis": cb,
                "lifi_swap_legs": legs,
                "dead_letter": dead_letter,
                "completed": completed,
            },
            "runtime_wiring": {
                "bundle_b5_module_present": module_imported,
                "reconcile_callable": reconcile_callable,
                "orchestrator_wired": "bundle_parent_controller" in orchestrator_src,
                "worker_wired": "bundle_parent_controller" in worker_src,
            },
            "checks": checks,
            "all_checks_pass": all(checks.values()),
        }
        print(json.dumps(result, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
