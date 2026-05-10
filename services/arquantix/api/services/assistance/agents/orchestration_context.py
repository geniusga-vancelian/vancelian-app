"""Couche « orchestrateur » — dimensions de décision au-delà du simple agent_id.

Aligné sur l'architecture produit (2026-05) : le router ne choisit pas
uniquement un sous-agent ; il estime aussi l'intention métier, l'urgence,
le besoin de données compte, le risque réglementaire et le style de réponse.

Ces champs sont **optionnels** dans l'appel `route_to` (compat ascendante) ;
quand présents ils sont normalisés, persistés dans
``assistance_agent_decisions`` et injectés dans le prompt des agents experts.

Réf. : ``docs/arquantix/COGNITIVE_BOT.md`` § Orchestration.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Valeurs canoniques (alignées message produit / audit) ─────────────

BUSINESS_INTENTS: frozenset[str] = frozenset({
    "product_education",
    "account_operations",
    "compliance_kyc",
    "wealth_advice",
    "trust_reassurance",
    "complaint_deescalation",
    "safety_guardrail",
    "general_in_scope",
    # CAL — intention transactionnelle guidée (embeds + deep-links ; pas d'ordre serveur).
    "action_request",
})

# Sous-type quand ``business_intent`` == ``action_request`` (router / audit).
TRANSACTION_KINDS: frozenset[str] = frozenset({
    "bundle_invest",
    "crypto_buy",
    "crypto_investment_intent",
    "crypto_sell",
    "crypto_swap",
    "deposit",
})

EMOTIONAL_STATES: frozenset[str] = frozenset({
    "calm",
    "confused",
    "anxious",
    "angry",
    "frustrated",
    "neutral",
})

LEVEL_LOW_MED_HIGH: frozenset[str] = frozenset({"low", "medium", "high"})

# P1 UX — création ``crypto_investment_intent`` : garder hors risque hallucination / chats informatifs.
# Si présent ET < seuil dans ``memory_state["orchestration"]``, les tools ``crypto_investment_intent_start``
# sont retirés du toolset tant que cette orchestration voyage dans le même tour mémoire.
ROUTING_CONFIDENCE_CRYPTO_INTENT_DRAFT_MIN: float = 0.6

DATA_NEEDS: frozenset[str] = frozenset({
    "none",
    "account_data",
    "transaction_data",
    "kyc_data",
    "human_review",
})

RESPONSE_STYLES: frozenset[str] = frozenset({
    "calm_deescalation",
    "factual_support",
    "educational",
    "neutral_advisor",
})


def _coerce_enum(value: Any, allowed: frozenset[str], default: str) -> str:
    s = str(value or "").strip().lower()
    return s if s in allowed else default


def _coerce_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in ("1", "true", "yes", "oui"):
        return True
    if s in ("0", "false", "no", "non"):
        return False
    return None


def _coerce_transaction_kind(value: Any) -> Optional[str]:
    s = str(value or "").strip().lower()
    return s if s in TRANSACTION_KINDS else None


def _coerce_secondary_intents(raw: Any, *, max_items: int = 4) -> list[str]:
    out: list[str] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if len(out) >= max_items:
            break
        t = str(item or "").strip().lower()[:80]
        if t and t not in out:
            out.append(t)
    return out


def normalize_orchestration(raw: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Santise un dict produit par le LLM routeur. Retourne ``None`` si vide."""
    if not isinstance(raw, dict) or not raw:
        return None

    business_intent = _coerce_enum(
        raw.get("business_intent"),
        BUSINESS_INTENTS,
        "general_in_scope",
    )
    emotional_state = _coerce_enum(
        raw.get("emotional_state"),
        EMOTIONAL_STATES,
        "neutral",
    )
    urgency = _coerce_enum(
        raw.get("urgency"),
        LEVEL_LOW_MED_HIGH,
        "medium",
    )
    regulatory_risk = _coerce_enum(
        raw.get("regulatory_risk"),
        LEVEL_LOW_MED_HIGH,
        "low",
    )
    data_need = _coerce_enum(
        raw.get("data_need"),
        DATA_NEEDS,
        "none",
    )
    response_style = _coerce_enum(
        raw.get("response_style"),
        RESPONSE_STYLES,
        "neutral_advisor",
    )

    secondary = _coerce_secondary_intents(raw.get("secondary_intents"))
    transaction_kind = _coerce_transaction_kind(raw.get("transaction_kind"))

    routing_conf_raw = raw.get("routing_confidence")
    routing_conf: Optional[float] = None
    if routing_conf_raw is not None:
        try:
            routing_conf = float(routing_conf_raw)
        except (TypeError, ValueError):
            routing_conf = None
        else:
            routing_conf = max(0.0, min(1.0, routing_conf))

    must_ack = _coerce_bool(raw.get("must_acknowledge_emotion"))
    must_data = _coerce_bool(raw.get("must_check_account_data"))
    human_esc = _coerce_bool(raw.get("needs_human_escalation"))

    out: dict[str, Any] = {
        "business_intent": business_intent,
        "emotional_state": emotional_state,
        "urgency": urgency,
        "regulatory_risk": regulatory_risk,
        "data_need": data_need,
        "response_style": response_style,
    }
    if secondary:
        out["secondary_intents"] = secondary
    if must_ack is not None:
        out["must_acknowledge_emotion"] = must_ack
    if must_data is not None:
        out["must_check_account_data"] = must_data
    if human_esc is not None:
        out["needs_human_escalation"] = human_esc
    if transaction_kind:
        out["transaction_kind"] = transaction_kind

    if routing_conf is not None:
        out["routing_confidence"] = routing_conf

    return out


def orchestration_from_route_to_args(args: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Extrait les champs orchestration d'un payload `route_to` (hors agent/conf/reason)."""
    if not isinstance(args, dict):
        return None
    keys = (
        "business_intent",
        "emotional_state",
        "urgency",
        "regulatory_risk",
        "data_need",
        "secondary_intents",
        "must_acknowledge_emotion",
        "must_check_account_data",
        "needs_human_escalation",
        "response_style",
        "transaction_kind",
        "routing_confidence",
    )
    sub: dict[str, Any] = {}
    for k in keys:
        if k in args and args[k] is not None:
            sub[k] = args[k]
    if not sub:
        return None
    return normalize_orchestration(sub)


def render_orchestration_for_prompt(orch: Optional[dict[str, Any]]) -> str:
    """Fragment markdown pour injection system prompt (agents experts)."""
    if not isinstance(orch, dict) or not orch:
        return ""

    lines: list[str] = [
        "## Décision orchestrateur (router)",
        "",
        "Ces dimensions ont été estimées **en même temps** que le choix d'agent.",
        "Respecte-les pour le ton, la priorisation et les données à consulter via outils.",
        "",
    ]

    order = [
        ("business_intent", "Intention métier"),
        ("transaction_kind", "Action transactionnelle (CAL)"),
        ("routing_confidence", "Score confiance routage transactionnel"),
        ("emotional_state", "État émotionnel perçu"),
        ("urgency", "Urgence"),
        ("regulatory_risk", "Risque réglementaire / conformité"),
        ("data_need", "Besoin de données"),
        ("response_style", "Style de réponse recommandé"),
        ("secondary_intents", "Intentions secondaires"),
        ("must_acknowledge_emotion", "Reconnaître l'émotion avant le fond"),
        ("must_check_account_data", "Vérifier les données compte / ops"),
        ("needs_human_escalation", "Escalade humaine suggérée"),
    ]

    for key, label in order:
        if key not in orch:
            continue
        val = orch[key]
        if val is None:
            continue
        if key == "secondary_intents" and isinstance(val, list):
            if val:
                lines.append(
                    f"- **{label}** : {', '.join(str(x) for x in val)}"
                )
            continue
        lines.append(f"- **{label}** : `{val}`")

    return "\n".join(lines) + "\n"


__all__ = [
    "BUSINESS_INTENTS",
    "ROUTING_CONFIDENCE_CRYPTO_INTENT_DRAFT_MIN",
    "TRANSACTION_KINDS",
    "EMOTIONAL_STATES",
    "DATA_NEEDS",
    "RESPONSE_STYLES",
    "LEVEL_LOW_MED_HIGH",
    "normalize_orchestration",
    "orchestration_from_route_to_args",
    "render_orchestration_for_prompt",
]
