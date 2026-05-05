"""Tests Lot 7 — Client Discovery Engine (extraction multi-projet).

Couvre :

  * Détection de label projet (FR + EN).
  * Extraction horizon (avec préfixe / bare / unités mois→years).
  * Extraction montants (k/M, EUR/USD).
  * Extraction recurring/liquidity/risk via keywords.
  * Règles d'attribution : co-mention / question ciblée bot / floating.
  * **Anti-bug critique** : « 4 ans » dit après projet maison sans
    co-mention ne s'attribue PAS automatiquement à maison.
  * Switch detection.
  * LLM gating decision.
  * Rendu prompt.
"""

from __future__ import annotations

import pytest

from services.assistance.agents.client_discovery import (
    FLOATING_STATUS_PENDING,
    PARAMETER_KIND_HORIZON_YEARS,
    PARAMETER_KIND_RECURRING_FREQUENCY,
    PARAMETER_KIND_RISK_APPETITE,
    PROJECT_LABEL_HOUSE,
    PROJECT_LABEL_RETIREMENT,
    PROJECT_LABEL_TRAVEL,
    PROJECT_STATUS_ACTIVE,
    ClientProject,
    ClientProjectParameters,
    DiscoveryExtraction,
    detect_project_label_from_message,
    detect_project_switch_signal,
    detect_targeted_project_in_assistant_question,
    extract_discovery_keyword_pass,
    render_discovery_for_prompt,
    should_invoke_llm_extractor,
)


# ─── 1. Detection de label projet ──────────────────────────────────────────


class TestDetectProjectLabel:
    def test_house_fr(self):
        assert (
            detect_project_label_from_message(
                "j'aimerais acheter une maison"
            )
            == PROJECT_LABEL_HOUSE
        )

    def test_house_en(self):
        assert (
            detect_project_label_from_message("I want to buy a house")
            == PROJECT_LABEL_HOUSE
        )

    def test_retirement(self):
        assert (
            detect_project_label_from_message(
                "préparer ma retraite tranquillement"
            )
            == PROJECT_LABEL_RETIREMENT
        )

    def test_travel(self):
        assert (
            detect_project_label_from_message("partir en vacances")
            == PROJECT_LABEL_TRAVEL
        )

    def test_no_match(self):
        assert (
            detect_project_label_from_message(
                "explique-moi le marché crypto"
            )
            is None
        )

    def test_empty(self):
        assert detect_project_label_from_message("") is None
        assert detect_project_label_from_message("   ") is None


# ─── 2. Extraction horizon ─────────────────────────────────────────────────


class TestHorizonExtraction:
    def test_horizon_dans_4_ans_attribued_to_house(self):
        ext = extract_discovery_keyword_pass(
            user_message="j'aimerais acheter une maison dans 4 ans",
            current_turn=1,
        )
        assert len(ext.new_or_updated_projects) == 1
        proj = ext.new_or_updated_projects[0]
        assert proj.label == PROJECT_LABEL_HOUSE
        assert proj.parameters.horizon_years == 4.0

    def test_horizon_in_months_converts_to_years(self):
        ext = extract_discovery_keyword_pass(
            user_message="acheter une voiture en 18 mois",
            current_turn=1,
        )
        assert len(ext.new_or_updated_projects) == 1
        assert ext.new_or_updated_projects[0].parameters.horizon_years == 1.5

    def test_horizon_bare_only_with_targeted_question(self):
        # "4 ans" SEUL ne doit PAS être extrait sans question ciblée
        ext = extract_discovery_keyword_pass(
            user_message="4 ans",
            last_assistant_text="Tu préfères quel rythme ?",
            current_turn=1,
        )
        assert ext.new_or_updated_projects == []
        # Même pas en floating (le matcher bare est désactivé sans question)
        assert ext.floating_parameters == []

    def test_horizon_bare_with_targeted_question_attributes_to_targeted_project(self):
        # "4 ans" + question ciblée "pour ton projet maison" → attribution
        # à maison, MÊME SI le user n'a pas dit "maison".
        ext = extract_discovery_keyword_pass(
            user_message="4 ans",
            last_assistant_text="Sur quel horizon pour ton projet maison ?",
            current_turn=2,
        )
        assert len(ext.new_or_updated_projects) == 1
        proj = ext.new_or_updated_projects[0]
        assert proj.label == PROJECT_LABEL_HOUSE
        assert proj.parameters.horizon_years == 4.0


# ─── 3. ANTI-BUG CRITIQUE — pas d'attribution croisée ─────────────────────


class TestAntiCrossProjectAttribution:
    """Le bug à éviter : user dit « 4 ans » à un tour donné sans nommer
    de projet et sans question ciblée → on NE DOIT PAS attribuer à un
    projet existant (ex. maison) par proximité temporelle.
    """

    def test_horizon_alone_without_target_goes_to_floating(self):
        ext = extract_discovery_keyword_pass(
            user_message="dans 4 ans",
            last_assistant_text="Continue, je t'écoute.",  # pas de targeting
            current_turn=3,
        )
        assert ext.new_or_updated_projects == []
        assert len(ext.floating_parameters) == 1
        fp = ext.floating_parameters[0]
        assert fp.parameter_kind == PARAMETER_KIND_HORIZON_YEARS
        assert fp.parameter_value == {"value": 4.0}
        assert fp.status == FLOATING_STATUS_PENDING

    def test_amount_alone_without_target_goes_to_floating(self):
        ext = extract_discovery_keyword_pass(
            user_message="200000 euros",
            current_turn=4,
        )
        assert ext.new_or_updated_projects == []
        assert len(ext.floating_parameters) == 1
        fp = ext.floating_parameters[0]
        assert fp.parameter_value["value"] == 200000.0

    def test_user_switches_to_vacances_after_house_horizon_does_not_carry(self):
        # Simulation du cas du user dans la conversation :
        #   tour A : "j'aimerais acheter une maison dans 4 ans" → maison/4y
        #   tour B : "et pour les vacances ?" → ne doit PAS hériter de 4y
        ext_b = extract_discovery_keyword_pass(
            user_message="et pour les vacances ?",
            last_assistant_text="OK on note 4 ans pour la maison.",
            current_turn=2,
        )
        # Vacances détecté MAIS aucun horizon dans ce message
        assert len(ext_b.new_or_updated_projects) == 1
        proj = ext_b.new_or_updated_projects[0]
        assert proj.label == PROJECT_LABEL_TRAVEL
        # Pas d'horizon hérité
        assert proj.parameters.horizon_years is None


# ─── 4. Extraction de montants ────────────────────────────────────────────


class TestAmountExtraction:
    def test_simple_amount(self):
        ext = extract_discovery_keyword_pass(
            user_message="acheter une maison à 300000 EUR",
            current_turn=1,
        )
        proj = ext.new_or_updated_projects[0]
        assert proj.parameters.target_amount == 300000.0
        assert proj.parameters.target_currency == "EUR"

    def test_k_suffix(self):
        ext = extract_discovery_keyword_pass(
            user_message="ma retraite avec 500k euros",
            current_turn=1,
        )
        proj = ext.new_or_updated_projects[0]
        assert proj.parameters.target_amount == 500000.0

    def test_two_amounts_largest_is_target(self):
        ext = extract_discovery_keyword_pass(
            user_message=(
                "acheter une maison de 400000 EUR avec un apport "
                "de 80000 EUR"
            ),
            current_turn=1,
        )
        proj = ext.new_or_updated_projects[0]
        assert proj.parameters.target_amount == 400000.0
        assert proj.parameters.initial_amount == 80000.0


# ─── 5. Recurring / liquidity / risk ──────────────────────────────────────


class TestRecurringLiquidityRisk:
    def test_recurring_monthly(self):
        ext = extract_discovery_keyword_pass(
            user_message="préparer ma retraite tous les mois",
            current_turn=1,
        )
        proj = ext.new_or_updated_projects[0]
        assert proj.parameters.recurring_frequency == "monthly"

    def test_liquidity_high(self):
        ext = extract_discovery_keyword_pass(
            user_message="acheter une maison avec besoin de liquidité",
            current_turn=1,
        )
        proj = ext.new_or_updated_projects[0]
        assert proj.parameters.liquidity_need == "high"

    def test_risk_low(self):
        ext = extract_discovery_keyword_pass(
            user_message=(
                "préparer ma retraite, je suis très prudent"
            ),
            current_turn=1,
        )
        proj = ext.new_or_updated_projects[0]
        assert proj.parameters.risk_appetite == "very_low"

    def test_floating_when_no_project(self):
        ext = extract_discovery_keyword_pass(
            user_message="je voudrais que ça soit dynamique chaque mois",
            current_turn=1,
        )
        kinds = {fp.parameter_kind for fp in ext.floating_parameters}
        assert PARAMETER_KIND_RECURRING_FREQUENCY in kinds
        assert PARAMETER_KIND_RISK_APPETITE in kinds


# ─── 6. Bot question targeting ────────────────────────────────────────────


class TestTargetedQuestion:
    def test_detect_house_in_question(self):
        assert (
            detect_targeted_project_in_assistant_question(
                "Sur quel horizon pour ton projet maison ?"
            )
            == PROJECT_LABEL_HOUSE
        )

    def test_no_match_generic_question(self):
        assert (
            detect_targeted_project_in_assistant_question(
                "Sur quel horizon ?"
            )
            is None
        )

    def test_concerning_voiture(self):
        assert (
            detect_targeted_project_in_assistant_question(
                "concernant ta voiture, c'est combien ?"
            )
            is not None
        )


# ─── 7. Switch detection ──────────────────────────────────────────────────


class TestSwitch:
    def test_explicit_switch_signal(self):
        assert detect_project_switch_signal("ok parlons d'autre chose")
        assert detect_project_switch_signal("autre projet maintenant")
        assert detect_project_switch_signal("oublions ça")

    def test_no_switch(self):
        assert not detect_project_switch_signal(
            "j'aimerais acheter une maison"
        )


# ─── 8. LLM gating ────────────────────────────────────────────────────────


class TestLLMGating:
    def test_llm_called_when_floating_pending(self):
        empty_ext = DiscoveryExtraction()
        assert should_invoke_llm_extractor(
            keyword_extraction=empty_ext,
            conversation_stage=None,
            has_pending_floating_params=True,
        )

    def test_llm_called_when_stage_discovery(self):
        empty_ext = DiscoveryExtraction()
        assert should_invoke_llm_extractor(
            keyword_extraction=empty_ext,
            conversation_stage="discovery",
            has_pending_floating_params=False,
        )

    def test_llm_not_called_when_neutral_state(self):
        empty_ext = DiscoveryExtraction()
        assert not should_invoke_llm_extractor(
            keyword_extraction=empty_ext,
            conversation_stage="recommendation",
            has_pending_floating_params=False,
        )


# ─── 9. Render prompt ─────────────────────────────────────────────────────


class TestRenderForPrompt:
    def test_empty_returns_empty_string(self):
        assert render_discovery_for_prompt(active_projects=[]) == ""

    def test_with_one_full_project(self):
        proj = ClientProject(
            label=PROJECT_LABEL_HOUSE,
            status=PROJECT_STATUS_ACTIVE,
            parameters=ClientProjectParameters(
                horizon_years=4.0,
                target_amount=300000.0,
                target_currency="EUR",
                risk_appetite="low",
            ),
        )
        out = render_discovery_for_prompt(active_projects=[proj])
        assert "[CLIENT DISCOVERY]" in out
        assert "achat_maison" in out
        assert "horizon=4y" in out
        assert "target=300000 EUR" in out
        assert "risk=low" in out


# ─── 10. ClientProjectParameters merge ────────────────────────────────────


class TestParametersMerge:
    def test_merge_non_destructive_on_none(self):
        a = ClientProjectParameters(horizon_years=4.0, risk_appetite="low")
        b = ClientProjectParameters(horizon_years=None, risk_appetite="mid")
        c = a.merge(b)
        assert c.horizon_years == 4.0  # b.None ne doit pas écraser
        assert c.risk_appetite == "mid"  # b.mid écrase a.low

    def test_merge_extends_known_constraints(self):
        a = ClientProjectParameters(known_constraints=["x"])
        b = ClientProjectParameters(known_constraints=["y", "x"])
        c = a.merge(b)
        # Pas de doublons
        assert sorted(c.known_constraints) == ["x", "y"]


# ─── 11. Round-trip from_dict / to_dict ───────────────────────────────────


class TestDictRoundTrip:
    def test_project_round_trip(self):
        proj = ClientProject(
            label=PROJECT_LABEL_HOUSE,
            confidence=0.85,
            parameters=ClientProjectParameters(
                horizon_years=4.0, target_amount=300000.0
            ),
            created_at_turn=2,
        )
        d = proj.to_dict()
        proj2 = ClientProject.from_dict(d)
        assert proj2.label == proj.label
        assert proj2.parameters.horizon_years == 4.0
        assert proj2.parameters.target_amount == 300000.0
        assert proj2.created_at_turn == 2
