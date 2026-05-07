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
from typing import Any, Optional

from services.assistance import memory as assistance_memory
from services.assistance.agents.base import (
    AGENT_ADVISOR_ID,
    AGENT_COMPLIANCE_ID,
    AGENT_DEFAULT_ID,
    AGENT_MARKET_ID,
    AGENT_PRODUCT_ID,
    AGENT_TRUST_ID,
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

from services.assistance.agents.conversation_continuity import (
    COMPOUND_USER_TURN_MEMORY_KEY,
    enrich_recent_turns_for_llm_semantic_user,
)
from services.assistance.agents.orchestration_context import (
    BUSINESS_INTENTS,
    TRANSACTION_KINDS,
    orchestration_from_route_to_args,
)

logger = logging.getLogger(__name__)


def _effective_router_user_text(agent_input: AgentInput) -> str:
    """Texte utilisateur « effectif » pour le routeur (tags + classement).

    Préfère ``compound_user_turn`` (réponse assistant enrichie + message
    court) lorsqu'elle est présente dans ``memory_state`` — aligné avec
    l'historique injecté aux LLM.
    """
    mem = agent_input.memory_state or {}
    cmp_raw = mem.get(COMPOUND_USER_TURN_MEMORY_KEY)
    if isinstance(cmp_raw, str) and cmp_raw.strip():
        return cmp_raw.strip()
    user_text = (getattr(agent_input, "user_message", "") or "").strip()
    if user_text:
        return user_text
    recent = getattr(agent_input, "recent_turns", None) or []
    for turn in reversed(recent):
        if isinstance(turn, dict) and turn.get("role") == "user":
            return str(turn.get("content") or "").strip()
    return ""


# Liste des `agent_id` que le router est autorisé à choisir.
# Cognitive Bot v4 — Lot 4 (2026-05-04) : ajout de `trust` pour les
# demandes purement sécurité / régulation / custody / hack.
ROUTABLE_AGENTS: list[str] = [
    AGENT_DEFAULT_ID,
    AGENT_COMPLIANCE_ID,
    AGENT_ADVISOR_ID,
    AGENT_PRODUCT_ID,
    AGENT_MARKET_ID,
    AGENT_TRUST_ID,
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
                    "claire (confidence ≥ 0.5). "
                    "**Remplis aussi les dimensions orchestrateur** "
                    "(business_intent, emotional_state, urgency, …) "
                    "pour guider ton, priorité et outils — cf. [ORCHESTRATION] "
                    "dans ton system prompt."
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
                        "business_intent": {
                            "type": "string",
                            "description": (
                                "OPTIONNEL — famille métier dominante. "
                                "Si plusieurs intentions coexistent, choisis "
                                "celle qui doit **piloter l'agent principal** "
                                "(ex. dépôt bloqué + colère → account_operations ; "
                                "la colère est traitée via emotional_state + style)."
                            ),
                            "enum": sorted(BUSINESS_INTENTS),
                        },
                        "transaction_kind": {
                            "type": "string",
                            "enum": sorted(TRANSACTION_KINDS),
                            "description": (
                                "OPTIONNEL — précise l'action CAL quand "
                                "`business_intent` vaut `action_request` : "
                                "`bundle_invest` (crypto basket / bundle), "
                                "`crypto_buy` (achat spot d'un actif). "
                                "Sans offre exclusive pour l'instant."
                            ),
                        },
                        "emotional_state": {
                            "type": "string",
                            "enum": [
                                "calm",
                                "confused",
                                "anxious",
                                "angry",
                                "frustrated",
                                "neutral",
                            ],
                            "description": (
                                "OPTIONNEL — état émotionnel perçu du message "
                                "(et du contexte court)."
                            ),
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": (
                                "OPTIONNEL — urgence opérationnelle ou affective."
                            ),
                        },
                        "regulatory_risk": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": (
                                "OPTIONNEL — risque de déraper vers conseil "
                                "non conforme, promesse, ou sujet sensible AML."
                            ),
                        },
                        "data_need": {
                            "type": "string",
                            "enum": [
                                "none",
                                "account_data",
                                "transaction_data",
                                "kyc_data",
                                "human_review",
                            ],
                            "description": (
                                "OPTIONNEL — données internes nécessaires pour "
                                "répondre correctement."
                            ),
                        },
                        "secondary_intents": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 4,
                            "description": (
                                "OPTIONNEL — intentions satellites "
                                "(ex. reassurance, complaint) quand le message est mixte."
                            ),
                        },
                        "must_acknowledge_emotion": {
                            "type": "boolean",
                            "description": (
                                "OPTIONNEL — True si la réponse doit reconnaître "
                                "l'émotion avant le fond (colère, peur forte)."
                            ),
                        },
                        "must_check_account_data": {
                            "type": "boolean",
                            "description": (
                                "OPTIONNEL — True si les outils compte/transactions "
                                "doivent être utilisés avant de conclure."
                            ),
                        },
                        "needs_human_escalation": {
                            "type": "boolean",
                            "description": (
                                "OPTIONNEL — True si un humain devrait probablement reprendre "
                                "(à communiquer sans promettre un délai irréaliste)."
                            ),
                        },
                        "response_style": {
                            "type": "string",
                            "enum": [
                                "calm_deescalation",
                                "factual_support",
                                "educational",
                                "neutral_advisor",
                            ],
                            "description": (
                                "OPTIONNEL — ton global attendu pour l'agent."
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
                    "apparaît dans le message. "
                    "ROUTER V2 — paramètre OPTIONNEL `tag` : si tu "
                    "fournis un tag d'intention ∈ {epargner, "
                    "securiser_capital, livret_coffre, rendement, "
                    "avenir_securite, investir, performance, retraite, "
                    "bundle_crypto, exclusive_offer, instrument_cote, "
                    "immobilier_long_terme, compte_kyc, depot, retrait, "
                    "virement_sepa, carte_visa, banque, actu_marche, "
                    "opinion_marche, cours_evolution, macro_inflation, "
                    "trading, reussir, projet_vie, decouvrir, "
                    "argent_general}, le runtime utilisera un QCM "
                    "canonique calibré (prompt + options éditoriales) "
                    "et IGNORERA les `prompt`/`options` que tu fournis. "
                    "Préfère cela quand le tag est clair (cf. bloc "
                    "[INTENT TAGS]). Si le sujet est très contextuel "
                    "(produit nommé dans recent_turns, instrument coté "
                    "spécifique), N'envoie PAS de `tag` et fournis des "
                    "options sur mesure."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tag": {
                            "type": "string",
                            "description": (
                                "OPTIONNEL — tag d'intention Vancelian "
                                "qui active un QCM canonique calibré. "
                                "Voir liste exhaustive dans la "
                                "description du tool. Si fourni et "
                                "présent dans le catalogue, override "
                                "complet de prompt + options."
                            ),
                        },
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

    # Phase 2 wiki v1.4 patch — Slot « topic en cours » injecté en
    # contexte system. Le LLM router lit cette ligne **avant** de
    # classifier ; sur un follow-up déictique (« ce bundle », « il/
    # elle »), il doit garder l'`agent_owner` du topic au lieu de
    # réinférer depuis le seul user message.
    topic_block = _build_topic_block(agent_input)
    if topic_block:
        messages.append({"role": "system", "content": topic_block})

    # Router v2 (2026-05-04) — pré-classification keyword-matching FR+EN
    # qui annote le user message avec son `primary_tag` / `family` /
    # `scope_level` / `preferred_agent`. C'est un **signal**, pas une
    # décision : le LLM peut surclasser. Mais cela permet de briser les
    # symétries dans les cas tendus (« quel bundle… » → bundle_crypto
    # détecté → product/advisor le plus probable).
    intent_block = _build_intent_tags_block(agent_input)
    if intent_block:
        messages.append({"role": "system", "content": intent_block})

    # Cognitive Bot v4 (2026-05-04) — bloc [COGNITIVE STATE] préliminaire
    # injecté dans le prompt routeur. Permet au LLM router de moduler
    # ses décisions selon l'état émotionnel du client :
    #   * FEAR / ANGER → favoriser advisor (rassure / désescalade) plutôt
    #     que product (pousse).
    #   * COMPLIANCE   → favoriser compliance.
    #   * OPPORTUNITY / CURIOSITY clair → router direct sur expert.
    # Le state injecté est PRÉLIMINAIRE (calculé avant la décision) ;
    # le state final est calculé après pour les agents experts.
    cognitive_block = _build_cognitive_state_block(agent_input)
    if cognitive_block:
        messages.append({"role": "system", "content": cognitive_block})

    # Cognitive Bot v4 — Lot 7 (2026-05-04). Bloc [CLIENT DISCOVERY]
    # injecté SI projets actifs ou floating params présents. Permet
    # au router de relier « investissements » à un projet en cours
    # (« achat maison ») au lieu de redémarrer thématiquement.
    discovery_block = _build_client_discovery_block(agent_input)
    if discovery_block:
        messages.append({"role": "system", "content": discovery_block})

    # Garder les 4 derniers tours max (2 user + 2 assistant) pour donner
    # un contexte conversationnel court, sans gonfler les tokens.
    mem = agent_input.memory_state or {}
    cmpv = mem.get(COMPOUND_USER_TURN_MEMORY_KEY)
    compound_arg = (
        cmpv.strip()
        if isinstance(cmpv, str) and cmpv.strip()
        else None
    )
    turns_router = enrich_recent_turns_for_llm_semantic_user(
        agent_input.recent_turns,
        compound_user_turn=compound_arg,
        raw_user_fallback=agent_input.user_message or "",
    )
    tail = (turns_router or [])[-4:]
    messages.extend(tail)

    return messages


def _build_client_discovery_block(agent_input: AgentInput) -> str:
    """Lot 7 — lit ``memory_state['client_discovery']`` (déjà rendu en
    string par ``service.start_chat_turn`` via
    ``discovery_engine.render_discovery_for_prompt``) et le retourne
    tel quel pour injection. Vide si rien à dire.
    """
    state = agent_input.memory_state or {}
    rendered = state.get("client_discovery")
    if isinstance(rendered, str) and rendered.strip():
        return rendered
    return ""


def _build_cognitive_state_block(agent_input: AgentInput) -> str:
    """Lit le ``cognitive_state`` du tour courant (préliminaire) depuis
    ``agent_input.memory_state`` et le rend en bloc compact pour le
    prompt routeur. Retourne ``""`` si rien à dire."""
    state = (agent_input.memory_state or {}).get("cognitive_state")
    if not isinstance(state, dict):
        return ""
    try:
        from services.assistance.agents.cognitive_state import (
            CognitiveState,
            render_cognitive_state_for_prompt,
        )

        cog = CognitiveState.from_dict(state)
        rendered = render_cognitive_state_for_prompt(cog)
        return rendered or ""
    except Exception:  # noqa: BLE001
        logger.exception("router._build_cognitive_state_block_failed")
        return ""


def _build_intent_tags_block(agent_input: AgentInput) -> str:
    """Pré-classifie le dernier user message via keyword-matching et
    rend le résultat dans un bloc system court pour le router LLM.

    Retourne ``""`` si le message est vide ou si rien n'a matché.
    """
    user_text = _effective_router_user_text(agent_input)
    if not user_text:
        return ""

    # Import local pour éviter un cycle au démarrage (router_intent_tags
    # n'a pas besoin du router lui-même mais ce module est aussi
    # importé par d'autres helpers du runtime).
    from services.assistance.agents.router_intent_tags import (
        classify_message_tags,
        render_classification_for_prompt,
    )

    classification = classify_message_tags(user_text)
    rendered = render_classification_for_prompt(classification)
    return rendered or ""


def _build_topic_block(agent_input: AgentInput) -> str:
    """Lit le topic depuis `agent_input.memory_state["current_topic"]`
    et le rend en libellé court pour le prompt router.

    Le `service.py` est responsable de remplir `memory_state` avec le
    topic lu en DB avant d'appeler `classify`. Si le slot est absent
    ou mal formé, on retourne `""` (pas de section dans le prompt).
    """
    state = agent_input.memory_state or {}
    raw = state.get("current_topic")
    if not isinstance(raw, dict):
        return ""

    # Import local pour éviter cycle d'imports (router est chargé tôt
    # dans services.assistance, conversation_topic charge database).
    from services.assistance.conversation_topic import (
        render_topic_for_prompt,
    )
    rendered = render_topic_for_prompt(raw)
    if not rendered:
        return ""
    return (
        "[CONTEXT TOPIC] "
        + rendered
        + " Si le user message est un follow-up déictique (« ce bundle », "
        "« il/elle », « la perf »), reste sur l'agent_owner ci-dessus "
        "(ne bascule PAS sur market sur un mot-clé isolé). Si le user "
        "change clairement de sujet, ignore ce topic."
    )


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

    # Router v2 — pré-classification keyword (cf. Lot 2). Le résultat
    # est attaché à toutes les RouterDecision de ce tour pour audit
    # via `assistance_agent_decisions` (admin monitoring).
    intent_dict = _compute_intent_classification_dict(agent_input)

    def _attach(decision: RouterDecision) -> RouterDecision:
        if intent_dict and decision.intent_classification is None:
            decision.intent_classification = intent_dict
        return decision

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
        return _attach(RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.0,
            reasoning="router_llm_failed",
        ))

    tool_calls = response_message.get("tool_calls") or []
    if not tool_calls:
        # Le modèle a répondu en texte au lieu d'un tool call. Rare avec
        # tool_choice="required", mais possible. Fallback default.
        logger.warning(
            "assistance.router.no_tool_call response_text=%s",
            (response_message.get("content") or "")[:200],
        )
        return _attach(RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.0,
            reasoning="router_no_tool_call",
        ))

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
        return _attach(RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.0,
            reasoning="router_invalid_args",
        ))

    if fn_name == "route_to":
        return _attach(_parse_route_to(args))
    if fn_name == "ask_clarification":
        return _attach(_parse_ask_clarification(args, confidence_min=confidence_min))
    if fn_name == "redirect_off_topic":
        memory_state = getattr(agent_input, "memory_state", None) or {}
        current_topic = (
            memory_state.get("current_topic")
            if isinstance(memory_state, dict)
            else None
        )
        return _attach(_parse_redirect_off_topic(
            args,
            confidence_min=confidence_min,
            current_topic=current_topic,
        ))

    logger.warning("assistance.router.unknown_function fn=%s", fn_name)
    return _attach(RouterDecision(
        agent_id=AGENT_DEFAULT_ID,
        confidence=0.0,
        reasoning=f"router_unknown_function:{fn_name}",
    ))


def _compute_intent_classification_dict(
    agent_input: AgentInput,
) -> Optional[dict]:
    """Calcule la classification keyword pour ce tour et la rend en
    dict serializable (pour persistance ``assistance_agent_decisions``
    et JSON-friendly).

    Retourne ``None`` si rien à dire (message vide ou aucun match).
    """
    user_text = _effective_router_user_text(agent_input)
    if not user_text:
        return None

    from services.assistance.agents.router_intent_tags import (
        classify_message_tags,
    )

    classification = classify_message_tags(user_text)
    if not classification.primary_tag:
        return None

    return {
        "primary_tag": classification.primary_tag,
        "family": classification.family,
        "scope_level": classification.scope_level,
        "preferred_agent": classification.preferred_agent,
        "tags": list(classification.tags),
    }


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

    orch = orchestration_from_route_to_args(args)

    return RouterDecision(
        agent_id=agent_id,
        confidence=confidence,
        reasoning=reasoning,
        orchestration=orch,
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

    **Router v2 — paramètre `tag`** : si fourni et présent dans le
    catalogue ``router_clarification_catalog``, le runtime substitue
    prompt + options par le QCM canonique (override complet). Sinon,
    fallback sur le `prompt`/`options` fournis par le LLM.
    """
    tag = str(args.get("tag") or "").strip() or None

    # Cas 1 — tag dans le catalogue : on ignore prompt/options du LLM.
    if tag:
        from services.assistance.agents.router_clarification_catalog import (
            get_clarification_for_tag,
        )

        canonical = get_clarification_for_tag(tag)
        if canonical:
            options: list[ChoiceOption] = []
            # Le catalogue autorise 2 entries avec le même agent_id
            # si les labels sont distincts. On déduplique sur le tuple
            # (id, label) plutôt que sur id seul.
            seen_pairs: set[tuple[str, str]] = set()
            for opt in canonical.get("options", []):
                opt_id = str(opt.get("agent_id") or "").strip()
                opt_label = str(opt.get("label") or "").strip()
                if (
                    not opt_id
                    or opt_id not in ROUTABLE_AGENTS
                    or not opt_label
                ):
                    continue
                pair = (opt_id, opt_label)
                if pair in seen_pairs:
                    continue
                options.append(ChoiceOption(id=opt_id, label=opt_label[:120]))
                seen_pairs.add(pair)

            if options:
                return RouterDecision(
                    agent_id=AGENT_DEFAULT_ID,
                    confidence=max(0.0, confidence_min - 0.01),
                    reasoning=(
                        canonical.get("prompt", "")[:500]
                        or f"clarification_tag:{tag}"
                    ),
                    fallback_choices=options,
                )
            # Catalogue vide ou mal formé : on retombe sur le path LLM.
            logger.warning(
                "assistance.router.clarification_catalog_empty_options "
                "tag=%s — fallback LLM",
                tag,
            )

    # Cas 2 — fallback LLM (pas de tag, ou tag inconnu).
    prompt = str(args.get("prompt") or "").strip()
    raw_options = args.get("options") or []

    options = []
    seen_ids = set()
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
    args: dict[str, Any],
    *,
    confidence_min: float,
    current_topic: Optional[dict[str, Any]] = None,
) -> RouterDecision:
    """Parse + sanitize un tool call `redirect_off_topic` (règle 6).

    Différences clés vs. `ask_clarification` :
      - Le tool est utilisé pour un **hors-sujet manifeste**, pas pour
        une ambiguïté entre 2 agents → l'intention est claire (hors
        scope), seul le recentrage doit être renvoyé.
      - `bridge` (texte) est obligatoire et reste libre (LLM-rédigé).
      - **Router v2 (2026-05-04)** : les ``options`` ne sont plus prises
        du LLM — elles sont **substituées par la liste FIXE**
        ``OFF_TOPIC_FIXED_OPTIONS`` (cf.
        ``router_off_topic_options.py``), avec ajout dynamique d'un slot
        ``resume_topic`` en 1ʳᵉ position si la conversation a un
        ``current_topic`` non-trivial. Cela corrige le pattern observé
        en prod où le LLM inventait des options bancales (« default →
        Discuter de Vancelian »).
      - L'option spéciale `resume_topic` est résolue serveur-side dans
        `service._decide_agent` (lookup du dernier `agent_used`
        non-router de la conversation).

    Le résultat est une `RouterDecision` avec :
      - `agent_id = AGENT_DEFAULT_ID` (placeholder, jamais instancié).
      - `confidence < confidence_min` pour basculer le `service.py`
        sur le path SSE `choices`.
      - `redirect_bridge = bridge` → flag `is_off_topic = True` côté
        consommateurs (logs, build_choices).
      - `fallback_choices = liste fixe + slot resume éventuel`.
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

    # Router v2 — liste FIXE + slot resume dynamique.
    # Import local pour éviter un cycle d'import au démarrage.
    from services.assistance.agents.router_off_topic_options import (
        build_off_topic_options,
    )

    fixed_options = build_off_topic_options(current_topic=current_topic)
    options: list[ChoiceOption] = [
        ChoiceOption(id=str(opt["id"]), label=str(opt["label"])[:120])
        for opt in fixed_options
    ]

    return RouterDecision(
        agent_id=AGENT_DEFAULT_ID,
        confidence=max(0.0, confidence_min - 0.01),
        reasoning="off_topic_redirect",
        fallback_choices=options,
        redirect_bridge=bridge[:500],
    )
