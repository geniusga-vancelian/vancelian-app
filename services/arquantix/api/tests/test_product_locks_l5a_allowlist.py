"""S4 L5a — allowlist Product Locks dédiée (fail-closed · flag OFF par défaut)."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import Person, engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person
from services.auth.person_identity_bridge import upsert_person_crypto_wallet
from services.product_locks.allowlist import (
    is_person_product_locks_allowlisted,
    product_locks_allowlist_configured,
    product_locks_allowed_person_emails,
    product_locks_enabled_for_person,
)
from services.product_locks.models import TransactionProductLock
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.orchestrator_product_locks import (
    apply_orchestrator_product_locks_before_queued,
)
from services.transaction_outbox.worker import process_transaction_outbox_intent_created
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.product_locks_test_utils import enable_product_locks_allowlist
from tests.test_product_locks_l2_engine import _migration_175_ready
from tests.test_transaction_outbox_worker_s2b import _migration_173_ready


pytestmark = [
    pytest.mark.skipif(not _migration_173_ready(), reason="Migration 173 requise."),
    pytest.mark.skipif(not _migration_175_ready(), reason="Migration 175 requise."),
]


@pytest.fixture
def locks_on(monkeypatch):
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", "true")


@pytest.fixture
def locks_off(monkeypatch):
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", raising=False)
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS", raising=False)


def _wallet(db: Session, pe_client):
    return upsert_person_crypto_wallet(
        db,
        person_id=pe_client.person_id,
        pe_client_id=pe_client.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=f"0x{uuid.uuid4().hex[:40]}",
    )


def test_allowed_emails_parsing_trim_and_lowercase(monkeypatch):
    monkeypatch.setenv(
        "TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS",
        "  Pilot@Example.COM , other@test.local  ",
    )
    assert product_locks_allowed_person_emails() == frozenset(
        {"pilot@example.com", "other@test.local"}
    )


def test_flag_off_with_allowlist_present_is_no_op(db: Session, monkeypatch):
    pe = make_linked_client(db, email="allowlisted@example.com")
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS", pe.email)
    assert product_locks_allowlist_configured() is True
    assert product_locks_enabled_for_person(db, pe.person_id) is False


def test_flag_on_allowlist_empty_fail_closed(db: Session, locks_on):
    pe = make_linked_client(db)
    assert product_locks_allowlist_configured() is False
    assert product_locks_enabled_for_person(db, pe.person_id) is False


def test_flag_on_user_allowlisted(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="locks-pilot@example.com")
    enable_product_locks_allowlist(monkeypatch, pe)
    assert product_locks_enabled_for_person(db, pe.person_id) is True


def test_flag_on_user_not_allowlisted(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="not-listed@example.com")
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS", "other@example.com")
    assert product_locks_enabled_for_person(db, pe.person_id) is False


def test_resolution_via_clients_email(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="client-email@example.com")
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS", pe.email)
    assert is_person_product_locks_allowlisted(db, pe.person_id) is True


def test_resolution_via_external_identity_email(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="ignored@example.com")
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=f"privy-{uuid.uuid4()}",
        external_email="external-match@example.com",
    )
    monkeypatch.setenv(
        "TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS",
        "external-match@example.com",
    )
    assert is_person_product_locks_allowlisted(db, pe.person_id) is True


def test_resolution_via_profile_collected_email(db: Session, locks_on, monkeypatch):
    pe = make_linked_client(db, email="ignored@example.com")
    person = db.query(Person).filter(Person.id == pe.person_id).one()
    person.profile_json = {
        "contact": {"collected_email": "  Profile@Example.COM "},
    }
    db.flush()
    monkeypatch.setenv(
        "TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS",
        "profile@example.com",
    )
    assert is_person_product_locks_allowlisted(db, pe.person_id) is True


def test_orchestrator_apply_respects_product_locks_allowlist(db: Session, monkeypatch, locks_on):
    pe = make_linked_client(db, email="orchestrator-locks@example.com")
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    enable_product_locks_allowlist(monkeypatch, pe)
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    _wallet(db, pe)
    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("5"),
    )
    db.commit()

    result = process_transaction_outbox_intent_created(db)
    assert result["processed"] == 1
    assert db.query(TransactionProductLock).count() == 1


def test_orchestrator_apply_skipped_when_not_product_locks_allowlisted(
    db: Session, monkeypatch, locks_on
):
    pe = make_linked_client(db, email="not-on-product-locks-list@example.com")
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS", "other@example.com")
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    _wallet(db, pe)
    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("3"),
    )
    db.commit()

    apply_result = apply_orchestrator_product_locks_before_queued(db, bundle.intent)
    assert apply_result.skipped is True
    assert apply_result.reason == "product_locks_not_enabled_for_person"
    assert db.query(TransactionProductLock).count() == 0
