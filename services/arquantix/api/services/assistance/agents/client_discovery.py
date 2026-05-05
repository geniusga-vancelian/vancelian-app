"""Cognitive Bot v4 — Lot 7 — Client Discovery Engine (multi-projet).

Référence : ``docs/arquantix/CLIENT_DISCOVERY.md``.

──────────────────────────────────────────────────────────────────────
Pourquoi ce module existe
──────────────────────────────────────────────────────────────────────

Avant ce Lot, le bot mémorisait l'émotion (Lot 1) et le sujet catalogue
(`current_topic` Lot 1.4) mais **rien sur le projet** du client : son
**why** (acheter une maison, préparer la retraite…) ni les **paramètres
adossés** (horizon, montant initial, récurrent, liquidité, risque).

Ce module introduit un modèle multi-projet :

  * ``ClientProject`` — un projet client (label libre, status), avec :
  * ``ClientProjectParameters`` — horizon, target_amount, initial_amount,
    recurring_amount/frequency, liquidity_need, risk_appetite, …
  * ``FloatingParameter`` — un paramètre extrait dont l'attribution à
    un projet n'est pas certaine (orphelin de projet).

──────────────────────────────────────────────────────────────────────
Règles d'attribution (ANTI-bug « 4 ans = vacances »)
──────────────────────────────────────────────────────────────────────

Un paramètre est attribué à un projet **uniquement si** :

  1. **Co-mention** dans le même message user : « j'ai 4 ans pour la
     maison » → maison est nommé, attribution OK.
  2. **Réponse à une question ciblée** : tour bot précédent posait
     « horizon pour ton projet maison ? » et le user répond « 4 ans »
     → attribution OK (le projet est explicite dans la question).
  3. **Sinon** → le paramètre est stocké en ``FloatingParameter``
     status=``pending_attribution`` et le bot demandera clarification
     au tour suivant.

Aucune propagation par proximité temporelle. Aucune attribution au
« projet le plus récent ». Le LLM extracteur DOIT explicitement nommer
le projet de rattachement, sinon → floating.

──────────────────────────────────────────────────────────────────────
Stratégie d'extraction — keyword + LLM gated
──────────────────────────────────────────────────────────────────────

A) **Keyword pass** (latence < 1 ms, couvre ~60 %) :

  * Détection de label de projet : `acheter (un|une|le|la) maison`,
    `appartement`, `voiture`, `vacances`, `voyage`, `retraite`,
    `études?`, `mariage`, `bébé`, `entreprise`, `héritage`.
  * Détection de paramètres typés :
    * Horizon : ``(en|dans|pour|sur)? N (mois|ans|années)``
    * Montant : ``N (euros|€|EUR|k€|K€)``
    * Récurrent : ``par mois``, ``chaque mois``, ``tous les mois``,
      ``mensuel`` ; ``chaque semaine|trimestre|année``.
    * Liquidité : ``besoin de liquidité``, ``accès rapide``,
      ``retirer``.
    * Risque : ``prudent``, ``risqué``, ``sécurisé``, ``défensif``,
      ``dynamique``, ``équilibré``, ``peur de perdre``.

B) **LLM pass** (gated, ~150 tokens) :

  Déclenché **uniquement si** :
    * keyword pass a trouvé un signal flou (label sans paramètre, ou
      paramètre sans label), OU
    * conversation_stage ∈ {discovery, clarification} (le bot vient de
      poser une question d'exploration), OU
    * un FloatingParameter pending_attribution existe et le tour user
      pourrait l'attribuer.

  ``gpt-4o-mini`` `temperature=0`, schéma JSON strict (function
  calling). Couvre ~85 % cumulés avec le keyword pass.

──────────────────────────────────────────────────────────────────────
Tests : ``tests/test_assistance_client_discovery_unit.py``.
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
# Constantes — labels canoniques de projets
# ─────────────────────────────────────────────────────────────────────


PROJECT_LABEL_HOUSE = "achat_maison"
PROJECT_LABEL_APARTMENT = "achat_appartement"
PROJECT_LABEL_CAR = "achat_voiture"
PROJECT_LABEL_TRAVEL = "voyage_vacances"
PROJECT_LABEL_RETIREMENT = "retraite"
PROJECT_LABEL_EDUCATION = "etudes"
PROJECT_LABEL_WEDDING = "mariage"
PROJECT_LABEL_FAMILY = "famille_bebe"
PROJECT_LABEL_BUSINESS = "creation_entreprise"
PROJECT_LABEL_INHERITANCE = "transmission_heritage"
PROJECT_LABEL_OTHER = "autre"


KNOWN_PROJECT_LABELS: frozenset[str] = frozenset({
    PROJECT_LABEL_HOUSE,
    PROJECT_LABEL_APARTMENT,
    PROJECT_LABEL_CAR,
    PROJECT_LABEL_TRAVEL,
    PROJECT_LABEL_RETIREMENT,
    PROJECT_LABEL_EDUCATION,
    PROJECT_LABEL_WEDDING,
    PROJECT_LABEL_FAMILY,
    PROJECT_LABEL_BUSINESS,
    PROJECT_LABEL_INHERITANCE,
    PROJECT_LABEL_OTHER,
})


PROJECT_STATUS_ACTIVE = "active"
PROJECT_STATUS_PAUSED = "paused"
PROJECT_STATUS_COMPLETED = "completed"
PROJECT_STATUS_ABANDONED = "abandoned"


KNOWN_PROJECT_STATUSES: frozenset[str] = frozenset({
    PROJECT_STATUS_ACTIVE,
    PROJECT_STATUS_PAUSED,
    PROJECT_STATUS_COMPLETED,
    PROJECT_STATUS_ABANDONED,
})


PARAMETER_KIND_HORIZON_YEARS = "horizon_years"
PARAMETER_KIND_TARGET_AMOUNT = "target_amount"
PARAMETER_KIND_INITIAL_AMOUNT = "initial_amount"
PARAMETER_KIND_RECURRING_AMOUNT = "recurring_amount"
PARAMETER_KIND_RECURRING_FREQUENCY = "recurring_frequency"
PARAMETER_KIND_LIQUIDITY_NEED = "liquidity_need"
PARAMETER_KIND_RISK_APPETITE = "risk_appetite"
PARAMETER_KIND_KNOWN_CONSTRAINT = "known_constraint"


KNOWN_PARAMETER_KINDS: frozenset[str] = frozenset({
    PARAMETER_KIND_HORIZON_YEARS,
    PARAMETER_KIND_TARGET_AMOUNT,
    PARAMETER_KIND_INITIAL_AMOUNT,
    PARAMETER_KIND_RECURRING_AMOUNT,
    PARAMETER_KIND_RECURRING_FREQUENCY,
    PARAMETER_KIND_LIQUIDITY_NEED,
    PARAMETER_KIND_RISK_APPETITE,
    PARAMETER_KIND_KNOWN_CONSTRAINT,
})


FLOATING_STATUS_PENDING = "pending_attribution"
FLOATING_STATUS_ATTRIBUTED = "attributed"
FLOATING_STATUS_DISCARDED = "discarded"


# Cap soft : on stocke jusqu'à N projets actifs / personne. Au-delà,
# l'extracteur fait passer le plus ancien `paused` (cf. repo).
MAX_ACTIVE_PROJECTS_PER_PERSON: int = 5


# ─────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────


@dataclass
class ClientProjectParameters:
    """Paramètres adossés à un projet client.

    Tous nullable — l'extraction se fait progressivement au fil des
    tours. JSON-serializable via ``to_dict`` / ``from_dict``.
    """

    horizon_years: Optional[float] = None
    target_amount: Optional[float] = None
    target_currency: Optional[str] = None
    initial_amount: Optional[float] = None
    initial_currency: Optional[str] = None
    recurring_amount: Optional[float] = None
    recurring_currency: Optional[str] = None
    recurring_frequency: Optional[str] = None
    liquidity_need: Optional[str] = None
    risk_appetite: Optional[str] = None
    known_constraints: list[str] = field(default_factory=list)
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "horizon_years": self.horizon_years,
            "target_amount": self.target_amount,
            "target_currency": self.target_currency,
            "initial_amount": self.initial_amount,
            "initial_currency": self.initial_currency,
            "recurring_amount": self.recurring_amount,
            "recurring_currency": self.recurring_currency,
            "recurring_frequency": self.recurring_frequency,
            "liquidity_need": self.liquidity_need,
            "risk_appetite": self.risk_appetite,
            "known_constraints": list(self.known_constraints),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, raw: Optional[dict[str, Any]]) -> "ClientProjectParameters":
        if not isinstance(raw, dict):
            return cls()
        return cls(
            horizon_years=_safe_float(raw.get("horizon_years")),
            target_amount=_safe_float(raw.get("target_amount")),
            target_currency=_safe_str(raw.get("target_currency")),
            initial_amount=_safe_float(raw.get("initial_amount")),
            initial_currency=_safe_str(raw.get("initial_currency")),
            recurring_amount=_safe_float(raw.get("recurring_amount")),
            recurring_currency=_safe_str(raw.get("recurring_currency")),
            recurring_frequency=_safe_str(raw.get("recurring_frequency")),
            liquidity_need=_safe_str(raw.get("liquidity_need")),
            risk_appetite=_safe_str(raw.get("risk_appetite")),
            known_constraints=[
                str(k)
                for k in (raw.get("known_constraints") or [])
                if isinstance(k, (str, int, float))
            ],
            notes=_safe_str(raw.get("notes")),
        )

    def merge(
        self, other: "ClientProjectParameters"
    ) -> "ClientProjectParameters":
        """Retourne une copie où ``other`` écrase les champs renseignés.

        Les champs ``None`` de ``other`` ne touchent pas les valeurs
        existantes (merge non destructif) ; les listes
        (``known_constraints``) sont **étendues** sans doublon.
        """
        merged = ClientProjectParameters(**self.to_dict())
        d = other.to_dict()
        for k, v in d.items():
            if v is None:
                continue
            if k == "known_constraints" and isinstance(v, list):
                seen = set(merged.known_constraints)
                for item in v:
                    if item not in seen:
                        merged.known_constraints.append(item)
                        seen.add(item)
                continue
            setattr(merged, k, v)
        return merged

    def is_empty(self) -> bool:
        d = self.to_dict()
        for k, v in d.items():
            if k == "known_constraints":
                if v:
                    return False
                continue
            if v is not None:
                return False
        return True


@dataclass
class ClientProject:
    """Un projet client (en mémoire, avant ou après persistance)."""

    label: str
    status: str = PROJECT_STATUS_ACTIVE
    confidence: float = 0.7
    parameters: ClientProjectParameters = field(
        default_factory=ClientProjectParameters
    )
    id: Optional[str] = None  # set par le repo après persistance
    created_at_turn: Optional[int] = None
    last_touched_at_turn: Optional[int] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "confidence": self.confidence,
            "parameters": self.parameters.to_dict(),
            "created_at_turn": self.created_at_turn,
            "last_touched_at_turn": self.last_touched_at_turn,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ClientProject":
        return cls(
            id=_safe_str(raw.get("id")),
            label=_safe_str(raw.get("label")) or PROJECT_LABEL_OTHER,
            status=_safe_str(raw.get("status")) or PROJECT_STATUS_ACTIVE,
            confidence=_safe_float(raw.get("confidence")) or 0.7,
            parameters=ClientProjectParameters.from_dict(
                raw.get("parameters")
            ),
            created_at_turn=_safe_int(raw.get("created_at_turn")),
            last_touched_at_turn=_safe_int(raw.get("last_touched_at_turn")),
            notes=_safe_str(raw.get("notes")),
        )


@dataclass
class FloatingParameter:
    """Paramètre extrait sans projet de rattachement explicite."""

    parameter_kind: str
    parameter_value: dict[str, Any]
    confidence: float = 0.7
    id: Optional[str] = None
    created_at_turn: Optional[int] = None
    status: str = FLOATING_STATUS_PENDING

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "parameter_kind": self.parameter_kind,
            "parameter_value": dict(self.parameter_value),
            "confidence": self.confidence,
            "created_at_turn": self.created_at_turn,
            "status": self.status,
        }


@dataclass
class DiscoveryExtraction:
    """Sortie de ``extract_discovery_from_user_message``.

    Contient la (les) extraction(s) attribuables à un projet existant
    ou nouveau, et la liste des paramètres ``floating`` qui n'ont pas
    pu être rattachés.
    """

    new_or_updated_projects: list[ClientProject] = field(default_factory=list)
    floating_parameters: list[FloatingParameter] = field(default_factory=list)
    raw_signals: dict[str, Any] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return (
            not self.new_or_updated_projects
            and not self.floating_parameters
        )


# ─────────────────────────────────────────────────────────────────────
# Helpers internes
# ─────────────────────────────────────────────────────────────────────


def _safe_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize(text: str) -> str:
    """Strip + lowercase + accents removed pour keyword matching."""
    if not text:
        return ""
    s = text.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s


# ─────────────────────────────────────────────────────────────────────
# Catalogue keyword → label projet (FR + EN)
# ─────────────────────────────────────────────────────────────────────


_PROJECT_KEYWORDS: dict[str, tuple[str, ...]] = {
    PROJECT_LABEL_HOUSE: (
        "maison",
        "house",
        "achat immo",
        "immobilier",
        "real estate",
    ),
    PROJECT_LABEL_APARTMENT: (
        "appartement",
        "apartment",
        "studio",
        "loft",
    ),
    PROJECT_LABEL_CAR: (
        "voiture",
        "car",
        "automobile",
        "vehicule",
        "vehicle",
    ),
    PROJECT_LABEL_TRAVEL: (
        "vacances",
        "vacation",
        "voyage",
        "travel",
        "tour du monde",
        "world tour",
    ),
    PROJECT_LABEL_RETIREMENT: (
        "retraite",
        "retirement",
        "pension",
    ),
    PROJECT_LABEL_EDUCATION: (
        "etudes",
        "studies",
        "ecole",
        "school",
        "universite",
        "university",
    ),
    PROJECT_LABEL_WEDDING: (
        "mariage",
        "wedding",
    ),
    PROJECT_LABEL_FAMILY: (
        "bebe",
        "baby",
        "enfant",
        "child",
        "famille",
        "family",
    ),
    PROJECT_LABEL_BUSINESS: (
        "entreprise",
        "business",
        "boite",
        "startup",
        "company",
    ),
    PROJECT_LABEL_INHERITANCE: (
        "heritage",
        "inheritance",
        "transmission",
        "succession",
    ),
}


# ─────────────────────────────────────────────────────────────────────
# Regex paramètres
# ─────────────────────────────────────────────────────────────────────


# Horizon — capture nombre + unité (mois/ans)
_RE_HORIZON = re.compile(
    r"\b(?:dans|en|sur|pour|d['’]ici|within|in)\s+"
    r"(\d{1,2})\s*(mois|month|months|an|ans|annees?|years?)\b",
    re.IGNORECASE,
)

# Variante sans préfixe : « 4 ans », « 6 mois » seuls (utilisable seulement
# si on est en mode question-réponse — sinon trop de faux positifs).
_RE_HORIZON_BARE = re.compile(
    r"^\s*(\d{1,2})\s*(mois|month|months|an|ans|annees?|years?)\s*\.?\s*$",
    re.IGNORECASE,
)

# Montant : capture nombre + suffixe k/K/€/euros/EUR
_RE_AMOUNT = re.compile(
    r"\b(\d{1,3}(?:[\s.,]?\d{3})*(?:[.,]\d+)?)\s*"
    r"(k|K|m|M)?\s*"
    r"(€|eur|euros?|usd|dollars?)\b",
    re.IGNORECASE,
)

# Recurring frequency keywords (FR+EN).
_RECURRING_FREQUENCY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("par semaine", "weekly"),
    ("chaque semaine", "weekly"),
    ("toutes les semaines", "weekly"),
    ("hebdo", "weekly"),
    ("weekly", "weekly"),
    ("par mois", "monthly"),
    ("chaque mois", "monthly"),
    ("tous les mois", "monthly"),
    ("mensuel", "monthly"),
    ("monthly", "monthly"),
    ("par trimestre", "quarterly"),
    ("trimestriel", "quarterly"),
    ("quarterly", "quarterly"),
    ("par an", "yearly"),
    ("annuel", "yearly"),
    ("chaque annee", "yearly"),
    ("yearly", "yearly"),
)

# Liquidity / risk keywords
_LIQUIDITY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("besoin de liquidite", "high"),
    ("besoin de sortir", "high"),
    ("acces rapide", "high"),
    ("doit pouvoir retirer", "high"),
    ("retirer a tout moment", "high"),
    ("withdrawable", "high"),
    ("liquide", "mid"),
    ("bloque", "low"),
    ("bloquer", "low"),
    ("long terme", "low"),
)

_RISK_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("tres prudent", "very_low"),
    ("ultra prudent", "very_low"),
    ("aucun risque", "very_low"),
    ("prudent", "low"),
    ("securise", "low"),
    ("conservateur", "low"),
    ("equilibre", "mid"),
    ("balanced", "mid"),
    ("dynamique", "high"),
    ("offensif", "high"),
    ("agressif", "very_high"),
    ("max risque", "very_high"),
)


# ─────────────────────────────────────────────────────────────────────
# Détection projet (keyword)
# ─────────────────────────────────────────────────────────────────────


def detect_project_label_from_message(message: str) -> Optional[str]:
    """Identifie le label canonique de projet présent dans le message,
    ou None si rien ne matche. Première occurrence priorisée.
    """
    norm = _normalize(message)
    if not norm:
        return None
    for label, keywords in _PROJECT_KEYWORDS.items():
        for kw in keywords:
            if kw in norm:
                return label
    return None


def detect_project_label_in_text(text: str) -> Optional[str]:
    """Variante exposée pour tests/réutilisation."""
    return detect_project_label_from_message(text)


# ─────────────────────────────────────────────────────────────────────
# Extraction paramètres (keyword)
# ─────────────────────────────────────────────────────────────────────


def _extract_horizon_years(message: str, *, allow_bare: bool) -> Optional[float]:
    """Capture 'dans 4 ans', 'sur 6 mois', etc. (canonical = years).

    Si ``allow_bare`` est True, accepte aussi les messages courts type
    « 4 ans » seuls — à n'utiliser que si l'on sait que le bot vient
    de poser une question d'horizon (cf. ``response_to_question``).
    """
    m = _RE_HORIZON.search(message)
    if m is None and allow_bare:
        m = _RE_HORIZON_BARE.match(message.strip())
    if m is None:
        return None
    try:
        n = float(m.group(1))
    except (TypeError, ValueError):
        return None
    unit = m.group(2).lower()
    if unit.startswith("mois") or unit.startswith("month"):
        return round(n / 12.0, 2)
    return n


def _extract_amount(message: str) -> list[tuple[float, str]]:
    """Capture toutes les sommes citées avec leur devise (best-effort).

    Retourne une liste ``[(value_float, currency_code)]``. Une devise
    par défaut « EUR » est posée si elle n'est pas détectable.
    """
    out: list[tuple[float, str]] = []
    for m in _RE_AMOUNT.finditer(message):
        raw_num = m.group(1).replace(" ", "").replace(",", ".")
        # un seul "." dans la fraction décimale, on retire les autres
        if raw_num.count(".") > 1:
            parts = raw_num.split(".")
            raw_num = "".join(parts[:-1]) + "." + parts[-1]
        try:
            val = float(raw_num)
        except (TypeError, ValueError):
            continue
        suffix = (m.group(2) or "").lower()
        if suffix == "k":
            val *= 1_000
        elif suffix == "m":
            val *= 1_000_000
        currency_raw = (m.group(3) or "").lower()
        if currency_raw in ("eur", "euro", "euros", "€"):
            currency = "EUR"
        elif currency_raw in ("usd", "dollar", "dollars"):
            currency = "USD"
        else:
            currency = "EUR"
        out.append((val, currency))
    return out


def _extract_recurring_frequency(norm_message: str) -> Optional[str]:
    for kw, label in _RECURRING_FREQUENCY_KEYWORDS:
        if kw in norm_message:
            return label
    return None


def _extract_liquidity(norm_message: str) -> Optional[str]:
    for kw, label in _LIQUIDITY_KEYWORDS:
        if kw in norm_message:
            return label
    return None


def _extract_risk(norm_message: str) -> Optional[str]:
    for kw, label in _RISK_KEYWORDS:
        if kw in norm_message:
            return label
    return None


# ─────────────────────────────────────────────────────────────────────
# Détection « question ciblée par le bot »
# ─────────────────────────────────────────────────────────────────────


# Patterns assistant qui demandent un paramètre nominativement attaché à
# un projet : « pour ton projet maison », « concernant ton projet
# vacances », « pour ton achat appart… ». La présence d'un de ces
# patterns dans le **dernier** tour assistant nous permet de
# **désambiguïser** un message user laconique sans risque.
_RE_BOT_QUESTION_TARGETED = re.compile(
    r"(?:pour|concernant|sur|de)\s+"
    r"(?:ton|ta|tes|votre|vos|ce|cet|cette|ces|le|la|les|l['’])"
    r"\s+"
    r"(?:projet\s+)?(maison|appartement|voiture|vacances|voyage|"
    r"retraite|etudes|mariage|bebe|enfant|entreprise|heritage)",
    re.IGNORECASE,
)


def detect_targeted_project_in_assistant_question(
    assistant_text: str,
) -> Optional[str]:
    """Si le tour assistant précédent posait une question explicitement
    rattachée à un projet (ex. « horizon pour ton projet maison ? »),
    retourne le label canonique du projet. Sinon ``None``.
    """
    if not assistant_text:
        return None
    norm = _normalize(assistant_text)
    m = _RE_BOT_QUESTION_TARGETED.search(norm)
    if not m:
        return None
    matched = m.group(1)
    # remap aux labels canoniques
    if matched in ("maison",):
        return PROJECT_LABEL_HOUSE
    if matched in ("appartement",):
        return PROJECT_LABEL_APARTMENT
    if matched in ("voiture",):
        return PROJECT_LABEL_CAR
    if matched in ("vacances", "voyage"):
        return PROJECT_LABEL_TRAVEL
    if matched in ("retraite",):
        return PROJECT_LABEL_RETIREMENT
    if matched in ("etudes",):
        return PROJECT_LABEL_EDUCATION
    if matched in ("mariage",):
        return PROJECT_LABEL_WEDDING
    if matched in ("bebe", "enfant"):
        return PROJECT_LABEL_FAMILY
    if matched in ("entreprise",):
        return PROJECT_LABEL_BUSINESS
    if matched in ("heritage",):
        return PROJECT_LABEL_INHERITANCE
    return None


# ─────────────────────────────────────────────────────────────────────
# Switch detection (« ok parlons d'autre chose »)
# ─────────────────────────────────────────────────────────────────────


_SWITCH_KEYWORDS: tuple[str, ...] = (
    "autre projet",
    "autre chose",
    "oublions",
    "laisse tomber",
    "parlons plutot de",
    "et pour",
    "switch to",
    "different topic",
    "another topic",
    "change of topic",
)


def detect_project_switch_signal(message: str) -> bool:
    """True si le user explicite un switch de projet."""
    norm = _normalize(message)
    return any(kw in norm for kw in _SWITCH_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────
# Extraction principale (keyword pass)
# ─────────────────────────────────────────────────────────────────────


def extract_discovery_keyword_pass(
    *,
    user_message: str,
    last_assistant_text: Optional[str] = None,
    active_projects: Optional[list[ClientProject]] = None,
    current_turn: Optional[int] = None,
) -> DiscoveryExtraction:
    """Extraction déterministe par keywords/regex (pas de LLM).

    Args:
        user_message : message du user à analyser.
        last_assistant_text : dernier tour assistant pour détection
            de question ciblée (cf. règle d'attribution #2).
        active_projects : projets actifs déjà connus (pour merge si
            même label détecté).
        current_turn : ``turn_index`` pour traçabilité.

    Returns:
        ``DiscoveryExtraction`` avec ``new_or_updated_projects`` et
        ``floating_parameters``.

    Stratégie d'attribution :

      * Co-mention dans ``user_message`` → projet détecté + paramètres
        attribués au même projet (règle #1).
      * Sinon, si ``last_assistant_text`` ciblait un projet précis →
        paramètres attribués à ce projet (règle #2).
      * Sinon → paramètres en floating.

    Cette fonction **ne touche pas la DB** — elle retourne juste des
    structures à persister par le repo.
    """
    extraction = DiscoveryExtraction()
    if not user_message or not user_message.strip():
        return extraction

    norm = _normalize(user_message)
    extraction.raw_signals["normalized"] = norm

    # ─── Étape 1 : détecter le projet co-mentionné dans le message ──
    co_mentioned_label = detect_project_label_from_message(user_message)
    targeted_label = detect_targeted_project_in_assistant_question(
        last_assistant_text or ""
    )

    # Choix du projet d'attribution :
    #   1. Co-mention prime (le user nomme explicitement → certitude).
    #   2. Sinon, question ciblée du bot → projet du bot.
    #   3. Sinon → None (les paramètres iront en floating).
    target_label: Optional[str] = co_mentioned_label or targeted_label

    # ─── Étape 2 : extraire les paramètres ──────────────────────────
    # Horizon : on autorise la forme « 4 ans » seule SEULEMENT si on a
    # une question ciblée (sinon trop de faux positifs).
    horizon = _extract_horizon_years(
        user_message, allow_bare=bool(targeted_label)
    )
    amounts = _extract_amount(user_message)
    recurring_freq = _extract_recurring_frequency(norm)
    liquidity = _extract_liquidity(norm)
    risk = _extract_risk(norm)

    # ─── Étape 3 : construction du résultat ─────────────────────────
    params = ClientProjectParameters()

    if horizon is not None:
        params.horizon_years = horizon
    if recurring_freq is not None:
        params.recurring_frequency = recurring_freq
    if liquidity is not None:
        params.liquidity_need = liquidity
    if risk is not None:
        params.risk_appetite = risk
    # Pour les amounts : on choisit le **plus gros** comme target_amount
    # (si plusieurs montants cités) et on stocke les autres en
    # known_constraints (raw text) pour l'instant. V2 affinera.
    if amounts:
        amounts_sorted = sorted(amounts, key=lambda a: a[0], reverse=True)
        params.target_amount = amounts_sorted[0][0]
        params.target_currency = amounts_sorted[0][1]
        if len(amounts_sorted) >= 2:
            params.initial_amount = amounts_sorted[1][0]
            params.initial_currency = amounts_sorted[1][1]

    if target_label and not params.is_empty():
        # Cas nominal : projet identifié + paramètres attribués au
        # projet (règle #1 ou #2).
        proj = ClientProject(
            label=target_label,
            status=PROJECT_STATUS_ACTIVE,
            confidence=0.85 if co_mentioned_label else 0.75,
            parameters=params,
            created_at_turn=current_turn,
            last_touched_at_turn=current_turn,
        )
        extraction.new_or_updated_projects.append(proj)
    elif target_label and params.is_empty():
        # Le projet est nommé mais aucun paramètre n'est extrait —
        # on crée/maj quand même le projet (le client a manifesté
        # son intention).
        proj = ClientProject(
            label=target_label,
            status=PROJECT_STATUS_ACTIVE,
            confidence=0.7,
            parameters=ClientProjectParameters(),
            created_at_turn=current_turn,
            last_touched_at_turn=current_turn,
        )
        extraction.new_or_updated_projects.append(proj)
    else:
        # Pas de projet identifié → tout va en floating (règle #3).
        if horizon is not None:
            extraction.floating_parameters.append(
                FloatingParameter(
                    parameter_kind=PARAMETER_KIND_HORIZON_YEARS,
                    parameter_value={"value": horizon},
                    confidence=0.7,
                    created_at_turn=current_turn,
                )
            )
        if amounts:
            big = amounts[0]
            extraction.floating_parameters.append(
                FloatingParameter(
                    parameter_kind=PARAMETER_KIND_TARGET_AMOUNT,
                    parameter_value={"value": big[0], "currency": big[1]},
                    confidence=0.65,
                    created_at_turn=current_turn,
                )
            )
        if recurring_freq is not None:
            extraction.floating_parameters.append(
                FloatingParameter(
                    parameter_kind=PARAMETER_KIND_RECURRING_FREQUENCY,
                    parameter_value={"value": recurring_freq},
                    confidence=0.7,
                    created_at_turn=current_turn,
                )
            )
        if liquidity is not None:
            extraction.floating_parameters.append(
                FloatingParameter(
                    parameter_kind=PARAMETER_KIND_LIQUIDITY_NEED,
                    parameter_value={"value": liquidity},
                    confidence=0.7,
                    created_at_turn=current_turn,
                )
            )
        if risk is not None:
            extraction.floating_parameters.append(
                FloatingParameter(
                    parameter_kind=PARAMETER_KIND_RISK_APPETITE,
                    parameter_value={"value": risk},
                    confidence=0.7,
                    created_at_turn=current_turn,
                )
            )

    return extraction


# ─────────────────────────────────────────────────────────────────────
# LLM gating decision
# ─────────────────────────────────────────────────────────────────────


def should_invoke_llm_extractor(
    *,
    keyword_extraction: DiscoveryExtraction,
    conversation_stage: Optional[str],
    has_pending_floating_params: bool,
) -> bool:
    """Décide s'il faut compléter le keyword pass par un LLM call.

    Critères (au moins un suffit) :

    * Le keyword pass a trouvé un signal flou (un projet sans param,
      ou un param sans projet → ``floating_parameters`` non vide).
    * Le conversation_stage est ``discovery`` ou ``clarification`` —
      le bot vient de poser une question d'exploration, on veut
      maximiser l'extraction.
    * Il existe déjà des floating params en attente d'attribution.
    """
    if conversation_stage in ("discovery", "clarification"):
        return True
    if has_pending_floating_params:
        return True
    if keyword_extraction.floating_parameters:
        return True
    # Cas où on a un projet mais sans params ET pas en discovery →
    # le LLM peut aider à extraire le « pourquoi » qualitatif.
    for proj in keyword_extraction.new_or_updated_projects:
        if proj.parameters.is_empty():
            return True
    return False


# ─────────────────────────────────────────────────────────────────────
# Rendu en bloc system prompt
# ─────────────────────────────────────────────────────────────────────


def render_discovery_for_prompt(
    *,
    active_projects: list[ClientProject],
    floating_parameters: Optional[list[FloatingParameter]] = None,
) -> str:
    """Format compact pour injection en system prompt router/agents.

    Exemple de sortie :

        [CLIENT DISCOVERY]
        active_projects:
          - achat_maison · horizon=4y · target=300000 EUR · risk=low
          - retraite     · horizon=15y · recurring=monthly
        pending_parameters:
          - horizon_years=4 (non attribué — clarifier)

    Vide si rien à dire.
    """
    if not active_projects and not (floating_parameters or []):
        return ""
    lines: list[str] = ["[CLIENT DISCOVERY]"]
    if active_projects:
        lines.append("active_projects:")
        for proj in active_projects:
            bits = [proj.label]
            p = proj.parameters
            if p.horizon_years is not None:
                bits.append(f"horizon={p.horizon_years:g}y")
            if p.target_amount is not None:
                cur = p.target_currency or "EUR"
                bits.append(f"target={p.target_amount:g} {cur}")
            if p.initial_amount is not None:
                cur = p.initial_currency or "EUR"
                bits.append(f"initial={p.initial_amount:g} {cur}")
            if p.recurring_amount is not None or p.recurring_frequency:
                ramt = (
                    f"{p.recurring_amount:g} "
                    if p.recurring_amount is not None
                    else ""
                )
                rfreq = p.recurring_frequency or ""
                bits.append(f"recurring={ramt}{rfreq}".strip())
            if p.liquidity_need:
                bits.append(f"liquidity={p.liquidity_need}")
            if p.risk_appetite:
                bits.append(f"risk={p.risk_appetite}")
            lines.append("  - " + " · ".join(bits))
    if floating_parameters:
        lines.append("pending_parameters:")
        for fp in floating_parameters:
            v = fp.parameter_value or {}
            lines.append(
                f"  - {fp.parameter_kind}={v} (non attribué — clarifier)"
            )
    return "\n".join(lines)
