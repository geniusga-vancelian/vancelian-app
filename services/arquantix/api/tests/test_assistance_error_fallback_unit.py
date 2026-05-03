"""Tests unitaires du fallback persistant sur erreur LLM — Phase 2c.1 (C.2).

Couvre :
  - `services.assistance.service._persist_error_fallback` : appelle bien
    `_persist_assistant_message` avec le contenu `LLM_ERROR_FALLBACK_MESSAGE`,
    `message_type='text'`, et un `message_payload.metadata` exposant
    `is_error_fallback=True` + `error_code` traçable.
  - `LLM_ERROR_FALLBACK_MESSAGE` : reste neutre côté tipping-off (pas
    de mention « LLM », « OpenAI », « erreur interne »).

Conformément à `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 6 (anti-tipping-off)
et au plan correctif Phase 2c.1 (cf. transcripts).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance import service as assistance_service


# ─────────────────────────────────────────────────────────────────────────
# A. Texte du fallback — garde-fou anti-tipping-off
# ─────────────────────────────────────────────────────────────────────────


# Termes interdits dans le message affiché à l'utilisateur final
# (ne pas révéler la nature interne du failure ni le provider LLM).
_FORBIDDEN_TERMS_IN_FALLBACK = (
    "llm",
    "openai",
    "gpt",
    "cloudflare",
    "502",
    "503",
    "504",
    "429",
    "timeout",
    "exception",
    "stack",
    "traceback",
)


class TestFallbackMessageNeutrality:
    def test_fallback_message_is_a_non_empty_string(self):
        msg = assistance_service.LLM_ERROR_FALLBACK_MESSAGE
        assert isinstance(msg, str)
        assert msg.strip() != ""

    def test_fallback_message_does_not_leak_technical_details(self):
        low = assistance_service.LLM_ERROR_FALLBACK_MESSAGE.lower()
        for term in _FORBIDDEN_TERMS_IN_FALLBACK:
            assert term not in low, (
                f"LLM_ERROR_FALLBACK_MESSAGE leaks '{term}' "
                f"(visible to client): {low!r}"
            )

    def test_fallback_message_invites_retry(self):
        # Heuristique souple : le message doit rester actionable
        # ('réessaie' / 'retry' / 'plus tard' / 'instant'…).
        low = assistance_service.LLM_ERROR_FALLBACK_MESSAGE.lower()
        action_hints = ("réessaie", "réessayer", "retry", "plus tard", "instant")
        assert any(hint in low for hint in action_hints), (
            f"fallback message lacks retry call-to-action: {low!r}"
        )


# ─────────────────────────────────────────────────────────────────────────
# B. _persist_error_fallback — args passés à _persist_assistant_message
# ─────────────────────────────────────────────────────────────────────────


class TestPersistErrorFallback:
    def test_calls_persist_with_fallback_text_and_error_metadata(self):
        conv_id = uuid4()
        captured = {}

        def _capture(db, **kwargs):
            captured.update(kwargs)
            sentinel = MagicMock()
            sentinel.id = uuid4()
            return sentinel

        with patch.object(
            assistance_service,
            "_persist_assistant_message",
            side_effect=_capture,
        ):
            out = assistance_service._persist_error_fallback(
                MagicMock(),
                conversation_id=conv_id,
                turn_index=4,
                agent_used="compliance.transactional",
                error_code="llm_unavailable",
            )

        assert out is not None
        assert captured["conversation_id"] == conv_id
        assert captured["turn_index"] == 4
        assert captured["agent_used"] == "compliance.transactional"
        assert captured["message_type"] == "text"
        assert (
            captured["content"] == assistance_service.LLM_ERROR_FALLBACK_MESSAGE
        )
        payload = captured["message_payload"]
        assert isinstance(payload, dict)
        meta = payload.get("metadata") or {}
        assert meta.get("is_error_fallback") is True
        assert meta.get("error_code") == "llm_unavailable"

    def test_propagates_none_when_conversation_gone(self):
        # _persist_assistant_message renvoie None si la conv a disparu
        # entre-temps (race rare, cf. son docstring). Le helper doit
        # propager le None sans masquer l'erreur.
        with patch.object(
            assistance_service,
            "_persist_assistant_message",
            return_value=None,
        ):
            out = assistance_service._persist_error_fallback(
                MagicMock(),
                conversation_id=uuid4(),
                turn_index=1,
                agent_used="default",
                error_code="agent_error",
            )
        assert out is None

    def test_works_with_agent_used_none(self):
        # Edge case : si l'erreur survient avant qu'aucun agent_id
        # ne soit fixé (très tôt dans le pipeline), on doit quand
        # même persister le fallback (le caller passe `None`).
        captured = {}

        def _capture(db, **kwargs):
            captured.update(kwargs)
            return MagicMock(id=uuid4())

        with patch.object(
            assistance_service,
            "_persist_assistant_message",
            side_effect=_capture,
        ):
            assistance_service._persist_error_fallback(
                MagicMock(),
                conversation_id=uuid4(),
                turn_index=1,
                agent_used=None,
                error_code="agent_error",
            )
        assert captured["agent_used"] is None
        assert captured["message_type"] == "text"

    @pytest.mark.parametrize(
        "code",
        ["llm_unavailable", "agent_error", "agent_timeout", "tool_not_found"],
    )
    def test_error_code_is_recorded_in_metadata(self, code):
        captured = {}

        def _capture(db, **kwargs):
            captured.update(kwargs)
            return MagicMock(id=uuid4())

        with patch.object(
            assistance_service,
            "_persist_assistant_message",
            side_effect=_capture,
        ):
            assistance_service._persist_error_fallback(
                MagicMock(),
                conversation_id=uuid4(),
                turn_index=1,
                agent_used="compliance",
                error_code=code,
            )
        meta = captured["message_payload"]["metadata"]
        assert meta["error_code"] == code
        assert meta["is_error_fallback"] is True
