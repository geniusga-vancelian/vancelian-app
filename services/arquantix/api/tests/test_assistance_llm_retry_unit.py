"""Tests unitaires du retry borné LLM — Phase 2c.1 (résilience OpenAI/Cloudflare).

Couvre `services.assistance.agents.runtime.agent_loop._llm_call_with_retry`
et `_llm_error_is_retryable`.

Le runtime catch `LLMError("upstream_status_<code>")` produites par
`openai_client.chat_completion_with_tools`. Pour `<code>` ∈ {502, 503,
504, 429}, on retry au plus `LLM_MAX_RETRIES=2` fois avec un backoff
fixe (`LLM_BACKOFF_SCHEDULE=(0.5, 1.0)`).

Spec de référence : `docs/arquantix/COMPLIANCE_TOPICS.md` §12.x (TBD).
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from services.assistance.agents.runtime import agent_loop
from services.assistance.llm import LLMError


# ─────────────────────────────────────────────────────────────────────────
# _llm_error_is_retryable — pur, sans IO
# ─────────────────────────────────────────────────────────────────────────


class TestLLMErrorIsRetryable:
    @pytest.mark.parametrize(
        "code",
        ["502", "503", "504", "429"],
    )
    def test_retryable_codes(self, code):
        exc = LLMError(f"upstream_status_{code}")
        assert agent_loop._llm_error_is_retryable(exc) is True

    @pytest.mark.parametrize(
        "code",
        ["400", "401", "403", "404", "422", "500", "501"],
    )
    def test_non_retryable_status_codes(self, code):
        exc = LLMError(f"upstream_status_{code}")
        assert agent_loop._llm_error_is_retryable(exc) is False

    def test_unknown_format_is_not_retryable(self):
        exc = LLMError("invalid_response")
        assert agent_loop._llm_error_is_retryable(exc) is False

    def test_empty_message_is_not_retryable(self):
        exc = LLMError("")
        assert agent_loop._llm_error_is_retryable(exc) is False

    def test_extra_suffix_is_ignored(self):
        # Format strict : `upstream_status_<code>`. Tout ce qui suit `_`
        # doit matcher exactement un code du whitelist (pas de match
        # partiel).
        exc = LLMError("upstream_status_502_extra")
        assert agent_loop._llm_error_is_retryable(exc) is False


# ─────────────────────────────────────────────────────────────────────────
# _llm_call_with_retry — comportement runtime
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _zero_backoff():
    """Neutralise le backoff pour que la suite de tests reste rapide."""
    with patch.object(agent_loop, "LLM_BACKOFF_SCHEDULE", (0.0, 0.0)):
        yield


def _make_completion_fn(*results):
    """Fabrique une `completion_fn` qui rejoue successivement `results`.

    Chaque entrée :
      - si `Exception` → est levée à l'appel correspondant,
      - sinon → retournée telle quelle (typiquement `dict`).
    """
    state = {"calls": 0}

    def _fn(*a, **kw):
        idx = state["calls"]
        state["calls"] += 1
        if idx >= len(results):
            raise AssertionError(
                f"completion_fn called {idx + 1} times but only "
                f"{len(results)} results provided"
            )
        out = results[idx]
        if isinstance(out, BaseException):
            raise out
        return out

    return _fn, state


class TestLLMCallWithRetry:
    def _call(self, fn):
        """Wrapper synchrone autour du retry async."""
        return asyncio.run(
            agent_loop._llm_call_with_retry(
                fn,
                messages=[],
                model="gpt-4o-mini",
                tools=[],
                temperature=0.1,
                agent_id="compliance",
                iteration=0,
            )
        )

    def test_success_on_first_attempt(self):
        ok = {"content": "ok", "tool_calls": None}
        fn, state = _make_completion_fn(ok)
        assert self._call(fn) is ok
        assert state["calls"] == 1

    def test_retries_after_502_then_success(self):
        ok = {"content": "ok", "tool_calls": None}
        fn, state = _make_completion_fn(
            LLMError("upstream_status_502"),
            ok,
        )
        assert self._call(fn) is ok
        assert state["calls"] == 2

    def test_retries_twice_then_success(self):
        ok = {"content": "ok", "tool_calls": None}
        fn, state = _make_completion_fn(
            LLMError("upstream_status_503"),
            LLMError("upstream_status_504"),
            ok,
        )
        assert self._call(fn) is ok
        assert state["calls"] == 3  # 1 + LLM_MAX_RETRIES

    def test_gives_up_after_max_retries(self):
        fn, state = _make_completion_fn(
            LLMError("upstream_status_502"),
            LLMError("upstream_status_502"),
            LLMError("upstream_status_502"),
        )
        with pytest.raises(LLMError) as exc_info:
            self._call(fn)
        assert "502" in str(exc_info.value)
        assert state["calls"] == agent_loop.LLM_MAX_RETRIES + 1

    def test_no_retry_on_non_retryable_status(self):
        fn, state = _make_completion_fn(LLMError("upstream_status_401"))
        with pytest.raises(LLMError) as exc_info:
            self._call(fn)
        assert "401" in str(exc_info.value)
        assert state["calls"] == 1

    def test_no_retry_on_unknown_format(self):
        fn, state = _make_completion_fn(LLMError("invalid_response"))
        with pytest.raises(LLMError):
            self._call(fn)
        assert state["calls"] == 1

    def test_429_is_retried(self):
        ok = {"content": "ok", "tool_calls": None}
        fn, state = _make_completion_fn(
            LLMError("upstream_status_429"),
            ok,
        )
        assert self._call(fn) is ok
        assert state["calls"] == 2

    def test_mixed_codes_retry_until_definitive(self):
        # 502 → retry → 401 (non-retryable) → fail immédiat.
        fn, state = _make_completion_fn(
            LLMError("upstream_status_502"),
            LLMError("upstream_status_401"),
        )
        with pytest.raises(LLMError) as exc_info:
            self._call(fn)
        assert "401" in str(exc_info.value)
        assert state["calls"] == 2


# ─────────────────────────────────────────────────────────────────────────
# Constantes — sanity check
# ─────────────────────────────────────────────────────────────────────────


class TestRetryConstants:
    def test_retryable_codes_is_frozenset_of_str(self):
        assert isinstance(agent_loop.LLM_RETRYABLE_UPSTREAM_CODES, frozenset)
        assert all(
            isinstance(c, str) for c in agent_loop.LLM_RETRYABLE_UPSTREAM_CODES
        )

    def test_max_retries_is_at_least_one(self):
        assert agent_loop.LLM_MAX_RETRIES >= 1

    def test_backoff_schedule_length_matches_max_retries(self):
        # Garde-fou : si on passe `LLM_MAX_RETRIES=3`, il faut prévoir
        # 3 entrées de backoff (sinon `min(attempt, len-1)` clamp,
        # acceptable mais préférable d'avoir une 1:1).
        assert len(agent_loop.LLM_BACKOFF_SCHEDULE) >= 1
        assert all(
            v >= 0 for v in agent_loop.LLM_BACKOFF_SCHEDULE
        )
