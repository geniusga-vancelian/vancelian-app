#!/usr/bin/env python3
"""Supprime tous les comptes custody client dépôt et ne garde qu’un settlement entreprise Vancelian.

- Supprime les transactions / webhooks liés aux comptes retirés.
- Supprime les autres comptes ``company_settlement_account`` (ne garde qu’un seul).
- Attribue un IBAN FR de test (format 27 car.) au compte settlement conservé.

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.custody_only_vancelian_settlement
"""
from __future__ import annotations

import random
import sys
from pathlib import Path
from uuid import UUID


def _ensure_api_path() -> None:
    api_dir = Path(__file__).resolve().parent.parent
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    import os

    os.chdir(api_dir)
    try:
        from dotenv import load_dotenv

        for p in (
            api_dir / ".env.local",
            api_dir / ".env",
            api_dir.parent.parent.parent / ".env.arquantix",
            api_dir.parent.parent.parent / ".env",
        ):
            if p.exists():
                load_dotenv(p)
    except ImportError:
        pass


def _random_fr_ibans() -> str:
    """IBAN FR 27 caractères (format plausible, usage dev / sandbox)."""
    return "FR76" + "".join(str(random.randint(0, 9)) for _ in range(23))


def _delete_account_cascade(db, account_id: UUID) -> None:
    from sqlalchemy import text

    db.execute(
        text(
            """
            DELETE FROM public.custody_webhook_events
            WHERE linked_transaction_id IN (
                SELECT id FROM public.custody_transactions WHERE account_id = :aid
            )
            """
        ),
        {"aid": account_id},
    )
    db.execute(
        text("DELETE FROM public.custody_transactions WHERE account_id = :aid"),
        {"aid": account_id},
    )
    db.execute(
        text("DELETE FROM public.custody_account_balances WHERE account_id = :aid"),
        {"aid": account_id},
    )
    db.execute(
        text("DELETE FROM public.custody_accounts WHERE id = :aid"),
        {"aid": account_id},
    )


def main() -> None:
    _ensure_api_path()
    from sqlalchemy import text

    from database import SessionLocal
    from services.custody.models import CustodyAccount

    db = SessionLocal()
    try:
        # 1) Choisir le settlement à conserver : Vancelian + EUR + company_settlement
        candidates = (
            db.query(CustodyAccount)
            .filter(
                CustodyAccount.account_type == "company_settlement_account",
                CustodyAccount.currency == "EUR",
            )
            .order_by(
                CustodyAccount.is_master_account.desc(),
                CustodyAccount.created_at.asc(),
            )
            .all()
        )
        keep: CustodyAccount | None = None
        for acc in candidates:
            if "vancelian" in (acc.account_holder_name or "").lower():
                keep = acc
                break
        if keep is None and candidates:
            keep = candidates[0]

        if keep is None:
            print(
                "ERREUR: aucun compte company_settlement_account EUR trouvé. "
                "Créez-en un via l’admin ou api.scripts.ensure_single_modulr_and_settlement.",
                file=sys.stderr,
            )
            sys.exit(1)

        keep_id = keep.id
        print(f"Conservation du settlement : id={keep_id} holder={keep.account_holder_name!r}")

        # 2) Supprimer tous les client_deposit_account
        client_ids = [
            r[0]
            for r in db.execute(
                text(
                    "SELECT id FROM public.custody_accounts "
                    "WHERE account_type = 'client_deposit_account'"
                )
            ).fetchall()
        ]
        for aid in client_ids:
            _delete_account_cascade(db, aid)
            db.commit()
            print(f"  Supprimé client_deposit_account {aid}")

        # 3) Supprimer les autres settlement (sauf keep)
        other_settlement = [
            r[0]
            for r in db.execute(
                text(
                    """
                    SELECT id FROM public.custody_accounts
                    WHERE account_type = 'company_settlement_account'
                      AND id != :kid
                    """
                ),
                {"kid": keep_id},
            ).fetchall()
        ]
        for aid in other_settlement:
            _delete_account_cascade(db, aid)
            db.commit()
            print(f"  Supprimé company_settlement_account doublon {aid}")

        # 4) IBAN aléatoire sur le compte conservé
        iban = _random_fr_ibans()
        db.execute(
            text(
                "UPDATE public.custody_accounts SET iban = :iban, updated_at = NOW() "
                "WHERE id = :kid"
            ),
            {"iban": iban, "kid": keep_id},
        )
        db.commit()
        print(f"IBAN mis à jour sur le settlement Vancelian : {iban}")

        # Récap
        n = db.execute(text("SELECT count(*) FROM public.custody_accounts")).scalar()
        print(f"OK — {n} compte(s) custody restant(s).")
    except Exception as e:
        db.rollback()
        print(f"ÉCHEC: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
