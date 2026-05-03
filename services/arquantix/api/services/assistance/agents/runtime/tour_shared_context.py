"""État partagé inter-sub-agents au sein d'un même tour client — Phase 2c.

Quand un sub-agent en handoff vers un autre, on veut éviter au target
de **relire** les données déjà collectées par le source (cohérence +
perfo). Mais on ne peut pas tout partager : certains tools de lecture
exposent des **signaux gated anti-tipping-off** (`requires_doc_upload`,
`requires_step_up`) qui doivent rester **internes au sub-agent
remediation** et NE JAMAIS apparaître dans le contexte d'un sub-agent
fonctionnel.

──────────────────────────────────────────────────────────────────────
Solution : whitelist explicite des clés safe-to-share

Ce module définit `_SAFE_KEYS_PER_TOOL` : pour chaque tool de lecture,
les clés du résultat qui peuvent être propagées à un autre sub-agent
en cas de handoff. Tout le reste est **filtré silencieusement**.

Exemple :
  - `read_documents` retourne `by_status` ✓ + `total_count` ✓ →
    safe à partager.
  - `read_external_aml_signals` retourne `flags` ✗ +
    `client_facing_message` ✗ → **rien** n'est partagé.
  - `read_compliance_state` retourne `status.kyc_status` ✓ et
    `status.account_state` ✓ → ok ; mais `safe_signals.requires_doc_upload`
    ✗ est strippé.

──────────────────────────────────────────────────────────────────────
Format du contexte injecté au target

Le runtime appelle `format_for_prompt(...)` qui retourne un bloc
markdown court à concaténer au system prompt du sub-agent target,
sous la section *« Données déjà collectées par le sub-agent
précédent »*. Si la whitelist filtre tout, on retourne ``""`` (et
le target rejoue ses tools normalement).

Cf. `docs/arquantix/MULTI_AGENTS.md` § 2.5 et
`COMPLIANCE_TOPICS.md` § 7bis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Whitelist clés safe-to-share par tool
# ─────────────────────────────────────────────────────────────────────


# Format : `tool_name -> set[clés top-level autorisées]`. Pour les
# tools où on veut filtrer plus profondément (ex.
# `read_compliance_state`), on utilise une fonction custom dans
# `_CUSTOM_FILTERS`. Le runtime applique d'abord le custom filter
# si présent, sinon la whitelist top-level.
_SAFE_KEYS_PER_TOOL: dict[str, frozenset[str]] = {
    # Transactions : agrégats publics + IDs opaques.
    "read_transactions": frozenset({
        "orders_count",
        "by_status",
        "last_order_at",
        "recent_order_ids",
        "cash_movements_count",
        "cash_by_kind",
        "cash_by_status",
        "last_cash_movement_at",
        "investment_orders_count",
    }),
    "read_transaction_detail": frozenset({
        "transaction_id",
        "status",
        "kind",
        "source",
        "created_at",
        "updated_at",
        "is_inbound",
    }),
    # Documents : agrégats par statut, total — pas les détails par doc.
    "read_documents": frozenset({
        "total_count",
        "by_type",
        "by_status",
        "latest_uploaded_at",
    }),
    # Registration : steps publics, pas de payload de saisie.
    "read_registration_progress": frozenset({
        "session_status",
        "current_step_id",
        "completed_steps",
        "total_steps_recorded",
        "last_activity_at",
    }),
    # Diagnose : on partage le topic + context_for_llm + secondary, mais
    # PAS triggers_used (peut leak des signaux internes par contagion).
    "diagnose_compliance_topic": frozenset({
        "dominant_topic",
        "secondary_topics",
        "context_for_llm",
        # `next_recommended_action` est safe : c'est déjà whitelisté
        # par `action_cta_catalog`.
        "next_recommended_action",
    }),
    # ── Tools NON listés ici → 0 partage par défaut ──
    # En particulier : `read_external_aml_signals` et `read_compliance_state`
    # passent par le filtre custom ci-dessous (filtrage gated).
}


def _filter_compliance_state(result: dict[str, Any]) -> dict[str, Any]:
    """Filtre custom pour `read_compliance_state` (gated anti-tipping-off).

    On ne propage QUE le bloc public ``status`` (kyc_status,
    account_state, etc.) — JAMAIS ``safe_signals`` qui contient
    `requires_doc_upload` / `requires_step_up`, qui sont des signaux
    métier sensibles internes au sub-agent compliance qui les a lus.
    """
    if not isinstance(result, dict):
        return {}
    status = result.get("status") or {}
    if not isinstance(status, dict):
        return {}
    # On ne garde QUE les champs publics qui sont déjà visibles client.
    safe_status = {
        k: status.get(k)
        for k in ("client_status", "kyc_status", "account_state", "login_frozen")
        if k in status
    }
    return {"status": safe_status} if safe_status else {}


def _filter_aml_signals(_result: dict[str, Any]) -> dict[str, Any]:
    """Filtre pour `read_external_aml_signals` : **rien** n'est partagé.

    Tout est gated — flags / client_facing_message sont du domaine
    exclusif du sub-agent qui les a lus. Le target d'un handoff doit
    relire s'il en a besoin (ce qui sera rare puisque le handoff a
    justement lieu après une investigation concluant *« pas de signal
    bloquant »*).
    """
    return {}


_CUSTOM_FILTERS: dict[str, Any] = {
    "read_compliance_state": _filter_compliance_state,
    "read_external_aml_signals": _filter_aml_signals,
}


# ─────────────────────────────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────────────────────────────


def filter_tool_result_for_share(
    *, tool_name: str, result: Any
) -> dict[str, Any]:
    """Applique la whitelist safe-to-share sur un résultat de tool.

    Args:
        tool_name: nom du tool ayant produit `result`.
        result:    dict produit par le tool (peut être non-dict en cas
                   d'erreur — on retourne ``{}`` dans ce cas).

    Returns:
        Dict avec UNIQUEMENT les clés safe à partager. Vide si rien
        n'est safe ou si le tool n'est pas dans la whitelist.

    Notes:
        Cette fn n'a pas d'effet si `result` est non-dict ou contient
        une `error` (on filtre `error` aussi : un sub-agent target
        n'a pas à hériter des erreurs du source — il pourra retenter
        s'il en a besoin).
    """
    if not isinstance(result, dict):
        return {}
    if "error" in result:
        return {}

    custom = _CUSTOM_FILTERS.get(tool_name)
    if custom is not None:
        try:
            return custom(result) or {}
        except Exception:  # noqa: BLE001
            logger.exception(
                "tour_shared_context.custom_filter_failed tool=%s",
                tool_name,
            )
            return {}

    allowed = _SAFE_KEYS_PER_TOOL.get(tool_name)
    if not allowed:
        return {}

    out: dict[str, Any] = {}
    for k in allowed:
        if k in result:
            out[k] = result[k]
    return out


def aggregate_tour_context(
    tools_history: list[tuple[str, Any]],
) -> dict[str, Any]:
    """Agrège l'historique tools du tour en un payload safe-to-share.

    Args:
        tools_history: liste ordonnée `[(tool_name, result), ...]` des
            tools appelés depuis le début du tour client.

    Returns:
        Dict ``{tool_name: filtered_result}``. Dernière exécution
        gagne en cas de doublon (le LLM peut avoir relu un tool).
        Vide si rien n'est safe.
    """
    out: dict[str, Any] = {}
    for tool_name, result in tools_history or []:
        filtered = filter_tool_result_for_share(
            tool_name=tool_name, result=result
        )
        if filtered:
            out[tool_name] = filtered
    return out


def format_for_prompt(shared: dict[str, Any]) -> str:
    """Formate le contexte safe-to-share en bloc markdown injectable.

    Le bloc résultant est concaténé au system prompt du sub-agent
    target d'un handoff, sous la section *« Données déjà collectées
    par le sub-agent précédent »*.

    Args:
        shared: dict produit par `aggregate_tour_context(...)`.

    Returns:
        Bloc markdown prêt à concaténer (vide si `shared` vide).
    """
    if not shared:
        return ""

    lines = [
        "## Données déjà collectées par le sub-agent précédent",
        "",
        (
            "Ces données ont été lues juste avant ton intervention. "
            "Tu peux **les utiliser sans relire** les tools "
            "correspondants, sauf si tu as besoin d'un détail plus "
            "précis (ex. `read_transaction_detail`)."
        ),
        "",
        "```json",
        json.dumps(shared, ensure_ascii=False, indent=2, default=str),
        "```",
    ]
    return "\n".join(lines)


__all__ = [
    "aggregate_tour_context",
    "filter_tool_result_for_share",
    "format_for_prompt",
]
