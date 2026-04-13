#!/usr/bin/env python3
"""
Compte custody EUR (provider Modulr) + IBAN aléatoire pour un client identifié par téléphone E.164.

Par défaut : **résolution stricte** (``Person`` + ``pe_clients``) via
``resolve_person_and_pe_client_for_custody`` — **aucune création d’identité**.

Pour l’ancien comportement (création Person + PE synthétique si introuvable), passer
``--create-missing`` (réservé sandbox / dev).

Usage (depuis ``services/arquantix/api``, avec ``DATABASE_URL``)::

    python3 scripts/ensure_modulr_eur_client_by_phone.py
    python3 scripts/ensure_modulr_eur_client_by_phone.py --phone +33600000001
    python3 scripts/ensure_modulr_eur_client_by_phone.py --phone +33600000001 --create-missing

Variables d’environnement (optionnel)::

    PHONE_E164=+33600000001
"""
from __future__ import annotations

import argparse
import os
import random
import re
import sys
from pathlib import Path

DEFAULT_PHONE = "+33600000001"
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


def _random_fr_iban() -> str:
    """IBAN FR 27 caractères (format plausible, dev / sandbox)."""
    return "FR76" + "".join(str(random.randint(0, 9)) for _ in range(23))


def _synthetic_email(phone_e164: str) -> str:
    digits = re.sub(r"\D", "", phone_e164)
    return f"phone-{digits}@sandbox.arquantix.local"


def main() -> None:
    _ensure_api_path()

    parser = argparse.ArgumentParser(description="Compte EUR Modulr + IBAN aléatoire par téléphone.")
    parser.add_argument(
        "--phone",
        default=os.environ.get("PHONE_E164", DEFAULT_PHONE).strip(),
        help=f"Numéro E.164 (défaut: {DEFAULT_PHONE})",
    )
    parser.add_argument(
        "--create-missing",
        action="store_true",
        help="Sandbox uniquement : créer Person + pe_client synthétiques si résolution impossible.",
    )
    args = parser.parse_args()
    phone = _normalize_phone_e164(args.phone)
    if not phone:
        print("Numéro de téléphone invalide.", file=sys.stderr)
        sys.exit(1)

    from database import Person, SessionLocal
    from services.custody.enums import CustodyAccountType, ProviderStatus, ProviderType
    from services.custody.identity_resolution import (
        CustodyIdentityResolutionError,
        resolve_person_and_pe_client_for_custody,
    )
    from services.custody.repository import CustodyAccountRepository, CustodyProviderRepository
    from services.custody.schemas import AccountCreate, ProviderCreate
    from services.custody.service import CustodyService
    from services.portfolio_engine.clients.enums import ClientStatus, KycStatus
    from services.portfolio_engine.clients.models import Client
    from services.portfolio_engine.hardening.security.context import ActorContext

    db = SessionLocal()
    actor = ActorContext(actor_type="script", actor_id="ensure_modulr_eur_client_by_phone")
    custody = CustodyService()
    prov_repo = CustodyProviderRepository()
    acc_repo = CustodyAccountRepository()

    iban = _random_fr_iban()
    holder = f"Client {phone}"

    try:
        client = None
        try:
            resolution = resolve_person_and_pe_client_for_custody(db, phone_e164=phone)
            client = db.query(Client).filter(Client.id == resolution.pe_client_id).first()
            print(
                f"ℹ️  Résolution stricte : person_id={resolution.person_id} "
                f"pe_client_id={resolution.pe_client_id} ({resolution.pe_client_email})"
            )
        except CustodyIdentityResolutionError as exc:
            if not args.create_missing:
                print(
                    "Échec résolution stricte (aucune ambiguïté autorisée). "
                    "Créez le pe_client via l’app ou un flux canonique, ou utilisez "
                    "`--create-missing` en sandbox uniquement.\n"
                    f"Détail : {exc}",
                    file=sys.stderr,
                )
                sys.exit(1)
            email = _synthetic_email(phone)
            existing_email = db.query(Client).filter(Client.email == email).first()
            if existing_email is not None:
                client = existing_email
                print(f"ℹ️  Client trouvé par e-mail synthétique : {client.id} ({email})")
            else:
                person = Person(
                    status="active",
                    jurisdiction="EU",
                    profile_json={
                        "collected": {
                            "first_name": "Client",
                            "last_name": phone,
                            "phone_e164": phone,
                        }
                    },
                )
                db.add(person)
                db.flush()
                client = Client(
                    email=email,
                    status=ClientStatus.ACTIVE.value,
                    kyc_status=KycStatus.APPROVED.value,
                    reference_currency="EUR",
                    person_id=person.id,
                )
                db.add(client)
                db.flush()
                print(f"✅ (--create-missing) Client PE créé : {client.id} ({email}, {phone})")

        assert client is not None

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
                    account_holder_name=holder,
                    client_id=client.id,
                    iban=iban,
                    bic=DEFAULT_BIC,
                ),
                actor,
            )
            print(f"✅ Compte custody EUR Modulr créé (IBAN {iban}, BIC {DEFAULT_BIC}).")
        else:
            eur.iban = iban
            eur.bic = DEFAULT_BIC
            eur.provider_id = modulr.id
            if (eur.account_holder_name or "").strip() != holder:
                eur.account_holder_name = holder
            db.flush()
            print(f"ℹ️  Compte EUR existant mis à jour (Modulr, IBAN {iban}).")

        db.commit()
        print("Terminé.")
    except Exception:
        db.rollback()
        raise


if __name__ == "__main__":
    main()
