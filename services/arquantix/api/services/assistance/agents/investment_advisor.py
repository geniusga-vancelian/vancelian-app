"""Agent `advisor` — Conseil en placement / robo-advisor.

Spécialiste des questions de **conseil personnalisé** : recommandations
d'allocation, comparaison de stratégies, simulations *« quoi faire à mon
profil »*.

V1 : utilise la mémoire long-terme (déjà disponible) + un snapshot
portefeuille **stub**. La phase 3 substituera le stub par un vrai
service de portefeuille + un moteur de règles d'allocation.

Modèle suggéré V1 : `gpt-4o` (configurable via
`ASSISTANCE_AGENT_ADVISOR_MODEL`) — la nuance prime sur la vitesse.

Référence d'archi : `docs/arquantix/MULTI_AGENTS.md` § 2.3.
"""

from __future__ import annotations

from typing import Optional

from services.assistance.agents._llm_agent_base import LLMAgentBase
from services.assistance.agents.base import AGENT_ADVISOR_ID, AGENT_LABELS, AgentInput
from services.assistance.agents.tools import advisor_tools


class InvestmentAdvisorAgent(LLMAgentBase):
    """Agent pédagogue pour le conseil d'allocation et la stratégie."""

    agent_id: str = AGENT_ADVISOR_ID
    display_label: str = AGENT_LABELS[AGENT_ADVISOR_ID]
    model_env_var: str = "ASSISTANCE_AGENT_ADVISOR_MODEL"
    _default_temperature: float = 0.5  # un peu de créativité dans la pédagogie

    def __init__(self, *, client_id: str | None = None) -> None:
        self._client_id = client_id

    def _collect_tool_context(
        self, agent_input: AgentInput
    ) -> Optional[str]:
        """Inject portfolio snapshot (stub V1) en plus de la mémoire long-terme.

        La mémoire long-terme est déjà injectée par `prompt_builder` via
        `memory.build_context` — pas besoin de la repasser ici. On
        complète uniquement avec le portefeuille.
        """
        if not self._client_id:
            return None

        snapshot = advisor_tools.get_portfolio_snapshot(self._client_id)
        if not snapshot:
            return None

        lines = ["**Snapshot portefeuille (stub V1)** :"]
        for k, v in snapshot.items():
            lines.append(f"- {k} : `{v}`")
        return "\n".join(lines)
