"""Tool ``stats_portfolio_allocation`` — agent **compliance.transactional**, autonomy **L0**.

Allocation macro du portefeuille client (Cash / Crypto en direct /
Bundles) rendue côté Flutter sous forme de donut chart via l'embed
``portfolio_allocation_donut``.

Phase 2c.5 — Lot 3 du sub-agent transactional. Pattern identique à
``read_transaction_detail`` : le tool **émet un embed structuré** dans
``ctx.embeds_to_emit`` (rendu par un widget Flutter dédié wrappant
``DonutsChartBig``), compose un ``summary`` textuel chaleureux, et le
prompt indique au LLM de **ne rien écrire** après l'appel — la carte
visuelle se suffit à elle-même.

Format de retour LLM : la slice list est exposée pour permettre au
LLM de répondre à des questions de suivi (« et en %, ça fait combien
de bundles ? »), mais sans montants bruts si jamais on filtre des
slices à 0. Les valeurs ici sont **client-visibles** (déjà accessibles
via l'écran Wallet/Allocation), pas de leak.

Cf. ``docs/arquantix/COMPLIANCE_TOPICS.md`` § 3.3 et § 6.4 (embeds).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "stats_portfolio_allocation",
        "description": (
            "Calcule l'ALLOCATION du portefeuille du client par grande "
            "classe (Cash, Crypto en direct, Bundles) et déclenche "
            "l'affichage d'une **carte donut chart** côté client. "
            "Tu DOIS te taire après cet appel : la carte contient TOUT "
            "(récap + donut + légende avec %), ne réécris ni intro ni "
            "résumé. À utiliser pour TOUTE question sur la "
            "**répartition**, l'**allocation** ou la **diversification** "
            "du portefeuille (« comment est réparti mon portefeuille ? "
            "», « j'ai combien en cash vs crypto ? », « mon allocation "
            "actuelle ? »). Idempotent."
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
        agg = compliance_repo.fetch_portfolio_allocation(
            ctx.db, client_id=ctx.client_id
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "stats_portfolio_allocation.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        out = _empty_payload()
        out["error"] = "repo_unavailable"
        return out

    currency = (agg.get("currency") or "EUR").upper()
    symbol = _CURRENCY_SYMBOLS.get(currency, currency)
    total_value = _to_decimal(agg.get("total_value"))
    slices = list(agg.get("slices") or [])

    # Cas portefeuille vide : on n'émet pas d'embed (donut vide n'a
    # pas de sens), on remonte un payload textuel exploitable.
    if total_value == 0 or not slices:
        return {
            "currency": currency,
            "total_value": "0",
            "slices": [],
            "embed_emitted": False,
            "summary": (
                "Ton portefeuille est vide pour l'instant — aucune "
                "allocation à afficher."
            ),
        }

    # Composition du summary textuel chaleureux : 1 phrase qui annonce
    # la valeur totale et la classe dominante. Le LLM ne dira rien.
    summary = _compose_summary(slices, total_value, symbol)

    embed: dict[str, Any] = {
        "type": "portfolio_allocation_donut",
        "currency": currency,
        "total_value": float(total_value),
        "summary": summary,
        "slices": [
            {
                "key": str(s.get("key", "")),
                "label": str(s.get("label", "")),
                "value": float(_to_decimal(s.get("value"))),
                "percentage": float(_to_decimal(s.get("percentage"))),
            }
            for s in slices
        ],
    }
    ctx.embeds_to_emit.append(embed)

    return {
        "currency": currency,
        "total_value": str(total_value),
        "slices": [
            {
                "key": str(s.get("key", "")),
                "label": str(s.get("label", "")),
                "percentage": float(_to_decimal(s.get("percentage"))),
            }
            for s in slices
        ],
        "embed_emitted": True,
        "summary": summary,
    }


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _empty_payload() -> dict[str, Any]:
    return {
        "currency": "EUR",
        "total_value": "0",
        "slices": [],
        "embed_emitted": False,
        "summary": (
            "Ton portefeuille est vide pour l'instant — aucune "
            "allocation à afficher."
        ),
    }


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value)) if value is not None else Decimal(0)
    except Exception:  # noqa: BLE001
        return Decimal(0)


def _compose_summary(
    slices: list[dict[str, Any]],
    total_value: Decimal,
    symbol: str,
) -> str:
    """Phrase courte : « Ton portefeuille de X € est composé de … »."""
    if not slices:
        return (
            "Ton portefeuille est vide pour l'instant — aucune "
            "allocation à afficher."
        )

    # Slice dominante = la plus haute en %. Si égalité (rare), la
    # première gagne (ordre venant du repo : fiat / direct / bundles).
    dominant = max(
        slices,
        key=lambda s: float(_to_decimal(s.get("percentage"))),
    )
    dominant_label = str(dominant.get("label") or "").strip()
    dominant_pct = float(_to_decimal(dominant.get("percentage")))

    total_str = _format_amount(total_value)

    # Si une seule slice non-nulle : message simplifié.
    if len(slices) == 1:
        return (
            f"Ton portefeuille s'élève à {total_str} {symbol}, "
            f"intégralement en {dominant_label.lower()}."
        )

    return (
        f"Ton portefeuille s'élève à {total_str} {symbol}, "
        f"avec une dominante en **{dominant_label}** "
        f"({_format_pct(dominant_pct)})."
    )


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


def _format_pct(value: float) -> str:
    return f"{value:.1f} %".replace(".", ",")
