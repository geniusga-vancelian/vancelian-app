"""
Mapping :class:`OperationStatementPayload` → dict Jinja2 pour le gabarit autonome ``operation_statement.html``.

Réutilise uniquement les **fonctions de formatage** du module IBAN (montants, dates), pas ``IbanStatementPayload``.
"""

from __future__ import annotations

from decimal import Decimal

from babel.dates import format_date, format_datetime

from pdf.operation_statement_schema import OperationStatementAssetImpact, OperationStatementPayload

from .iban_statement_mapper import (
    DEFAULT_LABELS_EN,
    DEFAULT_LEGAL_P1,
    DEFAULT_LEGAL_P2,
    DEFAULT_LEGAL_P2A,
    DEFAULT_LEGAL_P2B,
    format_booking_cell,
    format_money_line,
)


def _format_crypto_quantity(amount: Decimal, asset: str) -> str:
    q = amount.quantize(Decimal("0.00000001"))
    body = format(q, "f").rstrip("0").rstrip(".")
    return f"{body} {asset}"


def _format_fee_display(amount: Decimal, asset: str) -> str:
    """Frais : devise 3 lettres → format monétaire FR ; sinon traitement comme quantité + actif."""
    a = (asset or "").strip().upper()
    if len(a) == 3 and a.isalpha():
        return format_money_line(amount, a)
    return _format_crypto_quantity(amount, asset)


def _asset_impact_display_row(impact: OperationStatementAssetImpact) -> dict:
    flow_fr = "Entrée" if impact.flow == "in" else "Sortie"
    if impact.unit_kind == "fiat":
        cur = impact.asset[:3].upper() if len(impact.asset) >= 3 else impact.asset
        amt = format_money_line(impact.amount, cur)
    else:
        amt = _format_crypto_quantity(impact.amount, impact.asset)
    return {
        "flow": impact.flow,
        "flow_display": flow_fr,
        "asset": impact.asset,
        "amount_display": amt,
    }


def _operation_type_badge_fr(operation_type: str) -> str:
    """Libellé court pour badge — présentation uniquement."""
    m = {
        "deposit": "Dépôt",
        "withdrawal": "Retrait",
        "transfer_internal": "Transfert interne",
        "exchange_buy": "Échange · Achat",
        "exchange_sell": "Échange · Vente",
    }
    return m.get(operation_type, operation_type.replace("_", " ").title())


def _status_label_fr(status: str) -> str:
    return {
        "completed": "Finalisée",
        "pending": "En attente",
        "failed": "Échouée",
        "cancelled": "Annulée",
    }.get(status.lower(), status)


def _format_primary_amount_display(payload: OperationStatementPayload) -> str:
    """Montant principal documentaire (aligné sur ``amount`` + ``currency`` du payload)."""
    c = (payload.currency or "EUR").strip()
    if len(c) == 3 and c.isalpha():
        return format_money_line(payload.amount, c.upper())
    return _format_crypto_quantity(payload.amount, c)


def _presentation_block(
    payload: OperationStatementPayload,
    *,
    locale: str,
) -> dict:
    """Champs purement visuels pour le gabarit autonome ``operation_statement.html``."""
    booking_d = ""
    if payload.booking_date:
        booking_d = format_date(payload.booking_date, "d MMMM yyyy", locale=locale)
    sub = (payload.subtitle or "").strip()
    return {
        "badge": _operation_type_badge_fr(payload.operation_type),
        "primary_label": (payload.title or "").strip(),
        "secondary_label": sub,
        "status_label": _status_label_fr(payload.status),
        "amount_display": _format_primary_amount_display(payload),
        "direction_label": "Crédit" if payload.direction == "credit" else "Débit",
        "booking_display": booking_d,
    }


def _footer_block(
    *,
    cy: int,
    footer_legal_paragraph_1: str | None,
    footer_legal_paragraph_2: str | None,
) -> dict:
    legal_p2 = footer_legal_paragraph_2 or DEFAULT_LEGAL_P2
    footer_block: dict = {
        "support_phone": "+33 1 23 45 67 89",
        "legal_paragraph_1": footer_legal_paragraph_1 or DEFAULT_LEGAL_P1,
        "legal_paragraph_2": legal_p2,
        "copyright_line": f"© {cy} Vancelian Bank SAS – Tous droits réservés",
        "mark_image_src": "assets/vancelian-footer-mark.png",
    }
    if footer_legal_paragraph_2 is not None:
        footer_block["legal_second_block_plain"] = footer_legal_paragraph_2
    else:
        footer_block["legal_paragraph_2a"] = DEFAULT_LEGAL_P2A
        footer_block["legal_paragraph_2b"] = DEFAULT_LEGAL_P2B
    return footer_block


def custody_operation_payload_to_template_context(
    payload: OperationStatementPayload,
    *,
    labels: dict[str, str] | None = None,
    locale: str = "fr_FR",
    footer_legal_paragraph_1: str | None = None,
    footer_legal_paragraph_2: str | None = None,
    copyright_year: int | None = None,
) -> dict:
    """
    Construit le dict attendu par ``operation_statement.html`` pour le mode custody.
    """
    sec = payload.custody_pdf
    if sec is None:
        raise ValueError("custody_pdf is required for custody operation statement rendering")

    labels = {**DEFAULT_LABELS_EN, **(labels or {})}
    cur = sec.account_currency.upper()
    cy = copyright_year or payload.generated_at.year

    client_address = "\n".join(
        [
            sec.address_line_1.strip(),
            f"{sec.postal_code} {sec.city}".strip(),
            sec.country.strip(),
        ]
    )

    gen = payload.generated_at
    generated_day = format_datetime(gen, "d MMMM yyyy", locale=locale, tzinfo=gen.tzinfo)
    generated_utc = format_datetime(gen, "d MMMM yyyy 'à' HH:mm", locale=locale, tzinfo=gen.tzinfo)

    tx_rows = []
    for t in sec.lines:
        debit_d = ""
        credit_d = ""
        if t.amount_out is not None and t.amount_out != 0:
            debit_d = f"-{format_money_line(t.amount_out, cur)}"
        if t.amount_in is not None and t.amount_in != 0:
            credit_d = f"+{format_money_line(t.amount_in, cur)}"
        tx_rows.append(
            {
                "date_display": format_booking_cell(t.booking_date, locale=locale),
                "description": t.description,
                "debit_display": debit_d,
                "credit_display": credit_d,
                "balance_display": format_money_line(t.balance_after, cur),
            }
        )

    if tx_rows:
        tx_rows[-1]["balance_strong"] = True

    money_in_d = None
    money_out_d = None
    if sec.money_in is not None:
        money_in_d = format_money_line(sec.money_in, cur)
    if sec.money_out is not None:
        money_out_d = format_money_line(sec.money_out, cur)

    doc_title = sec.document_title or f"{sec.statement_title} — Vancelian"

    doc_header_ctx = {
        "title": sec.statement_title,
        "subtitle_line_1": f"Relevé généré le {generated_day}",
        "subtitle_line_2": f"Informations en date du {generated_utc} (UTC)",
    }
    page1_left_items = [
        {"label": labels["account_holder"], "value": sec.client_full_name, "align": "right", "bold": True},
        {"label": labels["address"], "value": client_address, "align": "right"},
    ]
    page1_right_items = [
        {"label": labels["currency"], "value": cur, "align": "left"},
        {"label": labels["iban"], "value": sec.iban, "align": "left"},
        {"label": labels["bic"], "value": sec.bic, "align": "left"},
        {"label": labels["account_number"], "value": sec.account_number, "align": "left"},
    ]

    return {
        "layout": {"mode": "custody"},
        "presentation": _presentation_block(payload, locale=locale),
        "meta": {
            "document_title": doc_title,
            "period_heading": sec.period_heading,
            "hide_balance_summary": sec.hide_balance_summary,
        },
        "header": {
            "statement_title": sec.statement_title,
            "generated_line": f"Relevé généré le {generated_day}",
            "utc_line": f"Informations en date du {generated_utc} (UTC)",
        },
        "client": {
            "full_name": sec.client_full_name,
            "address_multiline": client_address,
        },
        "account": {
            "currency": sec.account_currency,
            "iban": sec.iban,
            "bic": sec.bic,
            "account_number": sec.account_number,
        },
        "summary": {
            "opening_balance_display": format_money_line(sec.opening_balance, cur),
            "closing_balance_display": format_money_line(sec.closing_balance, cur),
            "money_in_display": money_in_d,
            "money_out_display": money_out_d,
        },
        "transactions": tx_rows,
        "doc_header": doc_header_ctx,
        "page1_left_items": page1_left_items,
        "page1_right_items": page1_right_items,
        "footer": _footer_block(
            cy=cy,
            footer_legal_paragraph_1=footer_legal_paragraph_1,
            footer_legal_paragraph_2=footer_legal_paragraph_2,
        ),
        "labels": labels,
        "brand": {
            "logo_svg_markup": None,
        },
        "execution_detail_rows": [],
        "asset_impact_rows": [],
        "fee_rows": [],
        "reference_rows": [],
    }


def exchange_operation_payload_to_template_context(
    payload: OperationStatementPayload,
    *,
    labels: dict[str, str] | None = None,
    locale: str = "fr_FR",
    footer_legal_paragraph_1: str | None = None,
    footer_legal_paragraph_2: str | None = None,
    copyright_year: int | None = None,
) -> dict:
    """Contexte Jinja pour un ordre Exchange (pas de bloc soldes bancaires)."""
    if payload.operation_ref.source_system != "exchange":
        raise ValueError("exchange payload expected")
    person = payload.person
    if person is None:
        raise ValueError("person block required for exchange operation statement rendering")

    labels = {**DEFAULT_LABELS_EN, **(labels or {})}
    cy = copyright_year or payload.generated_at.year

    client_address = "\n".join(
        [
            person.address_line_1.strip(),
            f"{person.postal_code} {person.city}".strip(),
            person.country.strip(),
        ]
    )

    gen = payload.generated_at
    generated_day = format_datetime(gen, "d MMMM yyyy", locale=locale, tzinfo=gen.tzinfo)
    generated_utc = format_datetime(gen, "d MMMM yyyy 'à' HH:mm", locale=locale, tzinfo=gen.tzinfo)

    booking = payload.booking_date
    if booking:
        period_heading = f"Ordre exécuté le {format_date(booking, 'd MMMM yyyy', locale=locale)}"
    else:
        period_heading = "Ordre Exchange"

    doc_title = "Relevé d'opération — Vancelian"
    statement_title = "Relevé d'opération"

    asset_impact_rows = [_asset_impact_display_row(a) for a in payload.asset_impacts]

    fee_rows = [{"display": _format_fee_display(f.amount, f.asset)} for f in payload.fees]

    ref_rows = []
    refs = payload.references
    if refs:
        if refs.order_id:
            ref_rows.append({"label": "ID ordre", "value": refs.order_id})
        if refs.external_reference:
            ref_rows.append({"label": "Référence externe", "value": refs.external_reference})

    execution_rows = [{"label": r.label, "value": r.value} for r in payload.execution_detail_rows]

    doc_header_ctx = {
        "title": statement_title,
        "subtitle_line_1": f"Relevé généré le {generated_day}",
        "subtitle_line_2": f"Informations en date du {generated_utc} (UTC)",
    }
    page1_left_items = [
        {"label": labels["account_holder"], "value": person.full_name, "align": "right", "bold": True},
        {"label": labels["address"], "value": client_address, "align": "right"},
    ]
    page1_right_items = [{"label": r.label, "value": r.value, "align": "left"} for r in payload.execution_detail_rows]

    return {
        "layout": {"mode": "exchange"},
        "presentation": _presentation_block(payload, locale=locale),
        "meta": {
            "document_title": doc_title,
            "period_heading": period_heading,
            "hide_balance_summary": True,
        },
        "header": {
            "statement_title": statement_title,
            "generated_line": f"Relevé généré le {generated_day}",
            "utc_line": f"Informations en date du {generated_utc} (UTC)",
        },
        "client": {
            "full_name": person.full_name,
            "address_multiline": client_address,
        },
        "account": {
            "currency": "—",
            "iban": "—",
            "bic": "—",
            "account_number": "—",
        },
        "summary": {
            "opening_balance_display": "",
            "closing_balance_display": "",
            "money_in_display": None,
            "money_out_display": None,
        },
        "transactions": [],
        "doc_header": doc_header_ctx,
        "page1_left_items": page1_left_items,
        "page1_right_items": page1_right_items,
        "footer": _footer_block(
            cy=cy,
            footer_legal_paragraph_1=footer_legal_paragraph_1,
            footer_legal_paragraph_2=footer_legal_paragraph_2,
        ),
        "labels": labels,
        "brand": {
            "logo_svg_markup": None,
        },
        "execution_detail_rows": execution_rows,
        "asset_impact_rows": asset_impact_rows,
        "fee_rows": fee_rows,
        "reference_rows": ref_rows,
    }


def operation_statement_payload_to_template_context(
    payload: OperationStatementPayload,
    **kwargs,
) -> dict:
    """Point d’entrée unique : custody (``custody_pdf``) ou Exchange."""
    if payload.custody_pdf is not None:
        return custody_operation_payload_to_template_context(payload, **kwargs)
    if payload.operation_ref.source_system == "exchange":
        return exchange_operation_payload_to_template_context(payload, **kwargs)
    raise ValueError("Unsupported OperationStatementPayload shape for PDF rendering")
