"""Phase 2 S1 — tests d'atomicité gate #1 (intent + swap + outbox).

A1 : échec volontaire → ROLLBACK → aucune row résiduelle.
A2 : succès → les 3 entités présentes avec cohérence des clés.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.transaction_outbox.atomic import (
    bundle_coherence_checks,
    persist_intent_swap_outbox_atomic,
)
from services.transaction_outbox.models import TransactionIntentTransition, TransactionOutbox
from services.transaction_outbox.repository import TransactionOutboxRepository
from tests.conftest import make_linked_client


class _IntentionalAtomicityFailure(Exception):
    """Simule une contrainte / erreur métier avant COMMIT."""


def _migration_173_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_outbox'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_173_ready(),
    reason="Migration 173 requise (transaction_outbox).",
)


def _counts(db: Session) -> tuple[int, int, int, int]:
    intents = db.query(TransactionIntent).count()
    swaps = db.query(PersonWalletSwap).count()
    outbox = db.query(TransactionOutbox).count()
    transitions = db.query(TransactionIntentTransition).count()
    return intents, swaps, outbox, transitions


def test_a1_rollback_no_intent_swap_outbox_or_transition(db: Session):
    """A1 — BEGIN → create → force failure → ROLLBACK → rien n'existe."""
    pe = make_linked_client(db)
    i0, s0, o0, t0 = _counts(db)

    nested = db.begin_nested()
    try:
        persist_intent_swap_outbox_atomic(
            db,
            person_id=pe.person_id,
            from_asset="USDC",
            to_asset="EURC",
            from_chain="base",
            to_chain="base",
            amount_in=Decimal("100"),
            record_initial_transition=True,
        )
        db.flush()
        raise _IntentionalAtomicityFailure("forced failure before commit")
    except _IntentionalAtomicityFailure:
        nested.rollback()

    i1, s1, o1, t1 = _counts(db)
    assert i1 == i0, "intent must not persist after rollback"
    assert s1 == s0, "swap must not persist after rollback"
    assert o1 == o0, "outbox must not persist after rollback"
    assert t1 == t0, "transition must not persist after rollback"


def test_a2_commit_intent_swap_outbox_present(db: Session):
    """A2 — BEGIN → create → flush (commit logique) → les 3 existent."""
    pe = make_linked_client(db)

    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="AAVE",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1.5"),
        record_initial_transition=True,
    )
    db.flush()

    assert bundle.intent.id is not None
    assert bundle.swap.id is not None
    assert bundle.outbox.id is not None

    assert (
        db.query(TransactionIntent).filter(TransactionIntent.id == bundle.intent.id).one()
        is bundle.intent
    )
    assert (
        db.query(PersonWalletSwap).filter(PersonWalletSwap.id == bundle.swap.id).one()
        is bundle.swap
    )
    assert (
        db.query(TransactionOutbox).filter(TransactionOutbox.id == bundle.outbox.id).one()
        is bundle.outbox
    )


def test_a2_correlation_linked_id_and_idempotency_coherent(db: Session):
    """A2 — correlation_id, linked_id, idempotency_key cohérents."""
    pe = make_linked_client(db)

    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("50"),
    )
    db.flush()

    checks = bundle_coherence_checks(bundle)
    assert all(checks.values()), checks

    assert bundle.intent.correlation_id is not None
    assert bundle.outbox.correlation_id == bundle.intent.correlation_id
    assert bundle.intent.linked_id == bundle.swap.id
    assert bundle.intent.idempotency_key == f"lifi_swap:{bundle.swap.id}"
    assert bundle.outbox.event_type == "intent.created"
    assert bundle.outbox.status == "pending"


def test_outbox_repository_insert_standalone(db: Session):
    """Repository outbox — insert minimal (sans branchement runtime)."""
    pe = make_linked_client(db)
    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        record_initial_transition=False,
    )
    db.flush()

    events = TransactionOutboxRepository.find_by_intent(
        db, bundle.intent.id, event_type="intent.created"
    )
    assert len(events) == 1
    assert events[0].id == bundle.outbox.id
