"""Post-deploy P0 — controlled verify shape batch 470c964f (read-only peek + resume path).

Ne modifie pas PE atoms / cost basis / LI.FI deposits.
Peut réacquérir bundle_invest_lock + appeler resume pour débloquer la reprise UI.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import SessionLocal
from services.portfolio_engine.bundles.bundle_invest_lock import (
    find_active_bundle_batch_ids_for_portfolio,
    get_invest_lock,
    peek_bundle_invest_lock_state,
    reacquire_invest_lock_for_batch,
)
from services.portfolio_engine.bundles.orchestrator import (
    BundleOrchestrator,
    BundleOrchestratorError,
)
from services.portfolio_engine.portfolios.models import Portfolio

PERSON_ID = "8b0e0044-f1ef-47a5-99d4-370598a77492"
CLIENT_ID = "080358a8-4519-4acf-b5da-25485446c967"
PORTFOLIO_ID = "daea3720-e58e-410f-a796-3bbd541ac608"
BATCH_ID = "470c964f-e166-4b93-97c7-b184510e2523"
PARENT_INTENT_ID = "138a2de1-9ee9-41f8-80d7-70a11f03ade3"

BASELINE_PE_ATOMS = int(os.environ.get("BUNDLE_BASELINE_PE_ATOMS", "19"))
BASELINE_COST_BASIS = int(os.environ.get("BUNDLE_BASELINE_COST_BASIS", "80"))
BASELINE_LIFI_LEGS = int(os.environ.get("BUNDLE_BASELINE_LIFI_LEGS", "131"))


def _flag_on(name: str) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _financial_counts(db: Session) -> dict[str, int]:
    pe = db.execute(text("SELECT COUNT(*) FROM pe_position_atoms")).scalar()
    cb = db.execute(text("SELECT COUNT(*) FROM cost_basis_executions")).scalar()
    legs = db.execute(
        text(
            "SELECT COUNT(*) FROM person_wallet_deposits "
            "WHERE idempotency_key LIKE 'lifi-swap:%'"
        )
    ).scalar()
    return {
        "pe_atoms": int(pe or 0),
        "cost_basis_entries": int(cb or 0),
        "bundle_lifi_legs": int(legs or 0),
    }


def _batch_swaps(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT s.id::text, s.status, s.to_asset, s.created_at, s.updated_at
            FROM person_wallet_swaps s
            WHERE s.person_id = :person
              AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(COALESCE(s.audit_log::jsonb,'[]'::jsonb)) e
                WHERE e->>'event' = 'bundle_leg_context'
                  AND e->>'batch_id' = :batch
              )
            ORDER BY s.created_at ASC
            """
        ),
        {"person": PERSON_ID, "batch": BATCH_ID},
    ).mappings()
    return [dict(r) for r in rows]


def _parent_intent(db: Session) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id::text, status, metadata_json->>'batch_id' AS batch_id,
                   metadata_json->'legs' AS legs, updated_at
            FROM transaction_intents
            WHERE id = :parent
            """
        ),
        {"parent": PARENT_INTENT_ID},
    ).mappings().first()
    return dict(row) if row else None


def main() -> None:
    db: Session = SessionLocal()
    out: dict[str, Any] = {
        "phase": "bundle_p0_470c964f_post_deploy_verify",
        "audit_iso": datetime.now(timezone.utc).isoformat(),
        "batch_id": BATCH_ID,
        "portfolio_id": PORTFOLIO_ID,
        "person_id": PERSON_ID,
    }
    try:
        baseline = _financial_counts(db)
        out["baseline"] = {
            **baseline,
            "expected_pe_atoms": BASELINE_PE_ATOMS,
            "expected_cost_basis": BASELINE_COST_BASIS,
            "expected_lifi_legs": BASELINE_LIFI_LEGS,
        }

        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.id == UUID(PORTFOLIO_ID))
            .first()
        )
        if portfolio is None:
            raise RuntimeError(f"portfolio_not_found: {PORTFOLIO_ID}")

        meta_before = deepcopy(portfolio.metadata_ or {})
        lock_before = get_invest_lock(meta_before)
        active_batches_before = find_active_bundle_batch_ids_for_portfolio(
            db,
            client_id=UUID(CLIENT_ID),
            portfolio_id=UUID(PORTFOLIO_ID),
        )

        peek = peek_bundle_invest_lock_state(
            db,
            client_id=UUID(CLIENT_ID),
            portfolio_id=UUID(PORTFOLIO_ID),
        )
        db.refresh(portfolio)
        meta_after_peek = deepcopy(portfolio.metadata_ or {})

        peek_read_only = meta_after_peek == meta_before
        peek_lock = peek.get("lock") or {}
        peek_batch = str(peek_lock.get("batch_id") or "")

        out["pre_peek"] = {
            "bundle_invest_lock": lock_before,
            "active_batches_portfolio": active_batches_before,
            "parent_intent": _parent_intent(db),
            "batch_swaps": _batch_swaps(db),
        }
        out["peek"] = peek
        out["checks_peek"] = {
            "metadata_unchanged_after_peek": peek_read_only,
            "read_only_flag": peek.get("read_only") is True,
            "status_active_or_ambiguous": peek.get("status") in {"active", "ambiguous"},
            "target_batch_visible": (
                BATCH_ID in active_batches_before
                or peek_batch.startswith(BATCH_ID[:8])
                or BATCH_ID in (peek.get("active_batches") or [])
            ),
            "recovered_from_pending_when_lock_null": (
                lock_before is None
                and peek.get("status") == "active"
                and peek.get("recovered_from_pending_batch") is True
            )
            if lock_before is None and len(active_batches_before) == 1
            else None,
            "ambiguous_when_multiple_batches": (
                len(active_batches_before) > 1 and peek.get("status") == "ambiguous"
            )
            if len(active_batches_before) > 1
            else None,
        }

        resume_result: dict[str, Any] | None = None
        resume_error: str | None = None
        reacquired = False

        if lock_before is None and BATCH_ID in active_batches_before:
            portfolio_locked = (
                db.query(Portfolio)
                .filter(Portfolio.id == UUID(PORTFOLIO_ID))
                .with_for_update()
                .first()
            )
            if portfolio_locked is not None:
                reacquire_invest_lock_for_batch(
                    db,
                    portfolio=portfolio_locked,
                    client_id=UUID(CLIENT_ID),
                    portfolio_id=UUID(PORTFOLIO_ID),
                    batch_id=BATCH_ID,
                    status="pending_signature",
                    reason="controlled_verify_470c964f",
                )
                db.flush()
                reacquired = True

        try:
            resume_result = BundleOrchestrator().resume_lifi_invest_batch(
                db,
                client_id=UUID(CLIENT_ID),
                portfolio_id=UUID(PORTFOLIO_ID),
            )
        except BundleOrchestratorError as exc:
            resume_error = str(exc)

        db.refresh(portfolio)
        lock_after = get_invest_lock(portfolio.metadata_ or {})
        post = _financial_counts(db)

        out["resume"] = {
            "reacquired_target_batch_first": reacquired,
            "result": resume_result,
            "error": resume_error,
            "lock_after": lock_after,
        }
        out["post_financial"] = post
        out["flags"] = {
            "GLOBAL_USER_TRANSACTION_LOCK_ENABLED": os.environ.get(
                "GLOBAL_USER_TRANSACTION_LOCK_ENABLED"
            ),
            "flag_global_lock_off": not _flag_on("GLOBAL_USER_TRANSACTION_LOCK_ENABLED"),
        }

        economic_unchanged = (
            post["pe_atoms"] == baseline["pe_atoms"] == BASELINE_PE_ATOMS
            and post["cost_basis_entries"] == baseline["cost_basis_entries"] == BASELINE_COST_BASIS
            and post["bundle_lifi_legs"] == baseline["bundle_lifi_legs"] == BASELINE_LIFI_LEGS
        )

        legs_pending = int((resume_result or {}).get("legs_pending") or 0)
        resume_ok = resume_result is not None and legs_pending >= 1
        lock_points_target = str((lock_after or {}).get("batch_id") or "") == BATCH_ID

        out["checks_final"] = {
            "peek_read_only": peek_read_only,
            "economic_unchanged": economic_unchanged,
            "global_lock_off": not _flag_on("GLOBAL_USER_TRANSACTION_LOCK_ENABLED"),
            "resume_legs_pending": legs_pending if resume_ok else None,
            "lock_reacquired_for_target_batch": lock_points_target,
        }
        out["all_checks_pass"] = (
            peek_read_only
            and economic_unchanged
            and not _flag_on("GLOBAL_USER_TRANSACTION_LOCK_ENABLED")
            and lock_points_target
            and resume_ok
        )

        if out["all_checks_pass"]:
            db.commit()
            out["committed"] = True
        else:
            db.rollback()
            out["committed"] = False

        print(json.dumps(out, indent=2, default=str))
        if not out["all_checks_pass"]:
            raise SystemExit(1)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
