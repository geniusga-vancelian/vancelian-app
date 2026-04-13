"""
Shared LLM helpers: load prompt, call OpenAI, hash for audit.
Uses config for OpenAI env vars. No PII in logs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx

from services.chatbot_epargne.config import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def load_prompt(name: str) -> str:
    p = _PROMPTS_DIR / f"system_{name}.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").strip()


def hash_prompt(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def chat(system: str, user: str, *, json_mode: bool = False, temperature: float = 0.2) -> str:
    if not OPENAI_API_KEY:
        return ""
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        r = httpx.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=60.0,
        )
        r.raise_for_status()
        return (r.json().get("choices") or [{}])[0].get("message", {}).get("content") or ""
    except Exception:
        return ""
