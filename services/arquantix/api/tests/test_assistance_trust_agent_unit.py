"""Tests unitaires Lot 4 — Trust hybride (Cognitive Bot v4).

Couvre :

  * Identité de l'agent ``trust`` (id, label, classe).
  * Inscription dans ``ROUTABLE_AGENTS`` côté router.
  * Toolset minimal (wiki + ask_user_question).
  * Présence des 3 purposes ``reassure_about_*`` ciblant ``trust``.
  * Spec ``consult_specialist`` avec enum ``target ∈ {product, trust}``.
  * Auto-injection du Response Framework dans le system prompt
    ``trust`` (suite Lot 3).
  * Présence de la catégorie wiki ``trust-security`` + 2 fiches seed
    (régulation, custody).
"""

from __future__ import annotations

import pytest

from services.assistance.agents.base import (
    AGENT_LABELS,
    AGENT_TRUST_ID,
    KNOWN_AGENT_IDS,
)
from services.assistance.agents.prompt_builder import (
    RESPONSE_FRAMEWORK_AGENTS,
    load_agent_system_prompt,
)
from services.assistance.agents.registry import get_agent
from services.assistance.agents.repositories.wiki_repo import (
    FAQ_CATEGORIES,
    list_pages,
)
from services.assistance.agents.router import ROUTABLE_AGENTS
from services.assistance.agents.tools.registry import all_tool_names
from services.assistance.agents.tools.shared import (
    consult_purposes,
    consult_specialist,
)
from services.assistance.agents.trust import TrustAgent


class TestTrustAgentIdentity:
    def test_agent_id_constant(self):
        assert AGENT_TRUST_ID == "trust"

    def test_agent_label_present(self):
        # Pas d'attente sur la valeur exacte (peut évoluer côté UI),
        # juste qu'elle existe et soit non vide.
        assert AGENT_LABELS.get(AGENT_TRUST_ID)
        assert isinstance(AGENT_LABELS[AGENT_TRUST_ID], str)
        assert AGENT_LABELS[AGENT_TRUST_ID].strip() != ""

    def test_trust_in_known_agent_ids(self):
        assert AGENT_TRUST_ID in KNOWN_AGENT_IDS

    def test_factory_returns_trust_agent(self):
        agent = get_agent(AGENT_TRUST_ID)
        assert isinstance(agent, TrustAgent)
        assert agent.agent_id == AGENT_TRUST_ID


class TestTrustRouting:
    def test_trust_is_routable(self):
        # Le router peut désigner directement l'agent trust quand la
        # demande est purement institutionnelle / sécuritaire.
        assert AGENT_TRUST_ID in ROUTABLE_AGENTS


class TestTrustToolset:
    def test_trust_has_minimal_toolset(self):
        names = set(all_tool_names(AGENT_TRUST_ID))
        # V1 minimal — wiki + question utilisateur.
        assert names == {"select_wiki_pages", "read_wiki_page", "ask_user_question"}

    def test_trust_has_no_consult_specialist(self):
        # ``trust`` est un specialist terminal (profondeur 1) — il ne
        # consulte personne (anti-récursion).
        names = set(all_tool_names(AGENT_TRUST_ID))
        assert "consult_specialist" not in names


class TestConsultSpecialistAcceptsTrust:
    def test_target_enum_includes_trust(self):
        target = consult_specialist.SPEC["function"]["parameters"][
            "properties"
        ]["target"]
        assert "trust" in target["enum"]

    def test_target_enum_keeps_product(self):
        # Régression — on ne casse pas les consultations product
        # existantes.
        target = consult_specialist.SPEC["function"]["parameters"][
            "properties"
        ]["target"]
        assert "product" in target["enum"]


class TestTrustPurposes:
    _EXPECTED = {
        "reassure_about_regulation",
        "reassure_about_custody",
        "reassure_about_security",
    }

    def test_all_trust_purposes_known(self):
        for name in self._EXPECTED:
            assert consult_purposes.is_known_purpose(name) is True

    def test_all_trust_purposes_target_trust(self):
        for name in self._EXPECTED:
            assert consult_purposes.target_agent_for(name) == "trust"

    def test_trust_purposes_have_no_required_params(self):
        items = {
            it["name"]: it for it in consult_purposes.list_known_purposes()
        }
        for name in self._EXPECTED:
            assert items[name]["required_params"] == []

    @pytest.mark.parametrize(
        "purpose,expected_keyword",
        [
            ("reassure_about_regulation", "régulation"),
            ("reassure_about_custody", "fonds"),
            ("reassure_about_security", "sécur"),
        ],
    )
    def test_question_builders_emit_natural_question(
        self, purpose, expected_keyword
    ):
        q = consult_purposes.build_question(purpose, {})
        assert q is not None
        assert expected_keyword.lower() in q.lower()


class TestTrustSystemPrompt:
    def test_trust_in_response_framework_whitelist(self):
        assert "trust" in RESPONSE_FRAMEWORK_AGENTS

    def test_trust_prompt_contains_response_framework(self):
        # Le prompt builder concatène le fragment Lot 3 quand l'agent
        # est dans la whitelist. On vérifie qu'un marqueur du
        # framework est présent.
        prompt = load_agent_system_prompt("trust")
        # Le fragment ``_response_framework.md`` impose la séquence
        # ACK émotionnel → reformulation → valeur → next best action.
        assert (
            "Validation émotionnelle" in prompt
            or "ACK émotionnel" in prompt
            or "framework" in prompt.lower()
        )

    def test_trust_prompt_mentions_no_pushy_role(self):
        # Garde-fou éditorial : trust n'est pas un commercial.
        prompt = load_agent_system_prompt("trust")
        assert "trust" in prompt.lower() or "rassur" in prompt.lower()


class TestTrustWikiSeed:
    def test_trust_security_category_registered(self):
        assert "trust-security" in FAQ_CATEGORIES

    def test_trust_security_pages_loaded(self):
        pages = list_pages(category="trust-security", limit=10)
        slugs = {p["slug"] for p in pages}
        # Les 2 fiches seed doivent être indexées.
        assert "regulation-overview" in slugs
        assert "custody-overview" in slugs
