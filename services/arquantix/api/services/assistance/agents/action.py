"""Agent ``action`` — parcours transactionnels guidés (widgets + deep-links)."""

from __future__ import annotations

from typing import Optional

from services.assistance.agents._llm_agent_base import LLMAgentBase
from services.assistance.agents.base import AGENT_ACTION_ID, AGENT_LABELS, AgentInput


class ActionAgent(LLMAgentBase):
    """Spécialiste des actions in-app (runtime tools, pas wiki produit)."""

    agent_id: str = AGENT_ACTION_ID
    display_label: str = AGENT_LABELS[AGENT_ACTION_ID]
    model_env_var: str = "ASSISTANCE_AGENT_ACTION_MODEL"
    _default_temperature: float = 0.2

    def _collect_tool_context(
        self,
        agent_input: AgentInput,
    ) -> Optional[str]:
        """Pas d'injection automatique : le routeur + tools portent le contexte."""
        return None


__all__ = ["ActionAgent"]
