"""Tests PR5 — snapshots OperationStatementPayload (hash stable, persistance, relecture)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import make_linked_client, mobile_auth_headers
from pdf.operation_statement_schema import OperationRefPayload, OperationStatementPayload
from services.exchange.models import ExchangeOrder
from services.test_clients.operation_statement_snapshot_model import ClientOperationStatementSnapshot
from services.test_clients.operation_statement_snapshot_service import (
    canonical_json_bytes,
    compute_hash_from_payload_dict,
    compute_payload_hash,
    payload_to_storable_dict,
)

from tests.test_transaction_detail import _setup_pipeline, _simulate_deposit


def _pdf_url(transaction_id: str) -> str:
    return f"/api/app/transactions/{transaction_id}/operation-statement.pdf"


def _sample_payload(**kwargs) -> OperationStatementPayload:
    base = dict(
        operation_ref=OperationRefPayload(source_system="custody", source_id=str(uuid.uuid4())),
        operation_type="deposit",
        status="completed",
        title="Virement entrant",
        amount=Decimal("100.00"),
        currency="EUR",
        direction="credit",
        generated_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    base.update(kwargs)
    return OperationStatementPayload(**base)


def test_compute_payload_hash_stable_for_identical_payload():
    p = _sample_payload()
    assert compute_payload_hash(p) == compute_payload_hash(p)


def test_compute_payload_hash_differs_when_payload_differs():
    a = _sample_payload(title="A")
    b = _sample_payload(title="B")
    assert compute_payload_hash(a) != compute_payload_hash(b)


def test_canonical_json_sorts_keys_nested():
    d = {"z": 1, "a": {"m": 2, "b": 3}}
    s1 = canonical_json_bytes(d).decode()
    s2 = canonical_json_bytes({"a": {"b": 3, "m": 2}, "z": 1}).decode()
    assert s1 == s2


def test_compute_hash_from_payload_dict_matches_model_dump():
    p = _sample_payload()
    d = payload_to_storable_dict(p)
    assert compute_payload_hash(p) == compute_hash_from_payload_dict(d)


def test_operation_statement_snapshot_created_after_first_successful_pdf(
    client: TestClient, db: Session
):
    """Premier GET PDF réussi → une ligne snapshot pour (client, custody, tx)."""
    provider, pe_client, client_account = _setup_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)
    _simulate_deposit(client, provider["name"], client_account["iban"], amount=1500)

    cash_res = client.get("/api/app/cash", headers=auth)
    assert cash_res.status_code == 200
    tx_id = cash_res.json()["recent_transactions"][0]["id"]
    tx_uuid = uuid.UUID(str(tx_id))

    pdf_res = client.get(_pdf_url(tx_id), headers=auth)
    if pdf_res.status_code != 200:
        pytest.skip("WeasyPrint indisponible — snapshot non créé sans PDF réussi")

    n = (
        db.query(ClientOperationStatementSnapshot)
        .filter(
            ClientOperationStatementSnapshot.client_id == pe_client.id,
            ClientOperationStatementSnapshot.source_system == "custody",
            ClientOperationStatementSnapshot.source_id == tx_uuid,
        )
        .count()
    )
    assert n == 1


def test_operation_statement_snapshot_freezes_payload_after_source_mutation(
    client: TestClient, db: Session
):
    """Après snapshot, une mutation métier ne change pas le hash stocké au second GET."""
    from services.custody.models import CustodyTransaction

    provider, pe_client, client_account = _setup_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)
    _simulate_deposit(client, provider["name"], client_account["iban"], amount=800)

    cash_res = client.get("/api/app/cash", headers=auth)
    tx_id = cash_res.json()["recent_transactions"][0]["id"]
    tx_uuid = uuid.UUID(str(tx_id))

    pdf1 = client.get(_pdf_url(tx_id), headers=auth)
    if pdf1.status_code != 200:
        pytest.skip("WeasyPrint indisponible")

    row1 = (
        db.query(ClientOperationStatementSnapshot)
        .filter(
            ClientOperationStatementSnapshot.client_id == pe_client.id,
            ClientOperationStatementSnapshot.source_system == "custody",
            ClientOperationStatementSnapshot.source_id == tx_uuid,
        )
        .one()
    )
    h1 = row1.content_sha256

    tx = db.query(CustodyTransaction).filter(CustodyTransaction.id == tx_uuid).one()
    meta = dict(tx.metadata_ or {})
    meta["remitter_name"] = f"MUTATED-{uuid.uuid4().hex[:8]}"
    tx.metadata_ = meta
    db.add(tx)
    db.commit()

    pdf2 = client.get(_pdf_url(tx_id), headers=auth)
    assert pdf2.status_code == 200

    row2 = (
        db.query(ClientOperationStatementSnapshot)
        .filter(
            ClientOperationStatementSnapshot.client_id == pe_client.id,
            ClientOperationStatementSnapshot.source_system == "custody",
            ClientOperationStatementSnapshot.source_id == tx_uuid,
        )
        .one()
    )
    assert row2.content_sha256 == h1
    assert row2.id == row1.id


def test_operation_statement_snapshot_exchange_stable_after_order_mutation(
    client: TestClient, db: Session
):
    pe_client = make_linked_client(db, email=f"snap-ex-{uuid.uuid4().hex[:8]}@example.com")
    auth = mobile_auth_headers(db, pe_client)

    order_id = uuid.uuid4()
    order = ExchangeOrder(
        id=order_id,
        client_id=pe_client.id,
        side="buy",
        asset="BTC",
        amount_crypto=Decimal("0.1"),
        amount_fiat=Decimal("5000"),
        price=Decimal("50000"),
        currency="EUR",
        status="completed",
        external_reference=f"opstmt-snap-{uuid.uuid4().hex}",
        from_asset="EUR",
        to_asset="BTC",
        amount_from=Decimal("5000"),
        amount_to=Decimal("0.1"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()

    pdf1 = client.get(_pdf_url(str(order_id)), headers=auth)
    if pdf1.status_code != 200:
        pytest.skip("WeasyPrint indisponible")

    row1 = (
        db.query(ClientOperationStatementSnapshot)
        .filter(
            ClientOperationStatementSnapshot.client_id == pe_client.id,
            ClientOperationStatementSnapshot.source_system == "exchange",
            ClientOperationStatementSnapshot.source_id == order_id,
        )
        .one()
    )
    h1 = row1.content_sha256

    order2 = db.query(ExchangeOrder).filter(ExchangeOrder.id == order_id).one()
    order2.price = Decimal("99999")
    db.add(order2)
    db.commit()

    pdf2 = client.get(_pdf_url(str(order_id)), headers=auth)
    assert pdf2.status_code == 200

    row2 = (
        db.query(ClientOperationStatementSnapshot)
        .filter(
            ClientOperationStatementSnapshot.client_id == pe_client.id,
            ClientOperationStatementSnapshot.source_system == "exchange",
            ClientOperationStatementSnapshot.source_id == order_id,
        )
        .one()
    )
    assert row2.content_sha256 == h1
