"""
Agent RiskGuardian: block forbidden phrases, prompt injection, escalation.
Patterns centralisés: aucune promesse de rendement, pas d'injection.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from ._llm import load_prompt

# Promesses / rendements interdits (assistant) — recherche en sous-chaîne, insensible à la casse
FORBIDDEN_PHRASES = [
    "garanti",
    "garantie",
    "vous gagnerez",
    "gagnerez",
    "rendement certain",
    "assuré",
    "sans risque",
]
# Injection / abus (user)
INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore les instructions",
    "oublie tout",
    "fais comme si",
    "ignore tes règles",
    "ignore tes regles",
]
_INJECTION_REGEX = re.compile(
    r"dis[\- ]moi\s+[0-9]+\s*%\s+en\s+(btc|crypto)",
    re.IGNORECASE,
)


def _has_forbidden(text: str | None) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(p in t for p in FORBIDDEN_PHRASES)


def _has_injection(text: str | None) -> bool:
    if not text:
        return False
    t = text.lower()
    if any(p in t for p in INJECTION_PHRASES):
        return True
    return bool(_INJECTION_REGEX.search(text))


def run_risk_guardian(
    user_message: str,
    assistant_message: str,
    profile: dict | None = None,
    product_proposal: dict | None = None,
    llm: object | None = None,
) -> dict[str, Any]:
    """
    Returns: { allowed: bool, replacement_message?: str, escalate_to_human: bool, refusal_reason?: str }
    """
    # 1) User: injection / abuse
    if _has_injection(user_message):
        return {
            "allowed": False,
            "replacement_message": "Je ne peux pas répondre à cette demande. Je suis là pour vous aider à cadrer votre projet d’épargne. Souhaitez-vous continuer ?",
            "escalate_to_human": False,
            "refusal_reason": "prompt_injection_or_abus",
        }

    # 2) Assistant: forbidden phrases (promesse de rendement)
    if _has_forbidden(assistant_message):
        return {
            "allowed": False,
            "replacement_message": "Je ne peux pas indiquer de rendement futur. Les performances passées ne préjugent pas des futures. Souhaitez-vous que l’on précise votre objectif ou votre horizon ?",
            "escalate_to_human": False,
            "refusal_reason": "forbidden_promise",
        }

    # 3) Optional LLM check
    system = load_prompt("risk_guardian")
    if system and (llm is not None or os.getenv("OPENAI_API_KEY")):
        from ._llm import chat
        user = (
            f"user_message: {user_message!r}\nassistant_message: {assistant_message!r}\n"
            "Réponds en JSON: allowed, replacement_message (si allowed=false), escalate_to_human, refusal_reason."
        )
        out = (llm.chat(system, user, json_mode=True, temperature=0.0) if llm and hasattr(llm, "chat") else chat(system, user, json_mode=True, temperature=0.0))
        if out:
            try:
                data = json.loads(out)
                return {
                    "allowed": data.get("allowed", True),
                    "replacement_message": data.get("replacement_message"),
                    "escalate_to_human": data.get("escalate_to_human", False),
                    "refusal_reason": data.get("refusal_reason"),
                }
            except json.JSONDecodeError:
                pass

    return {"allowed": True, "replacement_message": None, "escalate_to_human": False, "refusal_reason": None}
