#!/usr/bin/env python3
"""
Outil local : lister les admins et optionnellement renseigner `mobile_e164` (E.164).

Usage :
  cd api && python3 scripts/local_admin_mobile_e164.py list
  cd api && python3 scripts/local_admin_mobile_e164.py set --email 'a@b.com' --phone '+33612345678'

Ne pas utiliser en production. Charge `.env.local` puis `.env` comme `database.py`.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from sqlalchemy import create_engine, text  # noqa: E402


def _normalize_e164(raw: str) -> str:
    t = re.sub(r"\s+", "", (raw or "").strip())
    if not t.startswith("+"):
        t = "+" + t.lstrip("+")
    return t


def cmd_list(engine) -> None:
    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT id, email, mobile_e164 FROM admin_users ORDER BY id")
        )
        rows = r.fetchall()
    print(f"{'id':<6} {'email':<40} mobile_e164")
    print("-" * 80)
    for row in rows:
        print(f"{row[0]:<6} {row[1]:<40} {row[2]!r}")


def cmd_set(engine, email: str, phone: str) -> None:
    e164 = _normalize_e164(phone)
    if len(e164) < 10:
        print("ERREUR: numéro trop court après normalisation.", file=sys.stderr)
        sys.exit(1)
    with engine.begin() as conn:
        r = conn.execute(
            text("UPDATE admin_users SET mobile_e164 = :p WHERE lower(email) = lower(:e)"),
            {"p": e164, "e": email.strip()},
        )
        if r.rowcount != 1:
            print(
                f"ERREUR: aucune ou plusieurs lignes mises à jour (rowcount={r.rowcount}).",
                file=sys.stderr,
            )
            sys.exit(1)
    print(f"OK: mobile_e164={e164!r} pour email={email!r}")


def main() -> None:
    p = argparse.ArgumentParser(description="Admin mobile_e164 (local)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Lister id, email, mobile_e164")

    sp = sub.add_parser("set", help="Définir mobile_e164 pour un email")
    sp.add_argument("--email", required=True)
    sp.add_argument("--phone", required=True, help="E.164 ou 06… avec +33…")

    args = p.parse_args()
    import os

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL manquant", file=sys.stderr)
        sys.exit(1)
    engine = create_engine(url)

    if args.cmd == "list":
        cmd_list(engine)
    else:
        cmd_set(engine, args.email, args.phone)


if __name__ == "__main__":
    main()
