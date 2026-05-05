"""Whitelist des `purpose` autorisés pour `consult_specialist` — Phase 2c.

Source de vérité unique pour les **consultations cross-agent** : un
sub-agent (ex. `compliance.transactional`) ne peut interroger un
autre agent (ex. `product`) qu'à travers un purpose **structuré et
whitelisté**, pas via une question libre.

──────────────────────────────────────────────────────────────────────
Pourquoi pas de question libre ?

Si on laissait le LLM caller formuler sa propre question vers le
specialist, il pourrait **leak** des signaux sensibles dans le
payload, par exemple :

  > "Le client a un signal AML actif, comment le rassurer sans
  >  alerter sur sa demande de retrait ?"

Cette question fuite vers l'agent specialist (et son audit DB) un
détail interne qui ne devrait jamais sortir du sub-agent compliance.

Avec un `purpose` enum + `params` whitelistés, le LLM caller ne peut
choisir qu'**un objet de consultation prévu** (ex. *« explique le
délai standard d'un dépôt SEPA »*) — aucun signal interne ne peut
voyager.

──────────────────────────────────────────────────────────────────────
Garanties d'API

  - `is_known_purpose(name)` ─ True ssi `name` ∈ whitelist Phase 2c.
  - `target_agent_for(name)` ─ retourne l'`agent_id` cible
    (`"product"`, …) ou ``None``.
  - `validate_params(name, params)` ─ retourne ``(ok, errors)`` où
    `errors` est une liste de codes (`unknown_param`, `bad_value`,…).
  - `build_question(name, params)` ─ produit la question naturelle
    en français qu'on injecte au prompt user du specialist. **Pas
    de templating libre LLM** : la question est composée
    déterministiquement côté code.

Cf. `docs/arquantix/PRODUCT_AGENT.md` § 4 (catalogue purpose).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Types et enums
# ─────────────────────────────────────────────────────────────────────


PurposeName = Literal[
    "explain_deposit_delay",
    "explain_withdrawal_delay",
    "explain_kyc_review_typical_delay",
    "explain_product_basics",
    "explain_swap_settlement_delay",
    # Cognitive Bot v4 — Lot 4 (2026-05-04) : purposes ciblant l'agent
    # `trust` pour fournir un encart factuel rassurant aux agents
    # caller (typiquement `advisor` ou `compliance.general` sur un
    # client en FEAR / inquiet sur la sécurité).
    "reassure_about_regulation",
    "reassure_about_custody",
    "reassure_about_security",
]


# Méthodes de paiement reconnues (FR/EU pour Phase 2c).
_DEPOSIT_METHODS: frozenset[str] = frozenset({
    "bank_transfer_in",  # virement SEPA entrant
    "card",              # carte bancaire
    "crypto_in",         # crypto entrant
})

_WITHDRAWAL_METHODS: frozenset[str] = frozenset({
    "bank_transfer_out",  # SEPA sortant
    "sepa_out",            # alias accepté
    "crypto_out",
})

_PRODUCT_SLUGS: frozenset[str] = frozenset({
    "product_basics_vault",
    "product_basics_livret_vancelian",
    "product_basics_scpi",
})


# ─────────────────────────────────────────────────────────────────────
# Spec d'un purpose
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PurposeSpec:
    """Spec immuable d'un purpose whitelist."""

    name: str
    target_agent: str
    description: str
    params_schema: dict[str, dict[str, Any]] = field(default_factory=dict)
    """JSON Schema simplifié pour chaque param attendu.

    Format : ``{param_name: {"required": bool, "enum": list[str] | None,
    "max_length": int | None}}``.
    """
    question_builder: Optional[Callable[[dict[str, str]], str]] = None
    """Fonction qui prend les params validés et retourne la question
    naturelle en français à injecter au specialist. Si ``None``, la
    description est utilisée telle quelle."""


# ─────────────────────────────────────────────────────────────────────
# Question builders (déterministes, côté code)
# ─────────────────────────────────────────────────────────────────────


_DEPOSIT_METHOD_LABELS = {
    "bank_transfer_in": "un virement SEPA entrant",
    "card": "une carte bancaire",
    "crypto_in": "un dépôt en crypto-actifs",
}


_WITHDRAWAL_METHOD_LABELS = {
    "bank_transfer_out": "un virement SEPA sortant",
    "sepa_out": "un virement SEPA sortant",
    "crypto_out": "un retrait en crypto-actifs",
}


def _q_deposit_delay(params: dict[str, str]) -> str:
    method = params.get("method", "")
    label = _DEPOSIT_METHOD_LABELS.get(method, "ce moyen de dépôt")
    day_hint = params.get("day_of_week_made")
    if day_hint:
        return (
            f"Quel est le délai standard d'un dépôt par {label}, "
            f"sachant que l'opération a été effectuée un {day_hint} ?"
        )
    return f"Quel est le délai standard d'un dépôt par {label} ?"


def _q_withdrawal_delay(params: dict[str, str]) -> str:
    method = params.get("method", "")
    label = _WITHDRAWAL_METHOD_LABELS.get(method, "ce moyen de retrait")
    return f"Quel est le délai standard d'un retrait par {label} ?"


def _q_kyc_review(_params: dict[str, str]) -> str:
    return (
        "Quel est le délai typique de validation d'un nouveau dossier "
        "KYC ou d'un justificatif complémentaire ?"
    )


def _q_product_basics(params: dict[str, str]) -> str:
    slug = params.get("slug", "")
    return f"Donne-moi les caractéristiques de base du produit {slug}."


def _q_swap_settlement(_params: dict[str, str]) -> str:
    return (
        "Quel est le délai de règlement d'un échange (swap) entre deux "
        "actifs sur Vancelian ?"
    )


# Question builders pour les purposes `trust` (Lot 4).


def _q_reassure_regulation(_params: dict[str, str]) -> str:
    return (
        "Donne-moi un encart factuel et rassurant sur le cadre "
        "réglementaire de Vancelian (régulation, licence, supervision). "
        "Reste factuel, ne pousse aucun produit, focalise-toi sur ce qui "
        "rassure un client inquiet de la solidité institutionnelle."
    )


def _q_reassure_custody(_params: dict[str, str]) -> str:
    return (
        "Donne-moi un encart factuel et rassurant sur la custody / le "
        "stockage des fonds clients chez Vancelian (cold storage, "
        "ségrégation, partenaires). Reste factuel, ne pousse aucun "
        "produit, focalise-toi sur ce qui rassure un client inquiet de "
        "la sécurité de ses fonds."
    )


def _q_reassure_security(_params: dict[str, str]) -> str:
    return (
        "Donne-moi un encart factuel et rassurant sur l'infrastructure "
        "et la sécurité opérationnelle de Vancelian (audits, partenaires, "
        "monitoring, gestion des risques). Reste factuel, ne pousse aucun "
        "produit, focalise-toi sur ce qui rassure un client inquiet "
        "d'un hack, d'une faillite ou d'une indisponibilité."
    )


# ─────────────────────────────────────────────────────────────────────
# Catalogue
# ─────────────────────────────────────────────────────────────────────


_CATALOG: dict[str, PurposeSpec] = {
    "explain_deposit_delay": PurposeSpec(
        name="explain_deposit_delay",
        target_agent="product",
        description=(
            "Demande à l'agent product le délai standard d'un dépôt "
            "selon la méthode (virement SEPA, carte, crypto)."
        ),
        params_schema={
            "method": {
                "required": True,
                "enum": sorted(_DEPOSIT_METHODS),
                "max_length": 32,
            },
            "day_of_week_made": {
                "required": False,
                "enum": [
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ],
                "max_length": 16,
            },
        },
        question_builder=_q_deposit_delay,
    ),
    "explain_withdrawal_delay": PurposeSpec(
        name="explain_withdrawal_delay",
        target_agent="product",
        description=(
            "Demande à l'agent product le délai standard d'un retrait "
            "selon la méthode (SEPA, crypto)."
        ),
        params_schema={
            "method": {
                "required": True,
                "enum": sorted(_WITHDRAWAL_METHODS),
                "max_length": 32,
            },
        },
        question_builder=_q_withdrawal_delay,
    ),
    "explain_kyc_review_typical_delay": PurposeSpec(
        name="explain_kyc_review_typical_delay",
        target_agent="product",
        description=(
            "Demande à l'agent product le délai typique de validation "
            "d'un nouveau KYC ou d'un justificatif. Aucun param requis."
        ),
        params_schema={},
        question_builder=_q_kyc_review,
    ),
    "explain_product_basics": PurposeSpec(
        name="explain_product_basics",
        target_agent="product",
        description=(
            "Demande à l'agent product les caractéristiques de base "
            "d'un produit Vancelian par `slug` whitelisté."
        ),
        params_schema={
            "slug": {
                "required": True,
                "enum": sorted(_PRODUCT_SLUGS),
                "max_length": 80,
            },
        },
        question_builder=_q_product_basics,
    ),
    "explain_swap_settlement_delay": PurposeSpec(
        name="explain_swap_settlement_delay",
        target_agent="product",
        description=(
            "Demande à l'agent product le délai de règlement d'un "
            "échange entre actifs. Aucun param requis."
        ),
        params_schema={},
        question_builder=_q_swap_settlement,
    ),
    # Cognitive Bot v4 — Lot 4 (2026-05-04) : purposes Trust & sécurité.
    # Cibles `trust`. Aucun param requis (la question naturelle est
    # déjà précise) — laisse l'agent trust composer sa réponse à partir
    # du wiki ``faq/trust-security/``.
    "reassure_about_regulation": PurposeSpec(
        name="reassure_about_regulation",
        target_agent="trust",
        description=(
            "Demande à l'agent trust un encart factuel rassurant sur le "
            "cadre réglementaire de Vancelian (régulation, licence). "
            "Aucun param. À utiliser quand le client exprime de la "
            "fear sur la solidité institutionnelle."
        ),
        params_schema={},
        question_builder=_q_reassure_regulation,
    ),
    "reassure_about_custody": PurposeSpec(
        name="reassure_about_custody",
        target_agent="trust",
        description=(
            "Demande à l'agent trust un encart factuel rassurant sur la "
            "custody / le stockage des fonds clients (cold storage, "
            "ségrégation, partenaires). Aucun param. À utiliser quand "
            "le client exprime de la fear sur la sécurité de ses fonds."
        ),
        params_schema={},
        question_builder=_q_reassure_custody,
    ),
    "reassure_about_security": PurposeSpec(
        name="reassure_about_security",
        target_agent="trust",
        description=(
            "Demande à l'agent trust un encart factuel rassurant sur "
            "l'infrastructure et la sécurité opérationnelle (audits, "
            "monitoring, gestion des risques de hack / faillite). "
            "Aucun param."
        ),
        params_schema={},
        question_builder=_q_reassure_security,
    ),
}


KNOWN_PURPOSES: frozenset[str] = frozenset(_CATALOG.keys())
"""Set des `purpose.name` reconnus par le runtime Phase 2c."""


# ─────────────────────────────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────────────────────────────


def is_known_purpose(name: str) -> bool:
    """True ssi `name` est dans la whitelist."""
    return bool(name) and name in _CATALOG


def get_spec(name: str) -> Optional[PurposeSpec]:
    """Retourne la `PurposeSpec` immuable (ou None si inconnu)."""
    return _CATALOG.get(name)


def target_agent_for(name: str) -> Optional[str]:
    """Renvoie l'`agent_id` cible pour ce purpose, ou None."""
    spec = _CATALOG.get(name)
    return spec.target_agent if spec else None


def list_known_purposes() -> list[dict[str, str]]:
    """Liste publique des purposes (pour LLM hints / docs)."""
    return [
        {
            "name": s.name,
            "target_agent": s.target_agent,
            "description": s.description,
            "required_params": [
                k for k, sch in s.params_schema.items() if sch.get("required")
            ],
        }
        for s in _CATALOG.values()
    ]


def validate_params(
    name: str, params: Optional[dict[str, Any]] = None
) -> tuple[bool, list[str], dict[str, str]]:
    """Valide les `params` contre la spec du purpose.

    Args:
        name: nom du purpose.
        params: dict des paramètres fournis par le LLM.

    Returns:
        Tuple ``(ok, errors, normalized_params)`` où :
          - ``ok`` : True ssi tous les params requis sont présents
            et valides.
          - ``errors`` : codes machine (`unknown_purpose`,
            `missing_required:<key>`, `bad_value:<key>`,
            `unknown_param:<key>`).
          - ``normalized_params`` : dict avec uniquement les params
            connus de la spec, valeurs trimmed/lowered selon enum.
    """
    spec = _CATALOG.get(name)
    if spec is None:
        return False, ["unknown_purpose"], {}

    safe_params: dict[str, Any] = dict(params or {})
    errors: list[str] = []
    normalized: dict[str, str] = {}

    for key, schema in spec.params_schema.items():
        if key not in safe_params:
            if schema.get("required"):
                errors.append(f"missing_required:{key}")
            continue
        raw = safe_params.pop(key)
        if raw is None:
            if schema.get("required"):
                errors.append(f"missing_required:{key}")
            continue
        if not isinstance(raw, str):
            errors.append(f"bad_value:{key}")
            continue
        value = raw.strip().lower()
        max_len = schema.get("max_length")
        if max_len and len(value) > max_len:
            errors.append(f"bad_value:{key}")
            continue
        enum = schema.get("enum")
        if enum and value not in enum:
            errors.append(f"bad_value:{key}")
            continue
        normalized[key] = value

    for extra_key in safe_params:
        errors.append(f"unknown_param:{extra_key}")

    return (len(errors) == 0, errors, normalized)


def build_question(
    name: str, params: dict[str, str]
) -> Optional[str]:
    """Compose la question naturelle française pour le specialist.

    Args:
        name: nom du purpose (déjà whitelisté).
        params: params **déjà validés** par `validate_params`.

    Returns:
        Question prête à être injectée comme user message au runtime
        du specialist, ou None si le purpose est inconnu.
    """
    spec = _CATALOG.get(name)
    if spec is None:
        return None
    if spec.question_builder is None:
        return spec.description
    try:
        return spec.question_builder(params)
    except Exception:  # noqa: BLE001
        logger.exception("consult_purposes.build_question failed name=%s", name)
        return spec.description


__all__ = [
    "KNOWN_PURPOSES",
    "PurposeName",
    "PurposeSpec",
    "build_question",
    "get_spec",
    "is_known_purpose",
    "list_known_purposes",
    "target_agent_for",
    "validate_params",
]
