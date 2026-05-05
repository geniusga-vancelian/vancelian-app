"""Cognitive Bot v4 — Lot 7 — Conversation Continuity Layer.

Référence : ``docs/arquantix/CLIENT_DISCOVERY.md`` § 4 (« Continuité »).

──────────────────────────────────────────────────────────────────────
3 responsabilités
──────────────────────────────────────────────────────────────────────

A) ``should_embed_previous_bot_turn(user_message)`` — détection
   déterministe (longueur + keyword product/instrument/projet) qui
   décide si le user message est laconique au point qu'il faut **lui
   pré-pendre** le contenu du tour bot précédent dans le contexte
   transmis aux tools de retrieval (cf. cas conv ``f9d59f98`` tour #15
   « Les offres » qui dérive sans le tour #14 listant les 5 familles).

B) ``extract_assistant_listing(text)`` — parser déterministe qui
   détecte une liste numérotée ≥ 2 (et bullet ≥ 2) précédée d'une
   question dans la sortie texte d'un agent expert. Retourne la liste
   d'items canonisés ou ``None``.

C) ``auto_qcm_from_listing(listing, agent_id)`` — promotion d'une liste
   textuelle en payload ``choices`` cliquable côté Flutter (cf.
   ``ask_user_question`` Phase 2b). Hard-cap **7**, soft-cap **5**.
   N'est appliqué que pour les agents whitelist
   ``AUTO_QCM_AGENTS``.

Toutes les fonctions sont **purement déterministes** — pas de LLM
call, pas d'I/O DB, pas d'effet de bord. Le runtime appelle ces
fonctions en pré- et post-process autour du loop agentique.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Configuration — kill-switches env (charte env-stability)
# ─────────────────────────────────────────────────────────────────────


def assistance_previous_bot_context_injection_enabled() -> bool:
    """Lit ``ASSISTANCE_PREVIOUS_BOT_CONTEXT_INJECTION_ENABLED`` (default
    ``true``). Permet un rollback prod en 1 redémarrage.
    """
    raw = os.getenv(
        "ASSISTANCE_PREVIOUS_BOT_CONTEXT_INJECTION_ENABLED", "true"
    )
    return raw.strip().lower() in ("1", "true", "yes", "on")


def assistance_auto_qcm_enabled() -> bool:
    """Lit ``ASSISTANCE_AUTO_QCM_ENABLED`` (default ``true``)."""
    raw = os.getenv("ASSISTANCE_AUTO_QCM_ENABLED", "true")
    return raw.strip().lower() in ("1", "true", "yes", "on")


# Whitelist agents pouvant émettre un auto-QCM. ``compliance.*`` exclu
# pour ne pas interférer avec les flux KYC qui ont déjà leurs propres
# QCM ciblés (cf. `diagnose_compliance_topic`).
AUTO_QCM_AGENTS: frozenset[str] = frozenset({
    "default",
    "advisor",
    "product",
    "market",
    "trust",
})


# Caps QCM (Lot 7 — réviewé du framework Lot 3).
# Source : Miller's law (7±2) + UX mobile Vancelian (≤ 7 boutons
# tiennent sur les écrans 5,5″+).
QCM_HARD_CAP: int = 7
QCM_SOFT_CAP: int = 5


# Cognitive Bot v4 — Lot 7 V1.1 (2026-05-05). Seuil minimum d'items
# pour AUTO-promote en QCM (`auto_qcm_from_listing`). Distinct de la
# détection de listing (`extract_assistant_listing` reste à 2 items —
# ça reste utile pour exposer une liste détectée à un humain qui
# debug). Un listing à 2 items ressemble plus à du parallélisme
# rhétorique (« Côté A vs côté B ») qu'à un vrai menu de choix : on
# ne le promote pas en QCM cliquable pour ne pas générer de bruit UI.
QCM_AUTO_PROMOTE_MIN_ITEMS: int = 3


# Embeds backend qui fournissent **déjà** des CTAs cliquables au client
# Flutter (cf. `services/assistance/agents/tools/product/show_*.py`).
# Si l'un d'eux est attaché au tour assistant, on **ne promote pas**
# de QCM auto en plus — sinon doublon UI.
EMBEDS_WITH_BUILTIN_CTAS: frozenset[str] = frozenset({
    "crypto_bundles_card",      # show_crypto_bundles
    "bundle_detail_card",       # show_bundle_detail
    "instrument_detail_card",   # show_instrument_card
    "transaction_detail",       # read_transaction_detail (compliance)
})


# Valeurs `next_best_action` pour lesquelles l'auto-promote QCM est
# CONTRE-INDIQUÉE (cf. `_response_framework.md` § Listes structurantes).
# Quand l'objectif est de donner une preuve, redonner du contrôle ou
# imposer un micro-step, transformer la réponse en menu à choix
# **dilue** la directivité du tour. Le LLM peut quand même appeler
# `ask_user_question` explicitement si pertinent — mais on ne l'auto-
# promote PAS depuis une liste textuelle.
NEXT_BEST_ACTIONS_AUTO_QCM_FORBIDDEN: frozenset[str] = frozenset({
    "give_proof",
    "give_control",
    "micro_step",
    "call_to_action",
})


# ─────────────────────────────────────────────────────────────────────
# A) Embed previous bot turn — règle déterministe simple
# ─────────────────────────────────────────────────────────────────────


# Longueur seuil sous laquelle on considère le message « laconique »
# (en mots). 12 c'est un compromis : « le coffre flexible m'intéresse,
# pourquoi ? » fait 7 mots et est déjà standalone (présence de "coffre
# flexible"), tandis que « les offres » (2 mots) est laconique.
LACONIC_WORD_THRESHOLD: int = 12


# Catalogue des **labels qui rendent un message standalone** (FR+EN). Si
# l'un de ces tokens apparaît dans le user message, on considère qu'il
# est self-contained et on n'embarque PAS le tour précédent. Couvre :
#   * produits Vancelian propriétaires (Vault, Coffre, Bundle, Top 5,
#     Cloud Mining, Privilege Club, Vancelian Card, Coffre Flexible/Avenir).
#   * instruments cotés majeurs (BTC, ETH, USDT, USDC, …).
#   * mots-clés projet (maison, retraite, vacances, …) — le user prend
#     l'initiative de nommer un projet, on n'embarque pas.
_STANDALONE_TOKENS: tuple[str, ...] = (
    # Produits Vancelian
    "vault",
    "coffre",
    "coffre flexible",
    "coffre avenir",
    "bundle",
    "basket",
    "top 2",
    "top 5",
    "cloud mining",
    "privilege club",
    "vancelian card",
    "carte vancelian",
    "exclusive offer",
    "offre exclusive",
    "dubai villa",
    "munduk",
    "niseko",
    "al barari",
    # Instruments cotés
    "btc",
    "eth",
    "usdt",
    "usdc",
    "sol",
    "xrp",
    "ada",
    "avax",
    "dot",
    "doge",
    "trx",
    "bitcoin",
    "ethereum",
    # Mots-clés projet (initiative client)
    "maison",
    "appartement",
    "retraite",
    "vacances",
    "voyage",
    "etudes",
    "mariage",
    "entreprise",
    "heritage",
    "house",
    "apartment",
    "retirement",
    "vacation",
    "wedding",
    "studies",
    "business",
    "inheritance",
)


def _normalize(text: str) -> str:
    if not text:
        return ""
    s = text.strip().lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _word_count(text: str) -> int:
    if not text:
        return 0
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def contains_standalone_token(message: str) -> bool:
    """True si le message contient un token qui suffit à le rendre
    self-contained (produit Vancelian, instrument coté, ou label
    projet). Vide / None → False.
    """
    norm = _normalize(message)
    return any(tok in norm for tok in _STANDALONE_TOKENS)


def should_embed_previous_bot_turn(user_message: str) -> bool:
    """Décide si le tour assistant précédent doit être pré-pendu au
    user message dans le contexte des tools de retrieval.

    Règle :
      * désactivé si la feature flag est off ;
      * embed si word_count(user_message) ≤ LACONIC_WORD_THRESHOLD
        ET pas de token standalone détecté ;
      * sinon non.
    """
    if not assistance_previous_bot_context_injection_enabled():
        return False
    if not user_message or not user_message.strip():
        return False
    if _word_count(user_message) > LACONIC_WORD_THRESHOLD:
        return False
    if contains_standalone_token(user_message):
        return False
    return True


def build_previous_bot_context_block(
    *,
    user_message: str,
    last_assistant_text: Optional[str],
    truncate_chars: int = 400,
) -> Optional[str]:
    """Construit le bloc d'enrichissement à pré-pendre au user message
    pour les tools de retrieval, **uniquement** si
    ``should_embed_previous_bot_turn`` retourne True ET que ``last_assistant_text``
    est non vide.

    Retourne ``None`` si rien à faire — le caller peut alors envoyer
    le user_message brut.
    """
    if not should_embed_previous_bot_turn(user_message):
        return None
    text = (last_assistant_text or "").strip()
    if not text:
        return None
    truncated = text[: max(50, int(truncate_chars))]
    if len(text) > len(truncated):
        truncated = truncated + "…"
    return (
        "[CONTEXT FROM PREVIOUS BOT TURN]\n"
        + truncated
        + "\n[USER MESSAGE]\n"
        + user_message.strip()
    )


# ─────────────────────────────────────────────────────────────────────
# B) Listing extractor (post-process tour assistant)
# ─────────────────────────────────────────────────────────────────────


@dataclass
class ListingItem:
    """Un item extrait d'une liste numérotée/bullet du tour assistant."""

    index: int  # 1-based
    label: str  # texte court, normalisé pour QCM
    raw: str  # texte brut original (pour debug)


@dataclass
class ExtractedListing:
    items: list[ListingItem] = field(default_factory=list)
    has_question_after: bool = False
    raw_question: Optional[str] = None  # phrase question si trouvée


# Match « 1. … » ou « 1) … » ou « - … » ou « * … » en début de ligne.
_RE_LIST_LINE = re.compile(
    r"^\s*(?:(\d{1,2})[.)]\s+|[-*•]\s+)(.+?)\s*$",
)

# Markdown bold/italics inline qu'on retire pour normaliser le label.
_RE_INLINE_MD = re.compile(r"\*\*|__|\*|_|`")

# Mots-cibles qui, en fin de tour, signalent une question pour le user.
# Indépendamment du `?`. Permet de capturer aussi les listes informatives
# qui finissent par « lequel t'intéresse ? ».
_QUESTION_TRIGGER_PATTERNS: tuple[str, ...] = (
    "lequel",
    "laquelle",
    "lesquels",
    "lesquelles",
    "tu prefere",
    "tu preferes",
    "tu choisis",
    "duquel",
    "parmi",
    "te plait",
    "te plaisent",
    "souhaites tu",
    "tu veux",
    "interesse",
    "interessent",
    "which one",
    "what would you",
    "do you want",
    "which of these",
)


def _strip_inline_markdown(text: str) -> str:
    return _RE_INLINE_MD.sub("", text).strip()


def _clean_label(raw: str, *, max_chars: int = 60) -> str:
    """Normalise un item de liste pour QCM : strip markdown, garder la
    première phrase, tronquer à ``max_chars``.
    """
    text = _strip_inline_markdown(raw)
    # Couper sur la première ":" ou première phrase ("." suivi d'espace)
    if ":" in text:
        text = text.split(":", 1)[0].strip()
    else:
        # Couper sur " - " (description après tiret)
        if " - " in text:
            text = text.split(" - ", 1)[0].strip()
        elif " — " in text:
            text = text.split(" — ", 1)[0].strip()
    # Encore trop long ? Tronquer
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def extract_assistant_listing(text: str) -> Optional[ExtractedListing]:
    """Détecte une liste numérotée/bullet ≥ 2 dans la sortie assistant.

    Reconnaît :

      * Listes numérotées : ``1. … 2. …`` ou ``1) … 2) …``.
      * Bullets : ``- … - …`` ou ``* … * …`` (≥ 2 items).

    La liste doit être :
      * **continue** (lignes consécutives) — interruptions ignorées si
        ce sont juste des sauts de paragraphe.
      * suivie d'une question (présence d'un ``?`` après ou pattern
        question-déclencheur dans les 5 dernières lignes).

    Retourne ``None`` si pas de liste valide.
    """
    if not text or not text.strip():
        return None

    lines = text.splitlines()
    # Étape 1 : détecter le bloc de liste le plus long
    best_run: list[ListingItem] = []
    current_run: list[ListingItem] = []
    auto_index = 0
    for line in lines:
        m = _RE_LIST_LINE.match(line)
        if m is None:
            if len(current_run) >= 2 and len(current_run) > len(best_run):
                best_run = current_run[:]
            current_run = []
            continue
        num_str, body = m.group(1), m.group(2)
        if num_str is not None:
            try:
                idx = int(num_str)
            except ValueError:
                idx = len(current_run) + 1
        else:
            auto_index += 1
            idx = auto_index
        # On ignore les sous-listes "1.1" ou items vides
        if not body.strip():
            continue
        label = _clean_label(body)
        if not label:
            continue
        current_run.append(
            ListingItem(index=idx, label=label, raw=body.strip())
        )
    if len(current_run) >= 2 and len(current_run) > len(best_run):
        best_run = current_run[:]

    if len(best_run) < 2:
        return None

    # Étape 2 : détecter qu'une question est posée après la liste
    has_question = "?" in text[-300:]
    if not has_question:
        norm_tail = _normalize(text[-400:])
        for trigger in _QUESTION_TRIGGER_PATTERNS:
            if trigger in norm_tail:
                has_question = True
                break

    raw_question: Optional[str] = None
    if has_question:
        # Capture la dernière phrase qui se termine par '?' ou la
        # dernière phrase tout court (heuristique simple, best-effort).
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if sentences:
            for s in reversed(sentences):
                if "?" in s:
                    raw_question = s.strip()
                    break
            if raw_question is None:
                raw_question = sentences[-1].strip()

    return ExtractedListing(
        items=best_run,
        has_question_after=has_question,
        raw_question=raw_question,
    )


# ─────────────────────────────────────────────────────────────────────
# C) Auto-QCM promoter
# ─────────────────────────────────────────────────────────────────────


@dataclass
class AutoQcmCandidate:
    """Payload de QCM dérivé d'un listing assistant, prêt à être émis
    par le runtime en complément du texte assistant.

    Le caller (runtime SSE / `process_chat_turn`) reste responsable de
    l'émission elle-même. Cette fonction ne fait QUE construire le
    payload.
    """

    prompt: str
    options: list[dict[str, Any]]
    agent_hint: str
    truncated: bool  # True si on a coupé au hard-cap

    def to_choices_payload(self) -> dict[str, Any]:
        """Format compatible avec ``_build_choices_payload`` côté
        service.py (cf. l'event SSE ``choices``).
        """
        return {
            "prompt": self.prompt,
            "options": list(self.options),
        }


def auto_qcm_from_listing(
    listing: ExtractedListing,
    *,
    agent_id: str,
    fallback_prompt: str = "Sur quelle option tu veux qu'on continue ?",
    min_items: int = QCM_AUTO_PROMOTE_MIN_ITEMS,
) -> Optional[AutoQcmCandidate]:
    """Promotion d'un listing assistant en QCM cliquable.

    Retourne ``None`` si :
      * la feature flag ``ASSISTANCE_AUTO_QCM_ENABLED`` est off ;
      * ``agent_id`` n'est pas dans ``AUTO_QCM_AGENTS`` ;
      * le listing n'a pas de question après (``has_question_after=False``) ;
      * < ``min_items`` (par défaut ``QCM_AUTO_PROMOTE_MIN_ITEMS=3``).
        Un listing à 2 items est plus du parallélisme rhétorique qu'un
        menu de choix → on ne promote pas pour éviter le bruit UI.

    Cap les items à ``QCM_HARD_CAP=7``. Au-delà, ``truncated=True`` et un
    warning est loggé.
    """
    if not assistance_auto_qcm_enabled():
        return None
    if agent_id not in AUTO_QCM_AGENTS:
        return None
    if not listing or not listing.has_question_after:
        return None
    if len(listing.items) < max(2, int(min_items)):
        return None

    # Soft cap → log informatif (pas bloquant) ; hard cap → tronque.
    items = listing.items
    truncated = False
    if len(items) > QCM_HARD_CAP:
        logger.warning(
            "auto_qcm.truncated agent=%s items=%d hard_cap=%d",
            agent_id,
            len(items),
            QCM_HARD_CAP,
        )
        items = items[:QCM_HARD_CAP]
        truncated = True
    elif len(items) > QCM_SOFT_CAP:
        logger.info(
            "auto_qcm.over_soft_cap agent=%s items=%d soft_cap=%d",
            agent_id,
            len(items),
            QCM_SOFT_CAP,
        )

    options = [
        {
            "id": f"auto_qcm_{i + 1}",
            "label": item.label,
            # On suggère au runtime de **rester sur le même agent** au
            # tour suivant (le user clique → on reste dans la
            # conversation actuelle).
            "agent_hint": agent_id,
        }
        for i, item in enumerate(items)
    ]

    prompt = (
        listing.raw_question
        or fallback_prompt
    )
    if len(prompt) > 240:
        prompt = prompt[:239] + "…"

    return AutoQcmCandidate(
        prompt=prompt,
        options=options,
        agent_hint=agent_id,
        truncated=truncated,
    )


# ─────────────────────────────────────────────────────────────────────
# C bis) Orchestrateur runtime — `decide_auto_qcm`
# ─────────────────────────────────────────────────────────────────────


@dataclass
class AutoQcmDecision:
    """Résultat de ``decide_auto_qcm``.

    * ``candidate`` : payload de QCM à émettre, ou ``None`` si on
      ne promote pas.
    * ``skip_reason`` : raison du skip (None si promu) — utile pour
      logs/observabilité ; ne fuite jamais au client.
    """

    candidate: Optional[AutoQcmCandidate]
    skip_reason: Optional[str] = None

    @property
    def promoted(self) -> bool:
        return self.candidate is not None


# Codes de skip (pour logs ; libellés stables, ne pas renommer).
SKIP_DISABLED = "disabled_by_env"
SKIP_AGENT_NOT_WHITELISTED = "agent_not_whitelisted"
SKIP_RUNTIME_CHOICES_PRESENT = "runtime_choices_present"
SKIP_EMBED_HAS_CTAS = "embed_has_builtin_ctas"
SKIP_OBJECTIVE_FORBIDS = "objective_forbids_auto_qcm"
SKIP_OBJECTIVE_STOP_PUSHING = "objective_stop_pushing"
SKIP_NO_LISTING = "no_listing_detected"
SKIP_LISTING_NO_QUESTION = "listing_without_question"
SKIP_LISTING_TOO_SHORT = "listing_below_min_items"


def _objective_forbids_auto_qcm(objective: Optional[dict]) -> bool:
    """Lit ``objective.next_best_action`` et ``objective.stop_pushing``
    pour décider si l'auto-promote est contre-indiqué.

    Retourne ``True`` (= forbid) si :
      * ``stop_pushing == True`` (FEAR / ANGER → on ne pousse rien).
      * ``next_best_action`` ∈ ``NEXT_BEST_ACTIONS_AUTO_QCM_FORBIDDEN``.
    """
    if not isinstance(objective, dict):
        return False
    if bool(objective.get("stop_pushing")):
        return True
    nba = objective.get("next_best_action")
    if isinstance(nba, str) and nba in NEXT_BEST_ACTIONS_AUTO_QCM_FORBIDDEN:
        return True
    return False


def _embeds_have_builtin_ctas(embeds: Optional[list[dict]]) -> bool:
    """True si l'un des embeds émis par le runtime fournit déjà des
    CTAs cliquables (``crypto_bundles_card``, ``bundle_detail_card``,
    ``instrument_detail_card``, ``transaction_detail``).
    """
    if not embeds:
        return False
    for emb in embeds:
        if not isinstance(emb, dict):
            continue
        t = emb.get("type")
        if isinstance(t, str) and t in EMBEDS_WITH_BUILTIN_CTAS:
            return True
    return False


def decide_auto_qcm(
    *,
    full_text: str,
    agent_id: str,
    runtime_choices_present: bool,
    runtime_embeds: Optional[list[dict]] = None,
    objective: Optional[dict] = None,
) -> AutoQcmDecision:
    """Décide si on émet un auto-QCM en post-process SSE.

    Centralise tous les garde-fous (E) :

      1. Kill-switch env (``ASSISTANCE_AUTO_QCM_ENABLED=false``).
      2. Agent dans la whitelist (``AUTO_QCM_AGENTS``).
      3. Pas de QCM déjà émis par l'agent (``ask_user_question``).
      4. Pas d'embed avec CTAs intégrés (``crypto_bundles_card`` etc.).
      5. ``objective.stop_pushing`` False et ``next_best_action`` pas
         dans la liste interdite.
      6. Listing détecté + question présente + ≥ 3 items.

    Retourne ``AutoQcmDecision(candidate=…, skip_reason=…)``.
    """
    # 1) kill-switch
    if not assistance_auto_qcm_enabled():
        return AutoQcmDecision(None, skip_reason=SKIP_DISABLED)
    # 2) whitelist agent
    if agent_id not in AUTO_QCM_AGENTS:
        return AutoQcmDecision(None, skip_reason=SKIP_AGENT_NOT_WHITELISTED)
    # 3) pas de double-QCM
    if runtime_choices_present:
        return AutoQcmDecision(None, skip_reason=SKIP_RUNTIME_CHOICES_PRESENT)
    # 4) pas de redondance avec embeds CTA
    if _embeds_have_builtin_ctas(runtime_embeds):
        return AutoQcmDecision(None, skip_reason=SKIP_EMBED_HAS_CTAS)
    # 5) objective interdit ?
    if _objective_forbids_auto_qcm(objective):
        # Distinguer stop_pushing pour observabilité (proxy frustration
        # client → on veut surveiller spécifiquement).
        if isinstance(objective, dict) and bool(objective.get("stop_pushing")):
            return AutoQcmDecision(None, skip_reason=SKIP_OBJECTIVE_STOP_PUSHING)
        return AutoQcmDecision(None, skip_reason=SKIP_OBJECTIVE_FORBIDS)
    # 6) listing valide ?
    listing = extract_assistant_listing(full_text)
    if listing is None:
        return AutoQcmDecision(None, skip_reason=SKIP_NO_LISTING)
    if not listing.has_question_after:
        return AutoQcmDecision(None, skip_reason=SKIP_LISTING_NO_QUESTION)
    if len(listing.items) < QCM_AUTO_PROMOTE_MIN_ITEMS:
        return AutoQcmDecision(None, skip_reason=SKIP_LISTING_TOO_SHORT)

    candidate = auto_qcm_from_listing(listing, agent_id=agent_id)
    if candidate is None:
        # Cas rare : `auto_qcm_from_listing` re-vérifie kill-switch /
        # whitelist (on peut y arriver si l'env change entre les
        # appels). On reflète comme `disabled_by_env` par défaut.
        return AutoQcmDecision(None, skip_reason=SKIP_DISABLED)
    return AutoQcmDecision(candidate=candidate)
