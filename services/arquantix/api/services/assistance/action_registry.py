"""Registre produit officiel — types d'action CAL (Phase 3.5).

Une seule structure ``ActionDefinition`` par ``action_type`` persisté dans
``assistance_action_drafts`` : niveau prose (label, étapes autorisées, TTL,
sécurité) en plus des schémas Pydantic (``action_draft_payload_schemas.py``).

**Prochains verrous métier** (hors périmètre implémenté — ajouter avec schéma dédié) :
``kyc_resume``, ``account_creation_start``, ``investor_questionnaire_start``,
``exclusive_offer_subscribe``, ``vault_subscribe``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
from typing import Final, Literal, Mapping

# ── Produit : grille de sécurité (≠ ``cal_contract.security_level`` L0-L2) ─
ProductSecurityLevel = Literal["standard", "elevated", "high"]

# Clé pour mappings « flux sans étape métier » (widgets tools-only).
_WIDGET_STAGE_SENTINEL: Final[str] = "*"


def _frozen_map(stage_to_widget: Mapping[str, str | None]) -> FrozenMapping[str, str | None]:
    return MappingProxyType(dict(stage_to_widget))


def _frozen_params(stage_to_params: Mapping[str, frozenset[str]]) -> FrozenMapping[str, frozenset[str]]:
    return MappingProxyType(dict(stage_to_params))


@dataclass(frozen=True)
class ActionDefinition:
    """Déclaration fonctionnelle d'un ``action_type`` persisté."""

    action_type: str
    label: str
    description: str
    staged: bool
    allowed_stages: frozenset[str]
    required_params_by_stage: Mapping[str, frozenset[str]]
    widget_kind_by_stage: Mapping[str, str | None]
    security_level: ProductSecurityLevel
    requires_confirmation: bool
    requires_step_up: bool
    ttl_seconds: int
    allowed_payload_schema: str
    allow_parallel_actions: bool = False


def resolve_cal_security_level(
    meta: ActionDefinition,
    *,
    business_state: str,
) -> str:
    """Déduit ``cal_contract.security_level`` (``L0`` / ``L1`` / ``L2``)."""
    st = business_state.strip().lower() if business_state else ""
    if not meta.staged:
        if meta.security_level == "high":
            return "L2"
        if meta.security_level == "elevated":
            return "L1"
        return "L0"

    if meta.security_level == "high":
        if st == "confirmation":
            return "L2"
        if st == "awaiting_launch_confirm":
            return "L1"
        return "L0"
    if meta.security_level == "elevated":
        if st == "confirmation":
            return "L2"
        if st in {"awaiting_launch_confirm", "source_list"}:
            return "L1"
        return "L0"
    if st == "confirmation":
        return "L1"
    return "L0"


_ACTION_DEFINITIONS: dict[str, ActionDefinition] = {
    "crypto_buy": ActionDefinition(
        action_type="crypto_buy",
        label="Acheter une crypto",
        description=(
            "Parcours guidé CAL : liste des sources, recap avant widget, carte "
            "de confirmation dans l'app."
        ),
        staged=True,
        allowed_stages=frozenset(
            {"source_list", "awaiting_launch_confirm", "confirmation"}
        ),
        required_params_by_stage=_frozen_params(
            {
                "source_list": frozenset(
                    {"target_kind", "target_id", "stage", "accounts_count"}
                ),
                "awaiting_launch_confirm": frozenset(
                    {
                        "target_kind",
                        "target_id",
                        "stage",
                        "amount_from",
                        "currency_from",
                        "account_key",
                        "source_label",
                    }
                ),
                "confirmation": frozenset(
                    {
                        "target_kind",
                        "target_id",
                        "stage",
                        "amount",
                        "amount_currency",
                        "account_key",
                    }
                ),
            },
        ),
        widget_kind_by_stage=_frozen_map(
            {
                "source_list": "invest_source_account_list",
                "awaiting_launch_confirm": None,
                "confirmation": "invest_confirmation_draft",
            },
        ),
        security_level="high",
        requires_confirmation=True,
        requires_step_up=True,
        ttl_seconds=900,
        allowed_payload_schema="CryptoBuyBusinessPayload",
    ),
    "bundle_invest": ActionDefinition(
        action_type="bundle_invest",
        label="Investir dans un bundle",
        description=(
            "CAL bundles : liste des comptes source puis recap confirmation "
            "avant redirection native."
        ),
        staged=True,
        allowed_stages=frozenset({"source_list", "confirmation"}),
        required_params_by_stage=_frozen_params(
            {
                "source_list": frozenset(
                    {"target_kind", "target_id", "stage", "accounts_count"}
                ),
                "confirmation": frozenset(
                    {
                        "target_kind",
                        "target_id",
                        "stage",
                        "amount",
                        "amount_currency",
                        "account_key",
                    }
                ),
            },
        ),
        widget_kind_by_stage=_frozen_map(
            {
                "source_list": "invest_source_account_list",
                "confirmation": "invest_confirmation_draft",
            },
        ),
        security_level="high",
        requires_confirmation=True,
        requires_step_up=True,
        ttl_seconds=900,
        allowed_payload_schema="BundleInvestBusinessPayload",
    ),
    "crypto_sell_guide": ActionDefinition(
        action_type="crypto_sell_guide",
        label="Vendre une crypto (guide)",
        description="Widget unique : CTA vers le flux vendre natif (instrument contrôlé).",
        staged=False,
        allowed_stages=frozenset(),
        required_params_by_stage=_frozen_params(
            {
                _WIDGET_STAGE_SENTINEL: frozenset(
                    {"widget_kind", "symbol", "instrument_id"}
                ),
            },
        ),
        widget_kind_by_stage=_frozen_map(
            {_WIDGET_STAGE_SENTINEL: "crypto_sell_cta"},
        ),
        security_level="elevated",
        requires_confirmation=False,
        requires_step_up=False,
        ttl_seconds=600,
        allowed_payload_schema="CryptoSellGuidePayload",
    ),
    "crypto_swap_guide": ActionDefinition(
        action_type="crypto_swap_guide",
        label="Échanger des cryptos (guide)",
        description="Ouverture liste marchés + paire facultative indicative.",
        staged=False,
        allowed_stages=frozenset(),
        required_params_by_stage=_frozen_params(
            {
                _WIDGET_STAGE_SENTINEL: frozenset({"widget_kind"}),
            },
        ),
        widget_kind_by_stage=_frozen_map(
            {_WIDGET_STAGE_SENTINEL: "crypto_swap_guide"},
        ),
        security_level="standard",
        requires_confirmation=False,
        requires_step_up=False,
        ttl_seconds=900,
        allowed_payload_schema="CryptoSwapGuidePayload",
    ),
    "deposit_guide": ActionDefinition(
        action_type="deposit_guide",
        label="Déposer des fonds (guide)",
        description="Sélection de canaux dépôt (virement / carte / crypto inbound).",
        staged=False,
        allowed_stages=frozenset(),
        required_params_by_stage=_frozen_params(
            {
                _WIDGET_STAGE_SENTINEL: frozenset({"widget_kind", "channels"}),
            },
        ),
        widget_kind_by_stage=_frozen_map(
            {_WIDGET_STAGE_SENTINEL: "deposit_channel_picker"},
        ),
        security_level="standard",
        requires_confirmation=False,
        requires_step_up=False,
        ttl_seconds=900,
        allowed_payload_schema="DepositGuidePayload",
    ),
    "crypto_investment_intent": ActionDefinition(
        action_type="crypto_investment_intent",
        label="Intention investissement crypto (conversationnel)",
        description=(
            "Brouillon d’intention : slots + résolution backend sans LLM, "
            "sans widget transactionnel ni exécution d’ordre en V1."
        ),
        staged=True,
        allowed_stages=frozenset(
            {
                "draft_pending_slots",
                "draft_ready_for_backend_validation",
                "draft_backend_validated",
                "draft_pending_user_confirmation",
            },
        ),
        required_params_by_stage=_frozen_params(
            {
                "draft_pending_slots": frozenset(
                    {
                        "intent_schema_version",
                        "draft_origin",
                        "stage",
                        "slots",
                        "backend_validation",
                    },
                ),
                "draft_ready_for_backend_validation": frozenset(
                    {
                        "intent_schema_version",
                        "draft_origin",
                        "stage",
                        "slots",
                        "backend_validation",
                    },
                ),
                "draft_backend_validated": frozenset(
                    {
                        "intent_schema_version",
                        "draft_origin",
                        "stage",
                        "slots",
                        "backend_validation",
                        "confirmation",
                    },
                ),
                "draft_pending_user_confirmation": frozenset(
                    {
                        "intent_schema_version",
                        "draft_origin",
                        "stage",
                        "slots",
                        "backend_validation",
                        "confirmation",
                    },
                ),
            },
        ),
        widget_kind_by_stage=_frozen_map(
            {
                "draft_pending_slots": None,
                "draft_ready_for_backend_validation": None,
                "draft_backend_validated": None,
                "draft_pending_user_confirmation": None,
            },
        ),
        security_level="standard",
        requires_confirmation=False,
        requires_step_up=False,
        ttl_seconds=1800,
        allowed_payload_schema="CryptoInvestmentIntentDraft",
    ),
}


PLANNED_ACTION_TYPES: Final[tuple[str, ...]] = (
    "kyc_resume",
    "account_creation_start",
    "investor_questionnaire_start",
    "exclusive_offer_subscribe",
    "vault_subscribe",
)


@lru_cache(maxsize=1)
def registered_action_types() -> frozenset[str]:
    return frozenset(_ACTION_DEFINITIONS.keys())


def get_action_definition(action_type: str) -> ActionDefinition:
    key = (action_type or "").strip()
    return _ACTION_DEFINITIONS[key]


def registry_stage_bucket_for_validation(meta: ActionDefinition, raw: dict) -> str:
    if meta.staged:
        st = raw.get("stage")
        return str(st).strip().lower() if isinstance(st, str) else ""
    return _WIDGET_STAGE_SENTINEL


def _param_present(v: object) -> bool:
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (dict, list, tuple)):
        return True
    return True


def enforce_registry_before_business_validate(
    action_type: str,
    payload_root: Mapping[str, object],
) -> None:
    """Cohérence produit avant Pydantic. Lève ``ValueError`` → converti par l'appelant."""
    meta = get_action_definition(action_type)
    raw = dict(payload_root)

    if meta.staged:
        stage = raw.get("stage")
        if not isinstance(stage, str) or not stage.strip():
            raise ValueError("stage_requis_et_non_vide")
        key = stage.strip().lower()
        if key not in meta.allowed_stages:
            raise ValueError(f"stage_non_autorisé:{key!r}")
    else:
        if raw.get("stage") is not None:
            raise ValueError("stage_interdit_sur_action_widget")

    bucket = registry_stage_bucket_for_validation(meta, raw)
    declared = frozenset(
        k
        for k, v in raw.items()
        if k != "cal_contract" and v is not None and _param_present(v)
    )
    expect = frozenset(meta.required_params_by_stage.get(bucket, frozenset()))
    if expect and not expect <= declared:
        missing = sorted(expect - declared)
        raise ValueError(f"params_requis_registry_manquants:{missing}")

    if not meta.staged:
        exp_wk = meta.widget_kind_by_stage.get(_WIDGET_STAGE_SENTINEL)
        if isinstance(exp_wk, str) and exp_wk:
            raw_wk = raw.get("widget_kind")
            if isinstance(raw_wk, str) and raw_wk.strip() and raw_wk.strip() != exp_wk:
                raise ValueError(f"widget_kind_attendu:{exp_wk!r}")


def ttl_seconds_for_action(action_type: str) -> int:
    return get_action_definition(action_type).ttl_seconds


__all__ = [
    "PLANNED_ACTION_TYPES",
    "ActionDefinition",
    "ProductSecurityLevel",
    "_WIDGET_STAGE_SENTINEL",
    "enforce_registry_before_business_validate",
    "get_action_definition",
    "registered_action_types",
    "registry_stage_bucket_for_validation",
    "resolve_cal_security_level",
    "ttl_seconds_for_action",
]
