"""Tools de l'agent **compliance** — Phase 2a + Phase 2b.

Cf. `MULTI_AGENTS_RUNTIME.md` § 2.1 (structure répertoire) et
`COMPLIANCE_TOPICS.md` § 3 (sub-agents Phase 2b).

Tous les tools Phase 2a/2b sont **L0** (read-only, idempotent,
no side-effect). Les tools L1/L2 (`request_document_upload`,
`create_compliance_ticket`, `propose_account_action`) arriveront en
Phase 2c.

Phase 2b ajoute 3 tools :
  - `diagnose_compliance_topic` (dispatcher iter 0)
  - `propose_resume_registration` (sub-agent registration)
  - `read_transaction_detail` (sub-agent transactional)
"""

from __future__ import annotations

from services.assistance.agents.tools.compliance import (
    diagnose_compliance_topic,
    list_transactions,
    propose_resume_registration,
    read_compliance_state,
    read_documents,
    read_external_aml_signals,
    read_registration_progress,
    read_transaction_detail,
    read_transactions,
    stats_portfolio_allocation,
    stats_portfolio_performance,
    stats_transaction_amounts,
    stats_transaction_counts,
)

__all__ = [
    "diagnose_compliance_topic",
    "list_transactions",
    "propose_resume_registration",
    "read_compliance_state",
    "read_documents",
    "read_external_aml_signals",
    "read_registration_progress",
    "read_transaction_detail",
    "read_transactions",
    "stats_portfolio_allocation",
    "stats_portfolio_performance",
    "stats_transaction_amounts",
    "stats_transaction_counts",
]
