"""Phase 2 wiki v1.4 patch — hot-path follow-up du router.

Court-circuite l'appel LLM router pour certains **follow-ups courts**
qui suivent un tour d'agent expert, et conserve cet agent **uniquement**
quand le superviseur n'a pas besoin de relier la question à une **réponse
bot de fond** déjà livrée.

──────────────────────────────────────────────────────────────────────
Pourquoi (historique)

Économie ~150-300 ms sur les enchaînements « même sujet » après un
premier routage. Risque : une question courte (« sur quoi investir ? »)
sans rappel du hot-path **sans** re-lire le dernier message assistant
fige à tort l'agent (ex. `product` alors qu'il faut `advisor`).

──────────────────────────────────────────────────────────────────────
Règle actuelle (2026-05)

Si le **dernier message assistant avant le user courant** dépasse un
seuil de caractères (`ASSISTANCE_ROUTER_HOT_PATH_MIN_PRIOR_ASSISTANT_CHARS`,
défaut 40), on **ne** bypass **pas** le router : la longueur est mesurée
sur le texte **enrichi** (prompt + labels QCM comme côté LLM). Le message
user court est alors interprété **avec** ce contexte par
`router.classify`. Complément : une demande explicite de conseil
personnalisé (cf. `has_personalized_advice_signal`) force aussi le router
— sans réintroduire l’ancienne liste « produits » / advisory du hot-path
historique.

Le hot-path ne s'applique donc surtout quand la réponse assistant
précédente était courte (accusé de réception, etc.) **ou** seuil à 0
(rollback comportement ancien).

──────────────────────────────────────────────────────────────────────
Autres garde-fous

  * Long message user (> max_chars) → router LLM.
  * Pas d'agent précédent expert → router.
  * `agent_hint` (QCM) → géré ailleurs.
  * Signaux `TOPIC_CHANGE_SIGNALS` → router.
  * `ASSISTANCE_ROUTER_HOT_PATH_ENABLED=false`.

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
    assistance_router_hot_path_min_prior_assistant_chars,
)
from services.assistance.agents.conversation_continuity import (
    augment_assistant_content_for_followup,
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

# Demande explicite de conseil / recommandation personnalisée (court message).
# Le hot-path ne doit pas figer `product` alors que la bonne file est
# souvent `advisor` ou un routage nuancé — le superviseur LLM tranche.
_PERSONALIZED_ADVICE_RE: re.Pattern[str] = re.compile(
    r"(?is)"
    r"\bme\s+conseill\w*|"
    r"\btu\s+me\s+conseill\w*|"
    r"\bvous\s+me\s+conseill\w*|"
    r"que\s+(?:tu\s+|vous\s+)?(?:me\s+|m['\u2019])?conseill\w+|"
    r"qu['\u2019]est-ce\s+que\s+(?:tu|vous)\s+(?:me\s+|m['\u2019])?conseill\w*|"
    r"\bquel(?:le)?s?\s+placement[s]?\s+.*\bconseill\w*|"
    r"\bme\s+recommand\w*|"
    r"\b(?:what|which)\s+(?:investments?|products?|funds?)\s+(?:do|would)\s+you\s+"
    r"(?:recommend|suggest)\s+for\s+me|"
    r"\bwhat\s+should\s+i\s+invest\b"
)


def len_of_prior_assistant_reply(
    recent_turns: Optional[list[dict]],
) -> int:
    """Nombre de caractères du **dernier** message assistant avant le tour user.

    L'historique se termine en pratique par le message **user** du tour en
    cours (persistance avant décision router) : on prend l'assistant qui le
    précède. Si le dernier élément n'est pas un user, on prend le dernier
    assistant quand même (tolérance).
    """
    if not recent_turns:
        return 0
    n = len(recent_turns)
    last_idx = n - 1
    if last_idx < 0:
        return 0
    # Sauter le message user courant en fin d'historique.
    scan_from = last_idx
    if recent_turns[scan_from].get("role") == "user":
        scan_from -= 1
    for i in range(scan_from, -1, -1):
        turn = recent_turns[i]
        if not isinstance(turn, dict):
            continue
        if turn.get("role") != "assistant":
            continue
        pl = turn.get("message_payload")
        enriched = augment_assistant_content_for_followup(
            content=str(turn.get("content") or ""),
            message_type=(
                str(turn.get("message_type")).strip()
                if turn.get("message_type") is not None
                else None
            ),
            message_payload=pl if isinstance(pl, dict) else None,
        )
        return len(enriched.strip())
    return 0


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


def has_personalized_advice_signal(message: str) -> bool:
    """Demande orientée « conseil pour moi » (réglementaire / bon routage)."""
    if not message or not message.strip():
        return False
    return bool(_PERSONALIZED_ADVICE_RE.search(message.strip()))


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

    if has_personalized_advice_signal(msg):
        logger.debug(
            "router_hot_path.skip reason=personalized_advice_signal msg=%r",
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

    Si le dernier message assistant (avant ce user) apporte déjà du fond,
    on **n'applique pas** le hot-path : le router LLM doit relier la
    question courte à ce contexte.
    """
    if not assistance_router_hot_path_enabled():
        return None
    if agent_hint:
        return None

    min_prior = assistance_router_hot_path_min_prior_assistant_chars()
    if min_prior > 0:
        prior_len = len_of_prior_assistant_reply(agent_input.recent_turns)
        if prior_len >= min_prior:
            logger.info(
                "router_hot_path.skip reason=prior_assistant_context "
                "prior_len=%d min=%d",
                prior_len,
                min_prior,
            )
            return None

    last_agent = extract_last_assistant_agent(agent_input.recent_turns)
    return should_skip_router(
        user_message=agent_input.user_message or "",
        last_assistant_agent=last_agent,
        agent_hint=agent_hint,
    )


__all__ = [
    "DEICTIC_PATTERNS",
    "EXPERT_AGENTS_FOR_HOT_PATH",
    "TOPIC_CHANGE_SIGNALS",
    "len_of_prior_assistant_reply",
    "should_skip_router",
    "should_skip_router_from_input",
    "extract_last_assistant_agent",
    "has_topic_change_signal",
    "has_deictic",
    "has_personalized_advice_signal",
]
