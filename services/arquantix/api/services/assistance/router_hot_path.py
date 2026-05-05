"""Phase 2 wiki v1.4 patch — hot-path follow-up du router.

Court-circuite l'appel LLM router pour les **follow-ups courts** qui
suivent immédiatement un tour d'agent expert, et conserve cet agent.

──────────────────────────────────────────────────────────────────────
Pourquoi

Empiriquement (cf. analyse conv `5bef01e9` 2026-05-04), les
conversations productives suivent un pattern « 1 question initiale
classée → N follow-ups courts sur le même sujet ». Sur ces follow-ups :

  * Le LLM router consomme ~150-300 ms et ~500 tokens.
  * Il flippe parfois sur un mot-clé isolé (« perf », « cours »,
    « performance ») et casse la conversation en routant sur `market`
    alors qu'on parle d'un produit Vancelian.

Solution déterministe : si le user message tient en ≤ N caractères et
que le **dernier message assistant** non-user a été émis par un agent
expert (`product`/`compliance`/`advisor`/`market`), on garde cet agent.

──────────────────────────────────────────────────────────────────────
Garde-fous (refus du hot-path → fallback router LLM)

  * Long message (> N) → vraie question, classification LLM nécessaire.
  * Pas d'agent précédent (1ʳᵉ question) → router LLM obligatoire.
  * Agent précédent = `default` ou `router` → on n'a pas posé d'expert,
    le hot-path n'a pas de cible.
  * `agent_hint` fourni (clic QCM, deep-link) → continuité serveur-side
    déjà gérée par `service.py::_decide_agent`, on ne touche pas.
  * Message contient des **signaux de changement de sujet** (cf.
    `TOPIC_CHANGE_SIGNALS`) — ex. « par contre », « autre question » —
    on laisse le LLM router décider.
  * Module désactivé via `ASSISTANCE_ROUTER_HOT_PATH_ENABLED=false`.

──────────────────────────────────────────────────────────────────────
Tests : `tests/test_assistance_router_hot_path_unit.py`.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from services.assistance.agents.base import AgentInput, RouterDecision
from services.assistance.agents.config import (
    assistance_router_hot_path_enabled,
    assistance_router_hot_path_max_chars,
)

logger = logging.getLogger(__name__)


# Agents experts qui peuvent légitimement être conservés sur un
# follow-up. Volontairement explicite (pas une lecture du registry)
# pour rester déterministe : si on ajoute un agent à l'avenir, c'est
# un acte conscient de l'inclure dans le hot-path.
EXPERT_AGENTS_FOR_HOT_PATH: frozenset[str] = frozenset({
    "product",
    "compliance",
    "advisor",
    "market",
})


# Mots/phrases qui signalent un **changement de sujet**. Présence en
# début de message (ou phrase) → on laisse le LLM router décider.
# On reste conservateur — préférer un faux négatif (LLM appelé sans
# nécessité) à un faux positif (hot-path qui force un agent à
# tort sur un changement de sujet).
TOPIC_CHANGE_SIGNALS: tuple[str, ...] = (
    "par contre",
    "autre question",
    "autre chose",
    "sinon",
    "d'ailleurs",
    "au fait",
    "maintenant ",
    "change",
    "different",
    "différent",
    "quitte",
    "stop",
    # Anglicismes courants dans nos conversations.
    "by the way",
    "btw",
    "another question",
    "now ",
)


# Patterns déictiques qui *renforcent* l'éligibilité au hot-path.
# Présence = signal fort qu'on est sur un follow-up de la même entité.
# Pas obligatoire (un follow-up peut être contextuel sans déictique),
# mais utile en logging / future heuristique.
DEICTIC_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bce\b|\bcette\b|\bces\b|\bcet\b",
        r"\bil\b|\belle\b|\bils\b|\belles\b",
        r"\bsa\b|\bson\b|\bses\b|\bleur\b|\bleurs\b",
        r"\bçà\b|\bça\b",
    )
)


def has_topic_change_signal(message: str) -> bool:
    """`True` si le message contient un signal de changement de sujet.

    On normalise (lower + strip) avant comparaison. Match en début de
    phrase OU en début de message (les signaux comme « sinon » ou
    « par contre » sont rarement en milieu de phrase).
    """
    if not message:
        return False
    normalized = message.strip().lower()
    if not normalized:
        return False
    for signal in TOPIC_CHANGE_SIGNALS:
        if normalized.startswith(signal):
            return True
        # Aussi en milieu si précédé d'un séparateur (".,;!?\n").
        if re.search(rf"[\.\,\;\!\?\n]\s*{re.escape(signal)}", normalized):
            return True
    return False


def has_deictic(message: str) -> bool:
    """`True` si le message contient au moins 1 marqueur déictique."""
    if not message:
        return False
    return any(p.search(message) for p in DEICTIC_PATTERNS)


def should_skip_router(
    *,
    user_message: str,
    last_assistant_agent: Optional[str],
    agent_hint: Optional[str] = None,
) -> Optional[RouterDecision]:
    """Détermine si on peut bypasser le router LLM pour ce tour.

    Retourne :
      * `RouterDecision(agent_id=last_assistant_agent, confidence=0.85,
        reasoning="hot_path_short_followup")` si tous les critères
        sont satisfaits.
      * `None` sinon — le caller doit appeler `router.classify(...)`.

    Cette fonction est **pure** : pas de DB, pas de LLM, pas d'I/O.
    Elle peut être testée en isolation totale.
    """
    # Kill switch.
    if not assistance_router_hot_path_enabled():
        return None

    # `agent_hint` (clic QCM, deep-link) est déjà géré côté `service.py`
    # — on ne s'en mêle pas.
    if agent_hint:
        return None

    # Pas d'agent précédent → 1ʳᵉ question d'une conv : router obligatoire.
    if not last_assistant_agent:
        return None
    last_agent = last_assistant_agent.strip().lower()
    if last_agent not in EXPERT_AGENTS_FOR_HOT_PATH:
        return None

    # Longueur.
    msg = (user_message or "").strip()
    if not msg:
        return None
    max_chars = assistance_router_hot_path_max_chars()
    if len(msg) > max_chars:
        return None

    # Signal de changement de sujet → on laisse le LLM décider.
    if has_topic_change_signal(msg):
        logger.debug(
            "router_hot_path.skip reason=topic_change_signal msg=%r",
            msg[:80],
        )
        return None

    logger.info(
        "router_hot_path.bypass last_agent=%s len=%d deictic=%s",
        last_agent,
        len(msg),
        has_deictic(msg),
    )
    return RouterDecision(
        agent_id=last_agent,
        confidence=0.85,
        reasoning="hot_path_short_followup",
    )


def extract_last_assistant_agent(
    recent_turns: Optional[list[dict]],
) -> Optional[str]:
    """Inspecte `recent_turns` (ordre chronologique, dernier = plus récent)
    et retourne l'`agent_used` du dernier message assistant, ou `None`
    si aucun.

    Format attendu de chaque turn (cf. `service.py::_load_history` étendu) :

        {"role": "user" | "assistant", "content": "...",
         "agent_used": "product" | "compliance" | ...}

    On tolère l'absence du champ `agent_used` sur les anciens messages
    (migration 147 a backfillé NULL → on retourne None dans ce cas, ce
    qui désactive le hot-path naturellement pour les conv legacy).
    """
    if not recent_turns:
        return None
    for turn in reversed(recent_turns):
        if not isinstance(turn, dict):
            continue
        if turn.get("role") != "assistant":
            continue
        agent = turn.get("agent_used")
        if agent and isinstance(agent, str):
            return agent
        # Premier message assistant trouvé sans agent_used → on stoppe.
        # Inutile de remonter plus loin : la conv est probablement legacy.
        return None
    return None


def should_skip_router_from_input(
    agent_input: AgentInput,
    *,
    agent_hint: Optional[str] = None,
) -> Optional[RouterDecision]:
    """Wrapper haut-niveau qui prend un `AgentInput` et l'interprète :
    extrait `user_message` + dernier agent assistant depuis `recent_turns`,
    puis appelle `should_skip_router(...)`.

    Utilisé par `service.py::_decide_agent` pour intégrer le hot-path
    sans dupliquer la logique d'extraction.
    """
    last_agent = extract_last_assistant_agent(agent_input.recent_turns)
    return should_skip_router(
        user_message=agent_input.user_message or "",
        last_assistant_agent=last_agent,
        agent_hint=agent_hint,
    )


__all__ = [
    "EXPERT_AGENTS_FOR_HOT_PATH",
    "TOPIC_CHANGE_SIGNALS",
    "should_skip_router",
    "should_skip_router_from_input",
    "extract_last_assistant_agent",
    "has_topic_change_signal",
    "has_deictic",
]
