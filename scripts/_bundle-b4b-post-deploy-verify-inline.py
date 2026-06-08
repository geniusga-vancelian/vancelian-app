"""Post-deploy neutre B4b — bundle minimal runtime bridge · flags OFF · aucun runtime."""
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

MERGE_SHA = os.environ.get("BUNDLE_B4B_MERGE_SHA", "pending")
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


def _flag_on(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


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

        b4b_bridge_auto = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE metadata_json ? 'bundle_b4b_bridge'
                """
            )
        ).scalar()

        b4b_linked_swaps_auto = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE metadata_json ? 'bundle_b4b_bridge'
                  AND linked_table = 'person_wallet_swaps'
                  AND linked_id IS NOT NULL
                """
            )
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
                """
            )
        ).scalar()

        health_ok, health_status, health_error = _health_ok()

        module_imported = False
        bridge_callable = False
        module_src = ""
        orchestrator_src = ""
        worker_src = ""
        try:
            from services.portfolio_engine.bundles.event_driven.bundle_b4b_runtime_bridge import (  # noqa: F401
                run_bundle_b4b_minimal_bridge,
            )

            import services.portfolio_engine.bundles.event_driven.bundle_b4b_runtime_bridge as b4b

            module_imported = True
            bridge_callable = callable(run_bundle_b4b_minimal_bridge)
            module_src = inspect.getsource(b4b)
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
            "run_bundle_b4b_minimal_bridge" in orchestrator_src
            or "bundle_b4b_runtime_bridge" in orchestrator_src
            or "run_bundle_b4b_minimal_bridge" in worker_src
            or "bundle_b4b_runtime_bridge" in worker_src
        )

        flags = {
            "BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED": os.environ.get("BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED"),
            "GLOBAL_USER_TRANSACTION_LOCK_ENABLED": os.environ.get("GLOBAL_USER_TRANSACTION_LOCK_ENABLED"),
            "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED": os.environ.get("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED"),
            "BUNDLE_FUNDING_HANDLER_ENABLED": os.environ.get("BUNDLE_FUNDING_HANDLER_ENABLED"),
            "BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED": os.environ.get("BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED"),
        }

        git_sha = (
            os.environ.get("GIT_SHA")
            or os.environ.get("GIT_COMMIT")
            or os.environ.get("SOURCE_VERSION")
        )

        result = {
            "phase": "bundle_b4b_post_deploy_verify",
            "merge_sha": MERGE_SHA,
            "deploy_git_sha": git_sha,
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
                "bundle_b4b_bridge_metadata_auto": b4b_bridge_auto,
                "bundle_b4b_linked_swaps_auto": b4b_linked_swaps_auto,
                "pe_atoms": pe,
                "pe_atoms_expected": BASELINE_PE_ATOMS,
                "cost_basis": cb,
                "cost_basis_expected": BASELINE_COST_BASIS,
                "lifi_swap_legs": legs,
                "lifi_swap_legs_expected": BASELINE_LIFI_LEGS,
                "dead_letter": dead_letter,
                "completed": completed,
            },
            "runtime_wiring": {
                "bundle_b4b_module_present": module_imported,
                "run_bundle_b4b_minimal_bridge_callable": bridge_callable,
                "module_no_controller_imports": all(
                    token not in module_src
                    for token in ("bundle_controller", "BundleController", "finalize_bundle")
                ),
                "orchestrator_worker_calls_bridge": runtime_wired,
            },
            "all_checks_pass": (
                health_ok
                and str(alembic) == "176"
                and not _flag_on("BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED")
                and not _flag_on("GLOBAL_USER_TRANSACTION_LOCK_ENABLED")
                and not _flag_on("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED")
                and not _flag_on("BUNDLE_FUNDING_HANDLER_ENABLED")
                and not _flag_on("BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED")
                and financial_tx_locks == 0
                and b4b_bridge_auto == 0
                and pe == BASELINE_PE_ATOMS
                and cb == BASELINE_COST_BASIS
                and legs == BASELINE_LIFI_LEGS
                and dead_letter == 0
                and completed == 0
                and module_imported
                and bridge_callable
                and not runtime_wired
            ),
        }
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
