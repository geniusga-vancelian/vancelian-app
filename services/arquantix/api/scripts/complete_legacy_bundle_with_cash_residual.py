#!/usr/bin/env python3
"""Cleanup ops legacy bundle zombie — R4.5-E.2-C.

Usage (depuis ``services/arquantix/api``)::

    # Audit + dry-run (défaut — aucune mutation)
    python3 -m scripts.complete_legacy_bundle_with_cash_residual \\
        --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492 \\
        --portfolio-id daea3720-e58e-410f-a796-3bbd541ac608 \\
        --batch-id 8486fb48-09e6-421c-8654-8a0e5ad1b9be \\
        --idempotency-key e2c-8486fb48-v1 \\
        --actor-id ops@arquantix

    # Apply (uniquement après feu vert humain explicite)
    python3 -m scripts.complete_legacy_bundle_with_cash_residual \\
        ... \\
        --apply \\
        --actor-id ops@arquantix
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from database import SessionLocal
from services.portfolio_engine.bundles.bundle_legacy_cleanup import (
    BundleLegacyCleanupError,
    BundleLegacyCleanupRejected,
    audit_legacy_bundle_cleanup,
    complete_legacy_bundle_with_cash_residual,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cleanup legacy bundle invest zombie (ops, idempotent)",
    )
    parser.add_argument("--person-id", required=True)
    parser.add_argument("--portfolio-id", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument(
        "--idempotency-key",
        required=True,
        help="Clé idempotente unique pour cet apply (ex. e2c-8486fb48-v1)",
    )
    parser.add_argument("--actor-id", default="ops-script", help="Identifiant admin / ops")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Exécuter les mutations (défaut: dry-run uniquement)",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Audit read-only E.2-A + PE + ledger sans plan cleanup",
    )
    parser.add_argument("--pretty", action="store_true", default=True)
    args = parser.parse_args()

    person_id = UUID(args.person_id)
    portfolio_id = UUID(args.portfolio_id)
    batch_id = args.batch_id.strip()
    dry_run = not args.apply

    db = SessionLocal()
    try:
        if args.audit_only:
            payload = audit_legacy_bundle_cleanup(
                db,
                person_id=person_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
            )
            print(json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False))
            return 0

        result = complete_legacy_bundle_with_cash_residual(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            idempotency_key=args.idempotency_key.strip(),
            actor_id=args.actor_id.strip(),
            dry_run=dry_run,
        )
        if not dry_run and result.get("mutations_applied"):
            db.commit()
        else:
            db.rollback()

        print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False, default=str))
        if result.get("already_applied"):
            return 0
        return 0 if dry_run or result.get("mutations_applied") else 1
    except BundleLegacyCleanupRejected as exc:
        db.rollback()
        print(
            json.dumps(
                {
                    "rejected": True,
                    "code": exc.code,
                    "message": str(exc),
                    "details": exc.details,
                    "dry_run": dry_run,
                },
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    except BundleLegacyCleanupError as exc:
        db.rollback()
        print(json.dumps({"error": str(exc), "dry_run": dry_run}, indent=2), file=sys.stderr)
        return 1
    except Exception as exc:
        db.rollback()
        print(json.dumps({"error": str(exc), "dry_run": dry_run}, indent=2), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
