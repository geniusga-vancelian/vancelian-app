"""Agent `default` — généraliste, fallback historique.

C'est l'agent qui assure la **continuité** : en l'absence de routage
décisif (ou avec `ASSISTANCE_MULTI_AGENT_ENABLED=false`), c'est lui qui
répond, avec un comportement aussi proche que possible du comportement
pré-multi-agents (réf. `services.assistance.llm.SYSTEM_PROMPT`).

Il **n'utilise pas de tools**, juste la mémoire long-terme + l'historique
récent. C'est l'agent qu'on doit conserver verts dans la suite de tests
existante (mémoire) pour garantir zéro régression côté legacy.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from services.assistance.agents.base import (
    AGENT_DEFAULT_ID,
    AGENT_LABELS,
    AgentEvent,
    AgentInput,
)
from services.assistance.agents.config import (
    assistance_agent_model,
    assistance_agent_temperature,
)
from services.assistance.agents.openai_client import chat_completion_stream
from services.assistance.agents.prompt_builder import build_agent_messages
from services.assistance.llm import LLMError

logger = logging.getLogger(__name__)


class DefaultAgent:
    """Agent généraliste, fallback. N'utilise aucun tool."""

    agent_id: str = AGENT_DEFAULT_ID
    display_label: str = AGENT_LABELS[AGENT_DEFAULT_ID]
    model_env_var: str = "ASSISTANCE_AGENT_DEFAULT_MODEL"

    async def stream(self, *, agent_input: AgentInput) -> AsyncIterator[AgentEvent]:
        messages = build_agent_messages(
            agent_id=self.agent_id, agent_input=agent_input
        )
        model = assistance_agent_model(self.agent_id)
        temperature = assistance_agent_temperature(self.agent_id, default=0.7)

        try:
            async for delta in chat_completion_stream(
                messages, model=model, temperature=temperature
            ):
                yield AgentEvent(type="delta", content=delta)
        except LLMError as exc:
            logger.warning(
                "assistance.agent.%s llm_error=%s", self.agent_id, exc
            )
            yield AgentEvent(type="error", error_code="llm_unavailable")
            return

        # Le `done` est émis par le service.py après persistance — l'agent
        # se contente de fermer son générateur ici. Garde un dernier
        # event done sans message_id pour permettre une consommation
        # autonome (utile dans les tests unitaires).
        yield AgentEvent(type="done", completed=True)
