"""Politique v1 « data_need » : encourager au moins un tool de lecture métier.

Lorsque l’orchestration du router impose un besoin de données compte/transactions/KYC,
on attend au moins **un** appel d’outil de lecture pertinent avant une réponse finale.

PR3 : **audit + warning uniquement** — pas de blocage runtime.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence

logger = logging.getLogger(__name__)

DATA_NEEDS_REQUIRING_READ: frozenset[str] = frozenset(
    {
        "transaction_data",
        "account_data",
        "kyc_data",
    }
)

# Allowlists évolutives (noms canoniques registrés sous ``tools/*/``).
_TOOLS_TRANSACTION: frozenset[str] = frozenset(
    {
        "list_transactions",
        "read_transactions",
        "read_transaction_detail",
    }
)
_TOOLS_ACCOUNT: frozenset[str] = frozenset(
    {
        "list_transactions",
        "read_transactions",
        "read_transaction_detail",
        "read_compliance_state",
        "read_documents",
    }
)
_TOOLS_KYC: frozenset[str] = frozenset(
    {
        "read_registration_progress",
        "read_compliance_state",
        "read_documents",
        "read_external_aml_signals",
    }
)


def _allowed_tools_for_data_need(data_need: str) -> frozenset[str]:
    if data_need == "transaction_data":
        return _TOOLS_TRANSACTION
    if data_need == "account_data":
        return _TOOLS_ACCOUNT
    if data_need == "kyc_data":
        return _TOOLS_KYC
    return frozenset()


def data_need_reads_satisfied(
    data_need: str,
    tools_called_sequence: Sequence[str],
) -> bool:
    allowed = _allowed_tools_for_data_need(str(data_need or "").strip().lower())
    if not allowed:
        return True
    called = frozenset(str(t) for t in tools_called_sequence if t)
    return bool(called & allowed)


def maybe_audit_data_need_read_gap(
    db: Any,
    *,
    conversation_id: Any,
    agent_id: str,
    orchestration: Optional[Dict[str, Any]],
    tools_called_sequence: Sequence[str],
    correlation_id: Optional[str],
    iteration: int,
    early_break_reason: Optional[str],
) -> None:
    """Si ``data_need`` l’exige et aucun tool de lecture listé → warning + ligne audit."""
    if early_break_reason not in ("final_answer", "max_iter"):
        return
    if not isinstance(orchestration, dict):
        return
    need = str(orchestration.get("data_need") or "").strip().lower()
    if need not in DATA_NEEDS_REQUIRING_READ:
        return

    seq = tuple(tools_called_sequence)
    if data_need_reads_satisfied(need, seq):
        return

    allowed = sorted(_allowed_tools_for_data_need(need))
    try:
        from services.assistance.agents.tools.shared import audit

        audit.persist_decision(
            db,
            conversation_id=conversation_id,
            message_id=None,
            agent_id=agent_id,
            iteration=int(iteration),
            tool_name="policy_data_need_reads",
            autonomy_level="L0",
            arguments={
                "data_need": need,
                "tools_called_this_tour": list(seq),
                "expected_read_tools": allowed,
                "policy_version": 1,
            },
            result_summary={
                "status": "warn_no_read_attempt_before_final_answer",
                "reason": (
                    "orchestration data_need implies account/txn/kyc grounding; "
                    "no matching read tool was invoked before final emission"
                ),
            },
            correlation_id=correlation_id,
            review_status="auto",
            error_code="policy_soft_warn",
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "data_need_read_policy.audit_failed conv=%s agent=%s", conversation_id, agent_id
        )

    logger.warning(
        "assistance.policy.data_need_reads_unsatisfied conv=%s agent=%s "
        "data_need=%s tools=%s corr=%s",
        conversation_id,
        agent_id,
        need,
        ",".join(seq) or "-",
        correlation_id or "-",
    )
