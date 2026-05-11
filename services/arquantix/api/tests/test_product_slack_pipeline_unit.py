"""Tests unitaires — pipeline Slack-like agent product (guardrail + Pass 1)."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import patch
from uuid import uuid4

from services.assistance.agents.base import AgentEvent, AgentInput
from services.assistance.agents.runtime import product_slack_pipeline as psp
from services.assistance.agents.runtime.product_slack_pipeline import (
    _build_preload_block_and_refs,
    _embeds_include_cal_ui,
    _language_hint_for_replies,
    _run_input_guardrail,
    normalize_index_path,
    parse_index_path_to_category_slug,
    should_use_slack_pipeline,
)
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def test_language_hint_fr_without_accents():
    assert (
        _language_hint_for_replies("sur quoi tu me proposes d'investir ?") == "fr"
    )
    assert _language_hint_for_replies("comment ça marche le coffre ?") == "fr"


def test_language_hint_fr_from_recent_turns():
    turns = [{"role": "user", "content": "Épargne retraite"}]
    assert _language_hint_for_replies("ok thanks", turns) == "fr"


def test_normalize_judge_payload():
    raw = {
        "verdict": "REWRITE",
        "criteria_scores": {
            "GROUNDED": 5,
            "ACCURATE_VOCABULARY": 4,
            "NO_RECOMMENDATION": 5,
            "COMPLETE": 3,
            "DISCLAIMERS": 5,
        },
        "confidence": 0.88,
        "knowledge_gap": "minor",
        "disclaimers_triggered": ["indicative_yield"],
        "notes": "ok",
        "rewritten": "fixed",
    }
    n = psp.normalize_judge_llm_payload(raw)
    assert n["criteria_average"] == 4.4
    assert n["confidence"] == 0.88
    assert n["knowledge_gap"] == "minor"
    persist = psp.judge_metadata_for_persistence(
        n,
        rewritten_applied=True,
        blocked_fallback_applied=False,
    )
    assert "rewritten" not in persist
    assert persist["rewritten_applied"] is True
    assert persist["criteria_scores"]["GROUNDED"] == 5


class TestParseIndexPath:
    def test_faq_path(self):
        assert parse_index_path_to_category_slug(
            "faq/savings/what-is-the-flexible-vault.md"
        ) == ("savings", "what-is-the-flexible-vault")

    def test_concepts_path(self):
        assert parse_index_path_to_category_slug("concepts/vancelian-glossary.md") == (
            "concepts",
            "vancelian-glossary",
        )

    def test_normalize_strips_wiki_prefix(self):
        assert normalize_index_path("wiki/faq/crypto/foo.md") == "faq/crypto/foo.md"

    def test_sql_sentinel_not_parsed(self):
        assert parse_index_path_to_category_slug("__use_sql_catalog__") is None


class TestPreloadBlock:
    def test_build_returns_markdown_sections(self):
        block, refs = _build_preload_block_and_refs(
            ["faq/savings/what-is-the-flexible-vault.md"],
        )
        assert "Contexte wiki pré-chargé" in block
        assert "savings/what-is-the-flexible-vault" in block


class TestInputGuardrail:
    def test_guardrail_parses_json(self):
        fake = json.dumps(
            {
                "verdict": "OFF_TOPIC",
                "reply_fr": "Je parle seulement de Vancelian.",
                "reply_en": "I only cover Vancelian.",
                "use_wiki": False,
            }
        )
        with patch(
            "services.assistance.agents.runtime.product_slack_pipeline.chat_completion",
            return_value=fake,
        ):
            out = _run_input_guardrail(
                user_message="écris un poème",
                recent_turns=[],
            )
        assert out["verdict"] == "OFF_TOPIC"
        assert out["use_wiki"] is False


def test_iter_pipeline_runs_agent_loop(monkeypatch):
    monkeypatch.setenv("ASSISTANCE_PRODUCT_SLACK_PIPELINE_ENABLED", "true")
    monkeypatch.setenv("ASSISTANCE_PRODUCT_PIPELINE_OUTPUT_JUDGE_ENABLED", "false")
    assert should_use_slack_pipeline("product") is True

    async def fake_run_agent_loop(**kwargs):
        assert kwargs.get("product_pipeline_relax_product_guardrail") is False
        yield AgentEvent(type="delta", content="")
        yield AgentEvent(type="delta", content="ok")
        yield AgentEvent(type="done", completed=True)

    monkeypatch.setattr(psp, "run_agent_loop", fake_run_agent_loop)

    guard = {
        "verdict": "IN_DOMAIN",
        "reply_fr": "",
        "reply_en": "",
        "use_wiki": False,
    }
    monkeypatch.setattr(psp, "_run_input_guardrail", lambda **_: guard)

    async def collect():
        events: list[AgentEvent] = []
        async for ev in psp.iter_product_slack_pipeline_events(
            db=None,  # type: ignore[arg-type]
            agent_id="product",
            agent_input=AgentInput(
                user_message="délai SEPA",
                recent_turns=[],
                memory_state={},
            ),
            actor_kind=ActorKind.CUSTOMER,
            conversation_id=uuid4(),
            user_id=1,
        ):
            events.append(ev)
        return events

    events = asyncio.run(collect())
    texts = [e.content for e in events if e.type == "delta" and e.content]
    assert "ok" in texts
    assert events[-1].type == "done"


def test_embeds_include_cal_ui():
    assert _embeds_include_cal_ui(None) is False
    assert _embeds_include_cal_ui([]) is False
    assert _embeds_include_cal_ui([{"type": "foo"}]) is False
    assert _embeds_include_cal_ui([{"type": "invest_source_account_list"}]) is True
    assert _embeds_include_cal_ui([{"type": "invest_confirmation_draft"}]) is True


def test_pipeline_skips_output_judge_when_cal_embed(monkeypatch):
    """Le juge wiki ne voit pas les cartes CAL — ne pas BLOCK à tort."""
    monkeypatch.setenv("ASSISTANCE_PRODUCT_SLACK_PIPELINE_ENABLED", "true")
    monkeypatch.setenv("ASSISTANCE_PRODUCT_PIPELINE_OUTPUT_JUDGE_ENABLED", "true")

    judged_called: list[bool] = []

    def spy_judge(**kwargs):
        judged_called.append(True)
        return psp.normalize_judge_llm_payload({"verdict": "BLOCK"})

    monkeypatch.setattr(psp, "_run_output_judge", spy_judge)

    guard = {"verdict": "IN_DOMAIN", "reply_fr": "", "reply_en": "", "use_wiki": False}
    monkeypatch.setattr(psp, "_run_input_guardrail", lambda **_: guard)

    async def fake_run_agent_loop(**kwargs):
        yield AgentEvent(type="delta", content="")
        yield AgentEvent(type="delta", content="Choisis ton compte")
        yield AgentEvent(
            type="done",
            completed=True,
            embeds=[{"type": "invest_source_account_list", "id": "list1"}],
        )

    monkeypatch.setattr(psp, "run_agent_loop", fake_run_agent_loop)

    async def collect():
        events_out: list[AgentEvent] = []
        async for ev in psp.iter_product_slack_pipeline_events(
            db=None,  # type: ignore[arg-type]
            agent_id="product",
            agent_input=AgentInput(
                user_message="acheter btc",
                recent_turns=[],
                memory_state={},
            ),
            actor_kind=ActorKind.CUSTOMER,
            conversation_id=uuid4(),
            user_id=1,
        ):
            events_out.append(ev)
        return events_out

    events = asyncio.run(collect())
    assert judged_called == []
    assert events[-1].type == "done"
    meta = events[-1].output_judge_metadata or {}
    assert meta.get("verdict") == "PASS"
    assert "skipped" in (meta.get("notes") or "").lower()
    deltas = [e.content for e in events if e.type == "delta" and (e.content or "").strip()]
    assert any("Choisis ton compte" in (t or "") for t in deltas)


def test_guard_off_topic_emits_done_without_loop(monkeypatch):
    monkeypatch.setenv("ASSISTANCE_PRODUCT_SLACK_PIPELINE_ENABLED", "true")
    monkeypatch.setattr(
        psp,
        "_run_input_guardrail",
        lambda **_: {
            "verdict": "OFF_TOPIC",
            "reply_fr": "Désolé, hors sujet.",
            "reply_en": "Sorry, off topic.",
            "use_wiki": False,
        },
    )
    called = []

    async def fake_run_agent_loop(**kwargs):
        called.append(True)
        yield AgentEvent(type="done", completed=True)

    monkeypatch.setattr(psp, "run_agent_loop", fake_run_agent_loop)

    async def collect():
        events: list[AgentEvent] = []
        async for ev in psp.iter_product_slack_pipeline_events(
            db=None,  # type: ignore[arg-type]
            agent_id="product",
        agent_input=AgentInput(user_message="bonjour poème", recent_turns=[], memory_state={}),
            actor_kind=ActorKind.CUSTOMER,
            conversation_id=uuid4(),
            user_id=1,
        ):
            events.append(ev)
        return events

    events = asyncio.run(collect())

    assert called == []
    assert any(e.type == "delta" and "hors sujet" in (e.content or "") for e in events)
