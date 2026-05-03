"""Client OpenAI mutualisé pour tous les agents (chat completions + streaming).

Encapsule la mécanique HTTP partagée par tous les agents (router inclus) :

  - `chat_completion(messages, model, ...)`   → string complète (sync via httpx).
  - `chat_completion_stream(messages, ...)`   → AsyncIterator de deltas tokens.
  - `chat_completion_with_tools(messages, ...)` → dict (réponse complète),
    pour les agents/router qui font du function calling.

Tous les agents passent par cette couche **plutôt que par `llm.py`**, qui
est conservé tel quel pour ne pas régresser le code existant. À terme,
`llm.py` pourra appeler ce client (refacto trivial).

Référence : `docs/arquantix/MULTI_AGENTS.md` § 1.1 et § 2.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Iterable

import httpx

from services.assistance.config import OPENAI_API_KEY, OPENAI_BASE_URL
from services.assistance.llm import LLMError

logger = logging.getLogger(__name__)


_DEFAULT_TIMEOUT_SECONDS = 60.0
_DEFAULT_STREAM_TIMEOUT_SECONDS = 120.0


def _ensure_key() -> str:
    if not OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY missing")
    return OPENAI_API_KEY


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_ensure_key()}",
        "Content-Type": "application/json",
    }


# ── Chat completion non-streaming ───────────────────────────────────────


def chat_completion(
    messages: list[dict],
    *,
    model: str,
    temperature: float = 0.7,
    response_format: dict | None = None,
    timeout: float = _DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Appelle `chat/completions` et retourne le contenu texte.

    Lève `LLMError` sur tout problème réseau / status / payload invalide.
    """
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    try:
        r = httpx.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=_auth_headers(),
            json=payload,
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        logger.warning("assistance.agent_client.http_error: %s", exc)
        raise LLMError(f"upstream_http_error: {exc}") from exc

    if r.status_code >= 400:
        logger.warning(
            "assistance.agent_client.openai_status=%s body=%s",
            r.status_code,
            r.text[:300],
        )
        raise LLMError(f"upstream_status_{r.status_code}")

    try:
        data = r.json()
    except ValueError as exc:
        raise LLMError("upstream_invalid_json") from exc

    choices = data.get("choices") or []
    if not choices:
        raise LLMError("upstream_no_choices")
    content = (choices[0].get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMError("upstream_empty_content")
    return content.strip()


# ── Chat completion streaming ───────────────────────────────────────────


async def chat_completion_stream(
    messages: list[dict],
    *,
    model: str,
    temperature: float = 0.7,
    timeout: float = _DEFAULT_STREAM_TIMEOUT_SECONDS,
) -> AsyncIterator[str]:
    """Streame les deltas tokens d'OpenAI via SSE upstream.

    Yields chaque chunk de texte au fur et à mesure. Lève `LLMError` sur
    erreur réseau / status non-2xx avant le début du stream.
    """
    _ensure_key()
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{OPENAI_BASE_URL}/chat/completions",
                headers=_auth_headers(),
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    logger.warning(
                        "assistance.agent_client.stream_status=%s body=%s",
                        response.status_code,
                        body[:300],
                    )
                    raise LLMError(f"upstream_status_{response.status_code}")

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = (choices[0].get("delta") or {}).get("content", "")
                    if delta:
                        yield delta
    except httpx.HTTPError as exc:
        logger.warning("assistance.agent_client.stream_http_error: %s", exc)
        raise LLMError(f"upstream_http_error: {exc}") from exc


# ── Chat completion avec tools (function calling) ──────────────────────


def chat_completion_with_tools(
    messages: list[dict],
    *,
    model: str,
    tools: Iterable[dict],
    tool_choice: str | dict = "auto",
    temperature: float = 0.1,
    timeout: float = _DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Appelle `chat/completions` avec function calling et retourne le message.

    Le retour est le dict `choices[0].message` brut (peut contenir
    `content`, `tool_calls`, etc.) — c'est l'appelant (router ou agent
    avec tools) qui sait comment l'interpréter.

    Utilisé en V1 par le router. En V2, par les agents `compliance` et
    `advisor` quand ils auront des tools réels.
    """
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "tools": list(tools),
        "tool_choice": tool_choice,
    }

    try:
        r = httpx.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=_auth_headers(),
            json=payload,
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        logger.warning("assistance.agent_client.tools_http_error: %s", exc)
        raise LLMError(f"upstream_http_error: {exc}") from exc

    if r.status_code >= 400:
        logger.warning(
            "assistance.agent_client.tools_status=%s body=%s",
            r.status_code,
            r.text[:300],
        )
        raise LLMError(f"upstream_status_{r.status_code}")

    try:
        data = r.json()
    except ValueError as exc:
        raise LLMError("upstream_invalid_json") from exc

    choices = data.get("choices") or []
    if not choices:
        raise LLMError("upstream_no_choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise LLMError("upstream_invalid_message")
    return message
