"""Tool ``crypto_investment_intent_start`` — merge slots + upsert ``ActionDraft``.

Parcours V1 uniquement intention / audit : pas de deep-link, pas d’exécution.
Les champs ``resolved_*`` sont effacés à chaque merge (revalidation via
``crypto_investment_intent_resolve``)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from uuid import UUID

from services.assistance.action_drafts_repo import (
    create_action_draft,
    get_latest_active_draft_row,
    persist_action_draft_business_update,
    supersede_previous_drafts,
)
from services.assistance.agents.tools.action.crypto_investment_intent_logic import (
    crypto_intent_target_asset_supersedes_active_draft,
    infer_stage_from_slots,
    merge_slots_payload,
)
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)

_CRYPTO_INTENT_DRAFT_ORIGIN_ENUM: tuple[str, ...] = (
    "chat_free_text",
    "product_page_cta",
    "portfolio_recommendation",
    "advisor_handoff",
    "push_notification",
)
_CRYPTO_INTENT_ALLOWED_ORIGINS: frozenset[str] = frozenset(_CRYPTO_INTENT_DRAFT_ORIGIN_ENUM)


def _normalize_draft_origin(value: Optional[str]) -> str:
    s = str(value or "").strip().lower()
    return s if s in _CRYPTO_INTENT_ALLOWED_ORIGINS else "chat_free_text"


def _effective_draft_origin(
    *,
    incoming_explicit: Optional[str],
    previous: Optional[str],
) -> str:
    if incoming_explicit is not None and str(incoming_explicit).strip():
        return _normalize_draft_origin(str(incoming_explicit).strip())
    return _normalize_draft_origin(previous)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "crypto_investment_intent_start",
        "description": (
            "Crée ou met à jour un brouillon **crypto_investment_intent** "
            "(intention conversationnelle V1 — pas d'exécution). "
            "Transmets tout slot connu depuis le tour : texte brut, provenance, "
            "confiance. Appelle ensuite ``crypto_investment_intent_resolve`` pour "
            "les IDs / soldes **backend uniquement**."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_asset_raw": {"type": "string"},
                "target_asset_raw_provenance": {"type": "string"},
                "target_asset_symbol": {"type": "string"},
                "target_asset_confidence": {"type": "number"},
                "source_account_raw": {"type": "string"},
                "source_account_raw_provenance": {"type": "string"},
                "source_account_confidence": {"type": "number"},
                "source_account_selected_option_id": {
                    "type": "string",
                    "description": (
                        "Option QCM backend : valeur de ``option_id`` (ex. depuis "
                        "**clarification_options**), pas un index affiché 1/2/3."
                    ),
                },
                "amount_value": {"type": "number"},
                "amount_currency": {"type": "string"},
                "amount_raw": {"type": "string"},
                "amount_raw_provenance": {"type": "string"},
                "amount_use_all_available": {"type": "boolean"},
                "amount_confidence": {"type": "number"},
                "draft_origin": {
                    "type": "string",
                    "enum": list(_CRYPTO_INTENT_DRAFT_ORIGIN_ENUM),
                    "description": (
                        "Provenance fonctionnelle du brouillon (analytics / compliance)."
                    ),
                },
            },
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "action",
}


def _strip_backend_resolution_slots(slots: dict[str, Any]) -> None:
    for name in ("target_asset", "source_account"):
        d = slots.get(name)
        if not isinstance(d, dict):
            continue
        for f in ("resolved_id", "resolved_provenance", "resolution_status", "available_balance"):
            d.pop(f, None)
        d.pop("label", None)
    ad = slots.get("amount")
    if isinstance(ad, dict):
        for f in ("resolved_id", "resolved_provenance", "resolution_status"):
            ad.pop(f, None)


def _empty_slots() -> dict[str, Any]:
    return {
        "target_asset": {},
        "source_account": {},
        "amount": {},
    }


def execute(
    ctx: ToolContext,
    *,
    target_asset_raw: Optional[str] = None,
    target_asset_raw_provenance: str = "llm_extracted",
    target_asset_symbol: Optional[str] = None,
    target_asset_confidence: Optional[float] = None,
    source_account_raw: Optional[str] = None,
    source_account_raw_provenance: str = "llm_extracted",
    source_account_confidence: Optional[float] = None,
    source_account_selected_option_id: Optional[str] = None,
    amount_value: Optional[float] = None,
    amount_currency: Optional[str] = None,
    amount_raw: Optional[str] = None,
    amount_raw_provenance: str = "llm_extracted",
    amount_use_all_available: Optional[bool] = None,
    amount_confidence: Optional[float] = None,
    draft_origin: Optional[str] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    if not ctx.client_id:
        return {"ok": False, "error": "client_required", "flow": "crypto_investment_intent"}

    try:
        conv_uid = UUID(str(ctx.conversation_id))
        client_uid = UUID(str(ctx.client_id))
    except (ValueError, AttributeError):
        return {"ok": False, "error": "bad_uuid", "flow": "crypto_investment_intent"}

    patch: dict[str, Any] = {"target_asset": {}, "source_account": {}, "amount": {}}

    if target_asset_raw and str(target_asset_raw).strip():
        patch["target_asset"]["raw"] = str(target_asset_raw).strip()
        patch["target_asset"]["raw_provenance"] = str(
            target_asset_raw_provenance or "llm_extracted",
        ).strip()[:48]
        if target_asset_confidence is not None:
            patch["target_asset"]["confidence"] = float(target_asset_confidence)
    if target_asset_symbol and str(target_asset_symbol).strip():
        patch["target_asset"]["symbol"] = str(target_asset_symbol).strip().upper()
        patch["target_asset"].setdefault("raw_provenance", "llm_extracted")
        if target_asset_confidence is not None:
            patch["target_asset"]["confidence"] = float(target_asset_confidence)

    if source_account_raw and str(source_account_raw).strip():
        patch["source_account"]["raw"] = str(source_account_raw).strip()
        patch["source_account"]["raw_provenance"] = str(
            source_account_raw_provenance or "llm_extracted",
        ).strip()[:48]
        if source_account_confidence is not None:
            patch["source_account"]["confidence"] = float(source_account_confidence)

    if source_account_selected_option_id and str(source_account_selected_option_id).strip():
        patch["source_account"]["selected_option_id"] = str(
            source_account_selected_option_id,
        ).strip()[:256]
    amt_patch: dict[str, Any] = {}
    if amount_value is not None:
        amt_patch["value"] = float(amount_value)
    if amount_currency and str(amount_currency).strip():
        amt_patch["currency"] = str(amount_currency).strip()
    if amount_raw and str(amount_raw).strip():
        amt_patch["raw"] = str(amount_raw).strip()
        amt_patch["raw_provenance"] = str(amount_raw_provenance or "llm_extracted").strip()[:48]
    if amount_use_all_available is not None:
        amt_patch["use_all_available"] = bool(amount_use_all_available)
    if amount_confidence is not None:
        amt_patch["confidence"] = float(amount_confidence)

    patch["amount"] = amt_patch

    existing = get_latest_active_draft_row(
        ctx.db,
        conversation_id=conv_uid,
        action_type="crypto_investment_intent",
    )

    prev_origin: Optional[str] = None
    if existing:
        prev_payload = dict(existing.payload if isinstance(existing.payload, dict) else {})
        po = prev_payload.get("draft_origin")
        if isinstance(po, str) and po.strip():
            prev_origin = po.strip()

    if existing:
        prev = dict(existing.payload if isinstance(existing.payload, dict) else {})
        prev_slots_raw = prev.get("slots") if isinstance(prev.get("slots"), dict) else {}
        supersedes = crypto_intent_target_asset_supersedes_active_draft(
            prev_slots=dict(prev_slots_raw),
            patch_slots=patch,
        )
        merged_slots = merge_slots_payload(prev_slots_raw, patch)
        if supersedes:
            dor = _effective_draft_origin(
                incoming_explicit=draft_origin,
                previous=prev_origin,
            )
            supersede_previous_drafts(
                ctx.db,
                conversation_id=conv_uid,
                trigger_source="runtime_tool",
            )
            merged_slots = merge_slots_payload(_empty_slots(), patch)
            _strip_backend_resolution_slots(merged_slots)
            stage = infer_stage_from_slots(merged_slots)
            business = {
                "intent_schema_version": "1",
                "draft_origin": dor,
                "stage": stage,
                "slots": merged_slots,
                "backend_validation": {"status": "pending", "errors": []},
                "confirmation": {"status": "none", "summary": None},
            }
            row = create_action_draft(
                ctx.db,
                conversation_id=conv_uid,
                client_id=client_uid,
                action_type="crypto_investment_intent",
                payload=business,
            )
        else:
            _strip_backend_resolution_slots(merged_slots)
            stage = infer_stage_from_slots(merged_slots)
            dor = _effective_draft_origin(
                incoming_explicit=draft_origin,
                previous=prev_origin,
            )
            business = {
                "intent_schema_version": "1",
                "draft_origin": dor,
                "stage": stage,
                "slots": merged_slots,
                "backend_validation": {"status": "pending", "errors": []},
                "confirmation": {"status": "none", "summary": None},
            }
            persist_action_draft_business_update(
                ctx.db,
                row=existing,
                business_payload=business,
            )
            row = existing
    else:
        dor = _effective_draft_origin(
            incoming_explicit=draft_origin,
            previous=None,
        )
        merged_slots = merge_slots_payload(_empty_slots(), patch)
        _strip_backend_resolution_slots(merged_slots)
        stage = infer_stage_from_slots(merged_slots)
        business = {
            "intent_schema_version": "1",
            "draft_origin": dor,
            "stage": stage,
            "slots": merged_slots,
            "backend_validation": {"status": "pending", "errors": []},
            "confirmation": {"status": "none", "summary": None},
        }
        row = create_action_draft(
            ctx.db,
            conversation_id=conv_uid,
            client_id=client_uid,
            action_type="crypto_investment_intent",
            payload=business,
        )

    logger.info(
        "crypto_investment_intent_start conv=%s draft=%s stage=%s",
        ctx.conversation_id,
        row.id,
        stage,
    )
    return {
        "ok": True,
        "flow": "crypto_investment_intent",
        "action_draft_id": str(row.id),
        "stage": stage,
        "slots": merged_slots,
    }


__all__ = ["SPEC", "execute"]
