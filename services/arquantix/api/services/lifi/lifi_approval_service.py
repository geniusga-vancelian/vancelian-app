"""Métadonnées approval ERC-20 pour swaps LI.FI."""
from __future__ import annotations

from typing import Any

from config.supported_swap_assets import EVM_NATIVE_TOKEN
from services.lifi.schemas import SwapTokenApprovalPayload

_ZERO_ADDRESS = EVM_NATIVE_TOKEN.lower()


def _normalize_address(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return text


def read_chain_ids_from_lifi_quote(lifi_quote_raw: Any) -> tuple[int | None, int | None]:
    if not isinstance(lifi_quote_raw, dict):
        return None, None
    action = lifi_quote_raw.get("action") or {}
    from_chain = _coerce_chain_id(action.get("fromChainId"))
    to_chain = _coerce_chain_id(action.get("toChainId"))
    return from_chain, to_chain


def resolve_lifi_status_bridge(
    *,
    lifi_tool: str | None,
    from_chain_id: int | None,
    to_chain_id: int | None,
) -> str | None:
    """Bridge param LI.FI /status — uniquement pour routes cross-chain."""
    if not lifi_tool:
        return None
    if from_chain_id is None or to_chain_id is None:
        return None
    if from_chain_id != to_chain_id:
        return lifi_tool.strip()
    tool = lifi_tool.strip().lower()
    if "bridge" in tool:
        return lifi_tool.strip()
    return None


def build_token_approval_payload(lifi_quote_raw: Any) -> SwapTokenApprovalPayload:
    if not isinstance(lifi_quote_raw, dict):
        return SwapTokenApprovalPayload(required=False)

    action = lifi_quote_raw.get("action") or {}
    estimate = lifi_quote_raw.get("estimate") or {}
    from_token = action.get("fromToken") if isinstance(action.get("fromToken"), dict) else {}

    token_address = _normalize_address(from_token.get("address"))
    if not token_address or token_address.lower() == _ZERO_ADDRESS:
        return SwapTokenApprovalPayload(required=False)

    spender_address = _normalize_address(estimate.get("approvalAddress"))
    amount_atomic = _normalize_amount_atomic(action.get("fromAmount"))
    if not spender_address or not amount_atomic:
        return SwapTokenApprovalPayload(required=False)

    return SwapTokenApprovalPayload(
        required=True,
        token_address=token_address,
        spender_address=spender_address,
        amount_atomic=amount_atomic,
    )


def _coerce_chain_id(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _normalize_amount_atomic(raw: Any) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text == "0":
        return None
    return text
