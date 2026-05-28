"""Export CSV audit ops — discrepancies & corrections (Phase 5C)."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from sqlalchemy.orm import Session

from .correction_service import correction_to_dict
from .discrepancy_models import ReconciliationCorrection
from .discrepancy_repository import DiscrepancyRepository, discrepancy_to_dict


def _json_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def export_discrepancies_csv(
    db: Session,
    *,
    filters: dict[str, Any],
    limit: int = 5000,
) -> str:
    rows, _ = DiscrepancyRepository.list_filtered(db, skip=0, limit=limit, **filters)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "person_id",
            "wallet_address",
            "layer",
            "asset",
            "discrepancy_type",
            "db_amount",
            "onchain_amount",
            "delta",
            "severity",
            "status",
            "reference_type",
            "reference_id",
            "fingerprint",
            "created_at",
            "resolved_at",
            "metadata_json",
        ]
    )
    for row in rows:
        d = discrepancy_to_dict(row)
        writer.writerow(
            [
                d["id"],
                d["person_id"],
                d.get("wallet_address") or "",
                d["layer"],
                d.get("asset") or "",
                d["discrepancy_type"],
                d.get("db_amount") or "",
                d.get("onchain_amount") or "",
                d.get("delta") or "",
                d["severity"],
                d["status"],
                d.get("reference_type") or "",
                d.get("reference_id") or "",
                d["fingerprint"],
                d.get("created_at") or "",
                d.get("resolved_at") or "",
                _json_cell(d.get("metadata_json")),
            ]
        )
    return buf.getvalue()


def export_corrections_csv(db: Session, *, limit: int = 5000) -> str:
    rows = (
        db.query(ReconciliationCorrection)
        .order_by(ReconciliationCorrection.created_at.desc())
        .limit(limit)
        .all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "discrepancy_id",
            "action",
            "status",
            "requested_by",
            "approved_by",
            "applied_by",
            "rejected_by",
            "requested_at",
            "approved_at",
            "applied_at",
            "dry_run",
            "reject_reason",
            "before_json",
            "after_json",
            "metadata_json",
        ]
    )
    for row in rows:
        c = correction_to_dict(row)
        writer.writerow(
            [
                c["id"],
                c["discrepancy_id"],
                c["action"],
                c["status"],
                c.get("requested_by") or "",
                c.get("approved_by") or "",
                c.get("applied_by") or "",
                c.get("rejected_by") or "",
                c.get("requested_at") or "",
                c.get("approved_at") or "",
                c.get("applied_at") or "",
                str(c.get("dry_run")),
                c.get("reject_reason") or "",
                _json_cell(c.get("before_json")),
                _json_cell(c.get("after_json")),
                _json_cell(c.get("metadata_json")),
            ]
        )
    return buf.getvalue()


def export_audit_csv(
    db: Session,
    *,
    export_type: str,
    filters: dict[str, Any],
    limit: int = 5000,
) -> tuple[str, str]:
    """Retourne (filename, contenu CSV)."""
    normalized = export_type.strip().lower()
    if normalized == "discrepancies":
        return (
            "onchain_reconciliation_discrepancies.csv",
            export_discrepancies_csv(db, filters=filters, limit=limit),
        )
    if normalized == "corrections":
        return (
            "onchain_reconciliation_corrections.csv",
            export_corrections_csv(db, limit=limit),
        )
    if normalized == "audit":
        disc = export_discrepancies_csv(db, filters=filters, limit=limit)
        corr = export_corrections_csv(db, limit=limit)
        combined = f"# DISCREPANCIES\n{disc}\n# CORRECTIONS\n{corr}"
        return ("onchain_reconciliation_audit.csv", combined)
    raise ValueError(f"invalid_export_type:{export_type}")
