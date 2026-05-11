"""Phase 3.5 — registre produit ``action_registry``."""

from __future__ import annotations

import pytest

from services.assistance.action_draft_payload_schemas import (
    InvalidActionDraftBusinessPayload,
    assert_payload_models_synced_with_registry,
    validate_action_draft_business_payload,
)
from services.assistance.action_registry import (
    PLANNED_ACTION_TYPES,
    get_action_definition,
    ttl_seconds_for_action,
)


class TestRegistryFoundation:
    def test_models_sync_registry(self):
        assert_payload_models_synced_with_registry()

    def test_crypto_buy_definition(self):
        d = get_action_definition("crypto_buy")
        assert d.label
        assert "awaiting_launch_confirm" in d.allowed_stages
        assert d.requires_confirmation is True
        assert d.ttl_seconds == 900
        assert d.allowed_payload_schema == "CryptoBuyBusinessPayload"

    def test_bundle_no_awaiting_stage(self):
        d = get_action_definition("bundle_invest")
        assert "awaiting_launch_confirm" not in d.allowed_stages
        assert "source_list" in d.allowed_stages

    def test_ttl_helper(self):
        assert ttl_seconds_for_action("deposit_guide") == 900

    def test_planned_placeholder_tuple(self):
        assert "kyc_resume" in PLANNED_ACTION_TYPES


class TestRegistryEnforcedInValidator:
    def test_invalid_stage_bundle(self):
        pl = {
            "target_kind": "bundle",
            "target_id": "x",
            "stage": "awaiting_launch_confirm",
            "amount_from": 10,
            "currency_from": "EUR",
            "account_key": "k",
            "source_label": "l",
        }
        with pytest.raises(InvalidActionDraftBusinessPayload) as ei:
            validate_action_draft_business_payload("bundle_invest", pl)
        assert "stage" in str(ei.value.errors).lower()

    def test_widget_with_stage_key_rejected(self):
        pl = {
            "widget_kind": "deposit_channel_picker",
            "channels": ["a"],
            "stage": "nope",
        }
        with pytest.raises(InvalidActionDraftBusinessPayload) as ei:
            validate_action_draft_business_payload("deposit_guide", pl)
        assert "interdit" in str(ei.value.errors).lower()

    def test_widget_kind_mismatch(self):
        pl = {
            "widget_kind": "wrong_kind",
            "symbol": "BTC",
            "instrument_id": 1,
        }
        with pytest.raises(InvalidActionDraftBusinessPayload) as ei:
            validate_action_draft_business_payload("crypto_sell_guide", pl)
        assert "widget_kind" in str(ei.value.errors).lower()
