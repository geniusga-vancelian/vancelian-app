#!/usr/bin/env python3
"""
Attribue un IBAN (et BIC) de test au compte de dépôt EUR d’un ``pe_clients``.

Usage (depuis la racine du projet) ::

  CLIENT_ID=<uuid> python3 -m api.scripts.set_current_client_iban
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import UUID

# IBAN/BIC de test (format français)
DEFAULT_IBAN = "FR7630006000011234567890189"
DEFAULT_BIC = "AGFBFRCC"


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


def main():
    _ensure_api_path()
    from database import SessionLocal
    from services.custody.repository import CustodyAccountRepository

    raw = (os.environ.get("CLIENT_ID") or "").strip()
    if not raw:
        print("Définissez CLIENT_ID (UUID du pe_clients).")
        sys.exit(1)
    try:
        current_id = UUID(raw)
    except ValueError:
        print(f"UUID invalide : {raw!r}")
        sys.exit(1)

    db = SessionLocal()
    try:
        account_repo = CustodyAccountRepository()
        account = account_repo.find_client_account(db, current_id, "EUR")
        if not account:
            print("Aucun compte de dépôt EUR trouvé pour ce client.")
            sys.exit(1)
        account.iban = DEFAULT_IBAN
        account.bic = DEFAULT_BIC
        db.commit()
        db.refresh(account)
        print(f"IBAN attribué au compte de dépôt : {DEFAULT_IBAN}")
        print(f"BIC : {DEFAULT_BIC}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
