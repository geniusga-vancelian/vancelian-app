"""
Adapter ExchangeOrder → :class:`pdf.operation_statement_schema.OperationStatementPayload`.

PR4 : pas de sous-contrat ``exchange_pdf`` ; ``asset_impacts`` + méta génériques.

Règles montant principal / sous-titre (alignées addendum §4 et tableau ``asset_impacts``) :
- spot : achat → ``amount_fiat`` + devise ; vente → ``amount_crypto`` + ``asset`` ;
- swap (``from_asset`` ≠ devise de cotation) → ``amount_to`` + ``to_asset`` (actif reçu) ;
  si ``amount_to`` ou ``to_asset`` manquant → erreur ``operation_statement_swap_incomplete``.
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
    OperationStatementAssetImpact,
    OperationStatementBalanceContext,
    OperationStatementDetailRow,
    OperationStatementFeeItem,
    OperationStatementPayload,
    OperationStatementPersonBlock,
    OperationStatementReferences,
)
from services.exchange.models import ExchangeOrder
from services.portfolio_engine.clients.models import Client
from services.test_clients.iban_statement_payload import _booking_date_utc, _first_collected, _to_decimal
from services.test_clients.mobile_profile import load_person_for_client
from services.test_clients.operation_resolver import OperationRef, OperationResolver
from services.test_clients.operation_statement_errors import OperationStatementHttpError


def _is_swap_leg(order: ExchangeOrder) -> bool:
    """Swap crypto↔crypto lorsque la jambe « from » n’est pas la devise de cotation."""
    cur = order.currency or "EUR"
    return (
        order.from_asset is not None
        and order.to_asset is not None
        and order.from_asset != cur
    )


def _fmt_fiat(amount: Decimal, currency: str) -> str:
    q = amount.quantize(Decimal("0.01"))
    return f"{q} {currency}"


def _fmt_crypto(amount: Decimal, asset: str) -> str:
    q = amount.quantize(Decimal("0.00000001"))
    body = format(q, "f").rstrip("0").rstrip(".")
    return f"{body} {asset}"


def build_exchange_operation_statement_payload(
    db: Session,
    client: Client,
    transaction_id: UUID,
    *,
    resolved_ref: OperationRef | None = None,
) -> OperationStatementPayload:
    """
    Relevé PDF pour un ordre Exchange ``completed`` uniquement.

    Lève :class:`OperationStatementHttpError` si l’ordre est introuvable, non accessible
    ou non finalisé.
    """
    if resolved_ref is not None:
        ref = resolved_ref
        if ref.source_id != transaction_id:
            raise OperationStatementHttpError(
                "operation_statement_not_found",
                "Relevé indisponible : transaction introuvable ou non associée à votre compte.",
            )
        if ref.source_system != "exchange":
            raise OperationStatementHttpError(
                "operation_statement_not_found",
                "Relevé indisponible : identité d’opération inattendue.",
            )
    else:
        ref = OperationResolver.resolve(db, client, transaction_id)
        if ref is None:
            raise OperationStatementHttpError(
                "operation_statement_not_found",
                "Relevé indisponible : transaction introuvable ou non associée à votre compte.",
            )
        if ref.source_system != "exchange":
            raise OperationStatementHttpError(
                "operation_statement_not_found",
                "Relevé indisponible : ce n’est pas un ordre Exchange.",
            )

    order = (
        db.query(ExchangeOrder)
        .filter(ExchangeOrder.id == transaction_id, ExchangeOrder.client_id == client.id)
        .first()
    )
    if order is None:
        raise OperationStatementHttpError(
            "operation_statement_not_found",
            "Relevé indisponible : transaction introuvable ou non associée à votre compte.",
        )

    if order.status != "completed":
        raise OperationStatementHttpError(
            "operation_statement_not_completed",
            f"Relevé disponible uniquement une fois l'ordre finalisé (statut actuel : {order.status}).",
        )

    op_type: Literal["exchange_buy", "exchange_sell"] = (
        "exchange_buy" if order.side == "buy" else "exchange_sell"
    )
    cur = (order.currency or "EUR").upper()[:10]

    asset_impacts: list[OperationStatementAssetImpact] = []
    if _is_swap_leg(order):
        fa = order.from_asset or "?"
        ta = order.to_asset or "?"
        af = _to_decimal(order.amount_from) if order.amount_from is not None else Decimal("0")
        at = _to_decimal(order.amount_to) if order.amount_to is not None else Decimal("0")
        asset_impacts.append(
            OperationStatementAssetImpact(flow="out", asset=fa, amount=af, unit_kind="crypto")
        )
        asset_impacts.append(
            OperationStatementAssetImpact(flow="in", asset=ta, amount=at, unit_kind="crypto")
        )
    elif order.side == "buy":
        fiat_amt = _to_decimal(order.amount_fiat)
        crypto_amt = _to_decimal(order.amount_crypto)
        asset_impacts.append(
            OperationStatementAssetImpact(flow="out", asset=cur, amount=fiat_amt, unit_kind="fiat")
        )
        asset_impacts.append(
            OperationStatementAssetImpact(
                flow="in", asset=order.asset, amount=crypto_amt, unit_kind="crypto"
            )
        )
    else:
        fiat_amt = _to_decimal(order.amount_fiat)
        crypto_amt = _to_decimal(order.amount_crypto)
        asset_impacts.append(
            OperationStatementAssetImpact(
                flow="out", asset=order.asset, amount=crypto_amt, unit_kind="crypto"
            )
        )
        asset_impacts.append(
            OperationStatementAssetImpact(flow="in", asset=cur, amount=fiat_amt, unit_kind="fiat")
        )

    fees: list[OperationStatementFeeItem] = []
    if order.fee_amount and order.fee_asset:
        fees.append(
            OperationStatementFeeItem(amount=_to_decimal(order.fee_amount), asset=order.fee_asset)
        )

    booking_day = _booking_date_utc(order.created_at)
    side_label = "Achat" if order.side == "buy" else "Vente"
    title = f"{side_label} {order.asset}"

    # Montant principal documentaire (aligné addendum §4 + tableau asset_impacts) :
    # - spot fiat↔crypto : achat → fiat débité ; vente → crypto vendu
    # - swap crypto↔crypto : actif **reçu** (jambe « in », amount_to / to_asset)
    if _is_swap_leg(order):
        ta = order.to_asset
        at_raw = order.amount_to
        if ta is None or at_raw is None:
            raise OperationStatementHttpError(
                "operation_statement_swap_incomplete",
                "Relevé indisponible : ordre swap incomplet (montant ou actif cible manquant).",
            )
        primary_amt = _to_decimal(at_raw)
        primary_cur = ta
        subtitle = _fmt_crypto(primary_amt, ta)
    elif order.side == "buy":
        primary_amt = _to_decimal(order.amount_fiat)
        primary_cur = cur
        subtitle = _fmt_fiat(primary_amt, primary_cur)
    else:
        primary_amt = _to_decimal(order.amount_crypto)
        primary_cur = order.asset
        subtitle = _fmt_crypto(primary_amt, order.asset)

    direction: Literal["credit", "debit"] = "debit" if order.side == "buy" else "credit"

    person = load_person_for_client(db, client)
    fn = _first_collected(person, ("first_name", "given_name"))
    ln = _first_collected(person, ("last_name", "family_name"))
    full_name = " ".join(x for x in (fn, ln) if x).strip() or (client.email or "—")
    line1 = _first_collected(person, ("address_line_1", "street_address", "street", "address")) or "—"
    postal = _first_collected(person, ("postal_code", "zip", "zip_code")) or "—"
    city = _first_collected(person, ("city", "locality", "town")) or "—"
    country = _first_collected(person, ("country", "country_code")) or "—"

    period_heading = f"Ordre exécuté le {format_date(booking_day, 'd MMMM yyyy', locale='fr_FR')}"

    pair_display = None
    if _is_swap_leg(order) and order.from_asset and order.to_asset:
        pair_display = f"{order.from_asset} → {order.to_asset}"
    else:
        pair_display = f"{order.asset} / {cur}"

    execution_detail_rows = [
        OperationStatementDetailRow(label="Actif", value=order.asset),
        OperationStatementDetailRow(label="Sens", value=side_label),
        OperationStatementDetailRow(
            label="Prix d'exécution (indicatif)",
            value=f"{_to_decimal(order.price):,.2f} USD",
        ),
        OperationStatementDetailRow(label="Marché", value=pair_display),
    ]

    meta_scope = (order.metadata_ or {}).get("portfolio_scope")
    if meta_scope:
        execution_detail_rows.append(
            OperationStatementDetailRow(label="Portefeuille", value=str(meta_scope))
        )

    return OperationStatementPayload(
        operation_ref=OperationRefPayload(source_system="exchange", source_id=str(transaction_id)),
        operation_type=op_type,
        status=order.status,
        title=title,
        subtitle=subtitle,
        amount=primary_amt,
        currency=primary_cur,
        direction=direction,
        booking_date=booking_day,
        generated_at=datetime.now(timezone.utc),
        custody_pdf=None,
        balance_context=OperationStatementBalanceContext(applicable=False),
        person=OperationStatementPersonBlock(
            full_name=full_name,
            address_line_1=line1,
            postal_code=postal,
            city=city,
            country=country,
        ),
        execution_detail_rows=execution_detail_rows,
        asset_impacts=asset_impacts,
        fees=fees,
        references=OperationStatementReferences(
            order_id=str(order.id),
            external_reference=order.external_reference,
        ),
    )
