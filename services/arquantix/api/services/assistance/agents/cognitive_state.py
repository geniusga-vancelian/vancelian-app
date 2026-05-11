"""Cognitive State Engine — Couche A du modèle « Cognitive Bot v4 ».

Référence : ``docs/arquantix/COGNITIVE_BOT.md`` § A. STATE ENGINE.

──────────────────────────────────────────────────────────────────────
Pourquoi ce module existe
──────────────────────────────────────────────────────────────────────

Avant ce Lot, le router classifiait **uniquement le sujet** du message
(``router_intent_tags`` → 32 tags : bundle_crypto, epargner, retraite…).
On savait *de quoi* le client parle, mais **jamais comment il était** :

  * un client qui écrit « j'ai peur de perdre mes 10K€ sur le Cloud
    Mining » est routé vers ``product`` → réponse encyclopédique,
    alors qu'il fallait **rassurer d'abord** ;
  * un client en colère est traité comme un client neutre → le bot
    explique calmement au lieu de **désescalader**.

Le ``cognitive_state`` répond à ce manque : à chaque tour, on calcule
un snapshot orthogonal du tag thématique :

  * ``emotional_intent``     : FEAR, ANGER, CURIOSITY, COMPLIANCE,
                              TRANSACTION, OPPORTUNITY, NEUTRAL
  * ``conversation_stage``   : discovery, clarification, recommendation,
                              conversion
  * ``trust_level``          : float ∈ [0, 1] — érosion / gain
                              progressif selon les signaux observés
  * ``knowledge_level``      : low / medium / high — déduit de la
                              richesse de la mémoire long-terme client

Ce snapshot est **persisté** par le runtime (``service.py``) dans
``assistance_agent_decisions.arguments_json`` à chaque tour, ce qui
permet :

  1. au tour suivant de **lire l'état précédent** (continuité du
     ``trust_level``, transitions de stage stables).
  2. à la vue admin 3-colonnes (cf. v3.0) d'**afficher** la trajectoire
     cognitive du client tour par tour pour debug.

──────────────────────────────────────────────────────────────────────
Stratégie de détection
──────────────────────────────────────────────────────────────────────

Comme ``router_intent_tags``, on est en **keyword-matching FR+EN**
déterministe :

  * Pas de LLM call additionnel — l'``emotional_intent`` est aussi
    inféré par le LLM router (Lot 2 hybride) qui peut surclasser, mais
    la pré-classification keyword est **le filet** rapide et debuggable.
  * Latence quasi-nulle (< 1 ms).

──────────────────────────────────────────────────────────────────────
Mapping intention → priorité
──────────────────────────────────────────────────────────────────────

Quand plusieurs émotions matchent dans le même message (ex. « j'ai peur
mais je suis curieux »), on prend la **plus urgente** dans l'ordre :

    1. ANGER       — désescalade absolue prioritaire
    2. FEAR        — rassurance prioritaire
    3. COMPLIANCE  — blocage opérationnel
    4. TRANSACTION — monitoring (bénin)
    5. OPPORTUNITY — attente d'opportunité
    6. CURIOSITY   — exploration neutre-positive
    7. NEUTRAL     — fallback

Cf. ``EMOTIONAL_INTENT_PRIORITY`` ci-dessous.

──────────────────────────────────────────────────────────────────────
Tests : ``tests/test_assistance_cognitive_state_unit.py``.
──────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Émotions canoniques (orthogonales aux tags thématiques)
# ─────────────────────────────────────────────────────────────────────


EMOTIONAL_INTENT_FEAR = "fear"
EMOTIONAL_INTENT_ANGER = "anger"
EMOTIONAL_INTENT_CURIOSITY = "curiosity"
EMOTIONAL_INTENT_COMPLIANCE = "compliance"
EMOTIONAL_INTENT_TRANSACTION = "transaction"
EMOTIONAL_INTENT_OPPORTUNITY = "opportunity"
EMOTIONAL_INTENT_NEUTRAL = "neutral"


# Ordre de priorité — du plus urgent au plus bénin. Si plusieurs
# émotions matchent, on garde la première trouvée dans cet ordre.
EMOTIONAL_INTENT_PRIORITY: tuple[str, ...] = (
    EMOTIONAL_INTENT_ANGER,
    EMOTIONAL_INTENT_FEAR,
    EMOTIONAL_INTENT_COMPLIANCE,
    EMOTIONAL_INTENT_TRANSACTION,
    EMOTIONAL_INTENT_OPPORTUNITY,
    EMOTIONAL_INTENT_CURIOSITY,
)


KNOWN_EMOTIONAL_INTENTS: frozenset[str] = frozenset({
    EMOTIONAL_INTENT_FEAR,
    EMOTIONAL_INTENT_ANGER,
    EMOTIONAL_INTENT_CURIOSITY,
    EMOTIONAL_INTENT_COMPLIANCE,
    EMOTIONAL_INTENT_TRANSACTION,
    EMOTIONAL_INTENT_OPPORTUNITY,
    EMOTIONAL_INTENT_NEUTRAL,
})


# ─────────────────────────────────────────────────────────────────────
# Stages de conversation
# ─────────────────────────────────────────────────────────────────────


STAGE_DISCOVERY = "discovery"            # découverte initiale, exploration large
STAGE_CLARIFICATION = "clarification"    # le bot vient de poser un QCM
STAGE_RECOMMENDATION = "recommendation"  # un agent expert a livré une réponse riche
STAGE_CONVERSION = "conversion"          # un CTA / deep-link a été émis ou cliqué


KNOWN_STAGES: frozenset[str] = frozenset({
    STAGE_DISCOVERY,
    STAGE_CLARIFICATION,
    STAGE_RECOMMENDATION,
    STAGE_CONVERSION,
})


# ─────────────────────────────────────────────────────────────────────
# Knowledge level (du client)
# ─────────────────────────────────────────────────────────────────────


KNOWLEDGE_LOW = "low"
KNOWLEDGE_MEDIUM = "medium"
KNOWLEDGE_HIGH = "high"


KNOWN_KNOWLEDGE_LEVELS: frozenset[str] = frozenset({
    KNOWLEDGE_LOW,
    KNOWLEDGE_MEDIUM,
    KNOWLEDGE_HIGH,
})


# ─────────────────────────────────────────────────────────────────────
# Catalogue keyword par émotion (FR + EN)
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EmotionalIntentDefinition:
    """Définition keyword-matching d'une émotion canonique."""

    intent: str
    keywords_fr: tuple[str, ...] = ()
    keywords_en: tuple[str, ...] = ()


# Convention identique à ``router_intent_tags`` : keywords lowercase,
# sans accents, matchés en tokens entiers (cf. ``_matches_keyword``).
EMOTIONAL_INTENT_CATALOG: tuple[EmotionalIntentDefinition, ...] = (
    EmotionalIntentDefinition(
        intent=EMOTIONAL_INTENT_ANGER,
        keywords_fr=(
            "scandale", "scandaleux", "scandaleuse", "inacceptable",
            "j exige", "exiger", "exige",
            "marre", "ras le bol", "ras-le-bol",
            "remboursez", "rembourse", "remboursement",
            "incompetent", "incompetents", "incompetente",
            "honteux", "honteuse", "ridicule",
            "n importe quoi", "nimporte quoi",
            "putain", "merde", "foutu", "foutus",
            "ca suffit", "ca ne marche pas", "ca marche pas",
            "ne marche pas", "ne fonctionne pas",
            "j attends depuis", "attends depuis",
            "vous foutez", "vous moquez",
            "arnaque", "arnaqueurs", "voleurs", "vol",
            "harcelement", "harceler",
        ),
        keywords_en=(
            "outrageous", "outrage", "ridiculous",
            "demand", "refund", "incompetent",
            "useless", "scam", "scammers",
            "fed up", "broken", "doesn t work",
            "doesnt work", "stuck", "waiting since",
            "harassment", "harass",
        ),
    ),
    EmotionalIntentDefinition(
        intent=EMOTIONAL_INTENT_FEAR,
        keywords_fr=(
            "j ai peur", "ai peur", "peur de perdre",
            "perdre mon argent", "perdre mes",
            "perte", "pertes", "perdre",
            "risque", "risques", "risque", "risquee", "risques",
            "dangereux", "dangereuse", "danger",
            "scam", "fraude", "frauder",
            "hacker", "hackers", "hack", "hacke",
            "piratage", "pirate", "pirater",
            "doute", "doutes", "douter",
            "inquiet", "inquiete", "inquieter",
            "anxieux", "anxieuse", "anxiete",
            "stress", "stresse", "stresser",
            "n ose pas", "nose pas",
            "rassurer", "rassure", "rassurez",
            "garantie", "garantir", "fiable",
            "faillite", "faillites", "faillir",
            "krach", "crash",
            "j hesite", "hesite", "hesitation",
        ),
        keywords_en=(
            "afraid", "scared", "fear", "fears",
            "loss", "losses", "lose", "losing",
            "risky", "risk", "risks",
            "dangerous", "scam", "fraud",
            "hack", "hacker", "hacked",
            "stolen", "theft",
            "anxious", "worried", "worry", "worrying",
            "nervous", "doubt", "doubts",
            "guarantee", "secure", "trust",
            "bankrupt", "bankruptcy", "crash",
        ),
    ),
    EmotionalIntentDefinition(
        intent=EMOTIONAL_INTENT_COMPLIANCE,
        keywords_fr=(
            "kyc",
            "justificatif", "justificatifs",
            "validation", "valider", "validee",
            "verification", "verifier",
            "identite", "carte d identite", "passeport", "selfie",
            "documents", "document",
            "preuve de domicile", "rib", "kbis",
            "compte bloque", "bloque", "bloquee",
            "en attente de validation", "patiente",
            "patienter",
            "aml", "amf", "regulation",
            "anti blanchiment", "blanchiment",
            "rgpd", "lcb ft", "lcbft",
        ),
        keywords_en=(
            "kyc", "verification", "verify",
            "identity", "id card", "passport", "selfie",
            "proof of address", "documents",
            "blocked", "pending verification",
            "waiting validation",
            "regulation", "compliance",
            "aml", "anti money laundering",
        ),
    ),
    EmotionalIntentDefinition(
        intent=EMOTIONAL_INTENT_TRANSACTION,
        keywords_fr=(
            "mes gains", "mes pertes",
            "ma perf", "mes perfs",
            "ma performance", "mes performances",
            "mon historique", "mon solde", "mes soldes",
            "mes mouvements", "mes operations",
            "mon portefeuille", "mes investissements",
            "combien j ai", "combien je",
            "mon retour", "mes retours sur investissement",
            "mon etat", "mes statistiques", "mes stats",
        ),
        keywords_en=(
            "my balance", "my history", "my performance",
            "my returns", "my account stats",
            "my portfolio", "my gains",
            "my transactions", "my operations",
        ),
    ),
    EmotionalIntentDefinition(
        intent=EMOTIONAL_INTENT_OPPORTUNITY,
        keywords_fr=(
            "opportunite", "opportunites",
            "le bon moment", "bon moment",
            "vaut le coup", "ca vaut le coup",
            "rentable", "profitable", "bon plan",
            "potentiel", "fort potentiel",
            "promo", "promotion", "promotions",
            "offre", "offres", "deal",
            "exclusive", "exclusif", "exclusifs",
            "futur", "avenir", "demain",
            "capter", "saisir l opportunite",
        ),
        keywords_en=(
            "opportunity", "opportunities",
            "good time", "right time",
            "worth it", "worth", "profitable",
            "potential", "high potential",
            "deal", "offer", "exclusive",
            "future", "upcoming",
        ),
    ),
    EmotionalIntentDefinition(
        intent=EMOTIONAL_INTENT_CURIOSITY,
        keywords_fr=(
            "comment", "comment ca marche", "comment ca fonctionne",
            "c est quoi", "ce que c est",
            "qu est ce que",
            "que veut dire",
            "j aimerais comprendre", "aimerais comprendre",
            "expliquer", "explique", "explication",
            "decouvrir", "decouvrez",
            "interesse", "interessant", "interessante",
            "curieux", "curieuse",
            "fonctionnement",
            "voudrais savoir", "savoir plus",
            "en savoir plus", "en savoir un peu plus",
        ),
        keywords_en=(
            "how does", "how do",
            "what is", "what s",
            "explain", "tell me about",
            "discover", "curious", "interested",
            "would like to know", "learn more",
            "want to understand",
        ),
    ),
)


# Index inverse pour lookup O(1).
EMOTIONAL_INTENTS_BY_NAME: dict[str, EmotionalIntentDefinition] = {
    d.intent: d for d in EMOTIONAL_INTENT_CATALOG
}


# ─────────────────────────────────────────────────────────────────────
# Dataclasses I/O
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EmotionalClassification:
    """Résultat de la pré-classification émotionnelle keyword-only."""

    primary_intent: str
    """Émotion la plus saillante du message courant. ``NEUTRAL`` si
    aucun keyword n'a matché."""

    matched_intents: tuple[str, ...] = ()
    """Toutes les émotions trouvées (peut être vide)."""

    keyword_hits: tuple[tuple[str, str], ...] = ()
    """Tuples (intent, keyword) pour debug."""


@dataclass
class CognitiveState:
    """Snapshot complet de l'état cognitif du client à un tour donné.

    Persisté dans ``assistance_agent_decisions.arguments_json`` sous la
    clé ``cognitive_state``. Lu au tour suivant pour assurer la
    continuité (notamment du ``trust_level``).
    """

    emotional_intent: str = EMOTIONAL_INTENT_NEUTRAL
    """Émotion dominante détectée pour CE tour."""

    conversation_stage: str = STAGE_DISCOVERY
    """Phase de la conversation (cf. ``KNOWN_STAGES``)."""

    trust_level: float = 0.5
    """Indice de confiance ∈ [0, 1]. Démarre à 0.5, s'érode sur ANGER /
    FEAR persistantes, regagne lentement sur CURIOSITY / NEUTRAL."""

    knowledge_level: str = KNOWLEDGE_LOW
    """Maturité financière du client (déduite de la mémoire long-terme)."""

    matched_emotional_intents: tuple[str, ...] = field(default_factory=tuple)
    """Toutes les émotions trouvées au tour courant (debug / audit)."""

    keyword_hits: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    """Tuples (intent, keyword) — debug / persist optionnel."""

    def to_dict(self) -> dict[str, Any]:
        """Sérialise en dict JSON-friendly pour persistance."""
        return {
            "emotional_intent": self.emotional_intent,
            "conversation_stage": self.conversation_stage,
            "trust_level": round(float(self.trust_level), 3),
            "knowledge_level": self.knowledge_level,
            "matched_emotional_intents": list(self.matched_emotional_intents),
        }

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "CognitiveState":
        """Reconstruit un CognitiveState depuis un dict persisté.

        Robuste aux dicts partiels ou mal formés : retourne un état
        neutre par défaut plutôt que de lever.
        """
        if not isinstance(data, dict):
            return cls()
        emo = str(data.get("emotional_intent") or EMOTIONAL_INTENT_NEUTRAL)
        if emo not in KNOWN_EMOTIONAL_INTENTS:
            emo = EMOTIONAL_INTENT_NEUTRAL
        stage = str(data.get("conversation_stage") or STAGE_DISCOVERY)
        if stage not in KNOWN_STAGES:
            stage = STAGE_DISCOVERY
        try:
            trust = float(data.get("trust_level", 0.5))
        except (TypeError, ValueError):
            trust = 0.5
        trust = max(0.0, min(1.0, trust))
        kn = str(data.get("knowledge_level") or KNOWLEDGE_LOW)
        if kn not in KNOWN_KNOWLEDGE_LEVELS:
            kn = KNOWLEDGE_LOW
        matched_raw = data.get("matched_emotional_intents") or []
        matched = tuple(
            str(x) for x in matched_raw if str(x) in KNOWN_EMOTIONAL_INTENTS
        )
        return cls(
            emotional_intent=emo,
            conversation_stage=stage,
            trust_level=trust,
            knowledge_level=kn,
            matched_emotional_intents=matched,
        )


# ─────────────────────────────────────────────────────────────────────
# Détection (keyword-matching, identique au pattern intent_tags)
# ─────────────────────────────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Minuscules + sans accents + espaces collapsés. Idem
    ``router_intent_tags._normalize`` — DRY volontairement évité car
    cycle d'imports possible (ce module est importé en hot-path)."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", no_accents).strip()


def _matches_keyword(normalized_msg: str, keyword: str) -> bool:
    """Match délimité par non-alphanum. Évite les faux positifs.

    Identique à ``router_intent_tags._matches_keyword``.
    """
    norm_kw = _normalize(keyword)
    if not norm_kw:
        return False
    pattern = r"(?:^|\W)" + re.escape(norm_kw) + r"(?:$|\W)"
    return re.search(pattern, normalized_msg) is not None


def classify_emotional_intent(message: str) -> EmotionalClassification:
    """Pré-classifie l'émotion dominante d'un message utilisateur.

    Algorithme :
      1. Normalisation message.
      2. Pour chaque émotion du catalogue, on teste tous ses keywords
         FR+EN. Premier match → l'émotion est ajoutée à ``matched``.
      3. ``primary_intent`` = première émotion trouvée dans l'ordre
         ``EMOTIONAL_INTENT_PRIORITY`` (ANGER > FEAR > … > CURIOSITY).
      4. Si rien ne matche → ``NEUTRAL``.

    Important : cette fonction est **pure** (pas d'I/O, pas de DB).
    Hot-path appelable avec confiance.
    """
    if not message or not message.strip():
        return EmotionalClassification(
            primary_intent=EMOTIONAL_INTENT_NEUTRAL,
            matched_intents=(),
            keyword_hits=(),
        )

    normalized = _normalize(message)
    matched: set[str] = set()
    hits: list[tuple[str, str]] = []

    for definition in EMOTIONAL_INTENT_CATALOG:
        for kw in definition.keywords_fr + definition.keywords_en:
            if _matches_keyword(normalized, kw):
                matched.add(definition.intent)
                hits.append((definition.intent, kw))
                break

    if not matched:
        return EmotionalClassification(
            primary_intent=EMOTIONAL_INTENT_NEUTRAL,
            matched_intents=(),
            keyword_hits=(),
        )

    primary = next(
        (intent for intent in EMOTIONAL_INTENT_PRIORITY if intent in matched),
        EMOTIONAL_INTENT_NEUTRAL,
    )

    return EmotionalClassification(
        primary_intent=primary,
        matched_intents=tuple(
            intent for intent in EMOTIONAL_INTENT_PRIORITY if intent in matched
        ),
        keyword_hits=tuple(hits),
    )


# ─────────────────────────────────────────────────────────────────────
# Knowledge level
# ─────────────────────────────────────────────────────────────────────


def infer_knowledge_level(client_long_memory: Optional[dict]) -> str:
    """Mappe la richesse de la mémoire long-terme client en niveau de
    connaissance financière.

    Heuristique simple v1 :
      * 0 facts          → LOW
      * 1-3 facts        → MEDIUM
      * 4+ facts         → HIGH

    Refiné si nécessaire en V2 avec pondération par type de fact
    (``risk_appetite``, ``investment_horizon``, etc.).
    """
    facts = []
    if isinstance(client_long_memory, dict):
        facts = client_long_memory.get("facts") or []
    n = len(facts)
    if n == 0:
        return KNOWLEDGE_LOW
    if n <= 3:
        return KNOWLEDGE_MEDIUM
    return KNOWLEDGE_HIGH


# ─────────────────────────────────────────────────────────────────────
# Conversation stage
# ─────────────────────────────────────────────────────────────────────


def infer_conversation_stage(
    *,
    prev_state: Optional[CognitiveState],
    intent_classification: Optional[dict[str, Any]],
    last_router_decision_kind: Optional[str],
    recent_turns: Optional[list[dict]] = None,
) -> str:
    """Détermine le ``conversation_stage`` du tour courant.

    Logique v1 (pure, pas d'I/O) :

      1. Si AUCUN tour précédent (``prev_state is None`` ET
         ``recent_turns`` vide ou ne contient qu'un seul user turn) →
         ``DISCOVERY``.

      2. Si la **dernière** décision du router (tour n-1) était
         ``ask_clarification`` → ``CLARIFICATION`` (le bot vient de
         demander une précision, on est encore en exploration).

      3. Si la dernière décision était ``route_to`` vers un agent
         expert (``advisor`` / ``product`` / ``market``) → on a livré
         une réponse riche → ``RECOMMENDATION``.

      4. Si on détecte dans les ``recent_turns`` un assistant message
         contenant un deep-link / CTA (heuristique : présence d'un
         lien ``/products/`` ou ``/instruments/``) → ``CONVERSION``.

      5. Sinon → on garde le stage du ``prev_state`` (continuité), ou
         ``DISCOVERY`` par défaut.
    """
    has_prev = prev_state is not None
    n_turns = len(recent_turns or [])

    if not has_prev and n_turns <= 1:
        return STAGE_DISCOVERY

    decision_kind = (last_router_decision_kind or "").strip()

    if decision_kind == "ask_clarification":
        return STAGE_CLARIFICATION

    # Détection conversion (deep-link déjà émis dans recent_turns).
    for turn in recent_turns or []:
        if not isinstance(turn, dict):
            continue
        if turn.get("role") != "assistant":
            continue
        content = str(turn.get("content") or "")
        if "/products/" in content or "/instruments/" in content:
            return STAGE_CONVERSION
        # Embed deep-link sous forme de tag : `[CTA:` ou `deep_link:`
        if "deep_link" in content or "[cta" in content.lower():
            return STAGE_CONVERSION

    expert_agents = {"advisor", "product", "market", "action"}
    intent = intent_classification or {}
    preferred_agent = (
        str(intent.get("preferred_agent") or "").strip().lower()
    )

    if decision_kind == "route_to" and preferred_agent in expert_agents:
        return STAGE_RECOMMENDATION

    if has_prev and prev_state is not None:
        return prev_state.conversation_stage

    return STAGE_DISCOVERY


# ─────────────────────────────────────────────────────────────────────
# Trust level
# ─────────────────────────────────────────────────────────────────────


# Deltas appliqués au ``trust_level`` selon l'émotion observée. Les
# valeurs sont conservatrices : on érode plus vite qu'on ne regagne,
# par alignement avec la réalité émotionnelle (la confiance se perd
# vite, se reconquiert lentement — cf. § C2 du framework cognitif).
TRUST_DELTA_BY_EMOTION: dict[str, float] = {
    EMOTIONAL_INTENT_ANGER: -0.15,
    EMOTIONAL_INTENT_FEAR: -0.10,
    EMOTIONAL_INTENT_COMPLIANCE: -0.05,
    EMOTIONAL_INTENT_TRANSACTION: 0.02,
    EMOTIONAL_INTENT_OPPORTUNITY: 0.02,
    EMOTIONAL_INTENT_CURIOSITY: 0.03,
    EMOTIONAL_INTENT_NEUTRAL: 0.01,
}


def compute_trust_level(
    *,
    prev_trust: Optional[float],
    emotional_intent: str,
) -> float:
    """Met à jour le ``trust_level`` à partir de l'état précédent.

    Démarrage : ``prev_trust = 0.5`` si pas d'historique. Application
    du delta ``TRUST_DELTA_BY_EMOTION``. Clamp [0, 1].

    NB : on ne met PAS d'amortissement multiplicatif (ex. 0.95 × prev)
    en V1 — un client neutre devrait pouvoir maintenir son niveau
    sans érosion artificielle. Si on observe en prod une dérive vers
    le haut sur des conversations longues, on ajoutera un decay.
    """
    base = prev_trust if isinstance(prev_trust, (int, float)) else 0.5
    base = max(0.0, min(1.0, float(base)))
    delta = TRUST_DELTA_BY_EMOTION.get(
        emotional_intent, TRUST_DELTA_BY_EMOTION[EMOTIONAL_INTENT_NEUTRAL]
    )
    return max(0.0, min(1.0, base + delta))


# ─────────────────────────────────────────────────────────────────────
# Compute principal
# ─────────────────────────────────────────────────────────────────────


def compute_cognitive_state(
    *,
    user_message: str,
    prev_state: Optional[CognitiveState] = None,
    intent_classification: Optional[dict[str, Any]] = None,
    last_router_decision_kind: Optional[str] = None,
    client_long_memory: Optional[dict] = None,
    recent_turns: Optional[list[dict]] = None,
) -> CognitiveState:
    """Calcule le ``CognitiveState`` du tour courant.

    Args:
      user_message              : dernier message utilisateur (texte brut).
      prev_state                : snapshot du tour précédent (``None``
                                  au démarrage de la conversation).
      intent_classification     : sortie de ``router_intent_tags`` (dict
                                  contenant ``preferred_agent``,
                                  ``primary_tag``…). Sert à inférer le
                                  stage.
      last_router_decision_kind : ``"route_to"`` /
                                  ``"ask_clarification"`` /
                                  ``"redirect_off_topic"`` du tour n-1.
      client_long_memory        : mémoire long-terme client pour
                                  ``knowledge_level``.
      recent_turns              : K derniers tours user/assistant.

    Returns:
      CognitiveState — snapshot complet, prêt à persister + à injecter
      dans le prompt.
    """
    classification = classify_emotional_intent(user_message or "")

    stage = infer_conversation_stage(
        prev_state=prev_state,
        intent_classification=intent_classification,
        last_router_decision_kind=last_router_decision_kind,
        recent_turns=recent_turns,
    )

    prev_trust = prev_state.trust_level if prev_state else None
    trust = compute_trust_level(
        prev_trust=prev_trust,
        emotional_intent=classification.primary_intent,
    )

    knowledge = infer_knowledge_level(client_long_memory)

    return CognitiveState(
        emotional_intent=classification.primary_intent,
        conversation_stage=stage,
        trust_level=trust,
        knowledge_level=knowledge,
        matched_emotional_intents=classification.matched_intents,
        keyword_hits=classification.keyword_hits,
    )


# ─────────────────────────────────────────────────────────────────────
# Rendu pour injection dans le prompt système
# ─────────────────────────────────────────────────────────────────────


def render_cognitive_state_for_prompt(
    state: Optional[CognitiveState],
) -> Optional[str]:
    """Sérialise un ``CognitiveState`` en bloc compact pour le prompt
    router (ou tout autre prompt système qui en bénéficie).

    Format :
      ``[COGNITIVE STATE] emotional_intent = X | conversation_stage = Y |
      trust_level = 0.42 | knowledge_level = Z``

    Retourne ``None`` si l'état est neutre + discovery + trust ~ 0.5
    (cas démarrage) — on évite de polluer le prompt avec un bloc vide
    de sens.
    """
    if state is None:
        return None
    is_neutral_default = (
        state.emotional_intent == EMOTIONAL_INTENT_NEUTRAL
        and state.conversation_stage == STAGE_DISCOVERY
        and 0.45 <= state.trust_level <= 0.55
        and state.knowledge_level == KNOWLEDGE_LOW
    )
    if is_neutral_default:
        return None

    parts = [
        f"emotional_intent = {state.emotional_intent}",
        f"conversation_stage = {state.conversation_stage}",
        f"trust_level = {state.trust_level:.2f}",
        f"knowledge_level = {state.knowledge_level}",
    ]
    return "[COGNITIVE STATE] " + " | ".join(parts)


__all__ = [
    "CognitiveState",
    "EmotionalClassification",
    "EmotionalIntentDefinition",
    "EMOTIONAL_INTENT_ANGER",
    "EMOTIONAL_INTENT_CATALOG",
    "EMOTIONAL_INTENT_COMPLIANCE",
    "EMOTIONAL_INTENT_CURIOSITY",
    "EMOTIONAL_INTENT_FEAR",
    "EMOTIONAL_INTENT_NEUTRAL",
    "EMOTIONAL_INTENT_OPPORTUNITY",
    "EMOTIONAL_INTENT_PRIORITY",
    "EMOTIONAL_INTENT_TRANSACTION",
    "EMOTIONAL_INTENTS_BY_NAME",
    "KNOWN_EMOTIONAL_INTENTS",
    "KNOWN_KNOWLEDGE_LEVELS",
    "KNOWN_STAGES",
    "KNOWLEDGE_HIGH",
    "KNOWLEDGE_LOW",
    "KNOWLEDGE_MEDIUM",
    "STAGE_CLARIFICATION",
    "STAGE_CONVERSION",
    "STAGE_DISCOVERY",
    "STAGE_RECOMMENDATION",
    "TRUST_DELTA_BY_EMOTION",
    "classify_emotional_intent",
    "compute_cognitive_state",
    "compute_trust_level",
    "infer_conversation_stage",
    "infer_knowledge_level",
    "render_cognitive_state_for_prompt",
]
