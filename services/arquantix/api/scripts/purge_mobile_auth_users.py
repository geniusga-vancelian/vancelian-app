#!/usr/bin/env python3
"""
Purge tous les comptes d’authentification mobile (admin_users avec mobile_e164)
et les personnes / sessions d’inscription liées — pour un environnement sans clients.

- Le compte **ADMIN_EMAIL** (back-office web) n’est **jamais supprimé** : seul
  ``mobile_e164`` est effacé pour libérer le numéro côté auth mobile.
- Les comptes **mobile** (``mobile_e164`` non nul, hors ``ADMIN_EMAIL``) sont **supprimés** — avec ou sans e-mail (PR4).

Usage (depuis services/arquantix/api) :
  python3 scripts/purge_mobile_auth_users.py --dry-run
  python3 scripts/purge_mobile_auth_users.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from sqlalchemy import delete, func, select, update  # noqa: E402

from database import (  # noqa: E402
    AdminUser,
    AuthMobileLoginOtpChallenge,
    Person,
    RegistrationSession,
    SessionLocal,
)
from services.portfolio_engine.clients.models import Client  # noqa: E402


def _admin_email_protected() -> str:
    return (os.getenv("ADMIN_EMAIL") or "admin@arquantix.com").strip().lower()


def _collect_targets(db: Session, *, protected_email: str) -> tuple[list[AdminUser], list[UUID]]:
    """Comptes à supprimer (mobile), hors compte admin web."""
    users = (
        db.execute(
            select(AdminUser)
            .where(AdminUser.mobile_e164.isnot(None))
            .where(func.lower(AdminUser.email) != protected_email)
            .order_by(AdminUser.id)
        )
        .scalars()
        .all()
    )
    person_ids = [u.person_id for u in users if u.person_id is not None]
    return list(users), person_ids


def purge(dry_run: bool) -> int:
    db = SessionLocal()
    protected = _admin_email_protected()
    try:
        all_with_mobile = (
            db.execute(select(AdminUser).where(AdminUser.mobile_e164.isnot(None))).scalars().all()
        )
        if not all_with_mobile:
            print("Aucun utilisateur avec mobile_e164 — rien à faire.")
            return 0

        seed_admin = (
            db.execute(
                select(AdminUser).where(func.lower(AdminUser.email) == protected)
            )
            .scalars()
            .first()
        )

        users, person_ids = _collect_targets(db, protected_email=protected)

        print(f"ADMIN_EMAIL protégé (ne sera pas supprimé) : {protected!r}")
        if seed_admin and seed_admin.mobile_e164:
            print(
                f"  → Ce compte a un mobile_e164={seed_admin.mobile_e164!r} "
                f"(sera effacé en --apply, le compte reste pour le web)."
            )

        print(f"\nComptes à supprimer (auth mobile client) : {len(users)}")
        for u in users:
            print(
                f"  - id={u.id} email={u.email!r} mobile_e164={u.mobile_e164!r} "
                f"person_id={u.person_id}"
            )
        if person_ids:
            print(f"Personnes liées à purger ensuite : {len(person_ids)}")

        if dry_run:
            print("\n[--dry-run] Aucune modification.")
            return 0

        # 0) Retirer le numéro sur le compte admin web (sans supprimer la ligne)
        if seed_admin and seed_admin.mobile_e164:
            db.execute(
                update(AdminUser)
                .where(AdminUser.id == seed_admin.id)
                .values(mobile_e164=None)
            )
            print(f"admin_users : mobile_e164 effacé pour id={seed_admin.id} ({protected!r})")

        # 1) Sessions d’inscription (FK vers persons — à retirer avant person)
        if person_ids:
            rs = db.execute(
                delete(RegistrationSession).where(RegistrationSession.person_id.in_(person_ids))
            )
            print(f"registration_sessions supprimées : {rs.rowcount or 0}")

        # 2) Clients PE liés à ces personnes
        if person_ids:
            pc = db.execute(delete(Client).where(Client.person_id.in_(person_ids)))
            print(f"pe_clients supprimés : {pc.rowcount or 0}")

        # 3) Comptes auth mobile clients (sessions JWT / passkeys en CASCADE côté FK)
        if users:
            ids = [u.id for u in users]
            au = db.execute(delete(AdminUser).where(AdminUser.id.in_(ids)))
            print(f"admin_users (mobile / hors admin web) supprimés : {au.rowcount or 0}")

        # 4) Personnes (orphelines après suppression admin)
        if person_ids:
            pe = db.execute(delete(Person).where(Person.id.in_(person_ids)))
            print(f"persons supprimées : {pe.rowcount or 0}")

        # 5) Challenges OTP résiduels (même numéro / tests)
        ch = db.execute(delete(AuthMobileLoginOtpChallenge))
        print(f"auth_mobile_login_otp_challenges supprimés (tous) : {ch.rowcount or 0}")

        db.commit()
        print("\nOK — purge terminée.")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"ERREUR (rollback) : {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="Lister sans modifier")
    p.add_argument("--apply", action="store_true", help="Exécuter la purge")
    args = p.parse_args()
    if not args.apply and not args.dry_run:
        p.print_help()
        print("\nIndiquez --dry-run ou --apply.", file=sys.stderr)
        sys.exit(2)
    dry = not args.apply
    sys.exit(purge(dry_run=dry))


if __name__ == "__main__":
    main()
