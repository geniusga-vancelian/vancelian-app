"""Tests PR1 pour GET /api/app/transactions/{id}/operation-statement.pdf."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pdf.operation_statement_schema import OperationRefPayload, OperationStatementPayload

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import make_linked_client, mobile_auth_headers
from services.exchange.models import ExchangeOrder

from tests.test_transaction_detail import _setup_pipeline, _simulate_deposit


def _pdf_url(transaction_id: str) -> str:
    return f"/api/app/transactions/{transaction_id}/operation-statement.pdf"


def test_operation_statement_pdf_ok_for_completed_custody(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)
    _simulate_deposit(client, provider["name"], client_account["iban"], amount=1500)

    cash_res = client.get("/api/app/cash", headers=auth)
    assert cash_res.status_code == 200
    tx_id = cash_res.json()["recent_transactions"][0]["id"]

    pdf_res = client.get(_pdf_url(tx_id), headers=auth)
    # 200 si WeasyPrint disponible ; 503 en CI / macOS sans deps natives (comportement attendu PR1).
    assert pdf_res.status_code in (200, 503), pdf_res.text
    if pdf_res.status_code == 200:
        assert pdf_res.headers.get("content-type", "").startswith("application/pdf")
    else:
        detail = (pdf_res.json().get("detail") or "").lower()
        assert "pdf" in detail or "weasyprint" in detail


def test_operation_statement_pdf_unknown_id_has_error_code_header(client: TestClient, db: Session):
    pe_client = make_linked_client(db, email=f"opstmt-{uuid.uuid4().hex[:8]}@example.com")
    auth = mobile_auth_headers(db, pe_client)
    fake_id = str(uuid.uuid4())

    pdf_res = client.get(_pdf_url(fake_id), headers=auth)
    assert pdf_res.status_code == 404
    assert pdf_res.headers.get("X-Vancelian-Error-Code") == "operation_statement_not_found"


def test_operation_statement_pdf_wrong_client_is_404(client: TestClient, db: Session):
    provider, client_a, account_a = _setup_pipeline(client, db)
    auth_a = mobile_auth_headers(db, client_a)
    _simulate_deposit(client, provider["name"], account_a["iban"], amount=500)

    cash_res = client.get("/api/app/cash", headers=auth_a)
    tx_id = cash_res.json()["recent_transactions"][0]["id"]

    _, client_b, _ = _setup_pipeline(client, db)
    auth_b = mobile_auth_headers(db, client_b)

    pdf_res = client.get(_pdf_url(tx_id), headers=auth_b)
    assert pdf_res.status_code == 404
    assert pdf_res.headers.get("X-Vancelian-Error-Code") == "operation_statement_not_found"


def test_operation_statement_pdf_exchange_buy_completed(client: TestClient, db: Session):
    pe_client = make_linked_client(db, email=f"opstmt-{uuid.uuid4().hex[:8]}@example.com")
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
        external_reference=f"opstmt-pdf-{uuid.uuid4().hex}",
        from_asset="EUR",
        to_asset="BTC",
        amount_from=Decimal("5000"),
        amount_to=Decimal("0.1"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()

    pdf_res = client.get(_pdf_url(str(order_id)), headers=auth)
    assert pdf_res.status_code in (200, 503), pdf_res.text
    if pdf_res.status_code == 200:
        assert pdf_res.headers.get("content-type", "").startswith("application/pdf")


def test_operation_statement_pdf_exchange_sell_completed(client: TestClient, db: Session):
    pe_client = make_linked_client(db, email=f"opstmt-sell-{uuid.uuid4().hex[:8]}@example.com")
    auth = mobile_auth_headers(db, pe_client)

    order_id = uuid.uuid4()
    order = ExchangeOrder(
        id=order_id,
        client_id=pe_client.id,
        side="sell",
        asset="BTC",
        amount_crypto=Decimal("0.05"),
        amount_fiat=Decimal("4000"),
        price=Decimal("80000"),
        currency="EUR",
        status="completed",
        external_reference=f"opstmt-sell-{uuid.uuid4().hex}",
        from_asset="BTC",
        to_asset="EUR",
        amount_from=Decimal("0.05"),
        amount_to=Decimal("4000"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()

    pdf_res = client.get(_pdf_url(str(order_id)), headers=auth)
    assert pdf_res.status_code in (200, 503), pdf_res.text


def test_operation_statement_pdf_exchange_swap_completed(client: TestClient, db: Session):
    """Swap crypto↔crypto : montant principal = actif reçu (amount_to / to_asset)."""
    pe_client = make_linked_client(db, email=f"opstmt-swap-{uuid.uuid4().hex[:8]}@example.com")
    auth = mobile_auth_headers(db, pe_client)

    order_id = uuid.uuid4()
    order = ExchangeOrder(
        id=order_id,
        client_id=pe_client.id,
        side="buy",
        asset="BTC",
        amount_crypto=Decimal("0.05"),
        amount_fiat=Decimal("0"),
        price=Decimal("98000"),
        currency="EUR",
        status="completed",
        external_reference=f"opstmt-swap-{uuid.uuid4().hex}",
        from_asset="ETH",
        to_asset="BTC",
        amount_from=Decimal("1.5"),
        amount_to=Decimal("0.05"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()

    pdf_res = client.get(_pdf_url(str(order_id)), headers=auth)
    assert pdf_res.status_code in (200, 503), pdf_res.text


def test_operation_statement_pdf_exchange_swap_incomplete_returns_error(client: TestClient, db: Session):
    pe_client = make_linked_client(db, email=f"opstmt-swap-bad-{uuid.uuid4().hex[:8]}@example.com")
    auth = mobile_auth_headers(db, pe_client)

    order_id = uuid.uuid4()
    order = ExchangeOrder(
        id=order_id,
        client_id=pe_client.id,
        side="buy",
        asset="BTC",
        amount_crypto=Decimal("0.05"),
        amount_fiat=Decimal("0"),
        price=Decimal("98000"),
        currency="EUR",
        status="completed",
        external_reference=f"opstmt-swap-bad-{uuid.uuid4().hex}",
        from_asset="ETH",
        to_asset="BTC",
        amount_from=Decimal("1.5"),
        amount_to=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()

    pdf_res = client.get(_pdf_url(str(order_id)), headers=auth)
    assert pdf_res.status_code == 404
    assert pdf_res.headers.get("X-Vancelian-Error-Code") == "operation_statement_swap_incomplete"


def test_operation_statement_pdf_exchange_pending_returns_error(client: TestClient, db: Session):
    pe_client = make_linked_client(db, email=f"opstmt-pend-{uuid.uuid4().hex[:8]}@example.com")
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
        status="pending",
        external_reference=f"opstmt-pend-{uuid.uuid4().hex}",
        from_asset="EUR",
        to_asset="BTC",
        amount_from=Decimal("5000"),
        amount_to=Decimal("0.1"),
        created_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()

    pdf_res = client.get(_pdf_url(str(order_id)), headers=auth)
    assert pdf_res.status_code == 404
    assert pdf_res.headers.get("X-Vancelian-Error-Code") == "operation_statement_not_completed"


def test_operation_statement_payload_schema_instantiable():
    """PR2 : le contrat Pydantic est valide (sans rendu PDF)."""
    oid = str(uuid.uuid4())
    p = OperationStatementPayload(
        operation_ref=OperationRefPayload(source_system="custody", source_id=oid),
        operation_type="deposit",
        status="completed",
        title="Virement entrant",
        amount=Decimal("100.00"),
        currency="EUR",
        direction="credit",
        generated_at=datetime.now(timezone.utc),
    )
    assert p.operation_ref.source_id == oid
    assert p.direction == "credit"


def test_transaction_detail_includes_source_identity(client: TestClient, db: Session):
    provider, pe_client, client_account = _setup_pipeline(client, db)
    auth = mobile_auth_headers(db, pe_client)
    _simulate_deposit(client, provider["name"], client_account["iban"])

    cash_res = client.get("/api/app/cash", headers=auth)
    tx_id = cash_res.json()["recent_transactions"][0]["id"]

    detail_res = client.get(f"/api/app/transactions/{tx_id}", headers=auth)
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["source_system"] == "custody"
    assert data["source_id"] == str(tx_id)
