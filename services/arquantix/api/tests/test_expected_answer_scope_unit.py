"""Tests — `expected_answer_scope` (QCM / auto-QCM + attente tour suivant)."""

from __future__ import annotations

from services.assistance.agents.expected_answer_scope import (
    EXPECTED_ANSWER_SCOPE_KEY,
    build_scope_agent_qcm,
    build_scope_auto_qcm,
    build_scope_router_qcm,
    extract_pending_expectation_from_recent_turns,
    merge_expected_answer_scope_into_payload,
    render_pending_expectation_for_prompt,
)


class TestMergeExpectedAnswerScope:
    def test_empty_scope_returns_payload_unchanged(self):
        base = {"options": [], "allow_freeform": True}
        assert merge_expected_answer_scope_into_payload(base, {}) is base
        assert merge_expected_answer_scope_into_payload(base, None) is base  # type: ignore[arg-type]

    def test_adds_key_defensive_copy(self):
        base = {"a": 1}
        scope = {"kind": "multiple_choice", "source": "x", "choices": [{"label": "L"}]}
        out = merge_expected_answer_scope_into_payload(base, scope)
        assert out is not base
        assert out["a"] == 1
        assert out[EXPECTED_ANSWER_SCOPE_KEY] == scope

    def test_merge_from_none_payload(self):
        scope = {"kind": "listing_choice", "source": "auto_qcm", "choices": [{"ordinal": 1, "label": "X"}]}
        out = merge_expected_answer_scope_into_payload(None, scope)
        assert out == {EXPECTED_ANSWER_SCOPE_KEY: scope}


class TestBuildScopes:
    def test_router_skips_freeform(self):
        opts = [
            {"id": "x", "label": "A"},
            {"id": "freeform", "label": "Rien"},
        ]
        s = build_scope_router_qcm(prompt="Hello?", option_dicts=opts)
        assert s["source"] == "router_qcm"
        assert s["kind"] == "multiple_choice"
        assert len(s["choices"]) == 1
        assert s["choices"][0]["id"] == "x"

    def test_auto_qcm_ordinals(self):
        s = build_scope_auto_qcm(prompt="Pick", option_strings=["  One  ", "", "Three"])
        assert s["kind"] == "listing_choice"
        assert s["source"] == "auto_qcm"
        assert [c["ordinal"] for c in s["choices"]] == [1, 3]
        assert s["choices"][0]["label"] == "One"
        assert s["choices"][1]["label"] == "Three"

    def test_agent_qcm_same_normalization_as_router(self):
        raw = [{"id": "p", "label": "P"}]
        a = build_scope_agent_qcm(prompt="Q", option_dicts=raw)
        r = build_scope_router_qcm(prompt="Q", option_dicts=raw)
        assert a["choices"] == r["choices"]
        assert a["source"] == "agent_qcm_tool"


class TestExtractPendingExpectation:
    def test_too_few_turns(self):
        assert extract_pending_expectation_from_recent_turns([]) is None
        assert extract_pending_expectation_from_recent_turns([{"role": "user"}]) is None

    def test_last_not_user(self):
        turns = [
            {"role": "assistant", "content": "x"},
            {"role": "assistant", "content": "y"},
        ]
        assert extract_pending_expectation_from_recent_turns(turns) is None

    def test_prefers_persisted_expected_answer_scope(self):
        scope = {
            "kind": "multiple_choice",
            "source": "agent_qcm_tool",
            "choices": [{"id": "z", "label": "Zed"}],
        }
        turns = [
            {
                "role": "assistant",
                "content": "ignored",
                "message_type": "choices",
                "message_payload": {
                    "options": [{"id": "other", "label": "Other"}],
                    EXPECTED_ANSWER_SCOPE_KEY: scope,
                },
            },
            {"role": "user", "content": "z"},
        ]
        out = extract_pending_expectation_from_recent_turns(turns)
        assert out == scope

    def test_synthetic_from_choices_without_scope(self):
        turns = [
            {
                "role": "assistant",
                "content": "Quelle option ?",
                "message_type": "choices",
                "message_payload": {
                    "options": [
                        {"id": "a", "label": "Alpha"},
                        {"id": "freeform", "label": "Rien"},
                    ],
                },
            },
            {"role": "user", "content": "a"},
        ]
        out = extract_pending_expectation_from_recent_turns(turns)
        assert out is not None
        assert out["source"] == "agent_qcm_tool"
        assert len(out["choices"]) == 1
        assert out["choices"][0]["id"] == "a"

    def test_from_auto_qcm_on_text_message(self):
        turns = [
            {
                "role": "assistant",
                "content": "Répondez",
                "message_type": "text",
                "message_payload": {
                    "auto_qcm": {
                        "prompt": "Choix ?",
                        "options": ["Un", "Deux"],
                    },
                },
            },
            {"role": "user", "content": "1"},
        ]
        out = extract_pending_expectation_from_recent_turns(turns)
        assert out is not None
        assert out["source"] == "auto_qcm"
        assert out["kind"] == "listing_choice"
        assert out["choices"][0]["ordinal"] == 1
        assert out["choices"][0]["label"] == "Un"


class TestRenderPendingExpectation:
    def test_empty(self):
        assert render_pending_expectation_for_prompt(None) == ""
        assert render_pending_expectation_for_prompt({}) == ""

    def test_non_empty(self):
        text = render_pending_expectation_for_prompt(
            {
                "prompt_excerpt": "Question test",
                "choices": [{"id": "b", "label": "Bravo"}],
            }
        )
        assert "## Attente de réponse (tour précédent)" in text
        assert "Question test" in text
        assert "(b) Bravo" in text
        assert "elliptique" in text
