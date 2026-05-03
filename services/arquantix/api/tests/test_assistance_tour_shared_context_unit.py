"""Tests unitaires `tour_shared_context` — Phase 2c.

Vérifie la **whitelist anti-tipping-off** appliquée aux résultats
de tools partagés entre sub-agents lors d'un handoff.

Spec : `services/assistance/agents/runtime/tour_shared_context.py`.
"""

from __future__ import annotations

import pytest

from services.assistance.agents.runtime import tour_shared_context as ctx_mod


class TestFilterToolResultForShare:
    def test_unknown_tool_returns_empty(self):
        assert (
            ctx_mod.filter_tool_result_for_share(
                tool_name="unknown_tool", result={"foo": "bar"}
            )
            == {}
        )

    def test_non_dict_result_returns_empty(self):
        assert (
            ctx_mod.filter_tool_result_for_share(
                tool_name="read_documents", result=None
            )
            == {}
        )
        assert (
            ctx_mod.filter_tool_result_for_share(
                tool_name="read_documents", result="bad"
            )
            == {}
        )

    def test_error_results_filtered_out(self):
        # Si le tool a échoué, on ne propage rien (le target retentera
        # s'il en a besoin).
        assert (
            ctx_mod.filter_tool_result_for_share(
                tool_name="read_documents",
                result={"error": "repo_unavailable"},
            )
            == {}
        )

    def test_read_documents_keeps_only_aggregates(self):
        result = {
            "total_count": 3,
            "by_type": {"id_proof": 1, "address_proof": 2},
            "by_status": {"approved": 2, "rejected": 1},
            "latest_uploaded_at": "2025-01-15T10:00:00",
            # Champ hypothétique non whitelisté → strippé
            "rejection_reason": "internal-aml-flag",
        }
        out = ctx_mod.filter_tool_result_for_share(
            tool_name="read_documents", result=result
        )
        assert "rejection_reason" not in out
        assert out["total_count"] == 3
        assert out["by_type"] == {"id_proof": 1, "address_proof": 2}
        assert out["by_status"] == {"approved": 2, "rejected": 1}

    def test_read_compliance_state_strips_safe_signals_block(self):
        # `safe_signals` est un bloc gated réservé au sub-agent
        # qui l'a lu : il ne DOIT PAS apparaître dans le contexte
        # partagé (`requires_doc_upload` = signal interne).
        result = {
            "status": {
                "client_status": "active",
                "kyc_status": "approved",
                "account_state": "ACTIVE",
                "login_frozen": False,
            },
            "safe_signals": {
                "requires_doc_upload": True,
                "requires_step_up": True,
                "client_facing_message": "secret",
            },
        }
        out = ctx_mod.filter_tool_result_for_share(
            tool_name="read_compliance_state", result=result
        )
        assert "safe_signals" not in out
        assert out["status"]["kyc_status"] == "approved"
        assert "requires_doc_upload" not in str(out)

    def test_read_external_aml_signals_yields_nothing(self):
        # Tout le payload AML est gated → on partage RIEN.
        result = {
            "kyc_provider": "mock",
            "kyc_status": "approved",
            "watchlist_status": "approved",
            "flags": ["doc_quality_low"],
            "client_facing_message": None,
        }
        assert (
            ctx_mod.filter_tool_result_for_share(
                tool_name="read_external_aml_signals", result=result
            )
            == {}
        )

    def test_diagnose_keeps_topic_drops_triggers(self):
        result = {
            "dominant_topic": "remediation",
            "confidence": 0.8,
            "secondary_topics": [],
            "context_for_llm": {"orders_count": 0},
            "triggers_used": ["requires_doc_upload=true"],
            "next_recommended_action": {
                "kind": "view_account_info",
                "label": "Voir mes informations",
                "deep_link": "vancelian://app/profile/account",
            },
        }
        out = ctx_mod.filter_tool_result_for_share(
            tool_name="diagnose_compliance_topic", result=result
        )
        assert "triggers_used" not in out
        assert out["dominant_topic"] == "remediation"
        assert "context_for_llm" in out
        assert out["next_recommended_action"]["kind"] == "view_account_info"


class TestAggregateAndFormat:
    def test_aggregate_dedupes_last_wins(self):
        history = [
            ("read_documents", {"total_count": 1, "by_status": {}}),
            ("read_documents", {"total_count": 2, "by_status": {"approved": 2}}),
        ]
        out = ctx_mod.aggregate_tour_context(history)
        assert out["read_documents"]["total_count"] == 2

    def test_aggregate_filters_empty(self):
        history = [
            ("unknown_tool", {"data": "leaks"}),
            ("read_external_aml_signals", {"flags": ["x"]}),
        ]
        assert ctx_mod.aggregate_tour_context(history) == {}

    def test_format_for_prompt_empty_returns_empty_string(self):
        assert ctx_mod.format_for_prompt({}) == ""

    def test_format_for_prompt_has_markdown_header_and_json(self):
        block = ctx_mod.format_for_prompt(
            {
                "read_documents": {"total_count": 3, "by_status": {"approved": 3}}
            }
        )
        assert "## Données déjà collectées" in block
        assert "```json" in block
        assert '"total_count": 3' in block
