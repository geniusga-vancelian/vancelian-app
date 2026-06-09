"""Post-deploy verify — Bundle V3 hardening (worker cadence + executor retry)."""
from __future__ import annotations

import inspect
import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from database import SessionLocal
from services.portfolio_engine.bundles.bundle_v3_deposit_flow import ops_alerts as oa
from services.portfolio_engine.bundles.rebalance_executor import (
    MAX_SWAP_ATTEMPTS,
    V3LegExecutionResult,
    BundleRebalanceExecutor,
)


def main() -> int:
    loop_src = inspect.getsource(BundleRebalanceExecutor._execute_plan_legs)
    resolve_src = inspect.getsource(BundleRebalanceExecutor._resolve_pending_leg)
    fields = V3LegExecutionResult.__dataclass_fields__

    out: dict = {
        "phase": "bundle_v3_hardening_post_deploy_verify",
        "deploy_sha": os.environ.get("GIT_SHA", "unknown"),
        "max_swap_attempts": MAX_SWAP_ATTEMPTS,
        "executor": {
            "has_resolve_pending_leg": True,
            "loop_calls_resolve": "_resolve_pending_leg" in loop_src,
            "pending_no_immediate_break": (
                'if leg_result.status == "pending":\n                    break'
                not in loop_src
            ),
            "attempt_details_field": "attempt_details" in fields,
            "quote_ttl_in_resolve": "quote_ttl_expired" in resolve_src,
        },
        "flags": {
            k: os.environ.get(k)
            for k in (
                "BUNDLE_V3_DEPOSIT_FLOW_ENABLED",
                "BUNDLE_V3_DEPOSIT_WORKER_ENABLED",
                "BUNDLE_V3_REBALANCE_EXECUTOR_ENABLED",
            )
        },
    }

    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=2)
        rows = db.execute(
            text(
                """
                SELECT id::text, status, started_at,
                       summary_json->>'overall_status' AS overall_status
                FROM defi_observability_job_runs
                WHERE started_at >= :since
                ORDER BY started_at DESC
                """
            ),
            {"since": since},
        ).mappings().all()
        out["auto_ticks_last_2h"] = len(rows)
        out["latest_auto_ticks"] = [dict(r) for r in rows[:5]]

        out["outbox_pending"] = int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM transaction_outbox
                    WHERE event_type = 'bundle.v3_rebalance_requested'
                      AND status IN ('pending', 'processing')
                    """
                )
            ).scalar()
            or 0
        )
        out["guards_active"] = int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM portfolio_financial_operations
                    WHERE status = 'ACTIVE' AND operation_type = 'BUNDLE_INVEST'
                    """
                )
            ).scalar()
            or 0
        )
        audit = oa.audit_bundle_v3_deposit_ops(db)
        out["ops_critical_alerts"] = len(audit.get("alerts") or [])
    finally:
        db.close()

    ex = out["executor"]
    out["verdict"] = (
        "PASS"
        if ex["loop_calls_resolve"]
        and ex["pending_no_immediate_break"]
        and ex["attempt_details_field"]
        and out["auto_ticks_last_2h"] >= 1
        else "FAIL"
    )
    print(json.dumps(out, indent=2, default=str))
    return 0 if out["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
