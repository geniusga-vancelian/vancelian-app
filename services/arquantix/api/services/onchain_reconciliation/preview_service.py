"""Previews de correction (Phase 5A/5B)."""
from __future__ import annotations

from typing import Any

from .correction_policy import APPLY_WHITELIST_ACTIONS
from .discrepancy_models import ReconciliationDiscrepancy

PREVIEW_ACTIONS = frozenset(
    {
        "link_raw_event_to_existing_ledger_entry",
        "create_missing_deposit_from_raw_event",
        "link_deposit_to_raw_event",
        "mark_admin_sim_as_phantom_candidate",
        "mark_swap_settlement_missing_actual_amount",
        "mark_onchain_event_missing_ledger_entry",
    }
)

_TYPE_TO_DEFAULT_ACTION: dict[str, str] = {
    "admin_sim_deposit": "mark_admin_sim_as_phantom_candidate",
    "swap_confirmed_without_settlement": "mark_swap_settlement_missing_actual_amount",
    "onchain_event_without_db_ledger": "create_missing_deposit_from_raw_event",
    "db_ledger_without_onchain_proof": "link_raw_event_to_existing_ledger_entry",
    "no_matching_raw_onchain_event": "link_raw_event_to_existing_ledger_entry",
    "balance_ledger_vs_onchain": "create_missing_deposit_from_raw_event",
}

_ACTION_META: dict[str, dict[str, Any]] = {
    "link_raw_event_to_existing_ledger_entry": {
        "risk_level": "low",
        "requires_second_approval": False,
    },
    "create_missing_deposit_from_raw_event": {
        "risk_level": "high",
        "requires_second_approval": True,
    },
    "mark_admin_sim_as_phantom_candidate": {
        "risk_level": "high",
        "requires_second_approval": True,
    },
    "mark_swap_settlement_missing_actual_amount": {
        "risk_level": "high",
        "requires_second_approval": True,
    },
    "mark_onchain_event_missing_ledger_entry": {
        "risk_level": "medium",
        "requires_second_approval": True,
    },
}


def resolve_preview_action(
    discrepancy: ReconciliationDiscrepancy,
    *,
    explicit_action: str | None = None,
) -> str:
    if explicit_action:
        normalized = explicit_action.strip().lower()
        aliases = {
            "link_deposit_to_raw_event": "link_raw_event_to_existing_ledger_entry",
            "mark_onchain_event_missing_ledger_entry": "create_missing_deposit_from_raw_event",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized not in PREVIEW_ACTIONS:
            raise ValueError(f"Action preview inconnue: {explicit_action}")
        return normalized
    default = _TYPE_TO_DEFAULT_ACTION.get(discrepancy.discrepancy_type.strip().lower())
    if default:
        return default
    raise ValueError(
        f"Aucune action preview par défaut pour discrepancy_type={discrepancy.discrepancy_type}",
    )


def build_correction_preview(
    discrepancy: ReconciliationDiscrepancy,
    *,
    action: str,
    raw_event: dict[str, Any] | None = None,
    allowed_to_apply: bool | None = None,
) -> dict[str, Any]:
    meta = discrepancy.metadata_json if isinstance(discrepancy.metadata_json, dict) else {}
    before = {
        "discrepancy_id": str(discrepancy.id),
        "person_id": str(discrepancy.person_id),
        "status": discrepancy.status,
        "discrepancy_type": discrepancy.discrepancy_type,
        "layer": discrepancy.layer,
        "asset": discrepancy.asset,
        "reference_type": discrepancy.reference_type,
        "reference_id": discrepancy.reference_id,
        "metadata_json": meta,
    }

    after: dict[str, Any] = {
        "phase": "5B_preview",
        "proposed_action": action,
    }

    if action == "link_raw_event_to_existing_ledger_entry":
        after["note"] = "Metadata only — aucun changement de montant."
    elif action == "create_missing_deposit_from_raw_event":
        after["note"] = (
            "Créera un person_wallet_deposits idempotent + crédit balance via repository ledger."
        )
        after["raw_event"] = raw_event
    elif action == "mark_admin_sim_as_phantom_candidate":
        after["phantom_candidate"] = True
    elif action == "mark_swap_settlement_missing_actual_amount":
        after["settlement_state"] = "blocked_missing_actual_amount"

    action_meta = _ACTION_META.get(action, {"risk_level": "medium", "requires_second_approval": True})
    if allowed_to_apply is None:
        allowed_to_apply = action in APPLY_WHITELIST_ACTIONS and raw_event is not None

    return {
        "action": action,
        "before_json": before,
        "after_json": after,
        "risk_level": action_meta["risk_level"],
        "requires_second_approval": bool(action_meta["requires_second_approval"]),
        "allowed_to_apply": bool(allowed_to_apply),
        "dry_run": True,
    }
