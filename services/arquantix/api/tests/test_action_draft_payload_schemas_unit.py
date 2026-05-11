"""Phase 3 — validation stricte ``action_draft_payload_schemas``."""

from __future__ import annotations

import pytest

from services.assistance.action_draft_contract import (
    CAL_CONTRACT_KEY,
    merge_business_payload_with_contract,
    parse_contract_from_payload,
)
from services.assistance.action_draft_payload_schemas import (
    InvalidActionDraftBusinessPayload,
    validate_action_draft_business_payload,
)


def _cb_source_list() -> dict:
    return {
        "target_kind": "crypto_buy",
        "target_id": "BTC",
        "stage": "source_list",
        "accounts_count": 2,
    }


def _cb_launch() -> dict:
    return {
        "target_kind": "crypto_buy",
        "target_id": "ETH",
        "stage": "awaiting_launch_confirm",
        "amount_from": 50.0,
        "currency_from": "EUR",
        "account_key": "fiat",
        "source_label": "Compte Euro",
    }


def _cb_confirmation() -> dict:
    return {
        "target_kind": "crypto_buy",
        "target_id": "BTC",
        "stage": "confirmation",
        "amount": 100.0,
        "amount_currency": "EUR",
        "account_key": "fiat",
        "intent_kind": "invest",
        "compact": False,
    }


class TestCryptoBuyAccepted:
    def test_source_list(self):
        out = validate_action_draft_business_payload("crypto_buy", _cb_source_list())
        assert out["target_id"] == "BTC"

    def test_awaiting_launch_confirm(self):
        out = validate_action_draft_business_payload("crypto_buy", _cb_launch())
        assert out["currency_from"] == "EUR"

    def test_confirmation_ok(self):
        out = validate_action_draft_business_payload("crypto_buy", _cb_confirmation())
        assert out["amount"] == 100.0


class TestCryptoBuyRejected:
    def test_confirmation_missing_amount(self):
        pl = dict(_cb_confirmation())
        del pl["amount"]
        with pytest.raises(InvalidActionDraftBusinessPayload) as ei:
            validate_action_draft_business_payload("crypto_buy", pl)
        assert "amount" in str(ei.value.errors).lower()

    def test_extra_forbidden_key(self):
        pl = dict(_cb_source_list())
        pl["__evil"] = {"x": 1}
        with pytest.raises(InvalidActionDraftBusinessPayload):
            validate_action_draft_business_payload("crypto_buy", pl)


class TestBundleInvest:
    def test_confirmation_valid(self):
        pl = {
            "target_kind": "bundle",
            "target_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
            "stage": "confirmation",
            "amount": 200.0,
            "amount_currency": "EUR",
            "account_key": "fiat",
            "intent_kind": "bundle_invest",
            "compact": True,
        }
        out = validate_action_draft_business_payload("bundle_invest", pl)
        assert out["target_id"] == "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

    def test_awaiting_launch_invalid_for_bundle(self):
        pl = {
            "target_kind": "bundle",
            "target_id": "TOP5",
            "stage": "awaiting_launch_confirm",
        }
        with pytest.raises(InvalidActionDraftBusinessPayload):
            validate_action_draft_business_payload("bundle_invest", pl)


class TestWidgets:
    def test_deposit_guide(self):
        pl = {
            "widget_kind": "deposit_channel_picker",
            "channels": ["deposit_virement", "deposit_carte"],
        }
        out = validate_action_draft_business_payload("deposit_guide", pl)
        assert len(out["channels"]) == 2

    def test_crypto_sell_guide(self):
        pl = {
            "widget_kind": "crypto_sell_cta",
            "symbol": "btc",
            "instrument_id": 42,
        }
        out = validate_action_draft_business_payload("crypto_sell_guide", pl)
        assert out["symbol"] == "BTC"

    def test_crypto_swap_guide_null_symbols(self):
        pl = {
            "widget_kind": "crypto_swap_guide",
            "from_symbol": None,
            "to_symbol": None,
        }
        out = validate_action_draft_business_payload("crypto_swap_guide", pl)
        assert out["from_symbol"] is None


def _ci_partial() -> dict:
        return {
            "intent_schema_version": "1",
            "draft_origin": "chat_free_text",
            "stage": "draft_pending_slots",
        "slots": {
            "target_asset": {
                "raw": "bitcoin",
                "raw_provenance": "llm_extracted",
                "confidence": 0.92,
            },
            "source_account": {},
            "amount": {},
        },
        "backend_validation": {"status": "pending", "errors": []},
        "confirmation": {"status": "none", "summary": None},
    }


class TestCryptoInvestmentIntentDraft:
    def test_pending_slots_ok(self):
        out = validate_action_draft_business_payload(
            "crypto_investment_intent",
            _ci_partial(),
        )
        assert out["stage"] == "draft_pending_slots"
        assert out["slots"]["target_asset"]["raw_provenance"] == "llm_extracted"

    def test_user_confirmation_requires_summary(self):
        pl = dict(_ci_partial())
        pl["stage"] = "draft_pending_user_confirmation"
        pl["backend_validation"] = {"status": "ok", "errors": []}
        pl["confirmation"] = {"status": "pending", "summary": None}
        with pytest.raises(InvalidActionDraftBusinessPayload):
            validate_action_draft_business_payload("crypto_investment_intent", pl)


class TestCalContractPreservedInMerge:
    def test_validate_then_merge_has_contract(self):
        biz = validate_action_draft_business_payload("crypto_buy", _cb_launch())
        full = merge_business_payload_with_contract(biz, action_type="crypto_buy")
        assert CAL_CONTRACT_KEY in full
        cc = parse_contract_from_payload(full)
        assert cc is not None
        assert cc.action_type == "crypto_buy"


class TestLegacyReadNoCrash:
    def test_validate_ignores_cal_contract_key_in_input(self):
        pl = _cb_source_list()
        pl[CAL_CONTRACT_KEY] = {"hack": True}
        out = validate_action_draft_business_payload("crypto_buy", pl)
        assert CAL_CONTRACT_KEY not in out
