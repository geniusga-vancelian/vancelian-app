"""Tests unitaires — ``action_draft_contract`` (enveloppe ``cal_contract``)."""

from __future__ import annotations

from services.assistance.action_draft_contract import (
    CAL_CONTRACT_KEY,
    merge_business_payload_with_contract,
    parse_contract_from_payload,
)


class TestMergeCalContract:
    def test_crypto_buy_launch_confirm_contract_ok(self):
        biz = {
            "target_kind": "crypto_buy",
            "target_id": "BTC",
            "amount_from": 120.0,
            "currency_from": "EUR",
            "stage": "awaiting_launch_confirm",
        }
        full = merge_business_payload_with_contract(biz, action_type="crypto_buy")
        assert CAL_CONTRACT_KEY in full
        assert full["amount_from"] == 120.0
        cc = full[CAL_CONTRACT_KEY]
        assert cc["action_type"] == "crypto_buy"
        assert cc["action_version"] == "1"
        assert cc["missing_params"] == []
        assert cc["validation_status"] == "ok"
        assert cc["confirmation_status"] == "pending"
        assert cc["security_level"] == "L1"
        assert cc["expires_at"]

    def test_confirmation_with_amount_fields(self):
        biz = {
            "target_kind": "bundle",
            "target_id": "TOP5",
            "stage": "confirmation",
            "amount": 250.0,
            "amount_currency": "EUR",
            "account_key": "main",
        }
        full = merge_business_payload_with_contract(biz, action_type="bundle_invest")
        cc = full[CAL_CONTRACT_KEY]
        assert "amount" in cc["collected_params"]
        assert cc["missing_params"] == []
        assert cc["validation_status"] == "ok"
        assert cc["security_level"] == "L2"

    def test_parse_roundtrip(self):
        full = merge_business_payload_with_contract(
            {"stage": "source_list", "target_kind": "crypto_buy", "target_id": "ETH"},
            action_type="crypto_buy",
        )
        parsed = parse_contract_from_payload(full)
        assert parsed is not None
        assert parsed.state == "source_list"


class TestCryptoInvestmentIntentContract:
    def test_cal_contract_collecting_phase(self):
        biz = {
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
        full = merge_business_payload_with_contract(
            biz,
            action_type="crypto_investment_intent",
        )
        cc = parse_contract_from_payload(full)
        assert cc is not None
        assert cc.validation_status == "ok"
        assert cc.confirmation_status == "none"
        assert cc.action_type == "crypto_investment_intent"
