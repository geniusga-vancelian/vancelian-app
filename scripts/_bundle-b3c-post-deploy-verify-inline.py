"""Post-deploy neutre B3c — bundle leg settlement handler · flag OFF · aucun runtime."""
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

MERGE_SHA = "8252e9c9"
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

        child_intents = db.execute(
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

        child_settled_auto = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE product_type = 'bundle_leg'
                  AND (
                    metadata_json ? 'bundle_leg_settlement'
                    OR COALESCE(metadata_json->'bundle_leg_settlement'->>'settled', '') = 'true'
                    OR metadata_json ? 'child_report_hash'
                    OR (
                      metadata_json ? 'settlement_receipt_hash'
                      AND intent_role = 'child'
                    )
                  )
                """
            )
        ).scalar()

        bundle_parents_touched = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM transaction_intents
                WHERE product_type = 'bundle_invest'
                  AND (
                    metadata_json ? 'bundle_leg_settlement'
                    OR metadata_json ? 'child_report_hash'
                  )
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

        flag_env = os.environ.get("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED", "").strip().lower()
        health_ok, health_status, health_error = _health_ok()

        module_imported = False
        handler_callable = False
        flag_off_runtime = True
        module_src = ""
        orchestrator_src = ""
        worker_src = ""
        lifi_leg_src = ""
        try:
            from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler import (  # noqa: F401
                settle_bundle_leg_idempotently,
            )
            from services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler_config import (
                bundle_leg_settlement_handler_enabled,
            )

            import services.portfolio_engine.bundles.event_driven.bundle_leg_settlement_handler as blh

            module_imported = True
            handler_callable = callable(settle_bundle_leg_idempotently)
            flag_off_runtime = not bundle_leg_settlement_handler_enabled()
            module_src = inspect.getsource(blh)
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
            "settle_bundle_leg_idempotently" in orchestrator_src
            or "bundle_leg_settlement_handler" in orchestrator_src
            or "settle_bundle_leg_idempotently" in worker_src
            or "settle_bundle_leg_idempotently" in lifi_leg_src
        )

        git_sha = (
            os.environ.get("GIT_SHA")
            or os.environ.get("GIT_COMMIT")
            or os.environ.get("SOURCE_VERSION")
        )

        result = {
            "phase": "bundle_b3c_post_deploy_verify",
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
                "BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED": flag_env or None,
                "bundle_leg_settlement_handler_enabled()": flag_off_runtime,
            },
            "neutralite": {
                "bundle_scope_bundle_invest_locks": bundle_scope_locks,
                "bundle_leg_or_child_intents": child_intents,
                "bundle_leg_settlement_metadata_auto": child_settled_auto,
                "bundle_parents_leg_settlement_metadata": bundle_parents_touched,
                "pe_atoms": pe,
                "pe_atoms_expected": BASELINE_PE_ATOMS,
                "cost_basis": cb,
                "cost_basis_expected": BASELINE_COST_BASIS,
                "lifi_swap_legs": legs,
                "lifi_swap_legs_expected": BASELINE_LIFI_LEGS,
            },
            "runtime_wiring": {
                "bundle_leg_settlement_handler_module_present": module_imported,
                "settle_bundle_leg_callable": handler_callable,
                "module_no_worker_controller_lifi_imports": all(
                    token not in module_src.lower()
                    for token in (
                        "transaction_outbox",
                        "settlement_worker",
                        "lifi_swap_controller",
                        "reconcile_lifi_swap",
                        "services.settlement.settle",
                    )
                ),
                "orchestrator_worker_or_lifi_leg_calls_handler": runtime_wired,
                "legacy_apply_post_confirmation_still_present": "_apply_post_confirmation" in lifi_leg_src,
            },
            "all_checks_pass": (
                health_ok
                and str(alembic) == "176"
                and flag_env not in ("1", "true", "yes", "on")
                and flag_off_runtime
                and bundle_scope_locks == 0
                and child_intents == 0
                and child_settled_auto == 0
                and bundle_parents_touched == 0
                and pe == BASELINE_PE_ATOMS
                and cb == BASELINE_COST_BASIS
                and legs == BASELINE_LIFI_LEGS
                and module_imported
                and handler_callable
                and not runtime_wired
            ),
        }
        print(json.dumps(result, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
