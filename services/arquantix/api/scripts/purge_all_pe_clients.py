#!/usr/bin/env python3
"""Supprime toutes les données liées aux clients PE puis toutes les lignes ``pe_clients``.

À utiliser uniquement sur une base de **développement** (repartir à zéro côté client).

Usage (depuis le répertoire ``api``)::

    python3 -m scripts.purge_all_pe_clients

Variables d'environnement : ``DATABASE_URL`` (ou fichier ``.env`` chargé comme l'API).
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

        for p in (api_dir / ".env.local", api_dir / ".env"):
            if p.exists():
                load_dotenv(p)
                break
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
        report.append(f"persons.client_id mis à NULL: {r.rowcount}")

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

        for line in report:
            print(line)
        print("OK — purge clients terminée.")
    except Exception as e:
        db.rollback()
        print(f"ÉCHEC: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
