#!/usr/bin/env python3
"""
Conserver un seul provider bank « Modulr » et un compte settlement EUR.

- Supprime tous les providers sauf Modulr (type bank). Si Modulr n'existe pas, le crée.
- Supprime les données liées aux providers supprimés (webhooks, transactions, balances, comptes).
- Crée un compte company_settlement_account EUR pour Modulr s'il n'existe pas déjà.

Les comptes client custody (dépôt EUR, etc.) ne sont plus filtrés par un « client current »
en base : utilisez les scripts dédiés ou l'API admin par client.

Usage (depuis la racine du projet) :
  python3 -m api.scripts.ensure_single_modulr_and_settlement

Environnement : DATABASE_URL doit être défini (.env.local / .env).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import UUID


def _ensure_api_path():
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


def run():
    from sqlalchemy import text

    from database import SessionLocal
    from services.custody.enums import CustodyAccountType, ProviderStatus, ProviderType
    from services.custody.models import CustodyAccount, CustodyProvider
    from services.custody.repository import CustodyAccountRepository, CustodyProviderRepository
    from services.custody.schemas import AccountCreate, ProviderCreate
    from services.custody.service import CustodyService
    from services.portfolio_engine.hardening.security.context import ActorContext

    db = SessionLocal()
    actor = ActorContext(actor_type="script", actor_id="ensure_modulr")
    _provider_repo = CustodyProviderRepository()
    _account_repo = CustodyAccountRepository()
    _svc = CustodyService()

    report = {
        "created_modulr": False,
        "deleted_providers": 0,
        "deleted_accounts": 0,
        "created_settlement": False,
        "errors": [],
    }

    try:
        # 1) Get or create Modulr
        modulr = _provider_repo.get_by_name(db, "Modulr")
        if modulr is None:
            payload = ProviderCreate(name="Modulr", provider_type=ProviderType.BANK, status=ProviderStatus.ACTIVE)
            modulr = _svc.create_provider(db, payload, actor)
            db.commit()
            db.refresh(modulr)
            report["created_modulr"] = True
            print("Provider Modulr créé.")
        else:
            print("Provider Modulr déjà présent.")

        modulr_id = str(modulr.id)

        # 2) Delete all other providers (and their accounts, balances, transactions, webhooks)
        all_providers, _ = _provider_repo.list(db, skip=0, limit=500)
        for p in all_providers:
            if str(p.id) == modulr_id:
                continue
            # Get accounts for this provider
            accounts = db.query(CustodyAccount).filter(CustodyAccount.provider_id == p.id).all()
            for acc in accounts:
                aid = acc.id
                # Webhook events pointing to transactions of this account
                db.execute(
                    text("""
                    DELETE FROM public.custody_webhook_events
                    WHERE linked_transaction_id IN (
                        SELECT id FROM public.custody_transactions WHERE account_id = :aid
                    )
                """),
                    {"aid": aid},
                )
                db.execute(text("DELETE FROM public.custody_transactions WHERE account_id = :aid"), {"aid": aid})
                db.execute(text("DELETE FROM public.custody_account_balances WHERE account_id = :aid"), {"aid": aid})
                db.execute(text("DELETE FROM public.custody_accounts WHERE id = :aid"), {"aid": aid})
                report["deleted_accounts"] += 1
            db.execute(text("DELETE FROM public.custody_providers WHERE id = :pid"), {"pid": p.id})
            report["deleted_providers"] += 1
            db.commit()

        if report["deleted_providers"]:
            print(f"Providers supprimés : {report['deleted_providers']}. Comptes supprimés : {report['deleted_accounts']}.")

        # 3) Ensure one EUR settlement account for Modulr
        existing = _account_repo.find_settlement_account(db, "EUR")
        if existing is None:
            payload = AccountCreate(
                provider_id=UUID(modulr_id),
                account_type=CustodyAccountType.COMPANY_SETTLEMENT,
                currency="EUR",
                account_holder_name="Modulr Treasury EUR",
            )
            _svc.create_settlement_account(db, payload, actor)
            db.commit()
            report["created_settlement"] = True
            print("Compte de settlement EUR créé pour Modulr.")
        else:
            print("Compte de settlement EUR déjà présent.")

        return report
    except Exception as e:
        db.rollback()
        report["errors"].append(str(e))
        raise
    finally:
        db.close()


def main():
    _ensure_api_path()
    run()
    print("Terminé.")


if __name__ == "__main__":
    main()
