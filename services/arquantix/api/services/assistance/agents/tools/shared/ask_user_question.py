"""Tool transverse `ask_user_question` — interrupt-based clarification.

Disponible pour TOUS les agents (cf. `tools/registry.py`). Le tool ne
mute rien lui-même : il signale au runtime qu'il doit interrompre la
boucle et émettre un événement SSE `choices` côté client. Cf.
`MULTI_AGENTS_RUNTIME.md` § 7 et `COMPLIANCE_TOPICS.md` § 5.

Convention de retour (lue par le runtime) :

    {
      "interrupt_with_question": True,
      "prompt":          str,
      "options":         [{"id", "label"[, "agent_hint"][, "deep_link"]}, ...],
      "allow_freeform":  bool,
    }

Phase 2b — chaque option peut porter `agent_hint` OU `deep_link`
(mutuellement exclusifs). Les `deep_link` non-whitelistés sont stripés
silencieusement (defense-in-depth, cf. `action_cta_catalog`).

Lors de l'iteration suivante (déclenchée par la réponse client), le
runtime ne ré-injecte PAS ce tool dans le contexte LLM (le client a
répondu, pas l'agent → l'agent doit raisonner sur la réponse comme un
nouveau message user).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.assistance.agents.tools.contracts import (
    ToolContext,
    ToolSpec,
)
from services.assistance.agents.tools.shared import action_cta_catalog

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "ask_user_question",
        "description": (
            "Pose une question au client pour clarifier sa demande. À "
            "utiliser quand l'agent a besoin d'une information qu'il n'a "
            "pas dans ses tools (ex. « quel est l'objet exact de ton "
            "virement ? »). Le client recevra un QCM si `options` est "
            "fourni, sinon une question libre. Phase 2b : chaque option "
            "peut porter SOIT un `agent_hint` (relance LLM avec le bon "
            "agent), SOIT un `deep_link` (navigation Flutter), JAMAIS "
            "les deux. ATTENTION : interrompt la boucle agent — ne pas "
            "appeler en série."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "Question affichée au client. Doit être courte "
                        "(< 200 caractères), neutre, sans jargon AML/KYC."
                    ),
                    "minLength": 3,
                    "maxLength": 240,
                },
                "options": {
                    "type": "array",
                    "description": (
                        "Liste de choix proposés au client (QCM). Si "
                        "vide, le client tape une réponse libre."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "minLength": 1, "maxLength": 64},
                            "label": {"type": "string", "minLength": 1, "maxLength": 200},
                            "agent_hint": {
                                "type": "string",
                                "description": (
                                    "Si présent, signal au runtime de "
                                    "basculer vers cet agent au prochain "
                                    "tour (ex. 'product')."
                                ),
                                "maxLength": 32,
                            },
                            "deep_link": {
                                "type": "string",
                                "description": (
                                    "Si présent, le tap déclenche une "
                                    "navigation Flutter vers cet écran. "
                                    "DOIT appartenir à la whitelist du "
                                    "catalogue ; sinon strippé."
                                ),
                                "maxLength": 200,
                            },
                        },
                        "required": ["id", "label"],
                        "additionalProperties": False,
                    },
                    "maxItems": 8,
                },
                "allow_freeform": {
                    "type": "boolean",
                    "description": (
                        "Si True (défaut), ajoute une option « rien de "
                        "tout ça » qui rouvre l'input texte libre. "
                        "Recommandé tant que les options ne sont pas "
                        "exhaustives."
                    ),
                },
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "*",  # Marqueur : tool transverse, autorisé à tout agent.
}


def _sanitize_option(raw: Any) -> Optional[dict[str, str]]:
    """Validation + normalisation d'une option (Phase 2b).

    Règles :
      - `id` et `label` requis (sinon None).
      - `agent_hint` et `deep_link` mutuellement exclusifs : si les deux
        sont remplis → on strip `deep_link` (priorité agent_hint).
      - `deep_link` doit être whitelisté via `action_cta_catalog` ;
        sinon → on strip silencieusement (defense-in-depth).

    Returns:
        Option normalisée (ou None si invalide).
    """
    if not isinstance(raw, dict):
        return None
    opt_id = str(raw.get("id") or "").strip()
    opt_label = str(raw.get("label") or "").strip()
    if not opt_id or not opt_label:
        return None

    out: dict[str, str] = {
        "id": opt_id[:64],
        "label": opt_label[:200],
    }

    agent_hint = (raw.get("agent_hint") or "").strip()
    deep_link = (raw.get("deep_link") or "").strip()

    # Mutual exclusion (priorité agent_hint).
    if agent_hint and deep_link:
        logger.warning(
            "ask_user_question.option_conflict id=%s — agent_hint+deep_link, "
            "stripping deep_link",
            opt_id,
        )
        deep_link = ""

    if agent_hint:
        out["agent_hint"] = agent_hint[:32]

    if deep_link:
        if action_cta_catalog.is_known_deep_link(deep_link):
            out["deep_link"] = deep_link[:200]
        else:
            logger.warning(
                "ask_user_question.deep_link_rejected id=%s deep_link=%r "
                "— not in catalog whitelist",
                opt_id,
                deep_link,
            )

    return out


def execute(
    ctx: ToolContext,
    *,
    prompt: str,
    options: Optional[list[dict[str, Any]]] = None,
    allow_freeform: bool = True,
) -> dict[str, Any]:
    """Renvoie un payload signalant au runtime d'interrompre la boucle.

    Aucun side-effect ici : le runtime se charge d'émettre l'événement
    SSE `choices` et de persister le message `message_type='choices'`.

    Args:
        ctx: contexte runtime injecté (non utilisé directement, mais
             requis par la signature `ToolModule`).
        prompt: question affichée au client.
        options: liste `[{id, label, ...}, ...]`. Tronquée à 8 items.
                 Phase 2b : chaque option peut porter `agent_hint` OU
                 `deep_link` (mutuellement exclusifs). Les `deep_link`
                 hors whitelist sont stripés silencieusement.
        allow_freeform: ajoute le bouton « rien de tout ça » côté UI.

    Returns:
        Dict avec `interrupt_with_question=True` et le payload normalisé.
    """
    safe_options: list[dict[str, str]] = []
    for raw in (options or [])[:8]:
        normalized = _sanitize_option(raw)
        if normalized is not None:
            safe_options.append(normalized)

    return {
        "interrupt_with_question": True,
        "prompt": str(prompt or "")[:240].strip(),
        "options": safe_options,
        "allow_freeform": bool(allow_freeform) if allow_freeform is not None else True,
    }
