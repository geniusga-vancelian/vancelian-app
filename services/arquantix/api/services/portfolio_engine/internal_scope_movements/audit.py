"""Build full internal scope audit report — read-only."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .compare import compare_expected_scopes_vs_current_pe


def build_internal_scope_audit_report(
    db: Session,
    *,
    person_id: UUID,
) -> dict[str, Any]:
    payload = compare_expected_scopes_vs_current_pe(db, person_id)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload["ready"] = True
    payload["mode"] = "dry_run_read_only"
    payload["legacy_source_of_truth"] = True
    payload["pe_atoms_mutated"] = False
    return payload
