#!/usr/bin/env python3
"""Supprime tous les « customers » (personnes + inscription + clients PE associés).

Équivalent à :
  - purge financière + ``pe_clients`` (comme ``purge_all_pe_clients``)
  - sessions d’inscription
  - lignes ``persons`` (OTP 2FA, etc. en cascade)
  - ``admin_users.person_id`` remis à NULL (comptes admin conservés)

À utiliser uniquement en **développement**.

Usage (depuis le répertoire ``api``)::

    python3 -m scripts.purge_all_customers

Variables d'environnement : ``DATABASE_URL`` (fichiers ``.env`` / ``.env.local`` comme l'API).
"""
from __future__ import annotations

import sys
from pathlib import Path


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


def main() -> None:
    _ensure_api_path()
    from sqlalchemy import text

    from database import SessionLocal
    from services.financial_reset.reset import TABLES_DELETE_ORDER

    db = SessionLocal()
    report: list[str] = []
    try:
        r = db.execute(text("UPDATE public.persons SET client_id = NULL WHERE client_id IS NOT NULL"))
        db.commit()
        report.append(f"persons.client_id → NULL: {r.rowcount}")

        for table in TABLES_DELETE_ORDER:
            try:
                res = db.execute(text(f"DELETE FROM public.{table}"))
                db.commit()
                report.append(f"DELETE {table}: {res.rowcount}")
            except Exception as e:
                db.rollback()
                err = str(e)
                if "does not exist" in err or "UndefinedTable" in err:
                    report.append(f"DELETE {table}: (skip — table absente)")
                else:
                    report.append(f"DELETE {table}: ERREUR {e!s}")

        r = db.execute(text("DELETE FROM public.pe_clients"))
        db.commit()
        report.append(f"DELETE pe_clients: {r.rowcount}")

        r = db.execute(text("UPDATE public.admin_users SET person_id = NULL WHERE person_id IS NOT NULL"))
        db.commit()
        report.append(f"admin_users.person_id → NULL: {r.rowcount}")

        r = db.execute(text("DELETE FROM public.registration_sessions"))
        db.commit()
        report.append(f"DELETE registration_sessions: {r.rowcount}")

        r = db.execute(text("DELETE FROM public.persons"))
        db.commit()
        report.append(f"DELETE persons: {r.rowcount}")

        for line in report:
            print(line)
        print("OK — tous les customers supprimés (persons + PE + sessions d’inscription).")
    except Exception as e:
        db.rollback()
        print(f"ÉCHEC: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
