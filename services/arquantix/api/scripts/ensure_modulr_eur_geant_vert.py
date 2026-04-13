#!/usr/bin/env python3
"""
Compte custody EUR (provider Modulr) + IBAN pour le client :
  - e-mail : geant.vert@gmail.com
  - ou mobile : +33601000000 (recherche dans persons.profile_json.collected.phone_e164)

Idempotent : réexécuter met à jour l’IBAN/BIC si besoin et rattache au provider Modulr.

Usage (depuis services/arquantix/api, avec DATABASE_URL) ::
  python3 scripts/ensure_modulr_eur_geant_vert.py
  python3 scripts/ensure_modulr_eur_geant_vert.py --create-missing   # créer Person+PE si absent

Sans ``--create-missing``, le script **échoue** si aucun client ne correspond à l’e-mail ou au mobile.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from pathlib import Path
from uuid import UUID

EMAIL = "geant.vert@gmail.com"
PHONE_E164 = "+33601000000"
HOLDER_NAME = "Géant Vert"

# IBAN/BIC de test (format FR — dev / sandbox)
DEFAULT_IBAN = "FR7630006000011234567890189"
DEFAULT_BIC = "AGFBFRCC"


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


def _normalize_phone_e164(raw: str) -> str:
    t = re.sub(r"\s+", "", (raw or "").strip())
    if not t:
        return ""
    if not t.startswith("+"):
        t = "+" + t.lstrip("+")
    return t


def _fake_fr_iban() -> str:
    core = uuid.uuid4().hex[:18].upper()
    return f"FR76{core}"


def _find_client_by_phone(db, target: str):
    """Retourne le Client PE dont le profil personne contient ce numéro E.164."""
    from database import Person
    from services.portfolio_engine.clients.models import Client

    want = _normalize_phone_e164(target)
    for person in db.query(Person).all():
        pj = person.profile_json or {}
        coll = pj.get("collected") or {}
        ph = coll.get("phone_e164") or coll.get("phone") or ""
        if _normalize_phone_e164(str(ph)) == want:
            c = db.query(Client).filter(Client.person_id == person.id).first()
            if c:
                return c
    return None


def main() -> None:
    _ensure_api_path()

    from database import Person, SessionLocal
    from services.custody.enums import CustodyAccountType, ProviderStatus, ProviderType
    from services.custody.repository import CustodyAccountRepository, CustodyProviderRepository
    from services.custody.schemas import AccountCreate, ProviderCreate
    from services.custody.service import CustodyService
    from services.portfolio_engine.clients.enums import ClientStatus, KycStatus
    from services.portfolio_engine.clients.models import Client
    from services.portfolio_engine.hardening.security.context import ActorContext

    db = SessionLocal()
    actor = ActorContext(actor_type="script", actor_id="ensure_modulr_eur_geant_vert")
    custody = CustodyService()
    prov_repo = CustodyProviderRepository()
    acc_repo = CustodyAccountRepository()

    try:
        client = db.query(Client).filter(Client.email == EMAIL).first()
        if client is None:
            client = _find_client_by_phone(db, PHONE_E164)

        if client is None:
            if not args.create_missing:
                print(
                    "Aucun client pour cet e-mail / téléphone. "
                    "Créez l’identité ailleurs ou relancez avec --create-missing (sandbox).",
                    file=sys.stderr,
                )
                sys.exit(1)
            person = Person(
                status="active",
                jurisdiction="EU",
                profile_json={
                    "collected": {
                        "first_name": "Géant",
                        "last_name": "Vert",
                        "phone_e164": PHONE_E164,
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
            print(f"✅ (--create-missing) Client PE créé : {client.id} ({EMAIL}, {PHONE_E164})")
        else:
            print(f"ℹ️  Client PE trouvé : {client.id} ({client.email})")

        modulr = prov_repo.get_by_name(db, "Modulr")
        if modulr is None:
            modulr = custody.create_provider(
                db,
                ProviderCreate(
                    name="Modulr",
                    provider_type=ProviderType.BANK,
                    jurisdiction="EU",
                    status=ProviderStatus.ACTIVE,
                ),
                actor,
            )
            print(f"✅ Provider Modulr créé : {modulr.id}")
        else:
            print(f"ℹ️  Provider Modulr : {modulr.id}")

        eur = acc_repo.find_client_account(db, client.id, "EUR")
        if eur is None:
            custody.create_client_account(
                db,
                AccountCreate(
                    provider_id=modulr.id,
                    account_type=CustodyAccountType.CLIENT_DEPOSIT,
                    currency="EUR",
                    account_holder_name=HOLDER_NAME,
                    client_id=client.id,
                    iban=DEFAULT_IBAN,
                    bic=DEFAULT_BIC,
                ),
                actor,
            )
            print(f"✅ Compte custody EUR Modulr créé (IBAN {DEFAULT_IBAN}, BIC {DEFAULT_BIC}).")
        else:
            eur.iban = DEFAULT_IBAN
            eur.bic = DEFAULT_BIC
            eur.provider_id = modulr.id
            if (eur.account_holder_name or "").strip() != HOLDER_NAME:
                eur.account_holder_name = HOLDER_NAME
            db.flush()
            print(f"ℹ️  Compte EUR existant mis à jour (Modulr, IBAN {DEFAULT_IBAN}).")

        db.commit()
        print("Terminé.")
    except Exception:
        db.rollback()
        raise


if __name__ == "__main__":
    main()
