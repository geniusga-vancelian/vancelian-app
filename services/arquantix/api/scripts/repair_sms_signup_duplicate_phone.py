#!/usr/bin/env python3
"""
Répare un cas où l’inscription SMS a créé une Person + pe_clients vides alors qu’une autre
Person portait déjà le même numéro dans profile_json.collected.phone_e164 (ex. script Modulr,
parcours EU). Le JWT pointait alors vers le mauvais pe_clients → balance 0 sur le dashboard.

Ce script :
  - trouve l’admin_users avec mobile_e164 = PHONE ;
  - trouve la Person dont profile_json contient ce numéro (priorité) ;
  - si elles diffèrent, réassigne admin_users.person_id vers la Person « riche » ;
  - met persons.client_id cohérent ; supprime le pe_clients orphelin sans custody si possible.

Usage (depuis services/arquantix/api, DATABASE_URL chargé) ::
  python3 scripts/repair_sms_signup_duplicate_phone.py
  python3 scripts/repair_sms_signup_duplicate_phone.py --phone +33601000000 --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _ensure_api_path() -> None:
    api_dir = Path(__file__).resolve().parent.parent
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    os.chdir(api_dir)
    try:
        from dotenv import load_dotenv

        for p in (api_dir / ".env.local", api_dir / ".env"):
            if p.exists():
                load_dotenv(p)
                break
    except ImportError:
        pass


def main() -> None:
    _ensure_api_path()
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", default="+33601000000", help="E.164")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    phone = str(args.phone).strip()
    if not phone.startswith("+"):
        phone = "+" + phone.lstrip("+")

    from sqlalchemy import text

    from database import AdminUser, Person, SessionLocal
    from services.portfolio_engine.clients.models import Client as PeClient

    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.mobile_e164 == phone).first()
        if user is None:
            print(f"Aucun admin_users avec mobile_e164={phone}")
            return

        profile_pid = db.execute(
            text(
                "SELECT id FROM persons WHERE (profile_json->'collected'->>'phone_e164') = :ph LIMIT 1"
            ),
            {"ph": phone},
        ).scalar()

        if profile_pid is None:
            print(f"Aucune persons.profile_json.collected.phone_e164 = {phone}")
            return

        if str(user.person_id) == str(profile_pid):
            print("Déjà aligné : admin_users.person_id == personne profil téléphone.")
            return

        rich_person = db.query(Person).filter(Person.id == profile_pid).first()
        orphan_person = db.query(Person).filter(Person.id == user.person_id).first()
        if rich_person is None or orphan_person is None:
            print("Person introuvable")
            return

        rich_client = db.query(PeClient).filter(PeClient.person_id == rich_person.id).first()
        orphan_client = db.query(PeClient).filter(PeClient.person_id == orphan_person.id).first()

        print(f"admin_users id={user.id} email={user.email}")
        print(f"  actuel person_id (orphelin) : {orphan_person.id}")
        print(f"  cible person_id (profil)   : {rich_person.id}")
        if rich_client:
            print(f"  pe_client riche : {rich_client.id}")
        if orphan_client:
            print(f"  pe_client orphelin à retirer : {orphan_client.id}")

        if args.dry_run:
            print("Dry-run : aucune écriture.")
            return

        user.person_id = rich_person.id
        if rich_client and rich_person.client_id != rich_client.id:
            rich_person.client_id = rich_client.id

        if orphan_client is not None:
            orphan_person.client_id = None
            db.flush()
            n = (
                db.query(PeClient)
                .filter(
                    PeClient.id == orphan_client.id,
                )
                .delete(synchronize_session=False)
            )
            print(f"Suppression pe_clients orphelin : {n} ligne(s)")

        db.commit()
        print("OK — reconnectez l’app (nouveau JWT) pour voir le bon solde.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
