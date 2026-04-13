#!/usr/bin/env python3
"""
Génération locale de PDF pour itération design (sans Flutter).

Réutilise les mêmes builders / mappers / renderers que les routes :
  - operation : services.test_clients.router (pipeline operation_statement_*)
  - euro      : build_iban_statement_payload_for_client + iban_statement_renderer

Prérequis :
  - DATABASE_URL pointant vers la même base que la stack (ex. postgres Docker sur 5443)
  - WeasyPrint utilisable (souvent : exécuter depuis le conteneur arquantix-api)

Exemples (depuis la racine du dépôt) :

  PYTHONPATH=services/arquantix/api DATABASE_URL=postgresql://arquantix:arquantix@127.0.0.1:5443/arquantix \\
    python3 services/arquantix/api/scripts/generate_pdf_preview.py \\
      --email gaelitier@gmail.com --type operation --latest

  PYTHONPATH=services/arquantix/api DATABASE_URL=... python3 .../generate_pdf_preview.py \\
      --email gaelitier@gmail.com --type operation --transaction-id <UUID>

  PYTHONPATH=services/arquantix/api DATABASE_URL=... python3 .../generate_pdf_preview.py \\
      --email gaelitier@gmail.com --type euro
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from uuid import UUID

# Répertoire package API (services/arquantix/api)
_API_ROOT = Path(__file__).resolve().parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from sqlalchemy.orm import Session  # noqa: E402

from database import SessionLocal  # noqa: E402
from services.exchange.models import ExchangeOrder  # noqa: E402
from services.portfolio_engine.clients.models import Client as PeClient  # noqa: E402
from services.custody.models import CustodyAccount, CustodyTransaction  # noqa: E402
from services.test_clients.operation_resolver import OperationResolver  # noqa: E402


def _default_out_dir() -> Path:
    cwd = Path.cwd()
    candidate = cwd / "docs" / "arquantix" / "generated-pdfs"
    if candidate.parent.parent.name == "docs" or (cwd / "docs" / "arquantix").is_dir():
        return candidate
    return cwd / "generated-pdfs"


def _email_slug(email: str) -> str:
    s = email.strip().lower()
    s = s.replace("@", "-at-")
    s = re.sub(r"[^a-z0-9\-]+", "-", s)
    return s.strip("-") or "client"


def _get_client_by_email(db: Session, email: str) -> PeClient | None:
    e = email.strip().lower()
    return db.query(PeClient).filter(PeClient.email.isnot(None), PeClient.email.ilike(e)).first()


def _latest_custody_tx_id(db: Session, client: PeClient) -> UUID | None:
    row = (
        db.query(CustodyTransaction)
        .join(CustodyAccount, CustodyTransaction.account_id == CustodyAccount.id)
        .filter(
            CustodyAccount.client_id == client.id,
            CustodyTransaction.status == "completed",
        )
        .order_by(CustodyTransaction.created_at.desc())
        .first()
    )
    return row.id if row else None


def _latest_exchange_order_id(db: Session, client: PeClient) -> UUID | None:
    row = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client.id,
            ExchangeOrder.status == "completed",
        )
        .order_by(ExchangeOrder.created_at.desc())
        .first()
    )
    return row.id if row else None


def _resolve_latest_transaction_id(
    db: Session, client: PeClient, source: str
) -> tuple[UUID, str] | None:
    """Retourne (transaction_id, origine) ou None."""
    custody_id = _latest_custody_tx_id(db, client)
    exchange_id = _latest_exchange_order_id(db, client)

    if source == "custody":
        if custody_id is None:
            return None
        return custody_id, "custody"
    if source == "exchange":
        if exchange_id is None:
            return None
        return exchange_id, "exchange"

    # auto : le plus récent entre les deux (par created_at)
    c_row = (
        db.query(CustodyTransaction)
        .join(CustodyAccount, CustodyTransaction.account_id == CustodyAccount.id)
        .filter(
            CustodyAccount.client_id == client.id,
            CustodyTransaction.status == "completed",
        )
        .order_by(CustodyTransaction.created_at.desc())
        .first()
    )
    e_row = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client.id,
            ExchangeOrder.status == "completed",
        )
        .order_by(ExchangeOrder.created_at.desc())
        .first()
    )
    if c_row is None and e_row is None:
        return None
    if c_row is None:
        return e_row.id, "exchange"
    if e_row is None:
        return c_row.id, "custody"
    if c_row.created_at >= e_row.created_at:
        return c_row.id, "custody"
    return e_row.id, "exchange"


def _generate_euro_pdf(db: Session, client: PeClient, out_path: Path) -> None:
    from pdf.iban_statement_mapper import payload_to_template_context
    from pdf.iban_statement_renderer import render_iban_statement_pdf
    from services.test_clients.iban_statement_payload import build_iban_statement_payload_for_client

    payload = build_iban_statement_payload_for_client(db, client)
    if payload is None:
        sys.stderr.write(
            "Erreur : aucun compte custody EUR pour ce client (même condition que l’API 404).\n"
        )
        sys.exit(2)
    ctx = payload_to_template_context(payload)
    pdf_bytes = render_iban_statement_pdf(ctx)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(pdf_bytes)


def _write_operation_pdf_to_file(
    db: Session,
    client: PeClient,
    transaction_id: UUID,
    out_path: Path,
    *,
    persist_snapshot: bool,
) -> None:
    from pdf.operation_statement_mapper import operation_statement_payload_to_template_context
    from pdf.operation_statement_renderer import render_operation_statement_pdf
    from services.test_clients.custody_operation_statement import build_custody_operation_statement_payload
    from services.test_clients.exchange_operation_statement import build_exchange_operation_statement_payload
    from services.test_clients.operation_statement_errors import OperationStatementHttpError
    from services.test_clients.operation_statement_snapshot_service import (
        create_snapshot,
        get_snapshot,
        payload_from_snapshot_row,
    )

    ref = OperationResolver.resolve(db, client, transaction_id)
    if ref is None:
        sys.stderr.write(
            f"Erreur : transaction {transaction_id} introuvable ou non associée à ce client.\n"
        )
        sys.exit(2)

    snap_row = get_snapshot(db, client.id, ref)
    if snap_row is not None:
        try:
            payload = payload_from_snapshot_row(snap_row)
        except Exception as exc:
            sys.stderr.write(f"Erreur : snapshot invalide : {exc}\n")
            sys.exit(2)
    else:
        try:
            if ref.source_system == "custody":
                payload = build_custody_operation_statement_payload(
                    db, client, transaction_id, resolved_ref=ref
                )
            else:
                payload = build_exchange_operation_statement_payload(
                    db, client, transaction_id, resolved_ref=ref
                )
        except OperationStatementHttpError as exc:
            sys.stderr.write(f"Erreur métier : {exc.message} (code={exc.code})\n")
            sys.exit(2)

    ctx = operation_statement_payload_to_template_context(payload)
    pdf_bytes = render_operation_statement_pdf(ctx)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(pdf_bytes)

    if persist_snapshot and snap_row is None:
        try:
            create_snapshot(db, client.id, ref, payload)
            db.commit()
        except Exception as exc:
            sys.stderr.write(f"Avertissement : snapshot non enregistré : {exc}\n")
            db.rollback()


def main() -> None:
    p = argparse.ArgumentParser(description="Génère des PDF localement (même pipeline que l’API).")
    p.add_argument("--email", required=True, help="Email du client (pe_clients.email)")
    p.add_argument(
        "--type",
        choices=("operation", "euro"),
        required=True,
        help="operation = relevé unitaire ; euro = relevé IBAN global",
    )
    p.add_argument("--transaction-id", type=UUID, default=None, help="UUID custody ou exchange")
    p.add_argument(
        "--latest",
        action="store_true",
        help="Dernière transaction éligible (completed) — custody, exchange ou auto",
    )
    p.add_argument(
        "--source-system",
        choices=("auto", "custody", "exchange"),
        default="auto",
        help="Pour --latest : filtre la source (défaut: auto)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help=f"Dossier de sortie (défaut: {_default_out_dir()})",
    )
    p.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Ne pas persister le snapshot PR5 après génération operation PDF",
    )
    p.add_argument(
        "--open",
        action="store_true",
        help="macOS : ouvrir le PDF avec `open`",
    )
    args = p.parse_args()

    out_dir = args.out_dir or _default_out_dir()
    out_dir = out_dir.resolve()

    if args.type == "operation":
        if args.transaction_id is None and not args.latest:
            sys.stderr.write("Erreur : fournir --transaction-id ou --latest pour --type operation.\n")
            sys.exit(2)
        if args.transaction_id is not None and args.latest:
            sys.stderr.write("Erreur : ne pas combiner --transaction-id et --latest.\n")
            sys.exit(2)

    db: Session = SessionLocal()
    try:
        client = _get_client_by_email(db, args.email)
        if client is None:
            sys.stderr.write(f"Erreur : aucun client avec l’email « {args.email} ».\n")
            sys.exit(2)

        slug = _email_slug(args.email)

        if args.type == "euro":
            fname = f"euro-{slug}.pdf"
            out_path = out_dir / fname
            try:
                _generate_euro_pdf(db, client, out_path)
            except (OSError, ImportError) as exc:
                sys.stderr.write(
                    "Erreur WeasyPrint / libs système : "
                    f"{exc}\n"
                    "Astuce : lancer ce script dans le conteneur arquantix-api "
                    "où Cairo/Pango sont installés.\n"
                )
                sys.exit(3)
            except Exception as exc:
                sys.stderr.write(f"Erreur lors de la génération euro : {exc}\n")
                sys.exit(2)
        else:
            if args.latest:
                resolved = _resolve_latest_transaction_id(db, client, args.source_system)
                if resolved is None:
                    sys.stderr.write(
                        "Erreur : aucune transaction custody/exchange « completed » trouvée pour ce client.\n"
                    )
                    sys.exit(2)
                tx_id, origin = resolved
                fname = f"operation-{slug}-latest-{origin}.pdf"
            else:
                tx_id = args.transaction_id  # type: ignore[assignment]
                fname = f"operation-{slug}-{tx_id}.pdf"

            out_path = out_dir / fname
            persist = not args.no_snapshot
            try:
                _write_operation_pdf_to_file(
                    db, client, tx_id, out_path, persist_snapshot=persist
                )
            except FileNotFoundError as exc:
                sys.stderr.write(f"Erreur : ressource template/CSS manquante : {exc}\n")
                sys.exit(3)
            except (OSError, ImportError) as exc:
                sys.stderr.write(
                    f"Erreur WeasyPrint / système : {exc}\n"
                    "Astuce : exécuter dans le conteneur Docker API.\n"
                )
                sys.exit(3)
            except Exception as exc:
                sys.stderr.write(f"Erreur lors de la génération : {exc}\n")
                sys.exit(2)

        print(f"OK — PDF écrit : {out_path}")
        print(f"Open: {out_path}")
        if args.open and sys.platform == "darwin":
            subprocess.run(["open", str(out_path)], check=False)
    finally:
        db.close()


if __name__ == "__main__":
    main()
