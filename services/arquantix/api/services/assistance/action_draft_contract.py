"""Contrat strict CAL — enveloppe ``cal_contract`` dans ``AssistanceActionDraft.payload``.

La table (migration 154) garde ``action_type`` + ``payload`` JSONB. Tous les champs
métier additionnels (montants, ``stage``, etc.) restent au **niveau racine** du
payload pour compatibilité avec le code existant ; l'enveloppe ``cal_contract``
ajoute traçabilité audit : paramètres requis / manquants, statuts, TTL.

Chaque ``action_type`` enregistré dispose d'un jeu de clés **logiques** attendues
selon l'étape (``stage``).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Final, Iterable, Literal, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

CAL_CONTRACT_KEY: Final[str] = "cal_contract"

ActionDraftValidationStatus = Literal["pending", "ok", "invalid"]
ActionDraftConfirmationStatus = Literal["none", "pending", "confirmed", "declined"]
ActionDraftSecurityLevel = Literal["L0", "L1", "L2"]

ACTION_TYPE_VERSION_DEFAULT: Final[str] = "1"

# États CAL déjà utilisés dans les payloads métiers (``stage``) + fallback.
DEFAULT_STATE = "draft"


class CalActionDraftContract(BaseModel):
    """Contrat versionné sérialisé sous ``payload["cal_contract"]``."""

    model_config = ConfigDict(extra="forbid")

    action_type: str = Field(..., min_length=1, max_length=64)
    action_version: str = Field(default=ACTION_TYPE_VERSION_DEFAULT, max_length=16)
    state: str = Field(default=DEFAULT_STATE, max_length=64)
    required_params: list[str] = Field(default_factory=list)
    collected_params: dict[str, Any] = Field(default_factory=dict)
    missing_params: list[str] = Field(default_factory=list)
    validation_status: ActionDraftValidationStatus = "pending"
    confirmation_status: ActionDraftConfirmationStatus = "none"
    expires_at: Optional[str] = None  # ISO-8601
    security_level: ActionDraftSecurityLevel = "L0"


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _present(biz: Mapping[str, Any], key: str) -> bool:
    v = biz.get(key)
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (dict, list)):
        return True
    return True


def _collect_snapshot(business: Mapping[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    """Copie défensive des champs métier utilisés comme paramètres collectés."""
    out: dict[str, Any] = {}
    for k in keys:
        if k not in business:
            continue
        v = business[k]
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, dict):
            out[k] = dict(v)
        elif isinstance(v, list):
            out[k] = list(v)
        else:
            out[k] = v
    return out


def _required_for_crypto_investment_intent(
    *,
    stage: str,
    business: Mapping[str, Any],
) -> list[str]:
    """Paramètres CAL logiques pour ``crypto_investment_intent`` (≠ crypto_buy).

    Les slots détaillés restent sous ``slots`` ; l’audit surface les clés racine."""
    _ = business
    st = stage.strip().lower()
    base = ["intent_schema_version", "draft_origin", "stage", "slots", "backend_validation"]
    if st in {"draft_backend_validated", "draft_pending_user_confirmation"}:
        base.append("confirmation")
    return sorted(set(base))


def _required_for_crypto_like_registry(
    action_type: str,
    *,
    stage: str,
    business: Mapping[str, Any],
) -> list[str]:
    """Paramètres requis par défaut selon étape CAL (crypto / bundle invest)."""
    st = stage.strip().lower()

    if st == "source_list":
        out = ["target_kind", "target_id", "stage"]
        # Montant facultatif avant choix du compte source.
        return sorted(set(out))

    if st == "awaiting_launch_confirm":
        return sorted(
            {
                "target_kind",
                "target_id",
                "stage",
                "amount_from",
                "currency_from",
            },
        )

    if st == "confirmation":
        # Carte recap investissement : montant « quote » + compte (outil Product).
        base = {"target_kind", "target_id", "stage", "account_key"}
        if _present(dict(business), "amount"):
            return sorted(base | {"amount", "amount_currency"})
        return sorted(base | {"amount_from", "currency_from"})

    # fallback : ancrage minimal
    return sorted({"target_kind", "target_id", "stage"})


def _confirmation_status(stage: str) -> ActionDraftConfirmationStatus:
    sl = stage.strip().lower()
    if sl in {
        "awaiting_launch_confirm",
        "confirmation",
        "draft_pending_user_confirmation",
    }:
        return "pending"
    return "none"


def _validation_status(required: list[str], missing: list[str]) -> ActionDraftValidationStatus:
    if missing:
        return "pending"
    return "ok"


def _security_level(stage: str) -> ActionDraftSecurityLevel:
    sl = stage.strip().lower()
    if sl == "confirmation":
        return "L1"
    if sl == "awaiting_launch_confirm":
        return "L0"
    if sl == "draft_pending_user_confirmation":
        return "L1"
    return "L0"


def build_cal_contract(
    *,
    action_type: str,
    business: Mapping[str, Any],
    ttl_hours: Optional[float] = None,
) -> CalActionDraftContract:
    """Construit le contrat à partir du payload métier (sans clé ``cal_contract``).

    TTL : priorité **registre produit** ``action_registry.ttl_seconds`` ; repli
    historique ``ttl_hours`` (défaut 0,75 h) si ``action_type`` inconnu.

    Tolère les payloads asymétriques : ne lève pas, marque ``validation_status``.
    """
    at = action_type.strip()[:64]
    stage_raw = business.get("stage")
    state = (
        str(stage_raw).strip()[:64]
        if stage_raw is not None and str(stage_raw).strip()
        else DEFAULT_STATE
    )

    ttl_sec: float
    sec_override: Optional[ActionDraftSecurityLevel] = None
    try:
        from services.assistance import action_registry as ar

        meta = ar.get_action_definition(at)
        ttl_sec = float(meta.ttl_seconds)
        sec_override = ar.resolve_cal_security_level(meta, business_state=state)  # type: ignore[assignment]
    except KeyError:
        if ttl_hours is not None:
            ttl_sec = ttl_hours * 3600.0
        else:
            ttl_sec = 0.75 * 3600.0
        sec_override = None

    if at in {"crypto_buy", "bundle_invest"}:
        required = _required_for_crypto_like_registry(
            at,
            stage=state,
            business=business,
        )
    elif at == "crypto_investment_intent":
        required = _required_for_crypto_investment_intent(
            stage=state,
            business=business,
        )
    else:
        # Autres CAL (deposit, swap, sell, playbook…) : jeu minimal stable.
        required = sorted(
            {"target_kind", "target_id", "widget_kind"}
            & {k for k in business.keys() if k != CAL_CONTRACT_KEY}
        )
        if not required:
            required = ["widget_kind"] if business.get("widget_kind") else ["target_kind"]

    collected_keys = sorted(
        set(required)
        | {k for k, v in business.items() if k != CAL_CONTRACT_KEY and _present(dict(business), k)}
    )
    snapshot = _collect_snapshot(business, collected_keys)

    missing: list[str] = []
    for key in required:
        if key not in snapshot:
            missing.append(key)
            continue
        val = snapshot.get(key)
        if val is None:
            missing.append(key)
        elif isinstance(val, str) and not val.strip():
            missing.append(key)

    vstat = _validation_status(required, missing)
    expiry = datetime.now(timezone.utc) + timedelta(seconds=float(ttl_sec))

    sec_lvl: ActionDraftSecurityLevel
    if sec_override is not None:
        sec_lvl = sec_override  # type: ignore[assignment]
    else:
        sec_lvl = _security_level(state)

    contract = CalActionDraftContract(
        action_type=at,
        action_version=ACTION_TYPE_VERSION_DEFAULT,
        state=state,
        required_params=list(required),
        collected_params=snapshot,
        missing_params=missing,
        validation_status=vstat,
        confirmation_status=_confirmation_status(state),
        expires_at=_iso_utc(expiry),
        security_level=sec_lvl,
    )

    try:
        # Re-valider sortie vs schéma (defense duplicate / types)
        contract = CalActionDraftContract.model_validate(contract.model_dump())
    except Exception:  # noqa: BLE001
        logger.exception("action_draft_contract.build_invalid action_type=%s", at)
        return CalActionDraftContract(
            action_type=at or "unknown",
            action_version=ACTION_TYPE_VERSION_DEFAULT,
            state=state,
            required_params=list(required),
            collected_params=snapshot,
            missing_params=list(required),
            validation_status="invalid",
            confirmation_status=_confirmation_status(state),
            expires_at=_iso_utc(expiry),
            security_level="L2",
        )

    return contract


def merge_business_payload_with_contract(
    business_payload: dict[str, Any],
    *,
    action_type: str,
) -> dict[str, Any]:
    """Retourne un payload complet prêt pour ORM ``AssistanceActionDraft.payload``."""
    base = dict(business_payload or {})
    base.pop(CAL_CONTRACT_KEY, None)
    cc = build_cal_contract(action_type=action_type, business=base)
    base[CAL_CONTRACT_KEY] = cc.model_dump(mode="json")
    return base


def parse_contract_from_payload(payload: Any) -> Optional[CalActionDraftContract]:
    """Lit ``cal_contract`` si présent et valide (sinon ``None``, legacy rows)."""
    if not isinstance(payload, dict):
        return None
    raw = payload.get(CAL_CONTRACT_KEY)
    if not isinstance(raw, dict):
        return None
    try:
        return CalActionDraftContract.model_validate(raw)
    except Exception:  # noqa: BLE001
        logger.warning("action_draft_contract.parse_failed")
        return None


__all__ = [
    "ACTION_TYPE_VERSION_DEFAULT",
    "CAL_CONTRACT_KEY",
    "CalActionDraftContract",
    "build_cal_contract",
    "merge_business_payload_with_contract",
    "parse_contract_from_payload",
]
