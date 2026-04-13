"""
Adapter CustodyTransaction → :class:`pdf.operation_statement_schema.OperationStatementPayload`.

PR3 : seul le flux custody unitaire ; pas d'Exchange, pas de snapshot persistant.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID

from babel.dates import format_date
from sqlalchemy.orm import Session

from pdf.operation_statement_schema import (
    OperationRefPayload,
    OperationStatementCustodyPdfSection,
    OperationStatementPayload,
    OperationStatementPdfLine,
)
from services.custody.enums import TransactionDirection
from services.custody.models import CustodyTransaction
from services.custody.repository import (
    CustodyAccountRepository,
    CustodyBalanceRepository,
    CustodyTransactionRepository,
)
from services.portfolio_engine.clients.models import Client
from services.test_clients.iban_statement_payload import (
    _balance_before_after_for_transaction,
    _booking_date_utc,
    _first_collected,
    _iban_account_number,
    _single_operation_description,
    _to_decimal,
)
from services.test_clients.mobile_profile import load_person_for_client
from services.test_clients.operation_resolver import OperationRef, OperationResolver
from services.test_clients.operation_statement_errors import OperationStatementHttpError
from services.test_clients.schemas import (
    TRANSACTION_KIND_TITLE_MAP,
    TRANSACTION_TITLE_MAP,
)


def _s(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, str):
        stripped = val.strip()
        return stripped or None
    return str(val).strip() or None


def _custody_operation_type(tx: CustodyTransaction) -> str:
    """Taxonomie V1 : alignée sur ``transaction_type`` custody."""
    return tx.transaction_type


def _custody_ui_title(tx: CustodyTransaction) -> str:
    kind = tx.transaction_kind
    return (
        (TRANSACTION_KIND_TITLE_MAP.get(kind) if kind else None)
        or TRANSACTION_TITLE_MAP.get(
            tx.transaction_type,
            tx.transaction_type.replace("_", " ").title(),
        )
    )


def _custody_subtitle(tx: CustodyTransaction) -> str | None:
    meta = tx.metadata_ or {}
    return _s(meta.get("remitter_name")) or _s(meta.get("narrative"))


def build_custody_operation_statement_payload(
    db: Session,
    client: Client,
    transaction_id: UUID,
    *,
    resolved_ref: OperationRef | None = None,
) -> OperationStatementPayload:
    """
    Construit le relevé PDF unitaire custody.

    Lève :class:`OperationStatementHttpError` si le document ne peut pas être émis
    (mêmes règles qu'auparavant : custody ``completed``, chaîne de solde, etc.).
    """
    if resolved_ref is not None:
        ref = resolved_ref
        if ref.source_id != transaction_id:
            raise OperationStatementHttpError(
                "operation_statement_not_found",
                "Relevé indisponible : transaction introuvable ou non associée à votre compte.",
            )
        if ref.source_system != "custody":
            raise OperationStatementHttpError(
                "operation_statement_not_found",
                "Relevé indisponible : ce n’est pas une opération custody.",
            )
    else:
        ref = OperationResolver.resolve(db, client, transaction_id)
        if ref is None:
            raise OperationStatementHttpError(
                "operation_statement_not_found",
                "Relevé indisponible : transaction introuvable ou non associée à votre compte.",
            )
        if ref.source_system != "custody":
            raise OperationStatementHttpError(
                "operation_statement_exchange_not_supported",
                "Relevé PDF disponible uniquement pour les opérations compte custody (pas les ordres Exchange).",
            )

    tx = CustodyTransactionRepository.get_by_id(db, transaction_id)
    assert tx is not None
    account = CustodyAccountRepository.get_by_id(db, tx.account_id)
    assert account is not None

    if tx.status != "completed":
        raise OperationStatementHttpError(
            "operation_statement_not_completed",
            f"Relevé disponible uniquement une fois l'opération finalisée (statut actuel : {tx.status}).",
        )

    balance_row = CustodyBalanceRepository.get_by_account_id(db, account.id)
    available = _to_decimal(balance_row.available_balance) if balance_row is not None else Decimal("0")

    before_after = _balance_before_after_for_transaction(
        db,
        account_id=account.id,
        target_tx_id=transaction_id,
        available=available,
    )
    if before_after is None:
        raise OperationStatementHttpError(
            "operation_statement_balance_chain_unavailable",
            "Impossible d'établir le relevé : chaîne de solde indisponible pour cette opération.",
        )

    balance_before, balance_after = before_after
    amt_abs = _to_decimal(tx.amount)
    signed_delta = amt_abs if tx.direction == TransactionDirection.CREDIT.value else -amt_abs
    money_in: Decimal | None = None
    money_out: Decimal | None = None
    if signed_delta > 0:
        money_in = amt_abs
    elif signed_delta < 0:
        money_out = amt_abs

    booking_day = _booking_date_utc(tx.created_at)
    cur = (tx.currency or account.currency or "EUR")[:3].upper()

    pdf_line = OperationStatementPdfLine(
        booking_date=booking_day,
        description=_single_operation_description(tx),
        amount_in=money_in,
        amount_out=money_out,
        balance_after=balance_after,
    )

    period_heading = (
        f"Transaction datée du {format_date(booking_day, 'd MMMM yyyy', locale='fr_FR')}"
    )

    person = load_person_for_client(db, client)
    line1 = _first_collected(person, ("address_line_1", "street_address", "street", "address")) or "—"
    postal = _first_collected(person, ("postal_code", "zip", "zip_code")) or "—"
    city = _first_collected(person, ("city", "locality", "town")) or "—"
    country = _first_collected(person, ("country", "country_code")) or "—"

    iban = (account.iban or "").strip()
    bic = (account.bic or "").strip()

    direction: Literal["credit", "debit"] = (
        "credit" if tx.direction == TransactionDirection.CREDIT.value else "debit"
    )

    custody_pdf = OperationStatementCustodyPdfSection(
        statement_title="Relevé d'opération",
        document_title="Relevé d'opération — Vancelian",
        period_heading=period_heading,
        hide_balance_summary=False,
        client_full_name=account.account_holder_name or "—",
        address_line_1=line1,
        postal_code=postal,
        city=city,
        country=country,
        account_currency=cur or "—",
        iban=iban or "—",
        bic=bic or "—",
        account_number=_iban_account_number(iban) if iban and iban != "—" else "—",
        opening_balance=balance_before,
        closing_balance=balance_after,
        money_in=money_in,
        money_out=money_out,
        lines=[pdf_line],
    )

    return OperationStatementPayload(
        operation_ref=OperationRefPayload(source_system="custody", source_id=str(transaction_id)),
        operation_type=_custody_operation_type(tx),
        status=tx.status,
        title=_custody_ui_title(tx),
        subtitle=_custody_subtitle(tx),
        amount=amt_abs,
        currency=cur,
        direction=direction,
        booking_date=booking_day,
        generated_at=datetime.now(timezone.utc),
        custody_pdf=custody_pdf,
    )
