"""Tool ``stats_transaction_amounts`` — agent **compliance.transactional**, autonomy **L0**.

Sommes des montants des transactions cash du client : total déposé,
total retiré, solde net (sur les transactions ``completed`` par
défaut — les pending/failed sont exclus pour que les totaux aient un
sens métier).

Phase 2c.5 — second tool « stats » du sub-agent transactional. Format
de retour identique à ``list_transactions`` / ``stats_transaction_counts`` :
``markdown_table`` prêt-à-coller que le LLM colle tel quel.

Anti-tipping-off : les montants exposés sont des **agrégats client-
visibles** (totaux propres à l'utilisateur, déjà accessibles via les
écrans Wallet / Statement). Pas de leak de scoring ou de signaux
internes.

Cf. ``docs/arquantix/COMPLIANCE_TOPICS.md`` § 3.3 (stats).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "stats_transaction_amounts",
        "description": (
            "Calcule les MONTANTS totaux des transactions cash du "
            "client : total déposé, total retiré, solde net. Restreint "
            "par défaut aux transactions `completed` pour que les "
            "totaux reflètent la réalité du compte. Retourne un "
            "`markdown_table` prêt-à-coller (Direction / Montant total) "
            "+ une ligne Net. À utiliser pour TOUTE question sur des "
            "MONTANTS cumulés (« combien j'ai déposé en tout ? », "
            "« montant total des retraits ? », « bilan cash ? »). Pour "
            "le NOMBRE, utilise `stats_transaction_counts`. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "Catégorie de transactions à filtrer."
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
                    "description": "Filtre direction supplémentaire.",
                    "enum": ["credit", "debit"],
                },
                "status": {
                    "type": "string",
                    "description": (
                        "Filtre statut. Par défaut, seuls les "
                        "`completed` sont sommés (les pending/failed "
                        "n'ont pas de sens dans un total cash). "
                        "Peut être surchargé pour voir les montants "
                        "en attente, par exemple."
                    ),
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
                        "Date min ISO8601 (ex. `2026-01-01`)."
                    ),
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance.transactional",
}


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
    **_kwargs: Any,
) -> dict[str, Any]:
    if not ctx.client_id:
        return _empty_payload(category, direction, status, since)

    try:
        agg = compliance_repo.fetch_transaction_amounts(
            ctx.db,
            client_id=ctx.client_id,
            category=category,
            direction=direction,
            status=status,
            since=since,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "stats_transaction_amounts.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        out = _empty_payload(category, direction, status, since)
        out["error"] = "repo_unavailable"
        return out

    deposits = _to_decimal(agg.get("deposits_total"))
    withdrawals = _to_decimal(agg.get("withdrawals_total"))
    net = _to_decimal(agg.get("net"))
    currency = (agg.get("currency") or "EUR").upper()
    symbol = _CURRENCY_SYMBOLS.get(currency, currency)

    # Cas « rien à montrer » : aucun mouvement après filtres.
    if deposits == 0 and withdrawals == 0:
        return {
            "currency": currency,
            "deposits_total": "0",
            "withdrawals_total": "0",
            "net": "0",
            "by_currency": {},
            "markdown_table": "_Aucune transaction trouvée pour ces critères._",
            "filters_applied": _filters_applied(
                category, direction, status, since
            ),
        }

    # Construction du markdown.
    deposits_str = f"+{_format_amount(deposits)} {symbol}"
    withdrawals_str = f"-{_format_amount(withdrawals)} {symbol}"
    net_sign = "+" if net >= 0 else "-"
    net_str = f"{net_sign}{_format_amount(abs(net))} {symbol}"

    lines = [
        "| Direction | Montant total |",
        "|---|---:|",
        f"| **Total déposé** | {_escape_pipe(deposits_str)} |",
        f"| **Total retiré** | {_escape_pipe(withdrawals_str)} |",
        f"| _Solde net_ | **{_escape_pipe(net_str)}** |",
    ]
    markdown = "\n".join(lines)

    return {
        "currency": currency,
        "deposits_total": str(deposits),
        "withdrawals_total": str(withdrawals),
        "net": str(net),
        "by_currency": _serialize_by_currency(agg.get("by_currency") or {}),
        "markdown_table": markdown,
        "filters_applied": _filters_applied(
            category, direction, status, since
        ),
    }


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _empty_payload(
    category: Optional[str],
    direction: Optional[str],
    status: Optional[str],
    since: Optional[str],
) -> dict[str, Any]:
    return {
        "currency": "EUR",
        "deposits_total": "0",
        "withdrawals_total": "0",
        "net": "0",
        "by_currency": {},
        "markdown_table": "_Aucune transaction trouvée pour ces critères._",
        "filters_applied": _filters_applied(
            category, direction, status, since
        ),
    }


def _serialize_by_currency(raw: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Sérialise les Decimal → str pour JSON-safe."""
    out: dict[str, dict[str, str]] = {}
    for ccy, bucket in raw.items():
        out[ccy] = {
            "deposits": str(_to_decimal(bucket.get("deposits"))),
            "withdrawals": str(_to_decimal(bucket.get("withdrawals"))),
            "net": str(_to_decimal(bucket.get("net"))),
        }
    return out


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value)) if value is not None else Decimal(0)
    except Exception:  # noqa: BLE001
        return Decimal(0)


def _format_amount(value: Decimal) -> str:
    """``45000.00`` → ``45 000`` (FR, sans décimales si entier rond)."""
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
    if dec_part == "00":
        return f"{sign}{int_fr}"
    return f"{sign}{int_fr},{dec_part}"


def _filters_applied(
    category: Optional[str],
    direction: Optional[str],
    status: Optional[str],
    since: Optional[str],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if category:
        out["category"] = category
    if direction:
        out["direction"] = direction
    if status:
        out["status"] = status
    if since:
        out["since"] = since
    return out


def _escape_pipe(s: Any) -> str:
    return str(s).replace("|", r"\|") if s is not None else "—"
