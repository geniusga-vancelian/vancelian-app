"""CLI Phase 3B — plan de migration Lombard scope (dry-run par défaut)."""
from __future__ import annotations

import argparse
import json
import sys
from uuid import UUID

from database import SessionLocal
from services.portfolio_engine.lombard_execution.lombard_ovt_bridge import (
    apply_lombard_scope_movement_for_ovt,
    plan_lombard_scope_backfill_for_person,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lombard scope backfill / dry-run (Phase 3B)")
    parser.add_argument("--person-id", required=True, help="UUID person")
    parser.add_argument("--ovt-id", help="Appliquer ou simuler un OVT unique")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Écriture PE (désactivé par défaut — dry-run only)",
    )
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    person_id = UUID(args.person_id)
    dry_run = not args.apply

    db = SessionLocal()
    try:
        if args.ovt_id:
            result = apply_lombard_scope_movement_for_ovt(
                db,
                ovt_id=args.ovt_id,
                person_id=person_id,
                dry_run=dry_run,
            )
            if not dry_run and result.get("ok"):
                db.commit()
            else:
                db.rollback()
            print(json.dumps(result, indent=2, default=str))
            return 0 if result.get("ok") else 1

        plan = plan_lombard_scope_backfill_for_person(
            db,
            person_id=person_id,
            limit=args.limit,
        )
        if dry_run:
            db.rollback()
            print(json.dumps(plan, indent=2, default=str))
            return 0

        applied: list[dict] = []
        for preview in plan.get("planned_movements", []):
            if not preview.get("ok"):
                db.rollback()
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "reason": "planned_movement_not_ok",
                            "failed_preview": preview,
                            "applied_count": len(applied),
                        },
                        indent=2,
                        default=str,
                    )
                )
                return 1
            result = apply_lombard_scope_movement_for_ovt(
                db,
                ovt_id=str(preview["ovt_id"]),
                person_id=person_id,
                dry_run=False,
            )
            applied.append(result)
            if not result.get("ok"):
                db.rollback()
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "reason": "apply_failed",
                            "failed_result": result,
                            "applied_count": len(applied) - 1,
                        },
                        indent=2,
                        default=str,
                    )
                )
                return 1

        db.commit()
        print(
            json.dumps(
                {
                    "ok": True,
                    "dry_run": False,
                    "person_id": str(person_id),
                    "ovt_count": plan.get("ovt_count"),
                    "applied_count": len(applied),
                    "applied_movements": applied,
                },
                indent=2,
                default=str,
            )
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
