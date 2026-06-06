"""Settlement Layer — Phase 2 S2.5 skeleton (NOOP, aucune écriture économique)."""
from services.settlement.result import SettlementOutcome, SettlementResult
from services.settlement.settle import settle_transaction_intent_idempotently

__all__ = [
    "SettlementOutcome",
    "SettlementResult",
    "settle_transaction_intent_idempotently",
]
