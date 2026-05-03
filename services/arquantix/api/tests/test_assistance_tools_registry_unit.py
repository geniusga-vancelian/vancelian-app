"""Tests unitaires du registry des tools — Phase 2a + Phase 2b.

Couvre `services.assistance.agents.tools.registry` :
  - `tools_for(agent_id)` retourne la liste correcte par agent.
  - `find(agent_id, name)` résout en O(n) avec None si introuvable.
  - `all_tool_names(agent_id)` aligne les noms canoniques aux SPEC.
  - Tous les agents Phase 2a ont au moins `ask_user_question`.
  - **Phase 2b** : `compliance` top-level n'expose plus que
    `diagnose_compliance_topic` + `ask_user_question` (entry-point
    dispatcher). Les 5 tools L0 read-only sont sur les sub-agents
    `compliance.<topic>`.
  - **Phase 2b** : `compliance_subagent_id(topic)` mappe correctement.

Spec de référence : `MULTI_AGENTS_RUNTIME.md` § 2.4 et
`COMPLIANCE_TOPICS.md` § 1, § 3.
"""

from __future__ import annotations

import pytest

from services.assistance.agents.tools import registry
from services.assistance.agents.tools.shared import ask_user_question


class TestToolsFor:
    def test_compliance_top_level_is_dispatcher(self):
        # Phase 2b : entry-point compliance ne contient plus que
        # `diagnose_compliance_topic` + `ask_user_question`.
        names = registry.all_tool_names("compliance")
        assert "diagnose_compliance_topic" in names
        assert "ask_user_question" in names
        assert "read_compliance_state" not in names  # déplacé sub-agents

    def test_compliance_general_has_all_phase2a_tools(self):
        # Le sub-agent fallback récupère le scope Phase 2a complet.
        names = registry.all_tool_names("compliance.general")
        assert "read_compliance_state" in names
        assert "read_registration_progress" in names
        assert "read_documents" in names
        assert "read_transactions" in names
        assert "read_external_aml_signals" in names
        assert "ask_user_question" in names

    def test_compliance_registration_includes_propose_resume(self):
        names = registry.all_tool_names("compliance.registration")
        assert "propose_resume_registration" in names
        # Tools de base toujours là.
        assert "read_compliance_state" in names
        assert "read_registration_progress" in names

    def test_compliance_transactional_includes_read_transaction_detail(self):
        names = registry.all_tool_names("compliance.transactional")
        assert "read_transaction_detail" in names
        assert "read_transactions" in names

    def test_compliance_remediation_has_doc_signals(self):
        names = registry.all_tool_names("compliance.remediation")
        assert "read_documents" in names
        assert "read_external_aml_signals" in names

    @pytest.mark.parametrize(
        "agent_id", ["advisor", "product", "market", "default"]
    )
    def test_other_agents_have_at_least_ask_user_question(self, agent_id):
        names = registry.all_tool_names(agent_id)
        assert "ask_user_question" in names

    def test_unknown_agent_returns_empty(self):
        assert registry.tools_for("nonexistent") == []
        assert registry.all_tool_names("nonexistent") == []

    def test_returns_list_copies_for_safety(self):
        a = registry.tools_for("compliance.general")
        b = registry.tools_for("compliance.general")
        a.append("hack")
        assert b == registry.tools_for("compliance.general")
        assert "hack" not in [m for m in b]

    def test_subagents_cant_call_diagnose(self):
        """Anti-boucle : les sub-agents `compliance.*` n'ont PAS accès au
        dispatcher `diagnose_compliance_topic` (sinon récursion infinie).
        """
        for sub in (
            "compliance.registration",
            "compliance.remediation",
            "compliance.transactional",
            "compliance.general",
        ):
            names = registry.all_tool_names(sub)
            assert "diagnose_compliance_topic" not in names, (
                f"{sub} ne doit pas avoir diagnose_compliance_topic "
                f"dans son catalogue (anti-boucle)."
            )


class TestComplianceSubagentMapping:
    @pytest.mark.parametrize(
        "topic,expected",
        [
            ("registration", "compliance.registration"),
            ("remediation", "compliance.remediation"),
            ("transactional", "compliance.transactional"),
            ("general", "compliance.general"),
        ],
    )
    def test_known_topics(self, topic, expected):
        assert registry.compliance_subagent_id(topic) == expected

    @pytest.mark.parametrize(
        "topic", ["unknown", "", "REGISTRATION", "  ", None]
    )
    def test_unknown_topics_fallback_to_general(self, topic):
        # Tous les inputs douteux retombent sur `compliance.general`.
        assert registry.compliance_subagent_id(topic) == "compliance.general"


class TestFind:
    def test_finds_known_tool_in_subagent(self):
        mod = registry.find("compliance.general", "read_compliance_state")
        assert mod is not None
        assert mod.SPEC["function"]["name"] == "read_compliance_state"
        assert mod.SPEC["autonomy_level"] == "L0"

    def test_finds_diagnose_tool_only_at_top_level(self):
        # Top-level oui.
        assert registry.find("compliance", "diagnose_compliance_topic") is not None
        # Sub-agents non.
        assert (
            registry.find(
                "compliance.registration", "diagnose_compliance_topic"
            )
            is None
        )

    def test_returns_none_for_unknown_tool(self):
        assert registry.find("compliance.general", "nonexistent_tool") is None

    def test_returns_none_for_unknown_agent(self):
        assert registry.find("nonexistent", "read_compliance_state") is None

    def test_returns_none_for_empty_name(self):
        assert registry.find("compliance.general", "") is None

    def test_ask_user_question_resolvable_for_all_agents(self):
        for agent_id in (
            "compliance",
            "compliance.registration",
            "compliance.remediation",
            "compliance.transactional",
            "compliance.general",
            "advisor",
            "product",
            "market",
            "default",
        ):
            mod = registry.find(agent_id, "ask_user_question")
            assert mod is ask_user_question


class TestSpecIntegrity:
    """Tous les tools enregistrés ont une SPEC OpenAI + métadonnées valides."""

    def test_all_specs_have_required_keys(self):
        for agent_id, modules in registry.TOOLS_BY_AGENT.items():
            for mod in modules:
                spec = mod.SPEC
                assert spec.get("type") == "function", (
                    f"agent={agent_id} tool sans type=function : {spec}"
                )
                fn = spec.get("function") or {}
                assert isinstance(fn.get("name"), str) and fn["name"], (
                    f"agent={agent_id} fn sans name : {spec}"
                )
                assert isinstance(fn.get("description"), str), (
                    f"agent={agent_id} fn={fn['name']} sans description"
                )
                assert "parameters" in fn

    def test_all_compliance_tools_are_l0(self):
        for sub in (
            "compliance",
            "compliance.registration",
            "compliance.remediation",
            "compliance.transactional",
            "compliance.general",
        ):
            for mod in registry.TOOLS_BY_AGENT[sub]:
                level = mod.SPEC.get("autonomy_level")
                assert level == "L0", (
                    f"Phase 2a/2b interdit > L0, trouvé {level} pour "
                    f"agent={sub} tool={mod.SPEC['function']['name']}"
                )

    def test_no_l1_or_higher_in_phase2b(self):
        for agent_id, modules in registry.TOOLS_BY_AGENT.items():
            for mod in modules:
                level = mod.SPEC.get("autonomy_level", "L0")
                assert level in {"L0"}, (
                    f"Phase 2a/2b doit être 100% L0, agent={agent_id} "
                    f"tool={mod.SPEC['function']['name']} level={level}"
                )
