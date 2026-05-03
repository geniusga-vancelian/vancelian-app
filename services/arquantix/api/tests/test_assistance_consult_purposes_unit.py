"""Tests unitaires `consult_purposes` — whitelist Phase 2c.

Couvre :
  - `is_known_purpose`
  - `target_agent_for`
  - `validate_params` : params requis, enums, max_length, unknown_param
  - `build_question` : composition déterministe de la question naturelle
  - `list_known_purposes` : forme de la liste publique

Spec : `services/assistance/agents/tools/shared/consult_purposes.py`.
"""

from __future__ import annotations

import pytest

from services.assistance.agents.tools.shared import consult_purposes


class TestKnownPurposes:
    """`is_known_purpose` + `KNOWN_PURPOSES` : whitelist statique."""

    def test_all_5_purposes_listed_phase_2c(self):
        # Les 5 purposes initiaux validés dans l'archi Phase 2c.
        expected = {
            "explain_deposit_delay",
            "explain_withdrawal_delay",
            "explain_kyc_review_typical_delay",
            "explain_product_basics",
            "explain_swap_settlement_delay",
        }
        assert consult_purposes.KNOWN_PURPOSES == expected

    def test_is_known_purpose_true(self):
        assert consult_purposes.is_known_purpose("explain_deposit_delay") is True

    def test_is_known_purpose_false_for_random(self):
        assert consult_purposes.is_known_purpose("explain_market_outlook") is False

    def test_is_known_purpose_false_for_empty(self):
        assert consult_purposes.is_known_purpose("") is False
        assert consult_purposes.is_known_purpose(None) is False  # type: ignore[arg-type]


class TestTargetAgent:
    def test_target_agent_is_product_for_all(self):
        # Phase 2c : tous les purposes Phase 2c ciblent product.
        for name in consult_purposes.KNOWN_PURPOSES:
            assert consult_purposes.target_agent_for(name) == "product"

    def test_target_agent_none_for_unknown(self):
        assert consult_purposes.target_agent_for("explain_random") is None


class TestValidateParams:
    def test_explain_deposit_delay_requires_method(self):
        ok, errors, _ = consult_purposes.validate_params(
            "explain_deposit_delay", {}
        )
        assert ok is False
        assert "missing_required:method" in errors

    def test_explain_deposit_delay_method_enum_strict(self):
        ok, errors, _ = consult_purposes.validate_params(
            "explain_deposit_delay", {"method": "paypal"}
        )
        assert ok is False
        assert "bad_value:method" in errors

    def test_explain_deposit_delay_normalize_lower(self):
        ok, errors, normalized = consult_purposes.validate_params(
            "explain_deposit_delay",
            {"method": "BANK_TRANSFER_IN"},
        )
        assert ok is True
        assert errors == []
        assert normalized == {"method": "bank_transfer_in"}

    def test_explain_deposit_delay_optional_day(self):
        ok, errors, normalized = consult_purposes.validate_params(
            "explain_deposit_delay",
            {"method": "card", "day_of_week_made": "monday"},
        )
        assert ok is True
        assert normalized == {
            "method": "card",
            "day_of_week_made": "monday",
        }

    def test_explain_deposit_delay_unknown_param_rejected(self):
        ok, errors, _ = consult_purposes.validate_params(
            "explain_deposit_delay",
            {"method": "card", "amount": "1000"},
        )
        assert ok is False
        assert "unknown_param:amount" in errors

    def test_no_required_params_for_kyc(self):
        ok, errors, normalized = consult_purposes.validate_params(
            "explain_kyc_review_typical_delay", {}
        )
        assert ok is True
        assert errors == []
        assert normalized == {}

    def test_explain_product_basics_requires_slug(self):
        ok, errors, _ = consult_purposes.validate_params(
            "explain_product_basics", {}
        )
        assert ok is False
        assert "missing_required:slug" in errors

    def test_explain_product_basics_slug_enum(self):
        ok, errors, _ = consult_purposes.validate_params(
            "explain_product_basics", {"slug": "product_basics_unknown"}
        )
        assert ok is False
        assert "bad_value:slug" in errors

    def test_unknown_purpose(self):
        ok, errors, normalized = consult_purposes.validate_params(
            "explain_market_swing", {"foo": "bar"}
        )
        assert ok is False
        assert "unknown_purpose" in errors
        assert normalized == {}

    def test_bad_value_non_string(self):
        ok, errors, _ = consult_purposes.validate_params(
            "explain_deposit_delay", {"method": 42}
        )
        assert ok is False
        assert "bad_value:method" in errors


class TestBuildQuestion:
    def test_deposit_delay_includes_label(self):
        q = consult_purposes.build_question(
            "explain_deposit_delay", {"method": "bank_transfer_in"}
        )
        assert q is not None
        assert "virement SEPA entrant" in q

    def test_deposit_delay_with_day_hint(self):
        q = consult_purposes.build_question(
            "explain_deposit_delay",
            {"method": "card", "day_of_week_made": "saturday"},
        )
        assert q is not None
        assert "saturday" in q

    def test_withdrawal_delay_includes_label(self):
        q = consult_purposes.build_question(
            "explain_withdrawal_delay", {"method": "crypto_out"}
        )
        assert q is not None
        assert "crypto" in q

    def test_kyc_question_constant(self):
        q = consult_purposes.build_question(
            "explain_kyc_review_typical_delay", {}
        )
        assert q is not None
        assert "KYC" in q or "justificatif" in q

    def test_product_basics_uses_slug(self):
        q = consult_purposes.build_question(
            "explain_product_basics", {"slug": "product_basics_vault"}
        )
        assert q is not None
        assert "product_basics_vault" in q

    def test_unknown_purpose_returns_none(self):
        assert consult_purposes.build_question("nope", {}) is None


class TestListKnownPurposes:
    def test_list_includes_all_with_target_and_required(self):
        items = consult_purposes.list_known_purposes()
        assert len(items) == len(consult_purposes.KNOWN_PURPOSES)
        for it in items:
            assert "name" in it
            assert "target_agent" in it
            assert "description" in it
            assert "required_params" in it
            assert it["target_agent"] == "product"

    def test_required_params_correct(self):
        items = {it["name"]: it for it in consult_purposes.list_known_purposes()}
        assert items["explain_deposit_delay"]["required_params"] == ["method"]
        assert items["explain_withdrawal_delay"]["required_params"] == ["method"]
        assert items["explain_product_basics"]["required_params"] == ["slug"]
        assert items["explain_kyc_review_typical_delay"]["required_params"] == []
        assert items["explain_swap_settlement_delay"]["required_params"] == []
