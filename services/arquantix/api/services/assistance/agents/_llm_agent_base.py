"""Base utilitaire commune aux agents qui font du streaming LLM avec tools.

Pattern type :

    class ComplianceAgent(LLMAgentBase):
        agent_id = "compliance"
        display_label = "Assistance compte"
        model_env_var = "ASSISTANCE_AGENT_COMPLIANCE_MODEL"

        def _collect_tool_context(self, agent_input):
            account = self._tools.get_account_status(self._client_id)
            txs = self._tools.get_recent_transactions(self._client_id)
            return f"- Account status: {account}\\n- Last 10 txs: {txs}"

Le streaming OpenAI est géré une fois pour toutes ici. Chaque agent
n'a qu'à fournir :
  - son `agent_id` / `display_label` / `model_env_var`
  - son `_collect_tool_context(agent_input) -> str | None`
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from services.assistance.agents.base import AgentEvent, AgentInput
from services.assistance.agents.config import (
    assistance_agent_model,
    assistance_agent_temperature,
)
from services.assistance.agents.openai_client import chat_completion_stream
from services.assistance.agents.prompt_builder import build_agent_messages
from services.assistance.llm import LLMError

logger = logging.getLogger(__name__)


class LLMAgentBase:
    """Base abstraite pour les agents streaming Markdown (avec tools optionnels).

    Les sous-classes peuvent override :
      - `_collect_tool_context(agent_input)` pour injecter un bloc Markdown
        construit depuis les tools dans le prompt système (sous *« Contexte
        instantané (tools) »*).
      - `_default_temperature` pour le réglage du modèle.
    """

    agent_id: str = "abstract"
    display_label: str = ""
    model_env_var: str = "ASSISTANCE_AGENT_ABSTRACT_MODEL"
    _default_temperature: float = 0.7

    def _collect_tool_context(
        self, agent_input: AgentInput
    ) -> Optional[str]:  # pragma: no cover (override-able)
        """Sous-classes : retourne un bloc Markdown ou None.

        En V1, la plupart des agents retournent None (pas de tools réels)
        ou un stub. En V2, c'est ici que se font les vraies requêtes DB /
        APIs externes / RAG.
        """
        return None

    async def stream(self, *, agent_input: AgentInput) -> AsyncIterator[AgentEvent]:
        try:
            extra = self._collect_tool_context(agent_input)
        except Exception as exc:  # noqa: BLE001 — best-effort, surface = 1 event error
            logger.warning(
                "assistance.agent.%s tool_collection_failed=%s",
                self.agent_id,
                exc,
            )
            extra = None

        messages = build_agent_messages(
            agent_id=self.agent_id,
            agent_input=agent_input,
            extra_system_suffix=extra,
        )
        model = assistance_agent_model(self.agent_id)
        temperature = assistance_agent_temperature(
            self.agent_id, default=self._default_temperature
        )

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

        yield AgentEvent(type="done", completed=True)
