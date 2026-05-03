"""Assistance « sur mesure » — chatbot mobile Flutter (Search screen).

Persistence par client (`pe_clients.id`) + appel OpenAI avec `SYSTEM_PROMPT`
qui force un rendu Markdown compatible avec l'interpréteur côté Flutter
(`ArticleParagraphMarkdown`).

Public surface :
- `router` : APIRouter FastAPI (`POST /api/app/assistance/chat/turn`).
"""

from services.assistance.routes import router  # noqa: F401

__all__ = ["router"]
