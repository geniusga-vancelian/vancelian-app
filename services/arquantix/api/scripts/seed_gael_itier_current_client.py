#!/usr/bin/env python3
"""
Client de test « Gael ITIER » + compte custody EUR + définition comme client Flutter courant.

Idempotent : réexécuter met à jour le profil, assure le compte EUR et réécrit le client courant (fichier .current_test_client_id).

Usage (depuis services/arquantix/api, avec DATABASE_URL) ::
  python3 scripts/seed_gael_itier_current_client.py
"""
from __future__ import annotations

import os
import sys
import uuid
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


def _fake_fr_iban() -> str:
    """IBAN FR factice unique (tests / dev local)."""
    core = uuid.uuid4().hex[:18].upper()
    return f"FR76{core}"


def main() -> None:
    _ensure_api_path()

    from auth import get_password_hash
    from database import AdminUser, Person, SessionLocal
    from services.custody.enums import CustodyAccountType, ProviderStatus, ProviderType
    from services.custody.repository import CustodyAccountRepository, CustodyProviderRepository
    from services.custody.schemas import AccountCreate, ProviderCreate
    from services.custody.service import CustodyService
    from services.portfolio_engine.clients.enums import ClientStatus, KycStatus
    from services.portfolio_engine.clients.models import Client
    from services.portfolio_engine.hardening.security.context import ActorContext
    EMAIL = "gael.itier.flutter@test.arquantix.local"
    HOLDER_NAME = "Gael ITIER"
    FIRST = "Gael"
    LAST = "ITIER"
    PROVIDER_NAME = "Seed Bank — Gael ITier"

    db = SessionLocal()
    actor = ActorContext(actor_type="script", actor_id="seed_gael_itier")
    custody = CustodyService()
    prov_repo = CustodyProviderRepository()
    acc_repo = CustodyAccountRepository()

    try:
        client = db.query(Client).filter(Client.email == EMAIL).first()
        person: Person | None = None

        if client is None:
            person = Person(
                status="active",
                jurisdiction="EU",
                profile_json={
                    "collected": {
                        "first_name": FIRST,
                        "last_name": LAST,
                    }
                },
            )
            db.add(person)
            db.flush()
            client = Client(
                email=EMAIL,
                status=ClientStatus.ACTIVE.value,
                kyc_status=KycStatus.APPROVED.value,
                reference_currency="EUR",
                person_id=person.id,
            )
            db.add(client)
            db.flush()
            print(f"✅ Client PE créé : {client.id} ({EMAIL})")
        else:
            print(f"ℹ️  Client PE existant : {client.id} ({EMAIL})")
            if client.person_id:
                person = db.query(Person).filter(Person.id == client.person_id).first()
            if person is None:
                person = Person(
                    status="active",
                    jurisdiction="EU",
                    profile_json={"collected": {"first_name": FIRST, "last_name": LAST}},
                )
                db.add(person)
                db.flush()
                client.person_id = person.id
                db.flush()
            else:
                pj = dict(person.profile_json or {})
                coll = dict(pj.get("collected") or {})
                coll["first_name"] = FIRST
                coll["last_name"] = LAST
                pj["collected"] = coll
                person.profile_json = pj
                db.flush()

        provider = prov_repo.get_by_name(db, PROVIDER_NAME)
        if provider is None:
            items, _ = prov_repo.list(db, skip=0, limit=1)
            if items:
                provider = items[0]
                print(f"ℹ️  Provider custody existant : {provider.name} ({provider.id})")
            else:
                provider = custody.create_provider(
                    db,
                    ProviderCreate(
                        name=PROVIDER_NAME,
                        provider_type=ProviderType.BANK,
                        jurisdiction="EU",
                        status=ProviderStatus.ACTIVE,
                    ),
                    actor,
                )
                print(f"✅ Provider custody créé : {provider.name} ({provider.id})")

        eur = acc_repo.find_client_account(db, client.id, "EUR")
        if eur is None:
            custody.create_client_account(
                db,
                AccountCreate(
                    provider_id=provider.id,
                    account_type=CustodyAccountType.CLIENT_DEPOSIT,
                    currency="EUR",
                    account_holder_name=HOLDER_NAME,
                    client_id=client.id,
                    iban=_fake_fr_iban(),
                ),
                actor,
            )
            print("✅ Compte custody EUR créé (solde 0).")
        else:
            if (eur.account_holder_name or "").strip() != HOLDER_NAME:
                eur.account_holder_name = HOLDER_NAME
                db.flush()
                print(f"ℹ️  Titulaire compte EUR mis à jour : {HOLDER_NAME}")
            else:
                print(f"ℹ️  Compte EUR déjà présent : {eur.id}")

        # Table ``admin_users`` (OTP e-mail / back-office) : distincte du client portfolio.
        admin_row = db.query(AdminUser).filter(AdminUser.email == EMAIL).first()
        if admin_row is None:
            db.add(
                AdminUser(
                    email=EMAIL,
                    hashed_password=get_password_hash(
                        "local-dev-seed-not-for-password-login"
                    ),
                )
            )
            db.flush()
            print(f"✅ AdminUser créé pour OTP e-mail : {EMAIL}")
        else:
            print(f"ℹ️  AdminUser déjà présent : {EMAIL}")

        db.commit()
        print(f"✅ pe_clients seed : {client.id}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
