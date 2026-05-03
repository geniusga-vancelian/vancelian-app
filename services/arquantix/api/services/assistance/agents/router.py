"""Router multi-agents — function calling natif OpenAI.

Le router reçoit le **dernier message utilisateur** + la **mémoire
long-terme** + un **historique court** (3-5 derniers tours) et émet
une `RouterDecision`.

Décision : **function calling natif** (cf. § 1.1 du doc d'archi). Le
router déclare 2 tools à l'API OpenAI :

  - `route_to(agent_id, reasoning, confidence)` → cas nominal.
  - `ask_clarification(prompt, options)` → si l'intention est trop
    ambiguë pour décider sereinement.

Si OpenAI ne renvoie aucun tool call (rare, mais possible), on tombe
en **fallback texte → default agent** (confidence 0.0) plutôt que de
crasher.

Tous les paths logguent un JSON structuré côté `assistance.agent.tour`
(cf. § 1.8) — utile pour debug / monitoring.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from services.assistance import memory as assistance_memory
from services.assistance.agents.base import (
    AGENT_ADVISOR_ID,
    AGENT_COMPLIANCE_ID,
    AGENT_DEFAULT_ID,
    AGENT_MARKET_ID,
    AGENT_PRODUCT_ID,
    KNOWN_AGENT_IDS,
    RESUME_TOPIC_HINT_ID,
    AgentInput,
    ChoiceOption,
    RouterDecision,
)
from services.assistance.agents.config import (
    assistance_router_confidence_min,
    assistance_router_model,
    assistance_router_temperature,
)
from services.assistance.agents.openai_client import chat_completion_with_tools
from services.assistance.agents.prompt_builder import load_agent_system_prompt
from services.assistance.llm import LLMError

logger = logging.getLogger(__name__)


# Liste des `agent_id` que le router est autorisé à choisir.
ROUTABLE_AGENTS: list[str] = [
    AGENT_DEFAULT_ID,
    AGENT_COMPLIANCE_ID,
    AGENT_ADVISOR_ID,
    AGENT_PRODUCT_ID,
    AGENT_MARKET_ID,
]

# Identifiants d'option valides dans le QCM produit par
# `redirect_off_topic` : les 4 agents experts + une option spéciale
# `resume_topic` qui ramène l'utilisateur au dernier sujet en cours
# (résolue serveur-side dans `service._decide_agent`).
OFF_TOPIC_OPTION_IDS: list[str] = [
    AGENT_COMPLIANCE_ID,
    AGENT_ADVISOR_ID,
    AGENT_PRODUCT_ID,
    AGENT_MARKET_ID,
    RESUME_TOPIC_HINT_ID,
]


def _routing_tools() -> list[dict]:
    """Définit les 2 tools que le router peut appeler.

    Format : OpenAI function calling v1 (`tools` + `function`).
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "route_to",
                "description": (
                    "Route le tour conversationnel courant vers l'agent "
                    "spécialisé approprié. Utilise quand l'intention est "
                    "claire (confidence ≥ 0.5)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "enum": ROUTABLE_AGENTS,
                            "description": (
                                "Identifiant de l'agent à invoquer parmi "
                                f"{ROUTABLE_AGENTS}."
                            ),
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": (
                                "Niveau de certitude que cet agent est le "
                                "bon, dans [0.0, 1.0]. ≥ 0.8 si très clair."
                            ),
                        },
                        "reasoning": {
                            "type": "string",
                            "description": (
                                "Justification courte (1-2 phrases) du "
                                "choix. Pour debug et logs."
                            ),
                        },
                    },
                    "required": ["agent_id", "confidence", "reasoning"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "ask_clarification",
                "description": (
                    "Demande une clarification via un QCM quand le sujet "
                    "est dans le périmètre Vancelian mais qu'il faut "
                    "préciser. Couvre 2 cas : (A) sujet patrimonial/"
                    "financier large où aucun agent expert ne s'impose "
                    "(« et à propos d'argent ? », « parle-moi "
                    "d'investissement », « j'aimerais épargner ») — "
                    "valoriser le sujet et proposer 3-4 angles concrets "
                    "et engageants ; (B) ambiguïté entre 2 agents "
                    "Vancelian sur un sujet précis. À PRÉFÉRER à "
                    "redirect_off_topic dès qu'un mot-clé patrimonial "
                    "(argent, épargne, placement, investissement, "
                    "patrimoine, retraite, fiscalité, immobilier) "
                    "apparaît dans le message."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": (
                                "Phrase courte en français au ton "
                                "engageant et chaleureux, JAMAIS "
                                "technique ni condescendant. INTERDIT : "
                                "« peux-tu préciser ta question ? », "
                                "« je n'ai pas compris », « reformule "
                                "s'il te plaît ». Pour un sujet large "
                                "in-scope, valoriser : « Bonne nouvelle, "
                                "c'est exactement le cœur de Vancelian. "
                                "Sur quel angle veux-tu qu'on creuse ? »"
                            ),
                        },
                        "options": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 5,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "enum": ROUTABLE_AGENTS,
                                        "description": (
                                            "agent_id correspondant à "
                                            "cette reformulation. "
                                            "Plusieurs options peuvent "
                                            "pointer vers le même "
                                            "agent_id si les angles "
                                            "proposés sont distincts "
                                            "(ex. plusieurs questions "
                                            "advisor)."
                                        ),
                                    },
                                    "label": {
                                        "type": "string",
                                        "description": (
                                            "Label CONCRET et "
                                            "INSPIRANT en français — "
                                            "pas un intitulé technique "
                                            "d'agent. Ex. : « Conseils "
                                            "pour mes placements », "
                                            "« La situation des "
                                            "marchés en ce moment », "
                                            "« Investir pour le long "
                                            "terme », « Préparer ma "
                                            "retraite ». Éviter : "
                                            "« Conseil », « Marché », "
                                            "« Produit »."
                                        ),
                                    },
                                },
                                "required": ["id", "label"],
                            },
                        },
                    },
                    "required": ["prompt", "options"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "redirect_off_topic",
                "description": (
                    "Recentre poliment l'utilisateur quand son message "
                    "est CLAIREMENT étranger au monde Vancelian "
                    "(météo, blagues sans rapport, recettes, sport, "
                    "politique, santé, devoirs scolaires, code "
                    "générique, culture générale hors finance, etc.). "
                    "INTERDIT pour : (1) tout sujet patrimonial ou "
                    "financier — argent, épargne, placement, "
                    "investissement, patrimoine, retraite, fiscalité, "
                    "immobilier, projets de vie financés, éducation "
                    "financière — utilise ask_clarification ; "
                    "(2) salutations / remerciements / questions "
                    "précises sur l'app — utilise route_to(default). "
                    "Test : « une personne raisonnable trouverait-elle "
                    "que ce sujet a un rapport avec l'argent ou le "
                    "patrimoine ? » Si oui → ask_clarification, jamais "
                    "ce tool."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "bridge": {
                            "type": "string",
                            "description": (
                                "1 à 3 phrases courtes en français, "
                                "tutoiement, ton chaleureux et factuel. "
                                "DOIT contenir : (1) une reprise "
                                "explicite et naturelle du sujet "
                                "évoqué par le client (acknowledge), "
                                "(2) une mention non-jugeante que cet "
                                "espace est dédié à l'écosystème "
                                "Vancelian (compte, placements, "
                                "produits, marchés), (3) une "
                                "proposition de suite — soit reprendre "
                                "le sujet Vancelian en cours s'il y en "
                                "a un dans recent_turns, soit demander "
                                "ce qu'on peut aborder. INTERDIT : ton "
                                "condescendant, moralisateur, "
                                "paternaliste ; phrases comme « il "
                                "faut », « revenons à des choses "
                                "sérieuses », « concentrons-nous », "
                                "« ce n'est pas mon rôle ». Pas de "
                                "Markdown, pas de listes, pas d'emoji."
                            ),
                        },
                        "options": {
                            "type": "array",
                            "minItems": 0,
                            "maxItems": 5,
                            "description": (
                                "Si conversation engagée : OPTIONNEL, 1 "
                                "option `resume_topic` en première "
                                "position pour ramener au sujet courant. "
                                "Si conversation neuve : 3 à 4 options "
                                "parmi compliance/advisor/product/market "
                                "formulées en langage client."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "enum": OFF_TOPIC_OPTION_IDS,
                                        "description": (
                                            "ID de l'option : un agent "
                                            "expert ou la valeur "
                                            "spéciale `resume_topic`."
                                        ),
                                    },
                                    "label": {
                                        "type": "string",
                                        "description": (
                                            "Libellé court en français "
                                            "(ex. « Mon compte et mes "
                                            "opérations », « Reprendre "
                                            "<sujet courant> »)."
                                        ),
                                    },
                                },
                                "required": ["id", "label"],
                            },
                        },
                    },
                    "required": ["bridge"],
                },
            },
        },
    ]


def _build_router_messages(agent_input: AgentInput) -> list[dict]:
    """Compose les messages OpenAI pour le router.

    On ne passe **que** :
      - le system prompt router.
      - un bloc memory **synthétique** (long memory client).
      - le dernier message user (clé pour la classification).
      - éventuellement les 2-3 tours précédents pour la cohérence.

    Pas tout l'historique, pour réduire les tokens et accélérer la
    décision (le router doit être rapide).
    """
    system = load_agent_system_prompt("router")
    messages: list[dict] = [{"role": "system", "content": system}]

    memory_block = assistance_memory._format_memory_block(  # noqa: SLF001
        summary=(agent_input.memory_state or {}).get("conversation_summary"),
        client_long_memory=(agent_input.memory_state or {}).get("client_long_memory"),
    )
    if memory_block:
        messages.append({"role": "system", "content": memory_block})

    # Garder les 4 derniers tours max (2 user + 2 assistant) pour donner
    # un contexte conversationnel court, sans gonfler les tokens.
    tail = (agent_input.recent_turns or [])[-4:]
    messages.extend(tail)

    return messages


def classify(agent_input: AgentInput) -> RouterDecision:
    """Détermine quel agent doit traiter ce tour.

    Toujours retourne une `RouterDecision` — jamais d'exception remontée
    à l'appelant. En cas d'erreur LLM ou de réponse mal formée, fallback
    sur `default` agent avec confidence 0.0 (sera lu par le service.py
    et déclenchera potentiellement un QCM générique selon le seuil).
    """
    messages = _build_router_messages(agent_input)
    model = assistance_router_model()
    temperature = assistance_router_temperature()
    confidence_min = assistance_router_confidence_min()

    try:
        response_message = chat_completion_with_tools(
            messages,
            model=model,
            tools=_routing_tools(),
            tool_choice="required",
            temperature=temperature,
        )
    except LLMError as exc:
        logger.warning(
            "assistance.router.llm_failed exc=%s — fallback default", exc
        )
        return RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.0,
            reasoning="router_llm_failed",
        )

    tool_calls = response_message.get("tool_calls") or []
    if not tool_calls:
        # Le modèle a répondu en texte au lieu d'un tool call. Rare avec
        # tool_choice="required", mais possible. Fallback default.
        logger.warning(
            "assistance.router.no_tool_call response_text=%s",
            (response_message.get("content") or "")[:200],
        )
        return RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.0,
            reasoning="router_no_tool_call",
        )

    # On prend le premier tool call (un seul demandé par le prompt).
    call = tool_calls[0]
    fn = (call.get("function") or {})
    fn_name = fn.get("name") or ""
    raw_args = fn.get("arguments") or "{}"
    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    except json.JSONDecodeError:
        logger.warning(
            "assistance.router.invalid_args fn=%s raw=%s", fn_name, raw_args[:200]
        )
        return RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.0,
            reasoning="router_invalid_args",
        )

    if fn_name == "route_to":
        return _parse_route_to(args)
    if fn_name == "ask_clarification":
        return _parse_ask_clarification(args, confidence_min=confidence_min)
    if fn_name == "redirect_off_topic":
        return _parse_redirect_off_topic(args, confidence_min=confidence_min)

    logger.warning("assistance.router.unknown_function fn=%s", fn_name)
    return RouterDecision(
        agent_id=AGENT_DEFAULT_ID,
        confidence=0.0,
        reasoning=f"router_unknown_function:{fn_name}",
    )


def _parse_route_to(args: dict[str, Any]) -> RouterDecision:
    """Parse + sanitize un tool call `route_to`."""
    agent_id = str(args.get("agent_id") or "").strip()
    if agent_id not in KNOWN_AGENT_IDS or agent_id not in ROUTABLE_AGENTS:
        agent_id = AGENT_DEFAULT_ID

    try:
        confidence = float(args.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    if not (0.0 <= confidence <= 1.0):
        confidence = max(0.0, min(1.0, confidence))

    reasoning = str(args.get("reasoning") or "").strip()[:500]

    return RouterDecision(
        agent_id=agent_id,
        confidence=confidence,
        reasoning=reasoning,
    )


def _parse_ask_clarification(
    args: dict[str, Any], *, confidence_min: float
) -> RouterDecision:
    """Parse + sanitize un tool call `ask_clarification`.

    Le résultat est une `RouterDecision` dont :
      - `agent_id = AGENT_DEFAULT_ID` (placeholder, pas utilisé)
      - `confidence = confidence_min - 0.01` (volontairement < seuil)
      - `fallback_choices` rempli pour que le service.py puisse émettre
        l'event SSE `choices` directement (avec ajout automatique de
        l'option `"freeform"` côté service.py).
    """
    prompt = str(args.get("prompt") or "").strip()
    raw_options = args.get("options") or []

    options: list[ChoiceOption] = []
    seen_ids: set[str] = set()
    for opt in raw_options:
        if not isinstance(opt, dict):
            continue
        opt_id = str(opt.get("id") or "").strip()
        opt_label = str(opt.get("label") or "").strip()
        if not opt_id or opt_id not in ROUTABLE_AGENTS or opt_id in seen_ids:
            continue
        if not opt_label:
            continue
        options.append(ChoiceOption(id=opt_id, label=opt_label[:120]))
        seen_ids.add(opt_id)

    # Si aucune option valide n'a été produite, on dégrade vers default
    # sans QCM (mieux que d'envoyer un QCM vide à l'utilisateur).
    if not options:
        return RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.0,
            reasoning="ask_clarification_no_valid_options",
        )

    return RouterDecision(
        agent_id=AGENT_DEFAULT_ID,
        # Volontairement sous le seuil : ça forcera le service.py à
        # détecter que `is_decisive=False` et à pousser le QCM.
        confidence=max(0.0, confidence_min - 0.01),
        reasoning=prompt[:500] or "ambiguous_intent",
        fallback_choices=options,
    )


def _parse_redirect_off_topic(
    args: dict[str, Any], *, confidence_min: float
) -> RouterDecision:
    """Parse + sanitize un tool call `redirect_off_topic` (règle 6).

    Différences clés vs. `ask_clarification` :
      - Le tool est utilisé pour un **hors-sujet manifeste**, pas pour
        une ambiguïté entre 2 agents → l'intention est claire (hors
        scope), seul le recentrage doit être renvoyé.
      - `bridge` (texte) est obligatoire ; `options` est facultatif.
        Quand absent ou vide, le `service.py` n'émettra qu'un message
        de recentrage (`prompt = bridge`) avec uniquement l'option
        `freeform` (« Rien de tout ça — je reformule »), ajoutée
        systématiquement par `_build_choices_payload`.
      - L'option spéciale `resume_topic` est autorisée et résolue
        serveur-side dans `service._decide_agent` (lookup du dernier
        `agent_used` non-router de la conversation).

    Le résultat est une `RouterDecision` avec :
      - `agent_id = AGENT_DEFAULT_ID` (placeholder, jamais instancié).
      - `confidence < confidence_min` pour basculer le `service.py`
        sur le path SSE `choices`.
      - `redirect_bridge = bridge` → flag `is_off_topic = True` côté
        consommateurs (logs, build_choices).
      - `fallback_choices = options sanitizées` (peut être `[]`).
    """
    bridge = str(args.get("bridge") or "").strip()
    if not bridge:
        # Sans bridge, le recentrage n'a aucun sens. On dégrade vers
        # le default plutôt que d'envoyer un QCM vide à l'utilisateur.
        return RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.0,
            reasoning="redirect_off_topic_no_bridge",
        )

    raw_options = args.get("options") or []
    options: list[ChoiceOption] = []
    seen_ids: set[str] = set()
    for opt in raw_options:
        if not isinstance(opt, dict):
            continue
        opt_id = str(opt.get("id") or "").strip()
        opt_label = str(opt.get("label") or "").strip()
        if not opt_id or opt_id not in OFF_TOPIC_OPTION_IDS or opt_id in seen_ids:
            continue
        if not opt_label:
            continue
        options.append(ChoiceOption(id=opt_id, label=opt_label[:120]))
        seen_ids.add(opt_id)

    return RouterDecision(
        agent_id=AGENT_DEFAULT_ID,
        confidence=max(0.0, confidence_min - 0.01),
        reasoning="off_topic_redirect",
        fallback_choices=options,
        redirect_bridge=bridge[:500],
    )
