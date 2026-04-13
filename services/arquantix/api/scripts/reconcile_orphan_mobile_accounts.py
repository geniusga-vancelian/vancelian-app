#!/usr/bin/env python3
"""
Détecte les lignes ``admin_users`` avec ``mobile_e164`` mais sans ``person_id`` (orphelins).

Ces lignes bloquaient autrefois l’inscription ; la politique actuelle les libère à la vérif signup.
Ce script sert au diagnostic / nettoyage manuel en prod.

Usage (depuis services/arquantix/api) :
  python3 scripts/reconcile_orphan_mobile_accounts.py --dry-run
  python3 scripts/reconcile_orphan_mobile_accounts.py --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from sqlalchemy import select  # noqa: E402

from database import AdminUser, SessionLocal  # noqa: E402
from services.auth.account_policy import admin_email_protected, is_web_only_mobile_app_user  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Orphelins mobile admin_users sans person_id")
    parser.add_argument("--apply", action="store_true", help="Met mobile_e164 à NULL (hors compte protégé)")
    parser.add_argument("--dry-run", action="store_true", help="Lister uniquement (défaut si --apply absent)")
    args = parser.parse_args()
    dry = not args.apply

    protected = admin_email_protected()
    db = SessionLocal()
    try:
        rows = (
            db.execute(
                select(AdminUser)
                .where(AdminUser.mobile_e164.isnot(None))
                .where(AdminUser.person_id.is_(None))
                .order_by(AdminUser.id)
            )
            .scalars()
            .all()
        )
        if not rows:
            print("Aucun orphelin (mobile sans person_id).")
            return 0

        targets = [u for u in rows if not is_web_only_mobile_app_user(u)]
        print(f"Orphelins candidats (hors web-only): {len(targets)}")
        for u in targets:
            em = (u.email or "").strip().lower()
            flag = "SKIP_ADMIN_EMAIL" if em == protected else "OK"
            print(f"  id={u.id} email={u.email!r} mobile={u.mobile_e164!r} [{flag}]")

        if dry:
            print("--dry-run : aucune modification. Utilisez --apply pour effacer les mobiles (sauf protection).")
            return 0

        n = 0
        for u in targets:
            if (u.email or "").strip().lower() == protected:
                continue
            u.mobile_e164 = None
            n += 1
        db.commit()
        print(f"Mis à jour: {n} ligne(s).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
