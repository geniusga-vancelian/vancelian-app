"""Tool ``list_transactions`` — agent **compliance.transactional**, autonomy **L0**.

Liste détaillée et filtrable des transactions cash du client, pour
répondre aux questions du type :

  - *« peux-tu me lister mes dépôts ? »*
  - *« mes retraits du mois ? »*
  - *« mes dernières transactions par carte »*
  - *« mes virements en attente »*

Phase 2c.3 : ce tool renvoie au LLM **un tableau Markdown
prêt-à-coller** (clé ``markdown_table``) en plus des items bruts. Le
prompt instruit le LLM à coller ce tableau tel quel sous une phrase
d'introduction très courte. Cela évite :

  - les **hallucinations de montants** (le LLM ne calcule rien) ;
  - les **mises en forme incohérentes** entre conversations (toujours
    les mêmes 4 colonnes, mêmes formats) ;
  - le risque que le LLM oublie de mettre les **liens cliquables** par
    ligne (deep-link `vancelian://app/transactions/{id}`).

Pas d'embed UI structuré ici (volontairement) : la demande utilisateur
est un rendu Markdown direct dans la bulle assistant. Le widget
``ArticleParagraphMarkdown`` côté Flutter sait rendre les tables avec
des liens dans les cellules (cf.
``_ArticleParagraphMarkdownLinkBuilder``).

Cf. ``docs/arquantix/COMPLIANCE_TOPICS.md`` § 3.3.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "list_transactions",
        "description": (
            "Retourne la liste détaillée des transactions cash du client "
            "avec filtres (catégorie, direction, statut, date min, "
            "limite). En plus des items bruts, retourne un `markdown_table` "
            "prêt-à-coller (4 colonnes : Date, Type, Statut, Montant + "
            "lien cliquable vers le détail de chaque transaction). "
            "À utiliser pour TOUTE demande de LISTE (« mes dépôts », "
            "« mes retraits », « mon historique »). Pour une transaction "
            "précise, utilise plutôt `read_transaction_detail`. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "Catégorie de transactions à filtrer (LLM-friendly)."
                    ),
                    "enum": [
                        "deposits",
                        "withdrawals",
                        "cards",
                        "crypto",
                        "bank_transfer",
                        "all",
                    ],
                },
                "direction": {
                    "type": "string",
                    "description": (
                        "Filtre direction (combinable avec `category`). "
                        "`credit` = entrée d'argent, `debit` = sortie."
                    ),
                    "enum": ["credit", "debit"],
                },
                "status": {
                    "type": "string",
                    "description": "Filtre par statut.",
                    "enum": [
                        "pending",
                        "completed",
                        "failed",
                        "rejected",
                        "on_hold",
                        "cancelled",
                    ],
                },
                "since": {
                    "type": "string",
                    "description": (
                        "Date min ISO8601 (ex. `2026-01-01` ou "
                        "`2026-04-01T00:00:00Z`). Les transactions strictement "
                        "antérieures sont exclues."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre max de transactions (1..50).",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance.transactional",
}


# ─────────────────────────────────────────────────────────────────────
# Dictionnaire de libellés humains. Volontairement minimaliste — toute
# valeur inconnue retombe sur un humanize générique (`Bank Transfer
# In` → `Bank transfer in`). Évite l'enfer d'un mapping exhaustif.
# ─────────────────────────────────────────────────────────────────────
_KIND_LABELS: dict[str, str] = {
    "bank_transfer_in": "Virement entrant",
    "bank_transfer_out": "Virement sortant",
    "card_in": "Dépôt par carte",
    "crypto_in": "Dépôt crypto",
    "swap": "Échange",
    "fee": "Frais",
}

_TYPE_LABELS: dict[str, str] = {
    "deposit": "Dépôt",
    "withdrawal": "Retrait",
    "transfer": "Virement",
    "fee": "Frais",
    "swap": "Échange",
}

_STATUS_LABELS: dict[str, str] = {
    "pending": "En attente",
    "completed": "Complété",
    "failed": "Échec",
    "rejected": "Rejeté",
    "on_hold": "En attente",
    "cancelled": "Annulé",
}

# Symboles devises courantes — fallback = code ISO.
_CURRENCY_SYMBOLS: dict[str, str] = {
    "EUR": "€",
    "USD": "$",
    "GBP": "£",
    "CHF": "CHF",
}


def execute(
    ctx: ToolContext,
    *,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 20,
    **_kwargs: Any,
) -> dict[str, Any]:
    if not ctx.client_id:
        return {
            "count": 0,
            "items": [],
            "markdown_table": _empty_markdown(),
            "filters_applied": {},
        }

    # `limit=0` doit être clampé à 1 (et non retomber sur 20). On
    # distingue donc explicitement `None` (= défaut) de `0` (= valeur
    # fournie mais hors borne basse).
    safe_limit = max(
        1, min(int(limit) if limit is not None else 20, 50)
    )

    try:
        rows = compliance_repo.fetch_transactions_list(
            ctx.db,
            client_id=ctx.client_id,
            category=category,
            direction=direction,
            status=status,
            since=since,
            limit=safe_limit,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "list_transactions.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        return {
            "count": 0,
            "items": [],
            "markdown_table": _empty_markdown(),
            "filters_applied": _filters_applied(
                category, direction, status, since, safe_limit
            ),
            "error": "repo_unavailable",
        }

    items = [_format_item(r) for r in rows]
    md = _render_markdown_table(items)
    return {
        "count": len(items),
        "items": items,
        "markdown_table": md,
        "filters_applied": _filters_applied(
            category, direction, status, since, safe_limit
        ),
    }


# ─────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────


def _format_item(row: dict[str, Any]) -> dict[str, Any]:
    """Normalise une ligne SQL pour l'output LLM + rendu markdown."""
    raw_amount = row.get("amount")
    try:
        amount_value = Decimal(str(raw_amount)) if raw_amount is not None else Decimal(0)
    except (InvalidOperation, TypeError):
        amount_value = Decimal(0)

    currency = (row.get("currency") or "EUR").upper()
    symbol = _CURRENCY_SYMBOLS.get(currency, currency)

    direction = (row.get("direction") or "").lower()
    sign = "+" if direction == "credit" else "-"
    amount_display = f"{sign}{_format_amount(amount_value)} {symbol}"

    created_at = row.get("created_at")
    created_at_iso = (
        created_at.isoformat() if isinstance(created_at, datetime) else None
    )
    created_at_display = (
        _format_date_fr(created_at) if isinstance(created_at, datetime) else "—"
    )

    kind = row.get("transaction_kind")
    type_ = row.get("transaction_type") or "unknown"
    type_label = _KIND_LABELS.get(kind or "") or _TYPE_LABELS.get(
        type_, _humanize(kind or type_)
    )

    status = (row.get("status") or "unknown").lower()
    status_label = _STATUS_LABELS.get(status, _humanize(status))

    return {
        "id": row.get("id"),
        "transaction_type": type_,
        "transaction_kind": kind,
        "direction": direction or None,
        "status": status,
        "status_label": status_label,
        "type_label": type_label,
        "amount": str(amount_value),
        "currency": currency,
        "amount_display": amount_display,
        "created_at": created_at_iso,
        "created_at_display": created_at_display,
    }


def _format_amount(value: Decimal) -> str:
    """Format ``45000.00`` → ``45 000,00`` (FR, 2 décimales, espace fin)."""
    quantized = value.quantize(Decimal("0.01"))
    int_part, _, dec_part = f"{quantized:.2f}".partition(".")
    sign = ""
    if int_part.startswith("-"):
        sign = "-"
        int_part = int_part[1:]
    grouped: list[str] = []
    while len(int_part) > 3:
        grouped.append(int_part[-3:])
        int_part = int_part[:-3]
    grouped.append(int_part)
    int_fr = "\u202f".join(reversed(grouped))
    return f"{sign}{int_fr},{dec_part}"


_FR_MONTHS = (
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
)


def _format_date_fr(dt: datetime) -> str:
    """Format compact FR ``3 mai 2026 02:34``. Volontairement court
    pour rester dans une cellule de tableau."""
    try:
        local = dt
        return f"{local.day} {_FR_MONTHS[local.month - 1]} {local.year} {local.hour:02d}:{local.minute:02d}"
    except Exception:  # noqa: BLE001
        return dt.isoformat()


def _humanize(raw: str) -> str:
    return (
        raw.replace("_", " ").strip().capitalize()
        if isinstance(raw, str) and raw
        else "—"
    )


def _filters_applied(
    category: Optional[str],
    direction: Optional[str],
    status: Optional[str],
    since: Optional[str],
    limit: int,
) -> dict[str, Any]:
    out: dict[str, Any] = {"limit": limit}
    if category:
        out["category"] = category
    if direction:
        out["direction"] = direction
    if status:
        out["status"] = status
    if since:
        out["since"] = since
    return out


# ─────────────────────────────────────────────────────────────────────
# Rendu Markdown
# ─────────────────────────────────────────────────────────────────────


def _empty_markdown() -> str:
    """Tableau « pas de résultat » — le LLM peut le coller tel quel."""
    return (
        "_Aucune transaction trouvée pour ces critères._"
    )


def _render_markdown_table(items: list[dict[str, Any]]) -> str:
    """Construit le tableau Markdown prêt-à-coller.

    Colonnes : Date · Type · Statut · Montant · Détail (lien
    cliquable). Les pipes `|` éventuels dans les valeurs sont
    échappés pour ne pas casser la table.
    """
    if not items:
        return _empty_markdown()

    header = "| Date | Type | Statut | Montant | Détail |"
    sep = "|---|---|---|---:|---|"
    body_lines: list[str] = []
    for it in items:
        row = "| {date} | {type_} | {status} | {amount} | [Ouvrir](vancelian://app/transactions/{id}) |".format(
            date=_escape_pipe(it.get("created_at_display", "—")),
            type_=_escape_pipe(it.get("type_label", "—")),
            status=_escape_pipe(it.get("status_label", "—")),
            amount=_escape_pipe(it.get("amount_display", "—")),
            id=it.get("id"),
        )
        body_lines.append(row)
    return "\n".join([header, sep, *body_lines])


def _escape_pipe(s: Any) -> str:
    if s is None:
        return "—"
    return str(s).replace("|", r"\|")
