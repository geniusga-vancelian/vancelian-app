"""Post-deploy neutre B4a — bundle child factory · flag OFF · aucun runtime."""
from __future__ import annotations

import inspect
import json
import os
import urllib.error
import urllib.request

from sqlalchemy import text

from database import SessionLocal
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.transaction_intents.enums import IntentProductType, IntentRole

MERGE_SHA = "8711c92d"
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

        bundle_scope_locks = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_product_locks
                WHERE scope = 'bundle'
                  AND product_type = 'bundle_invest'
                """
            )
        ).scalar()

        child_intents_total = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE product_type = :ptype
                   OR intent_role = :role
                """
            ),
            {
                "ptype": IntentProductType.BUNDLE_LEG.value,
                "role": IntentRole.CHILD.value,
            },
        ).scalar()

        child_factory_auto = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE metadata_json ? 'bundle_child_factory'
                """
            )
        ).scalar()

        parent_child_factory_auto = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE product_type = 'bundle_invest'
                  AND metadata_json ? 'child_factory'
                """
            )
        ).scalar()

        parents_child_legs_created_auto = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE product_type = 'bundle_invest'
                  AND COALESCE(metadata_json->>'phase', '') = 'CHILD_LEGS_CREATED'
                  AND metadata_json ? 'child_factory'
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

        flag_funding = os.environ.get("BUNDLE_FUNDING_HANDLER_ENABLED", "").strip().lower()
        flag_settlement = os.environ.get("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED", "").strip().lower()
        flag_dual_run = os.environ.get("BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED", "").strip().lower()
        health_ok, health_status, health_error = _health_ok()

        module_imported = False
        factory_callable = False
        module_src = ""
        orchestrator_src = ""
        worker_src = ""
        lifi_leg_src = ""
        try:
            from services.portfolio_engine.bundles.event_driven.bundle_child_factory import (  # noqa: F401
                create_bundle_child_intents_from_frozen_plan,
            )

            import services.portfolio_engine.bundles.event_driven.bundle_child_factory as bcf

            module_imported = True
            factory_callable = callable(create_bundle_child_intents_from_frozen_plan)
            module_src = inspect.getsource(bcf)
            orchestrator_src = inspect.getsource(BundleOrchestrator)
            try:
                import services.transaction_outbox.settlement_worker as sw

                worker_src = inspect.getsource(sw)
            except Exception:
                worker_src = ""
            try:
                from services.portfolio_engine.bundle_execution import bundle_lifi_leg_service as bls

                lifi_leg_src = inspect.getsource(bls.BundleLifiLegService)
            except Exception:
                lifi_leg_src = ""
        except Exception as exc:
            module_src = str(exc)

        runtime_wired = (
            "create_bundle_child_intents_from_frozen_plan" in orchestrator_src
            or "bundle_child_factory" in orchestrator_src
            or "create_bundle_child_intents_from_frozen_plan" in worker_src
            or "bundle_child_factory" in worker_src
            or "create_bundle_child_intents_from_frozen_plan" in lifi_leg_src
        )

        git_sha = (
            os.environ.get("GIT_SHA")
            or os.environ.get("GIT_COMMIT")
            or os.environ.get("SOURCE_VERSION")
        )

        result = {
            "phase": "bundle_b4a_post_deploy_verify",
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
                "BUNDLE_FUNDING_HANDLER_ENABLED": flag_funding or None,
                "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED": flag_settlement or None,
                "BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED": flag_dual_run or None,
            },
            "neutralite": {
                "bundle_scope_bundle_invest_locks": bundle_scope_locks,
                "bundle_leg_or_child_intents_total": child_intents_total,
                "bundle_child_factory_metadata_auto": child_factory_auto,
                "bundle_parents_child_factory_metadata": parent_child_factory_auto,
                "bundle_parents_child_legs_created_factory": parents_child_legs_created_auto,
                "pe_atoms": pe,
                "pe_atoms_expected": BASELINE_PE_ATOMS,
                "cost_basis": cb,
                "cost_basis_expected": BASELINE_COST_BASIS,
                "lifi_swap_legs": legs,
                "lifi_swap_legs_expected": BASELINE_LIFI_LEGS,
            },
            "runtime_wiring": {
                "bundle_child_factory_module_present": module_imported,
                "create_bundle_child_intents_callable": factory_callable,
                "module_no_swap_settlement_worker_imports": all(
                    token not in module_src.lower()
                    for token in (
                        "bundle_leg_settlement_handler",
                        "settle_bundle_leg",
                        "lifi",
                        "transaction_outbox",
                        "settlement_worker",
                        "lifi_swap_controller",
                        "reconcile_lifi_swap",
                        "services.settlement.settle",
                        "person_wallet_swaps",
                    )
                ),
                "orchestrator_worker_or_lifi_leg_calls_factory": runtime_wired,
            },
            "all_checks_pass": (
                health_ok
                and str(alembic) == "176"
                and flag_funding not in ("1", "true", "yes", "on")
                and flag_settlement not in ("1", "true", "yes", "on")
                and flag_dual_run not in ("1", "true", "yes", "on")
                and bundle_scope_locks == 0
                and child_factory_auto == 0
                and parent_child_factory_auto == 0
                and parents_child_legs_created_auto == 0
                and pe == BASELINE_PE_ATOMS
                and cb == BASELINE_COST_BASIS
                and legs == BASELINE_LIFI_LEGS
                and module_imported
                and factory_callable
                and not runtime_wired
            ),
        }
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
