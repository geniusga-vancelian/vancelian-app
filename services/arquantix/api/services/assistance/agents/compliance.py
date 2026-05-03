"""Agent `compliance` — Assistance compte / opérationnel.

Spécialiste des questions sur l'**état du compte** du client : KYC,
dépôts, transactions, validations administratives.

V1 (Phase 1) : tools **stubs** qui renvoient des données neutres ou
issues de tables existantes minimales. La vraie intégration aux tables
KYC / transactions Vancelian arrive en Phase 2.

Référence d'archi : `docs/arquantix/MULTI_AGENTS.md` § 2.2 et § 4 toolbox.
"""

from __future__ import annotations

from typing import Optional

from services.assistance.agents._llm_agent_base import LLMAgentBase
from services.assistance.agents.base import AGENT_COMPLIANCE_ID, AGENT_LABELS, AgentInput
from services.assistance.agents.tools import compliance_tools


class ComplianceAgent(LLMAgentBase):
    """Agent factuel pour l'opérationnel compte client (KYC, transactions)."""

    agent_id: str = AGENT_COMPLIANCE_ID
    display_label: str = AGENT_LABELS[AGENT_COMPLIANCE_ID]
    model_env_var: str = "ASSISTANCE_AGENT_COMPLIANCE_MODEL"
    _default_temperature: float = 0.2  # factuel, peu de créativité

    def __init__(self, *, client_id: str | None = None) -> None:
        self._client_id = client_id

    def _collect_tool_context(
        self, agent_input: AgentInput
    ) -> Optional[str]:
        """Récupère le statut compte + transactions récentes.

        En V1 : stubs renvoyant des données minimales. La transition vers
        des tools réels est pure substitution (signature inchangée).
        """
        if not self._client_id:
            return None

        account = compliance_tools.get_account_status(self._client_id)
        txs = compliance_tools.get_recent_transactions(self._client_id, limit=10)

        lines: list[str] = []
        if account is not None:
            lines.append("**Statut compte** :")
            lines.append(
                f"- KYC : `{account.get('kyc_state', 'unknown')}`"
            )
            lines.append(
                f"- Compte actif : `{account.get('account_active', 'unknown')}`"
            )

        if txs:
            lines.append("")
            lines.append("**Transactions récentes (10 max)** :")
            for tx in txs:
                lines.append(
                    f"- `{tx.get('id', '?')}` "
                    f"{tx.get('type', '?')} "
                    f"{tx.get('amount', '?')} € "
                    f"→ `{tx.get('status', '?')}` "
                    f"({tx.get('created_at', '?')})"
                )

        return "\n".join(lines) if lines else None
