"""Agent `market` — Veille marché et analyses.

Spécialiste des questions **macro / actualités économiques** : opinions
sur indices et secteurs, contexte macro, mise en perspective avec le
portefeuille du client.

V1 : tool `get_recent_news(topic, limit=5)` est un stub avec items
hard-codés. En V2, connecteur API news + base d'analyses internes.

Référence d'archi : `docs/arquantix/MULTI_AGENTS.md` § 2.5.
"""

from __future__ import annotations

from typing import Optional

from services.assistance.agents._llm_agent_base import LLMAgentBase
from services.assistance.agents.base import AGENT_LABELS, AGENT_MARKET_ID, AgentInput
from services.assistance.agents.tools import market_tools


class MarketAgent(LLMAgentBase):
    """Agent analytique pour la veille marché et le commentaire macro."""

    agent_id: str = AGENT_MARKET_ID
    display_label: str = AGENT_LABELS[AGENT_MARKET_ID]
    model_env_var: str = "ASSISTANCE_AGENT_MARKET_MODEL"
    _default_temperature: float = 0.4

    def _collect_tool_context(
        self, agent_input: AgentInput
    ) -> Optional[str]:
        """Récupère les 3-5 items news/analyses les plus pertinents.

        V1 : extraction très simple d'un sujet à partir du message
        utilisateur, puis stub renvoyant des items hard-codés. V2
        substituera l'implémentation sans changer la signature.
        """
        topic = market_tools.guess_topic(agent_input.user_message or "")
        items = market_tools.get_recent_news(topic, limit=5)
        if not items:
            return None

        lines = ["**Items récents (stub V1)** :"]
        for it in items:
            title = it.get("title") or "(sans titre)"
            date = it.get("date") or "?"
            src = it.get("source") or "interne"
            excerpt = (it.get("excerpt") or "").strip()
            lines.append(f"- **{title}** _({date} — {src})_ : {excerpt}")
        return "\n".join(lines)
