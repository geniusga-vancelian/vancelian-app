"""Tool ``stats_portfolio_performance`` — agent **compliance.transactional**, autonomy **L0**.

Performance globale du portefeuille client : NAV courant, capital net
déposé, PnL réalisé / non réalisé / total et pourcentage de
performance.

Phase 2c.5 — Lot 2 / 3 du sub-agent transactional. Format de retour
identique à ``stats_transaction_amounts`` : ``markdown_table``
prêt-à-coller que le LLM colle tel quel.

Anti-tipping-off : les chiffres exposés sont des **agrégats client-
visibles** (déjà présents dans les écrans Wallet / Performance). Pas
de leak de scoring ou de signaux internes.

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
        "name": "stats_portfolio_performance",
        "description": (
            "Calcule la performance globale du portefeuille du client : "
            "valeur courante (NAV), capital net déposé, PnL réalisé, "
            "PnL non réalisé, PnL total, et pourcentage de performance "
            "(PnL total / capital net déposé). Retourne un "
            "`markdown_table` prêt-à-coller (Indicateur / Valeur). "
            "À utiliser pour TOUTE question sur la **performance** du "
            "portefeuille (« combien j'ai gagné ? », « quelle est ma "
            "performance ? », « bilan de mon portefeuille ? », « ai-je "
            "fait des plus-values ? »). Ne pas utiliser pour des "
            "transactions individuelles (utiliser `read_transactions` ou "
            "`list_transactions`). Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
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
    **_kwargs: Any,
) -> dict[str, Any]:
    if not ctx.client_id:
        return _empty_payload()

    try:
        agg = compliance_repo.fetch_portfolio_performance(
            ctx.db, client_id=ctx.client_id
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "stats_portfolio_performance.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        out = _empty_payload()
        out["error"] = "repo_unavailable"
        return out

    currency = (agg.get("currency") or "EUR").upper()
    symbol = _CURRENCY_SYMBOLS.get(currency, currency)
    nav = _to_decimal(agg.get("current_value"))
    net_deposits = _to_decimal(agg.get("net_deposits"))
    realized = _to_decimal(agg.get("realized_pnl"))
    unrealized = _to_decimal(agg.get("unrealized_pnl"))
    total_pnl = _to_decimal(agg.get("total_pnl"))
    perf_pct = agg.get("performance_pct")

    # Cas « portefeuille vide » : NAV = 0 et aucun mouvement → message
    # explicite plutôt qu'un tableau de zéros.
    if nav == 0 and net_deposits == 0 and total_pnl == 0:
        return {
            "currency": currency,
            "current_value": "0",
            "net_deposits": "0",
            "realized_pnl": "0",
            "unrealized_pnl": "0",
            "total_pnl": "0",
            "performance_pct": None,
            "markdown_table": (
                "_Ton portefeuille est vide pour l'instant — aucune "
                "performance à afficher._"
            ),
        }

    nav_str = f"{_format_amount(nav)} {symbol}"
    net_deposits_str = f"{_format_amount(net_deposits)} {symbol}"
    realized_str = _signed_amount(realized, symbol)
    unrealized_str = _signed_amount(unrealized, symbol)
    total_pnl_str = _signed_amount(total_pnl, symbol)
    perf_pct_str = _format_perf_pct(perf_pct)

    lines = [
        "| Indicateur | Valeur |",
        "|---|---:|",
        f"| **Valeur actuelle** | {_escape_pipe(nav_str)} |",
        f"| Capital net déposé | {_escape_pipe(net_deposits_str)} |",
        f"| Plus-values réalisées | {_escape_pipe(realized_str)} |",
        f"| Plus-values latentes | {_escape_pipe(unrealized_str)} |",
        f"| _PnL total_ | **{_escape_pipe(total_pnl_str)}** |",
        f"| _Performance_ | **{_escape_pipe(perf_pct_str)}** |",
    ]
    markdown = "\n".join(lines)

    return {
        "currency": currency,
        "current_value": str(nav),
        "net_deposits": str(net_deposits),
        "realized_pnl": str(realized),
        "unrealized_pnl": str(unrealized),
        "total_pnl": str(total_pnl),
        "performance_pct": perf_pct,
        "markdown_table": markdown,
    }


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _empty_payload() -> dict[str, Any]:
    return {
        "currency": "EUR",
        "current_value": "0",
        "net_deposits": "0",
        "realized_pnl": "0",
        "unrealized_pnl": "0",
        "total_pnl": "0",
        "performance_pct": None,
        "markdown_table": (
            "_Ton portefeuille est vide pour l'instant — aucune "
            "performance à afficher._"
        ),
    }


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value)) if value is not None else Decimal(0)
    except Exception:  # noqa: BLE001
        return Decimal(0)


def _format_amount(value: Decimal) -> str:
    """``45000.00`` → ``45 000`` (FR, 2 décimales si non rondes)."""
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


def _signed_amount(value: Decimal, symbol: str) -> str:
    """Force le signe ``+`` / ``-`` (zéro = `0` sans signe)."""
    if value == 0:
        return f"0 {symbol}"
    if value > 0:
        return f"+{_format_amount(value)} {symbol}"
    # Negative : _format_amount préserve le signe -.
    return f"{_format_amount(value)} {symbol}"


def _format_perf_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    if value > 0:
        return f"+{value:.2f} %".replace(".", ",")
    if value < 0:
        return f"{value:.2f} %".replace(".", ",")
    return "0,00 %"


def _escape_pipe(s: Any) -> str:
    return str(s).replace("|", r"\|") if s is not None else "—"
