"""Validation stricte des payloads métier ``AssistanceActionDraft.payload`` (Phase 3).

Cartographie sources (valeur ``action_type`` en colonne DB) :

+---------------+---------------------------+--------------------------------------------+
| action_type   | widget_kind / contexte    | Fichier source                              |
+---------------+---------------------------+--------------------------------------------+
| crypto_buy    | (étape ACHAT CAL)          | crypto_buy_start, show_invest_source_accts,|
|               |                           | invest_confirmation_emit (crypto)           |
+---------------+---------------------------+--------------------------------------------+
| bundle_invest | (étape BUNDLE CAL)        | show_invest_source_accounts,               |
|               |                           | invest_confirmation_emit (bundle)           |
+---------------+---------------------------+--------------------------------------------+
| crypto_sell_guide | crypto_sell_cta       | crypto_sell_start → append_action_widget   |
+---------------+---------------------------+--------------------------------------------+
| crypto_swap_guide | crypto_swap_guide     | crypto_swap_start                          |
+---------------+---------------------------+--------------------------------------------+
| deposit_guide | deposit_channel_picker    | deposit_present_channels                   |
+---------------+---------------------------+--------------------------------------------+

- ``cal_contract`` (Phase 2) est **retiré** avant validation métier puis réinjecté dans
  ``create_action_draft`` — ce module ne valide que la partie métier racine.

- Lecture legacy : payloads sans enveloppe Phase 3 restent utilisables hors écriture
  (mémoire, merge intake) sans passer par ces schémas.

Phase 3.5 : vérité produit par ``action_type`` dans ``action_registry.py``
(étapes, TTL, sécurité produit) ; cette couche Pydantic reste le contrat technique strict.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from services.assistance.action_draft_contract import CAL_CONTRACT_KEY
from services.assistance.action_registry import (
    enforce_registry_before_business_validate,
    get_action_definition,
    registered_action_types,
)

_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9]{0,31}$")
_CCY_RE = re.compile(r"^[A-Z]{2,16}$")


class InvalidActionDraftBusinessPayload(ValueError):
    """Levée quand le payload métier ne respecte pas le schéma ``action_type``."""

    def __init__(self, action_type: str, errors: list[str]):
        self.action_type = action_type
        self.errors = errors
        detail = "; ".join(errors) if errors else "validation_error"
        super().__init__(f"invalid_action_draft_payload[{action_type}]: {detail}")


# ── Invest flows (crypto_buy / bundle) ───────────────────────────────────


class CryptoBuyBusinessPayload(BaseModel):
    """Brouillon ``action_type=crypto_buy`` — achat spot / recap invest crypto."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_kind: Literal["crypto_buy"]
    target_id: str = Field(..., min_length=1, max_length=256)
    stage: Literal["source_list", "awaiting_launch_confirm", "confirmation"]

    accounts_count: Optional[int] = Field(None, ge=0, le=100_000)
    amount_from: Optional[float] = Field(None, gt=0)
    currency_from: Optional[str] = Field(None, min_length=2, max_length=16)
    amount: Optional[float] = Field(None, gt=0)
    amount_currency: Optional[str] = Field(None, min_length=2, max_length=16)
    account_key: Optional[str] = Field(None, min_length=1, max_length=256)
    intent_kind: Optional[str] = Field(None, max_length=48)
    compact: Optional[bool] = None
    source_label: Optional[str] = Field(None, max_length=256)

    @model_validator(mode="after")
    def _stage_consistency(self) -> "CryptoBuyBusinessPayload":
        st = self.stage
        if st == "source_list":
            if self.accounts_count is None:
                raise ValueError("source_list requiert accounts_count")
        elif st == "awaiting_launch_confirm":
            if self.amount_from is None:
                raise ValueError("awaiting_launch_confirm requiert amount_from")
            if not self.currency_from:
                raise ValueError("awaiting_launch_confirm requiert currency_from")
            if not self.account_key:
                raise ValueError("awaiting_launch_confirm requiert account_key")
            if not self.source_label:
                raise ValueError("awaiting_launch_confirm requiert source_label")
        elif st == "confirmation":
            if self.amount is None:
                raise ValueError("confirmation requiert amount")
            if not self.amount_currency:
                raise ValueError("confirmation requiert amount_currency")
            if not self.account_key:
                raise ValueError("confirmation requiert account_key")
        return self

    @model_validator(mode="after")
    def _formats(self) -> "CryptoBuyBusinessPayload":
        if self.currency_from and not _CCY_RE.match(self.currency_from.upper()):
            raise ValueError("currency_from_invalide")
        if self.amount_currency and not _CCY_RE.match(self.amount_currency.upper()):
            raise ValueError("amount_currency_invalide")
        sym = self.target_id.strip().upper()
        if not _SYMBOL_RE.match(sym):
            raise ValueError("target_id_instrument_invalide")
        object.__setattr__(self, "target_id", sym)
        if self.currency_from:
            object.__setattr__(self, "currency_from", self.currency_from.upper())
        if self.amount_currency:
            object.__setattr__(self, "amount_currency", self.amount_currency.upper())
        return self


class BundleInvestBusinessPayload(BaseModel):
    """Brouillon ``action_type=bundle_invest`` — pas d'étape ``awaiting_launch_confirm``."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_kind: Literal["bundle"]
    target_id: str = Field(..., min_length=1, max_length=256)
    stage: Literal["source_list", "confirmation"]

    accounts_count: Optional[int] = Field(None, ge=0, le=100_000)
    amount_from: Optional[float] = Field(None, gt=0)
    currency_from: Optional[str] = Field(None, min_length=2, max_length=16)
    amount: Optional[float] = Field(None, gt=0)
    amount_currency: Optional[str] = Field(None, min_length=2, max_length=16)
    account_key: Optional[str] = Field(None, min_length=1, max_length=256)
    intent_kind: Optional[str] = Field(None, max_length=48)
    compact: Optional[bool] = None

    @model_validator(mode="after")
    def _stage_consistency(self) -> "BundleInvestBusinessPayload":
        st = self.stage
        if st == "source_list":
            if self.accounts_count is None:
                raise ValueError("source_list requiert accounts_count")
        elif st == "confirmation":
            if self.amount is None:
                raise ValueError("confirmation requiert amount")
            if not self.amount_currency:
                raise ValueError("confirmation requiert amount_currency")
            if not self.account_key:
                raise ValueError("confirmation requiert account_key")
        return self

    @model_validator(mode="after")
    def _formats(self) -> "BundleInvestBusinessPayload":
        if self.currency_from and not _CCY_RE.match(self.currency_from.upper()):
            raise ValueError("currency_from_invalide")
        if self.amount_currency and not _CCY_RE.match(self.amount_currency.upper()):
            raise ValueError("amount_currency_invalide")
        tid = self.target_id.strip()
        if not tid:
            raise ValueError("target_id_bundle_vide")
        object.__setattr__(self, "target_id", tid)
        if self.currency_from:
            object.__setattr__(self, "currency_from", self.currency_from.upper())
        if self.amount_currency:
            object.__setattr__(self, "amount_currency", self.amount_currency.upper())
        return self


# ── Widgets action (_widget append_action_widget) ───────────────────────


class CryptoSellGuidePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    widget_kind: Literal["crypto_sell_cta"]
    symbol: str = Field(..., min_length=1, max_length=32)
    instrument_id: int = Field(..., gt=0)

    @model_validator(mode="after")
    def _sym(self) -> "CryptoSellGuidePayload":
        s = self.symbol.strip().upper()
        if not _SYMBOL_RE.match(s):
            raise ValueError("symbol_invalide")
        object.__setattr__(self, "symbol", s)
        return self


class CryptoSwapGuidePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    widget_kind: Literal["crypto_swap_guide"]
    from_symbol: Optional[str] = Field(None, max_length=32)
    to_symbol: Optional[str] = Field(None, max_length=32)

    @model_validator(mode="after")
    def _sym(self) -> "CryptoSwapGuidePayload":
        for attr in ("from_symbol", "to_symbol"):
            raw = getattr(self, attr)
            if raw is None or raw == "":
                object.__setattr__(self, attr, None)
                continue
            s = str(raw).strip().upper()
            if not _SYMBOL_RE.match(s):
                raise ValueError(f"{attr}_invalide")
            object.__setattr__(self, attr, s)
        return self


class DepositGuidePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    widget_kind: Literal["deposit_channel_picker"]
    channels: list[str] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _channels(self) -> "DepositGuidePayload":
        out: list[str] = []
        for c in self.channels:
            k = str(c).strip()[:64]
            if not k:
                raise ValueError("channel_vide")
            out.append(k)
        object.__setattr__(self, "channels", out)
        return self


# ── Crypto investment intent (conversationnel V1) ────────────────────────

_CRYPTO_INTENT_SYM = _SYMBOL_RE


class CryptoIntentTargetAssetSlot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    raw: Optional[str] = Field(None, max_length=512)
    raw_provenance: Optional[str] = Field(None, max_length=48)
    resolved_id: Optional[str] = Field(None, max_length=256)
    resolved_provenance: Optional[str] = Field(None, max_length=48)
    label: Optional[str] = Field(None, max_length=256)
    symbol: Optional[str] = Field(None, max_length=64)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    resolution_status: Optional[str] = Field(None, max_length=48)
    available_balance: Optional[float] = None


class CryptoIntentSourceAccountSlot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    raw: Optional[str] = Field(None, max_length=512)
    raw_provenance: Optional[str] = Field(None, max_length=48)
    selected_option_id: Optional[str] = Field(
        None,
        max_length=256,
        description=(
            "Identifiant backend stable (ex. clé compte source), jamais un index affiché 1/2/3."
        ),
    )
    resolved_id: Optional[str] = Field(None, max_length=256)
    resolved_provenance: Optional[str] = Field(None, max_length=48)
    label: Optional[str] = Field(None, max_length=256)
    symbol: Optional[str] = Field(None, max_length=64)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    resolution_status: Optional[str] = Field(None, max_length=48)
    available_balance: Optional[float] = None


class CryptoIntentAmountSlot(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    raw: Optional[str] = Field(None, max_length=512)
    raw_provenance: Optional[str] = Field(None, max_length=48)
    value: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=16)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    resolution_status: Optional[str] = Field(None, max_length=48)
    use_all_available: Optional[bool] = None


class CryptoIntentSlots(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_asset: CryptoIntentTargetAssetSlot = Field(
        default_factory=CryptoIntentTargetAssetSlot,
    )
    source_account: CryptoIntentSourceAccountSlot = Field(
        default_factory=CryptoIntentSourceAccountSlot,
    )
    amount: CryptoIntentAmountSlot = Field(default_factory=CryptoIntentAmountSlot)


class BackendValidationBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["pending", "ok", "invalid"] = "pending"
    errors: list[str] = Field(default_factory=list)


class ConfirmationBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["none", "pending", "confirmed", "declined"] = "none"
    summary: Optional[str] = Field(None, max_length=4000)


CryptoIntentStage = Literal[
    "draft_pending_slots",
    "draft_ready_for_backend_validation",
    "draft_backend_validated",
    "draft_pending_user_confirmation",
]

CryptoIntentDraftOrigin = Literal[
    "chat_free_text",
    "product_page_cta",
    "portfolio_recommendation",
    "advisor_handoff",
    "push_notification",
]


class CryptoInvestmentIntentDraft(BaseModel):
    """Brouillon ``action_type=crypto_investment_intent`` — V1 sans exécution."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    intent_schema_version: Literal["1"] = "1"
    draft_origin: CryptoIntentDraftOrigin = "chat_free_text"
    stage: CryptoIntentStage
    slots: CryptoIntentSlots
    backend_validation: BackendValidationBlock = Field(
        default_factory=BackendValidationBlock,
    )
    confirmation: ConfirmationBlock = Field(default_factory=ConfirmationBlock)

    @model_validator(mode="after")
    def _stage_coherence(self) -> "CryptoInvestmentIntentDraft":
        if self.stage == "draft_backend_validated":
            if self.backend_validation.status != "ok":
                raise ValueError("draft_backend_validated requiert backend_validation.status=ok")
        if self.stage == "draft_pending_user_confirmation":
            if self.backend_validation.status != "ok":
                raise ValueError(
                    "draft_pending_user_confirmation requiert backend_validation.status=ok",
                )
            if self.confirmation.status == "pending" and (
                not self.confirmation.summary
                or not str(self.confirmation.summary).strip()
            ):
                raise ValueError("draft_pending_user_confirmation requiert confirmation.summary")
        return self

    @model_validator(mode="after")
    def _formats(self) -> "CryptoInvestmentIntentDraft":
        c = self.slots.amount.currency
        if c:
            cu = c.strip().upper()[:16]
            if not _CCY_RE.match(cu):
                raise ValueError("slots.amount.currency_invalide")
            object.__setattr__(self.slots.amount, "currency", cu)

        tsym = self.slots.target_asset.symbol
        if tsym:
            su = tsym.strip().upper()
            if not _CRYPTO_INTENT_SYM.match(su):
                raise ValueError("slots.target_asset.symbol_invalide")
            object.__setattr__(self.slots.target_asset, "symbol", su)
        return self


_ACTION_TYPE_MODEL: dict[str, type[BaseModel]] = {
    "crypto_buy": CryptoBuyBusinessPayload,
    "bundle_invest": BundleInvestBusinessPayload,
    "crypto_sell_guide": CryptoSellGuidePayload,
    "crypto_swap_guide": CryptoSwapGuidePayload,
    "deposit_guide": DepositGuidePayload,
    "crypto_investment_intent": CryptoInvestmentIntentDraft,
}


def assert_payload_models_synced_with_registry() -> None:
    """Invariant dev : clés Pydantic ≡ registre produit."""
    reg = registered_action_types()
    mkeys = frozenset(_ACTION_TYPE_MODEL.keys())
    if reg != mkeys:
        raise AssertionError(f"registry/schema mismatch reg={reg} models={mkeys}")


def _pydantic_errors(exc: ValidationError) -> list[str]:
    return [f"{e['loc']}: {e['msg']}" for e in exc.errors()]


def validate_action_draft_business_payload(
    action_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Valide et normalise le payload métier (sans ``cal_contract``).

    Returns:
        dict prêt pour ``merge_business_payload_with_contract``.

    Raises:
        InvalidActionDraftBusinessPayload si schéma inconnu ou invalide.
    """
    at = (action_type or "").strip()
    raw = {k: v for k, v in (payload or {}).items() if k != CAL_CONTRACT_KEY}
    if not raw:
        raise InvalidActionDraftBusinessPayload(at, ["payload_metier_vide"])

    try:
        get_action_definition(at)
    except KeyError:
        raise InvalidActionDraftBusinessPayload(
            at,
            [f"action_type_non_enregistre:{at!r}"],
        ) from None

    try:
        enforce_registry_before_business_validate(at, raw)
    except ValueError as exc:
        raise InvalidActionDraftBusinessPayload(at, [str(exc)]) from exc

    model_cls = _ACTION_TYPE_MODEL.get(at)
    if model_cls is None:
        raise InvalidActionDraftBusinessPayload(
            at,
            [f"schéma pydantic manquant pour:{at!r}"],
        )

    try:
        model = model_cls.model_validate(raw)
    except ValidationError as exc:
        raise InvalidActionDraftBusinessPayload(at, _pydantic_errors(exc)) from exc
    except ValueError as exc:
        raise InvalidActionDraftBusinessPayload(at, [str(exc)]) from exc

    out = model.model_dump(mode="python", exclude_none=False)
    return out


def sanitize_action_draft_payload_readonly(
    payload: Any,
    *,
    max_depth: int = 4,
) -> dict[str, Any]:
    """Best-effort : copie plate JSON-safe pour logs (ne modifie pas la DB)."""
    if not isinstance(payload, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in list(payload.items())[:256]:
        if not isinstance(k, str) or len(k) > 128:
            continue
        if k == CAL_CONTRACT_KEY:
            out[k] = "<omitted>"
        elif isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, dict) and max_depth > 0:
            out[k] = sanitize_action_draft_payload_readonly(v, max_depth=max_depth - 1)
        elif isinstance(v, list) and max_depth > 0:
            out[k] = [
                (
                    sanitize_action_draft_payload_readonly(x, max_depth=max_depth - 1)
                    if isinstance(x, dict)
                    else str(x)[:200]
                )
                for x in v[:50]
            ]
    return out


__all__ = [
    "BundleInvestBusinessPayload",
    "CryptoBuyBusinessPayload",
    "CryptoInvestmentIntentDraft",
    "CryptoSellGuidePayload",
    "CryptoSwapGuidePayload",
    "DepositGuidePayload",
    "InvalidActionDraftBusinessPayload",
    "assert_payload_models_synced_with_registry",
    "sanitize_action_draft_payload_readonly",
    "validate_action_draft_business_payload",
]
