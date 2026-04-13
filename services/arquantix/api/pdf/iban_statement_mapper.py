"""
Mapping IbanStatementPayload → dict Jinja2 (`Statement.html`, via `iban_statement.html`).

Règles d’affichage : montants et dates fr_FR, cohérents avec le preview Flutter
(`formatStatementAmount` + intitulés de section).
"""

from __future__ import annotations

from decimal import Decimal

from babel.dates import format_datetime, format_date

from .iban_statement_schema import IbanStatementPayload

# Libellés cartes en-tête — alignés sur StatementHeader Flutter (anglais).
DEFAULT_LABELS_EN = {
    "account_holder": "Account holder",
    "address": "Address",
    "currency": "Currency",
    "iban": "IBAN",
    "bic": "BIC / SWIFT",
    "account_number": "Account Number",
}

DEFAULT_LEGAL_P1 = (
    "Vancelian Bank SAS est un établissement de crédit agréé en France sous le numéro "
    "d'entreprise 912 345 678 et le code d'autorisation ACPR-2026-001, dont le siège social "
    "est situé 10 rue de la Paix, 75002 Paris, France. Vancelian Bank SAS est supervisée par "
    "l'Autorité de contrôle prudentiel et de résolution (ACPR) ainsi que par la Banque de France."
)

DEFAULT_LEGAL_P2 = (
    "Les dépôts sont protégés par le Fonds de Garantie des Dépôts et de Résolution (FGDR), "
    "dans les limites et conditions prévues par la réglementation en vigueur. Certaines exceptions "
    "peuvent s'appliquer. Pour plus d'informations, veuillez consulter le site officiel du FGDR. "
    "Si vous avez des questions, veuillez nous contacter via la messagerie intégrée à l'application Vancelian."
)

# Bloc légal 2 découpé comme le composant design system (texte courant + phrase d’appel en semi-gras PDF).
DEFAULT_LEGAL_P2A = (
    "Les dépôts sont protégés par le Fonds de Garantie des Dépôts et de Résolution (FGDR), "
    "dans les limites et conditions prévues par la réglementation en vigueur. Certaines exceptions "
    "peuvent s'appliquer. Pour plus d'informations, veuillez consulter le site officiel du FGDR."
)

DEFAULT_LEGAL_P2B = (
    "Si vous avez des questions, veuillez nous contacter via la messagerie intégrée à "
    "l'application Vancelian."
)


def format_amount_fr(value: Decimal) -> str:
    """Nombre décimal → chaîne type `15 420,50` (espaces insécables évités : espace ASCII)."""
    q = value.quantize(Decimal("0.01"))
    neg = q < 0
    q = abs(q)
    integral, frac = divmod(int(q * 100), 100)
    s = f"{integral:,}".replace(",", " ")
    out = f"{s},{frac:02d}"
    return f"-{out}" if neg else out


def format_money_line(value: Decimal, currency: str) -> str:
    return f"{format_amount_fr(value)} {currency}"


def format_booking_cell(d, locale: str = "fr_FR") -> str:
    """Date opération → JJ/MM/AAAA (comme le preview Flutter sur relevé mars 2026)."""
    return format_date(d, "dd/MM/yyyy", locale=locale)


def payload_to_template_context(
    payload: IbanStatementPayload,
    *,
    labels: dict[str, str] | None = None,
    locale: str = "fr_FR",
    footer_legal_paragraph_1: str | None = None,
    footer_legal_paragraph_2: str | None = None,
    copyright_year: int | None = None,
) -> dict:
    """
    Construit le dict attendu par `Statement.html`.

    Clés racine : meta, header, client, account, summary, transactions, footer, labels, brand.
    """
    labels = {**DEFAULT_LABELS_EN, **(labels or {})}
    cur = payload.account.currency.upper()
    cy = copyright_year or payload.generated_at.year

    client_address = "\n".join(
        [
            payload.client.address_line_1.strip(),
            f"{payload.client.postal_code} {payload.client.city}".strip(),
            payload.client.country.strip(),
        ]
    )

    gen = payload.generated_at
    generated_day = format_datetime(gen, "d MMMM yyyy", locale=locale, tzinfo=gen.tzinfo)
    generated_utc = format_datetime(gen, "d MMMM yyyy 'à' HH:mm", locale=locale, tzinfo=gen.tzinfo)

    p_from = format_date(payload.period.date_from, "d MMMM yyyy", locale=locale)
    p_to = format_date(payload.period.date_to, "d MMMM yyyy", locale=locale)
    period_heading = payload.period_heading_override or f"Relevé de compte · {p_from} au {p_to}"

    tx_rows = []
    for t in payload.transactions:
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
    if payload.summary.money_in is not None:
        money_in_d = format_money_line(payload.summary.money_in, cur)
    if payload.summary.money_out is not None:
        money_out_d = format_money_line(payload.summary.money_out, cur)

    doc_title = payload.document_title or f"{payload.statement_title} — Vancelian"

    doc_header_ctx = {
        "title": payload.statement_title,
        "subtitle_line_1": f"Relevé généré le {generated_day}",
        "subtitle_line_2": f"Informations en date du {generated_utc} (UTC)",
    }

    page1_left_items = [
        {"label": labels["account_holder"], "value": payload.client.full_name, "align": "right", "bold": True},
        {"label": labels["address"], "value": client_address, "align": "right"},
    ]
    page1_right_items = [
        {"label": labels["currency"], "value": cur, "align": "left"},
        {"label": labels["iban"], "value": payload.account.iban, "align": "left"},
        {"label": labels["bic"], "value": payload.account.bic, "align": "left"},
        {"label": labels["account_number"], "value": payload.account.account_number, "align": "left"},
    ]

    legal_p2 = footer_legal_paragraph_2 or DEFAULT_LEGAL_P2
    footer_block: dict = {
        "support_phone": payload.support_phone,
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

    return {
        "meta": {
            "document_title": doc_title,
            "period_heading": period_heading,
            "hide_balance_summary": payload.hide_balance_summary,
        },
        "header": {
            "statement_title": payload.statement_title,
            "generated_line": f"Relevé généré le {generated_day}",
            "utc_line": f"Informations en date du {generated_utc} (UTC)",
        },
        "client": {
            "full_name": payload.client.full_name,
            "address_multiline": client_address,
        },
        "account": {
            "currency": payload.account.currency,
            "iban": payload.account.iban,
            "bic": payload.account.bic,
            "account_number": payload.account.account_number,
        },
        "summary": {
            "opening_balance_display": format_money_line(payload.summary.opening_balance, cur),
            "closing_balance_display": format_money_line(payload.summary.closing_balance, cur),
            "money_in_display": money_in_d,
            "money_out_display": money_out_d,
        },
        "transactions": tx_rows,
        "footer": footer_block,
        "doc_header": doc_header_ctx,
        "page1_left_items": page1_left_items,
        "page1_right_items": page1_right_items,
        "labels": labels,
        "brand": {
            "logo_svg_markup": None,
        },
    }
