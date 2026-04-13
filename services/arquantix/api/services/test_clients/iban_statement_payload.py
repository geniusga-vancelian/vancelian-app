"""
Construction de IbanStatementPayload depuis custody + profil personne (usage interne PDF uniquement).
"""
from __future__ import annotations

# NOTE:
# Avoid generic local names like 'desc', 'list', 'type', 'id', etc.
# They can shadow builtins or helpers (e.g. SQLAlchemy sql_desc) and cause UnboundLocalError.

import calendar
import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import asc, desc as sql_desc
from sqlalchemy.orm import Session

from database import Person
from pdf.iban_statement_schema import (
    IbanStatementAccount,
    IbanStatementClient,
    IbanStatementPayload,
    IbanStatementPeriod,
    IbanStatementSummary,
    IbanStatementTransaction,
)
from services.custody.enums import TransactionDirection
from services.custody.models import CustodyTransaction
from services.custody.repository import (
    CustodyAccountRepository,
    CustodyBalanceRepository,
    CustodyTransactionRepository,
)
from services.portfolio_engine.clients.models import Client
from services.registration.service import get_person_collected_value
from services.test_clients.mobile_profile import load_person_for_client
from services.test_clients.schemas import (
    TRANSACTION_KIND_TITLE_MAP,
    TRANSACTION_TITLE_MAP,
)

logger = logging.getLogger(__name__)


def _s(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        stripped = val.strip()
        return stripped or None
    return str(val).strip() or None


def _to_decimal(val) -> Decimal:
    return val if isinstance(val, Decimal) else Decimal(str(val))


def _booking_date_utc(dt) -> date:
    """Date comptable en UTC (relevé bancaire cohérent si ``created_at`` est tz-aware)."""
    if dt is None:
        return date.today()
    if getattr(dt, "tzinfo", None) is not None:
        return dt.astimezone(timezone.utc).date()
    return dt.date()


def _first_collected(person: Optional[Person], slugs: tuple[str, ...]) -> Optional[str]:
    if person is None:
        return None
    for slug in slugs:
        raw_value = get_person_collected_value(person, slug)
        out = _s(raw_value)
        if out:
            return out
    return None


def _tx_description(tx: CustodyTransaction) -> str:
    kind = tx.transaction_kind
    title = (
        TRANSACTION_KIND_TITLE_MAP.get(kind) if kind else None
    ) or TRANSACTION_TITLE_MAP.get(
        tx.transaction_type,
        tx.transaction_type.replace("_", " ").title(),
    )
    meta = tx.metadata_ or {}
    remitter_or_narrative = meta.get("remitter_name") or meta.get("narrative") or ""
    if remitter_or_narrative:
        return f"{title} — {remitter_or_narrative}"
    return title


def _iban_account_number(iban: str) -> str:
    """Numéro de compte affiché : derniers 11 caractères alphanumériques (usage courant FR), sinon IBAN compact."""
    compact = "".join(ch for ch in iban if ch.isalnum())
    if len(compact) >= 11:
        return compact[-11:]
    return compact or "—"


def _custody_signed_delta(custody_tx: CustodyTransaction) -> Decimal:
    amt = _to_decimal(custody_tx.amount)
    if custody_tx.direction == TransactionDirection.CREDIT.value:
        return amt
    return -amt


def build_iban_statement_payload_for_client(
    db: Session,
    client: Client,
    *,
    max_transactions: int = 5000,
    calendar_month: Optional[tuple[int, int]] = None,
) -> Optional[IbanStatementPayload]:
    """
    Retourne None si aucun compte dépôt EUR actif.

    Mouvements : ``completed`` uniquement. On affiche les **derniers**
    ``max_transactions`` (les plus récents), puis ordre chronologique dans le PDF.

    Soldes : ``opening`` = solde **juste avant** la plus ancienne opération de cette fenêtre ;
    ``closing`` = solde custody actuel (**vérité comptable**). Il coïncide avec le dernier
    ``balance_after`` des lignes affichées car ces lignes couvrent exactement la chaîne de
    mouvements entre ces deux soldes **pour la fenêtre chargée**. Si l’historique dépasse
    ``max_transactions``, le relevé ne montre qu’une **fraction récente** de l’historique :
    le solde de clôture reste le solde réel du compte, pas une somme partielle.

    Si ``calendar_month`` est fourni, relevé limité à ce mois calendaire UTC (usage admin).
    """
    if calendar_month is not None:
        y, m = calendar_month
        return _build_iban_statement_payload_calendar_month_utc(db, client, y, m)

    account = CustodyAccountRepository.find_client_account(db, client.id, "EUR")
    if account is None:
        return None

    balance_row = CustodyBalanceRepository.get_by_account_id(db, account.id)
    available = _to_decimal(balance_row.available_balance) if balance_row is not None else Decimal("0")

    _tx_filter = (
        CustodyTransaction.account_id == account.id,
        CustodyTransaction.status == "completed",
    )
    total_completed = db.query(CustodyTransaction).filter(*_tx_filter).count()

    # Derniers N mouvements (les plus récents), puis ordre chronologique pour le relevé.
    transactions_newest_first = (
        db.query(CustodyTransaction)
        .filter(*_tx_filter)
        .order_by(
            sql_desc(CustodyTransaction.created_at),
            sql_desc(CustodyTransaction.id),
        )
        .limit(max_transactions)
        .all()
    )
    txs = list(reversed(transactions_newest_first))

    if total_completed > len(txs):
        logger.warning(
            "iban_statement: transaction window truncated account_id=%s total_completed=%s shown=%s",
            account.id,
            total_completed,
            len(txs),
        )

    signed_deltas: list[Decimal] = [_custody_signed_delta(tx) for tx in txs]

    total_movement = sum(signed_deltas, Decimal("0"))
    opening = available - total_movement

    stmt_txs: list[IbanStatementTransaction] = []
    running = opening
    money_in = Decimal("0")
    money_out = Decimal("0")

    for custody_tx, signed_delta in zip(txs, signed_deltas):
        running = running + signed_delta
        booking_day = _booking_date_utc(custody_tx.created_at)
        tx_description = _tx_description(custody_tx)
        amt_abs = _to_decimal(custody_tx.amount)
        if signed_delta > 0:
            money_in += amt_abs
            stmt_txs.append(
                IbanStatementTransaction(
                    booking_date=booking_day,
                    description=tx_description,
                    amount_in=amt_abs,
                    amount_out=None,
                    balance_after=running,
                )
            )
        else:
            money_out += amt_abs
            stmt_txs.append(
                IbanStatementTransaction(
                    booking_date=booking_day,
                    description=tx_description,
                    amount_in=None,
                    amount_out=amt_abs,
                    balance_after=running,
                )
            )

    # Solde de clôture = solde custody réel. Avec fenêtre tronquée, il reste aligné avec
    # le dernier balance_after des lignes affichées (fenêtre = N derniers completed).
    closing = available

    if txs:
        period_start = _booking_date_utc(txs[0].created_at)
        period_end = _booking_date_utc(txs[-1].created_at)
    else:
        today = datetime.now(timezone.utc).date()
        period_start = period_end = today

    person = load_person_for_client(db, client)
    line1 = _first_collected(person, ("address_line_1", "street_address", "street", "address")) or "—"
    postal = _first_collected(person, ("postal_code", "zip", "zip_code")) or "—"
    city = _first_collected(person, ("city", "locality", "town")) or "—"
    country = _first_collected(person, ("country", "country_code")) or "—"

    iban = (account.iban or "").strip()
    bic = (account.bic or "").strip()
    currency_code = (account.currency or "EUR")[:3].upper()

    return IbanStatementPayload(
        generated_at=datetime.now(timezone.utc),
        period=IbanStatementPeriod(date_from=period_start, date_to=period_end),
        client=IbanStatementClient(
            full_name=account.account_holder_name or "—",
            address_line_1=line1,
            postal_code=postal,
            city=city,
            country=country,
        ),
        account=IbanStatementAccount(
            account_name=currency_code or "—",
            currency=currency_code,
            iban=iban or "—",
            bic=bic or "—",
            account_number=_iban_account_number(iban) if iban and iban != "—" else "—",
        ),
        summary=IbanStatementSummary(
            opening_balance=opening,
            closing_balance=closing,
            money_in=money_in if txs else None,
            money_out=money_out if txs else None,
        ),
        transactions=stmt_txs,
    )


def _build_iban_statement_payload_calendar_month_utc(
    db: Session,
    client: Client,
    year: int,
    month: int,
) -> Optional[IbanStatementPayload]:
    """Relevé EUR limité à un mois calendaire (bornes UTC). Usage admin / support."""
    account = CustodyAccountRepository.find_client_account(db, client.id, "EUR")
    if account is None:
        return None

    balance_row = CustodyBalanceRepository.get_by_account_id(db, account.id)
    _ = _to_decimal(balance_row.available_balance) if balance_row is not None else Decimal("0")

    now = datetime.now(timezone.utc)
    start_dt = datetime.combine(date(year, month, 1), time.min, tzinfo=timezone.utc)
    last_dom = calendar.monthrange(year, month)[1]
    eod = time(23, 59, 59, 999999)
    month_end_dt = datetime.combine(date(year, month, last_dom), eod, tzinfo=timezone.utc)
    end_dt = min(now, month_end_dt)

    base = (
        CustodyTransaction.account_id == account.id,
        CustodyTransaction.status == "completed",
    )

    pre_txs = (
        db.query(CustodyTransaction)
        .filter(*base, CustodyTransaction.created_at < start_dt)
        .order_by(asc(CustodyTransaction.created_at), asc(CustodyTransaction.id))
        .all()
    )
    opening = sum((_custody_signed_delta(tx) for tx in pre_txs), Decimal("0"))

    month_txs = (
        db.query(CustodyTransaction)
        .filter(
            *base,
            CustodyTransaction.created_at >= start_dt,
            CustodyTransaction.created_at <= end_dt,
        )
        .order_by(asc(CustodyTransaction.created_at), asc(CustodyTransaction.id))
        .all()
    )

    stmt_txs: list[IbanStatementTransaction] = []
    running = opening
    money_in = Decimal("0")
    money_out = Decimal("0")

    for custody_tx in month_txs:
        signed_delta = _custody_signed_delta(custody_tx)
        running = running + signed_delta
        booking_day = _booking_date_utc(custody_tx.created_at)
        tx_description = _tx_description(custody_tx)
        amt_abs = _to_decimal(custody_tx.amount)
        if signed_delta > 0:
            money_in += amt_abs
            stmt_txs.append(
                IbanStatementTransaction(
                    booking_date=booking_day,
                    description=tx_description,
                    amount_in=amt_abs,
                    amount_out=None,
                    balance_after=running,
                )
            )
        else:
            money_out += amt_abs
            stmt_txs.append(
                IbanStatementTransaction(
                    booking_date=booking_day,
                    description=tx_description,
                    amount_in=None,
                    amount_out=amt_abs,
                    balance_after=running,
                )
            )

    closing = running
    period_start = start_dt.date()
    period_end = end_dt.date()
    if month_txs:
        period_end = _booking_date_utc(month_txs[-1].created_at)

    person = load_person_for_client(db, client)
    line1 = _first_collected(person, ("address_line_1", "street_address", "street", "address")) or "—"
    postal = _first_collected(person, ("postal_code", "zip", "zip_code")) or "—"
    city = _first_collected(person, ("city", "locality", "town")) or "—"
    country = _first_collected(person, ("country", "country_code")) or "—"

    iban = (account.iban or "").strip()
    bic = (account.bic or "").strip()
    currency_code = (account.currency or "EUR")[:3].upper()

    return IbanStatementPayload(
        generated_at=datetime.now(timezone.utc),
        period=IbanStatementPeriod(date_from=period_start, date_to=period_end),
        client=IbanStatementClient(
            full_name=account.account_holder_name or "—",
            address_line_1=line1,
            postal_code=postal,
            city=city,
            country=country,
        ),
        account=IbanStatementAccount(
            account_name=currency_code or "—",
            currency=currency_code,
            iban=iban or "—",
            bic=bic or "—",
            account_number=_iban_account_number(iban) if iban and iban != "—" else "—",
        ),
        summary=IbanStatementSummary(
            opening_balance=opening,
            closing_balance=closing,
            money_in=money_in if month_txs else None,
            money_out=money_out if month_txs else None,
        ),
        transactions=stmt_txs,
    )


def _single_operation_description(tx: CustodyTransaction) -> str:
    """Description multi-lignes : libellé métier + ID + références."""
    base = _tx_description(tx)
    lines = [base, "", f"ID transaction : {tx.id}"]
    if tx.external_reference:
        lines.append(f"Référence externe : {tx.external_reference}")
    if tx.provider_reference:
        lines.append(f"Réf. fournisseur : {tx.provider_reference}")
    meta = tx.metadata_ or {}
    if meta.get("narrative"):
        lines.append(f"Libellé : {meta['narrative']}")
    return "\n".join(lines)


def _balance_before_after_for_transaction(
    db: Session,
    *,
    account_id,
    target_tx_id: UUID,
    available: Decimal,
) -> Optional[tuple[Decimal, Decimal]]:
    """Solde avant / après pour une opération `completed` dans la chaîne du compte."""
    _tx_filter = (
        CustodyTransaction.account_id == account_id,
        CustodyTransaction.status == "completed",
    )
    txs = (
        db.query(CustodyTransaction)
        .filter(*_tx_filter)
        .order_by(asc(CustodyTransaction.created_at), asc(CustodyTransaction.id))
        .all()
    )
    signed_deltas: list[Decimal] = []
    for custody_tx in txs:
        amt = _to_decimal(custody_tx.amount)
        if custody_tx.direction == TransactionDirection.CREDIT.value:
            signed_deltas.append(amt)
        else:
            signed_deltas.append(-amt)
    total_movement = sum(signed_deltas, Decimal("0"))
    opening = available - total_movement
    running = opening
    for custody_tx, signed_delta in zip(txs, signed_deltas):
        running = running + signed_delta
        if custody_tx.id == target_tx_id:
            before = running - signed_delta
            return (before, running)
    return None
