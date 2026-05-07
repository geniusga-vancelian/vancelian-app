"""Univers de **tags d'intention** Vancelian (router v2 — Niveau 2).

Traduction concrète de la spec user 2026-05-04 :

  > « identification du sujet dans un univers élargi de Vancelian
  >   (tag à trouver: argent, épargne, avenir, performance, sécuriser,
  >   réussir, compte, banque, trading, etc.) »

──────────────────────────────────────────────────────────────────────
Rôle
──────────────────────────────────────────────────────────────────────

  1. **Classifier** la requête utilisateur dans 1 ou plusieurs tags
     parmi un univers fini → on peut **savoir si on est en Niveau 1
     (sujet clair routable), Niveau 2 (univers Vancelian flou) ou
     Niveau 3 (off-topic)**.
  2. **Brancher** le bon agent ou le bon QCM de clarifications dans
     les lots Lot 3 et Lot 4 (catalogue clarifications + advisor-first).
  3. **Rendre traçable** la décision du router : chaque tour est
     annoté avec ses tags détectés, visibles dans l'admin monitoring
     3-colonnes (cf. v3.0).

──────────────────────────────────────────────────────────────────────
Architecture
──────────────────────────────────────────────────────────────────────

Hiérarchie en **4 familles** validée par le user :

  1. ÉPARGNE          — constituer / sécuriser
  2. INVESTIR         — faire fructifier
  3. COMPTE_OPS       — utiliser le compte / opérations bancaires
  4. MARCHÉS_ANALYSES — comprendre / opinions

+ une catégorie **TRANSVERSE** pour les tags qui matchent plusieurs
familles (`reussir`, `avenir`, `decouvrir`, etc.).

+ une catégorie **HORS_SUJET** explicitée pour bien repérer
le Niveau 3 (météo, blagues, sport, etc.).

──────────────────────────────────────────────────────────────────────
Détection
──────────────────────────────────────────────────────────────────────

Stratégie **hybride** validée par le user :

  1. **Pass 1 — keyword-matching FR+EN** (ce module). Déterministe,
     rapide (<1 ms), debuggable. Couvre 80 % des cas.
  2. **Pass 2 — LLM router** (cf. ``router.py``). Le tool
     ``classify_intent_tags`` permet au LLM de surclasser ou compléter
     la pré-classification keyword. Hybride : on pass au LLM les tags
     déjà détectés en input, il peut les valider ou en ajouter.

──────────────────────────────────────────────────────────────────────
Intégration
──────────────────────────────────────────────────────────────────────

  * ``classify_message_tags(message)`` retourne les tags + family +
    scope_level → utilisé par ``router._build_router_messages`` pour
    injecter un bloc ``[INTENT TAGS]`` dans le prompt système.
  * Le tool ``classify_intent_tags`` (cf. lot 2b) permet au LLM de
    persister sa propre classification dans ``assistance_agent_decisions``
    pour audit.
  * ``router_clarification_catalog.py`` (lot 3) consomme le
    ``primary_tag`` pour choisir le QCM canonique.

Tests : ``tests/test_assistance_router_intent_tags_unit.py``.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Familles + tags canoniques
# ─────────────────────────────────────────────────────────────────────


# 4 familles principales + 1 transverse + 1 hors-sujet.
TAG_FAMILY_EPARGNE = "epargne"
TAG_FAMILY_INVESTIR = "investir"
TAG_FAMILY_COMPTE_OPS = "compte_ops"
TAG_FAMILY_MARCHES = "marches_analyses"
TAG_FAMILY_TRANSVERSE = "transverse"
TAG_FAMILY_HORS_SUJET = "hors_sujet"


@dataclass(frozen=True)
class TagDefinition:
    """Définition d'un tag d'intention.

    Attrs:
      tag         : identifiant kebab-case unique (ex. ``"epargner"``).
      family      : 1 des 6 familles ci-dessus.
      keywords_fr : mots-clés FR (lowercase, sans accents). Match si le
                    mot apparaît comme token entier dans le message.
      keywords_en : idem en anglais.
      preferred_agent : agent vers lequel ce tag pointe naturellement
                       (utilisé par ``router_clarification_catalog`` et
                       le pattern advisor-first).
    """

    tag: str
    family: str
    keywords_fr: tuple[str, ...] = ()
    keywords_en: tuple[str, ...] = ()
    preferred_agent: Optional[str] = None
    aliases: tuple[str, ...] = field(default_factory=tuple)


# ─────────────────────────────────────────────────────────────────────
# Catalogue complet des tags (router v2 — version 1, 2026-05-04)
# ─────────────────────────────────────────────────────────────────────
#
# **Convention** : les keywords sont stockés en minuscules sans
# accents (cf. ``_normalize`` ci-dessous). On match par tokens entiers
# pour éviter les faux positifs (« banane » ne doit pas matcher
# « banane »→ « banc »).

TAG_CATALOG: tuple[TagDefinition, ...] = (
    # ── ÉPARGNE ────────────────────────────────────────────────
    TagDefinition(
        tag="epargner",
        family=TAG_FAMILY_EPARGNE,
        keywords_fr=("epargne", "epargner", "economiser", "economies"),
        keywords_en=("savings", "save", "saving"),
        preferred_agent="advisor",
    ),
    TagDefinition(
        tag="securiser_capital",
        family=TAG_FAMILY_EPARGNE,
        keywords_fr=(
            "securiser", "securite", "proteger", "protection",
            "sans risque", "garanti",
        ),
        keywords_en=("secure", "safe", "protect", "guaranteed"),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="livret_coffre",
        family=TAG_FAMILY_EPARGNE,
        keywords_fr=(
            "livret", "coffre", "vault", "coffre-fort",
            "compte epargne", "rendement quotidien",
        ),
        keywords_en=("vault", "savings account"),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="rendement",
        family=TAG_FAMILY_EPARGNE,
        keywords_fr=(
            "rendement", "interets", "interet", "taux", "yield",
            "rentabilite", "rentable",
        ),
        keywords_en=("yield", "interest", "rate", "return"),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="avenir_securite",
        family=TAG_FAMILY_EPARGNE,
        keywords_fr=("avenir", "securite financiere", "tranquillite"),
        keywords_en=("future", "financial security"),
        preferred_agent="advisor",
    ),
    # ── INVESTIR ───────────────────────────────────────────────
    TagDefinition(
        tag="investir",
        family=TAG_FAMILY_INVESTIR,
        keywords_fr=(
            "investir", "investissement", "placement", "placer",
            "fructifier", "faire fructifier",
        ),
        keywords_en=("invest", "investment"),
        preferred_agent="advisor",
    ),
    TagDefinition(
        tag="performance",
        family=TAG_FAMILY_INVESTIR,
        keywords_fr=(
            "performance", "performances", "perf", "perfs",
            "gain", "gains", "croissance", "plus-value",
            "beneficier", "rentabilite",
        ),
        keywords_en=("performance", "gains", "growth", "profitable"),
        preferred_agent="market",
    ),
    TagDefinition(
        tag="retraite",
        family=TAG_FAMILY_INVESTIR,
        keywords_fr=(
            "retraite", "retraites", "pension", "vieux jours",
            "preparer ma retraite", "preparer la retraite",
        ),
        keywords_en=("retirement", "pension"),
        preferred_agent="advisor",
    ),
    TagDefinition(
        tag="bundle_crypto",
        family=TAG_FAMILY_INVESTIR,
        keywords_fr=(
            "bundle", "bundles", "panier", "paniers",
            "crypto basket", "basket", "top 2", "top 5",
        ),
        keywords_en=("bundle", "crypto basket", "basket"),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="exclusive_offer",
        family=TAG_FAMILY_INVESTIR,
        keywords_fr=(
            "offre exclusive", "offres exclusives",
            "cloud mining", "mining", "rwa",
            "dubai", "bali", "niseko", "villa", "munduk",
            "al barari",
        ),
        keywords_en=(
            "exclusive offer", "exclusive offers",
            "cloud mining", "rwa",
        ),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="instrument_cote",
        family=TAG_FAMILY_INVESTIR,
        keywords_fr=(
            "bitcoin", "btc", "ethereum", "ether", "eth",
            "solana", "sol", "usdc", "usdt", "xrp", "ada",
            "avax", "dot", "doge", "trx",
            "action", "actions", "etf", "indice", "indices",
        ),
        keywords_en=(
            "bitcoin", "btc", "ethereum", "ether", "eth",
            "solana", "stocks", "etf", "index",
        ),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="immobilier_long_terme",
        family=TAG_FAMILY_INVESTIR,
        keywords_fr=(
            "immobilier", "immo", "long terme", "transmission",
            "patrimoine", "heritage",
        ),
        keywords_en=("real estate", "long term", "inheritance"),
        preferred_agent="advisor",
    ),
    # ── COMPTE & OPS ───────────────────────────────────────────
    TagDefinition(
        tag="compte_kyc",
        family=TAG_FAMILY_COMPTE_OPS,
        keywords_fr=(
            "compte", "kyc", "identite", "validation",
            "justificatif", "verification",
        ),
        keywords_en=("account", "kyc", "verification", "identity"),
        preferred_agent="compliance",
    ),
    TagDefinition(
        tag="depot",
        family=TAG_FAMILY_COMPTE_OPS,
        keywords_fr=(
            "depot", "deposit", "versement", "crediter",
            "ajouter de l argent", "alimenter",
        ),
        keywords_en=("deposit", "top up", "fund"),
        preferred_agent="compliance",
    ),
    TagDefinition(
        tag="retrait",
        family=TAG_FAMILY_COMPTE_OPS,
        keywords_fr=(
            "retrait", "retirer", "sortir des fonds",
            "withdraw", "debiter", "recuperer",
        ),
        keywords_en=("withdraw", "withdrawal", "redeem"),
        preferred_agent="compliance",
    ),
    TagDefinition(
        tag="virement_sepa",
        family=TAG_FAMILY_COMPTE_OPS,
        keywords_fr=(
            "virement", "sepa", "iban", "rib",
        ),
        keywords_en=("transfer", "sepa", "iban", "wire"),
        preferred_agent="compliance",
    ),
    TagDefinition(
        tag="carte_visa",
        family=TAG_FAMILY_COMPTE_OPS,
        keywords_fr=("carte", "carte visa", "visa", "cb"),
        keywords_en=("card", "visa card", "debit card"),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="banque",
        family=TAG_FAMILY_COMPTE_OPS,
        keywords_fr=("banque", "bancaire", "compte bancaire"),
        keywords_en=("bank", "banking"),
        preferred_agent="compliance",
    ),
    # ── MARCHÉS & ANALYSES ─────────────────────────────────────
    TagDefinition(
        tag="actu_marche",
        family=TAG_FAMILY_MARCHES,
        keywords_fr=(
            "actualite", "actu", "news", "infos marche",
            "que se passe", "ce qui se passe",
        ),
        keywords_en=("news", "market update"),
        preferred_agent="market",
    ),
    TagDefinition(
        tag="opinion_marche",
        family=TAG_FAMILY_MARCHES,
        keywords_fr=(
            "que penses-tu", "quel est ton avis", "ton avis",
            "vaut-il le coup", "vaut le coup",
            "est-ce le bon moment", "bon moment",
        ),
        keywords_en=(
            "what do you think", "your opinion",
            "is it worth", "good time",
        ),
        preferred_agent="market",
    ),
    TagDefinition(
        tag="trading",
        family=TAG_FAMILY_MARCHES,
        keywords_fr=(
            "trading", "trader", "spot", "swap",
            "echanger", "echange",
        ),
        keywords_en=("trading", "spot", "swap", "exchange"),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="cours_evolution",
        family=TAG_FAMILY_MARCHES,
        keywords_fr=(
            "cours", "prix", "evolution", "graphique",
            "tendance", "tendances",
        ),
        keywords_en=("price", "chart", "trend", "trends"),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="macro_inflation",
        family=TAG_FAMILY_MARCHES,
        keywords_fr=(
            "inflation", "macro", "macroeconomie", "taux directeur",
            "fed", "bce", "powell", "lagarde",
        ),
        keywords_en=("inflation", "macro", "fed", "ecb"),
        preferred_agent="market",
    ),
    TagDefinition(
        tag="volatilite",
        family=TAG_FAMILY_MARCHES,
        keywords_fr=("volatilite", "krach", "crash", "correction"),
        keywords_en=("volatility", "crash", "correction"),
        preferred_agent="market",
    ),
    # ── TRANSVERSE (matchent plusieurs familles) ───────────────
    TagDefinition(
        tag="reussir",
        family=TAG_FAMILY_TRANSVERSE,
        keywords_fr=("reussir", "reussite", "succeed"),
        keywords_en=("succeed", "success"),
        preferred_agent="advisor",
    ),
    TagDefinition(
        tag="projet_vie",
        family=TAG_FAMILY_TRANSVERSE,
        keywords_fr=(
            "projet", "objectif", "preparer", "achat immo",
            "etudes des enfants", "mariage", "voyage",
        ),
        keywords_en=("project", "goal", "objective"),
        preferred_agent="advisor",
    ),
    TagDefinition(
        tag="decouvrir",
        family=TAG_FAMILY_TRANSVERSE,
        keywords_fr=(
            "decouvrir", "que propose", "que faites-vous",
            "vos produits", "votre offre",
            "c est quoi", "comment ca marche",
        ),
        keywords_en=("discover", "what do you offer"),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="centre_aide_faq",
        family=TAG_FAMILY_TRANSVERSE,
        keywords_fr=(
            "faq",
            "articles faq",
            "liste faq",
            "centre aide",
            "aide en ligne",
            "rubrique aide",
            "documentation app",
            "manuel app",
            "guides app",
            "help center",
        ),
        keywords_en=(
            "faq",
            "help center",
            "help articles",
            "faq articles",
            "knowledge base",
        ),
        preferred_agent="product",
    ),
    TagDefinition(
        tag="argent_general",
        family=TAG_FAMILY_TRANSVERSE,
        keywords_fr=(
            "argent", "pognon", "tunes", "money", "thunes",
            "patrimoine", "richesse",
        ),
        keywords_en=("money", "wealth"),
        preferred_agent=None,  # → ask_clarification systématique
    ),
    # ── HORS-SUJET (Niveau 3) ──────────────────────────────────
    TagDefinition(
        tag="off_topic_meteo",
        family=TAG_FAMILY_HORS_SUJET,
        keywords_fr=("meteo", "pluie", "soleil", "neige"),
        keywords_en=("weather", "rain", "snow"),
    ),
    TagDefinition(
        tag="off_topic_sport",
        family=TAG_FAMILY_HORS_SUJET,
        keywords_fr=(
            "sport", "foot", "football", "rugby", "tennis",
            "basket", "psg", "om",
        ),
        keywords_en=("sport", "football", "soccer"),
    ),
    TagDefinition(
        tag="off_topic_cuisine",
        family=TAG_FAMILY_HORS_SUJET,
        keywords_fr=(
            "recette", "cuisine", "tiramisu", "gateau",
            "pates", "soupe",
        ),
        keywords_en=("recipe", "cooking", "cake"),
    ),
    TagDefinition(
        tag="off_topic_blague",
        family=TAG_FAMILY_HORS_SUJET,
        keywords_fr=("blague", "blagues", "raconter", "rigoler"),
        keywords_en=("joke", "jokes"),
    ),
)


# Index inverse pour lookup rapide.
TAGS_BY_NAME: dict[str, TagDefinition] = {td.tag: td for td in TAG_CATALOG}


# ─────────────────────────────────────────────────────────────────────
# Détection (keyword-matching)
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IntentClassification:
    """Résultat du keyword-matching sur un message utilisateur.

    Attrs:
      tags         : list de tags détectés (peut être vide).
      primary_tag  : tag le plus saillant (premier matché en pratique).
      family       : famille du primary_tag, ou ``None`` si tags vide.
      scope_level  : 1 (Vancelian clair, agent évident),
                     2 (univers Vancelian flou),
                     3 (off-topic),
                     0 (rien détecté → on laisse le LLM décider).
      preferred_agent : agent vers lequel le primary_tag pointe.
      keyword_hits : list (tag, keyword) qui ont matché — pour debug.
    """

    tags: tuple[str, ...]
    primary_tag: Optional[str]
    family: Optional[str]
    scope_level: int
    preferred_agent: Optional[str]
    keyword_hits: tuple[tuple[str, str], ...] = ()


def _normalize(text: str) -> str:
    """Normalise un texte pour le matching : minuscules + sans
    accents + espaces collapsés. Préserve les digits et tirets."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", no_accents).strip()


def _matches_keyword(normalized_msg: str, keyword: str) -> bool:
    """Match strict : le keyword doit apparaître **comme phrase
    entière ou délimité par des non-alphanum**. Évite les faux
    positifs (« banane » ne doit pas matcher « banc »)."""
    norm_kw = _normalize(keyword)
    if not norm_kw:
        return False
    pattern = r"(?:^|\W)" + re.escape(norm_kw) + r"(?:$|\W)"
    return re.search(pattern, normalized_msg) is not None


def _scope_level_from_family(family: Optional[str]) -> int:
    """Map une famille à son scope_level :

      * ``hors_sujet``    → 3 (off-topic).
      * ``compte_ops``    → 1 (sujet clair, agent compliance évident).
      * ``investir`` avec ``instrument_cote`` ou ``bundle_crypto`` → 1.
      * autre famille     → 2 (univers Vancelian, mais flou).
      * ``None``          → 0 (rien détecté).
    """
    if family is None:
        return 0
    if family == TAG_FAMILY_HORS_SUJET:
        return 3
    if family == TAG_FAMILY_COMPTE_OPS:
        return 1
    return 2


def classify_message_tags(message: str) -> IntentClassification:
    """Classifie un message utilisateur via keyword-matching.

    Hot path — appelé à chaque tour pour annoter le prompt router.
    Ordre de matching :
      1. On normalise le message.
      2. Pour chaque tag du catalogue, on teste tous ses keywords FR+EN.
      3. Le **premier match** dans l'ordre du catalogue devient
         ``primary_tag``. Cela donne la priorité aux familles dans
         l'ordre déclaré : épargne → investir → compte_ops → marchés
         → transverse → hors_sujet (cohérent avec « le client a-t-il
         exprimé un besoin métier précis ? »).
      4. Tous les autres tags qui matchent sont collectés dans
         ``tags`` (pour annotation).

    Cas spéciaux :
      * Une fiche off_topic_* + un tag in-scope → on garde le tag
        in-scope comme primary (le client peut comparer crypto et
        météo dans la même phrase, on reste in-scope).
      * Aucun match → ``primary_tag = None``, ``scope_level = 0``,
        on laisse le LLM décider seul.
    """
    if not message or not message.strip():
        return IntentClassification(
            tags=(), primary_tag=None, family=None,
            scope_level=0, preferred_agent=None,
        )

    normalized = _normalize(message)
    matched: list[TagDefinition] = []
    keyword_hits: list[tuple[str, str]] = []

    for td in TAG_CATALOG:
        for kw in td.keywords_fr + td.keywords_en:
            if _matches_keyword(normalized, kw):
                matched.append(td)
                keyword_hits.append((td.tag, kw))
                break  # un keyword suffit pour ce tag

    if not matched:
        return IntentClassification(
            tags=(), primary_tag=None, family=None,
            scope_level=0, preferred_agent=None,
            keyword_hits=(),
        )

    # Priorité : tag in-scope > off_topic. On extrait les non-off-topic
    # en respectant l'ordre du catalogue.
    in_scope = [td for td in matched if td.family != TAG_FAMILY_HORS_SUJET]
    primary = in_scope[0] if in_scope else matched[0]

    return IntentClassification(
        tags=tuple(td.tag for td in matched),
        primary_tag=primary.tag,
        family=primary.family,
        scope_level=_scope_level_from_family(primary.family),
        preferred_agent=primary.preferred_agent,
        keyword_hits=tuple(keyword_hits),
    )


def render_classification_for_prompt(
    classification: IntentClassification,
) -> Optional[str]:
    """Rend la classification en bloc compact pour injection dans le
    prompt système du router. Retourne ``None`` si rien à dire."""
    if not classification.primary_tag:
        return None

    parts = [
        f"primary_tag = {classification.primary_tag}",
        f"family = {classification.family or '?'}",
        f"scope_level = {classification.scope_level}",
    ]
    if classification.preferred_agent:
        parts.append(f"preferred_agent = {classification.preferred_agent}")
    if len(classification.tags) > 1:
        other = [t for t in classification.tags if t != classification.primary_tag]
        if other:
            parts.append(f"other_tags = {', '.join(other[:5])}")

    return "[INTENT TAGS] " + " | ".join(parts)


__all__ = [
    "IntentClassification",
    "TAG_CATALOG",
    "TAG_FAMILY_COMPTE_OPS",
    "TAG_FAMILY_EPARGNE",
    "TAG_FAMILY_HORS_SUJET",
    "TAG_FAMILY_INVESTIR",
    "TAG_FAMILY_MARCHES",
    "TAG_FAMILY_TRANSVERSE",
    "TAGS_BY_NAME",
    "TagDefinition",
    "classify_message_tags",
    "render_classification_for_prompt",
]
