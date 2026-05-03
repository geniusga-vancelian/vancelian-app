"""Appel OpenAI Markdown-only pour l'assistance mobile.

Le `SYSTEM_PROMPT` est aligné sur celui injecté côté Next.js (`/api/chat`)
afin que la sortie reste compatible avec `ArticleParagraphMarkdown` côté
Flutter (titres `##`/`###`, listes, citations `>`, tableaux, blocs code,
liens, gras/italique — pas de HTML brut).
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Iterable

import httpx

from services.assistance.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    assistance_temperature,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Tu réponds **toujours** en Markdown valide, en français.

Utilise selon les besoins :
- titres `##` et `###` (jamais `#`)
- gras `**…**`, italique `*…*`
- listes à puces `- ` ou numérotées `1. `
- liens `[texte](https://…)`
- citations `> …` (avec attribution `— Auteur` sur la dernière ligne quand c'est pertinent)
- tableaux Markdown `| col | col |`
- blocs de code triple-backtick ``` pour le code ou les extraits à recopier littéralement

Pas de HTML brut. Reste clair, factuel et concis."""


class LLMError(Exception):
    """Erreur de l'appel OpenAI (réseau, status non-2xx, payload invalide)."""


def chat_markdown(history: Iterable[dict]) -> str:
    """Appelle `chat/completions` avec [SYSTEM_PROMPT] + ``history``.

    `history` : iterable de `{"role": "user"|"assistant", "content": str}`,
    déjà filtré côté service (rôles/longueurs validés).

    Retourne le contenu (string) ; lève `LLMError` en cas d'échec, pour que
    la route puisse répondre 502/500 plutôt que de stocker une réponse vide.
    """
    if not OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY missing")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *list(history)]
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": assistance_temperature(),
    }

    try:
        r = httpx.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("assistance.llm http_error: %s", exc)
        raise LLMError(f"upstream_http_error: {exc}") from exc

    if r.status_code >= 400:
        logger.warning(
            "assistance.llm openai_status=%s body=%s",
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


async def chat_markdown_stream(history: Iterable[dict]) -> AsyncIterator[str]:
    """Variante streaming de [chat_markdown] — yield chaque delta token reçu.

    Utilise `httpx.AsyncClient.stream` avec `stream=True` côté OpenAI pour
    consommer les Server-Sent Events `data: {…}` au fur et à mesure. Le
    consumer côté FastAPI ré-emballe les deltas en SSE applicatif vers le
    client mobile (effet « machine à écrire » ChatGPT).

    Lève `LLMError` au début du stream si l'API OpenAI répond un statut
    non-2xx ou en cours de stream sur erreur HTTP. Les `JSONDecodeError`
    locaux sur des chunks malformés sont silencieusement ignorés.
    """
    if not OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY missing")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, *list(history)]
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": assistance_temperature(),
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    logger.warning(
                        "assistance.llm.stream openai_status=%s body=%s",
                        response.status_code,
                        body[:300],
                    )
                    raise LLMError(f"upstream_status_{response.status_code}")

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if not line.startswith("data: "):
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
        logger.warning("assistance.llm.stream http_error: %s", exc)
        raise LLMError(f"upstream_http_error: {exc}") from exc
