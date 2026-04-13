"""
LLM client abstraction: real (OpenAI) and Fake for tests.
No network in tests when using FakeLLMClient.
"""
from __future__ import annotations

from typing import Optional, Protocol


class LLMProtocol(Protocol):
    def chat(
        self, system: str, user: str, *, json_mode: bool = False, temperature: float = 0.2
    ) -> str:
        ...


class LLMClient:
    """Real OpenAI client. Uses OPENAI_API_KEY from config."""

    def chat(
        self, system: str, user: str, *, json_mode: bool = False, temperature: float = 0.2
    ) -> str:
        from .agents._llm import chat as _chat
        return _chat(system, user, json_mode=json_mode, temperature=temperature)


class FakeLLMClient:
    """Deterministic client for tests. No network."""

    def chat(
        self, system: str, user: str, *, json_mode: bool = False, temperature: float = 0.2
    ) -> str:
        if "extractor" in system.lower() or "extract" in system.lower():
            # Minimal JSON for extractor
            return '{"extracted":[{"field":"goal.target_amount","value":50000,"confidence":0.9,"source_quote":"50 000"},{"field":"horizon_months","value":60,"confidence":0.9,"source_quote":"5 ans"}],"missing_fields":[],"contradictions":[]}'
        if "compliance" in system.lower():
            return '{"missing_mandatory":[],"contradictions":[],"disclaimer_ids_to_show":["non_advice"],"next_suggested_question_id":"q_recap","warnings":[]}'
        if "risk" in system.lower() or "guardian" in system.lower():
            return '{"allowed":true,"replacement_message":null,"escalate_to_human":false,"refusal_reason":null}'
        if "copywriter" in system.lower():
            return '{"summary_text":"Répartition indicative. Illustration pédagogique. Les performances passées ne préjugent pas des futures.","disclaimer_block":"Les marchés peuvent varier. Valeur non garantie."}'
        # coach or other
        return "En une phrase, quel est pour vous l’objectif de cette épargne ?"
