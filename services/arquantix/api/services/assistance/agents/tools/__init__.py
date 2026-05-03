"""Tools V1 (stubs) pour les agents multi-agents.

Chaque sous-module expose des fonctions **pures** (pas de side effects)
qui retournent des données structurées que l'agent injecte dans son
prompt système comme « contexte instantané ».

V1 = stubs **stables et déterministes** pour pouvoir tester le pipeline
end-to-end sans dépendre d'intégrations externes ou de tables remplies.
V2 = vraies implémentations (DB, RAG, news API).

Substitution V1 → V2 = pure substitution d'implémentation, signatures
inchangées.
"""

from services.assistance.agents.tools import (
    advisor_tools,
    compliance_tools,
    market_tools,
    product_tools,
)

__all__ = [
    "advisor_tools",
    "compliance_tools",
    "market_tools",
    "product_tools",
]
