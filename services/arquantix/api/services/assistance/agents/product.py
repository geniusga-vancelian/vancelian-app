"""Agent `product` — Connaissance des produits Vancelian.

Spécialiste des questions sur les **produits Vancelian** :
caractéristiques, frais, fonctionnement, comparatifs.

V1 : tool `get_product_summary(slug)` est un stub qui lit la table CMS
`pages` (qui contient déjà les pages produits). En V2, vrai **RAG
vectoriel** sur fiches PDF/MD ingérées depuis le CMS.

Référence d'archi : `docs/arquantix/MULTI_AGENTS.md` § 2.4.
"""

from __future__ import annotations

from typing import Optional

from services.assistance.agents._llm_agent_base import LLMAgentBase
from services.assistance.agents.base import AGENT_LABELS, AGENT_PRODUCT_ID, AgentInput
from services.assistance.agents.tools import product_tools


class ProductAgent(LLMAgentBase):
    """Agent informatif sur les produits Vancelian."""

    agent_id: str = AGENT_PRODUCT_ID
    display_label: str = AGENT_LABELS[AGENT_PRODUCT_ID]
    model_env_var: str = "ASSISTANCE_AGENT_PRODUCT_MODEL"
    _default_temperature: float = 0.3

    def _collect_tool_context(
        self, agent_input: AgentInput
    ) -> Optional[str]:
        """Tente d'extraire un slug produit du message courant et fetch un résumé.

        En V1 : best-effort heuristique très simple. Si rien de pertinent,
        on n'injecte rien — l'agent répondra avec ce qu'il connaît
        nativement de Vancelian (et avec un disclaimer de prudence).
        """
        msg = (agent_input.user_message or "").lower()
        # Heuristique V1 : on cherche des mots-clés produit. La V2 utilisera
        # un RAG embedding-based.
        candidates = product_tools.guess_product_slugs(msg)
        if not candidates:
            return None

        summaries: list[str] = []
        for slug in candidates[:3]:  # cap à 3 produits par tour
            summary = product_tools.get_product_summary(slug)
            if summary:
                summaries.append(f"### Produit `{slug}`\n{summary}")

        return "\n\n".join(summaries) if summaries else None
