"""Registry / factory pour instancier l'agent à partir d'un agent_id.

Sépare la **résolution agent_id → instance** du `service.py`, pour :
  - tester facilement (mock un agent en remplaçant l'entrée du registry)
  - permettre d'injecter du contexte (ex. `client_id`) à l'instanciation
    sans coupler `service.py` à l'API de chaque agent.
"""

from __future__ import annotations

from typing import Optional

from services.assistance.agents.assistant_default import DefaultAgent
from services.assistance.agents.base import (
    AGENT_ACTION_ID,
    AGENT_ADVISOR_ID,
    AGENT_COMPLIANCE_ID,
    AGENT_DEFAULT_ID,
    AGENT_MARKET_ID,
    AGENT_PRODUCT_ID,
    AGENT_TRUST_ID,
    AgentBase,
)
from services.assistance.agents.action import ActionAgent
from services.assistance.agents.compliance import ComplianceAgent
from services.assistance.agents.investment_advisor import InvestmentAdvisorAgent
from services.assistance.agents.market import MarketAgent
from services.assistance.agents.product import ProductAgent
from services.assistance.agents.trust import TrustAgent


def get_agent(agent_id: str, *, client_id: Optional[str] = None) -> AgentBase:
    """Retourne une instance d'agent prête à être utilisée.

    Args:
        agent_id: identifiant retourné par le router (déjà sanitizé).
        client_id: UUID du client courant — passé aux agents qui en ont
            besoin (`compliance`, `advisor`). Ignoré par les autres.

    Returns:
        Instance implémentant `AgentBase`.

    Raises:
        ValueError: si `agent_id` est inconnu (ne devrait jamais arriver
            si le router applique bien `KNOWN_AGENT_IDS`).
    """
    if agent_id == AGENT_DEFAULT_ID:
        return DefaultAgent()
    if agent_id == AGENT_COMPLIANCE_ID:
        return ComplianceAgent(client_id=client_id)
    if agent_id == AGENT_ADVISOR_ID:
        return InvestmentAdvisorAgent(client_id=client_id)
    if agent_id == AGENT_PRODUCT_ID:
        return ProductAgent()
    if agent_id == AGENT_MARKET_ID:
        return MarketAgent()
    if agent_id == AGENT_TRUST_ID:
        return TrustAgent()
    if agent_id == AGENT_ACTION_ID:
        return ActionAgent()
    raise ValueError(f"Unknown agent_id: {agent_id!r}")
