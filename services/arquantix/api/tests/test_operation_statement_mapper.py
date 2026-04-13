"""Tests unitaires mapper / HTML relevé d'opération (sans WeasyPrint)."""

from datetime import date, datetime, timezone
from decimal import Decimal

from pdf.operation_statement_mapper import (
    custody_operation_payload_to_template_context,
    exchange_operation_payload_to_template_context,
    operation_statement_payload_to_template_context,
)
from pdf.operation_statement_renderer import render_operation_statement_html
from pdf.operation_statement_schema import (
    OperationRefPayload,
    OperationStatementAssetImpact,
    OperationStatementBalanceContext,
    OperationStatementCustodyPdfSection,
    OperationStatementDetailRow,
    OperationStatementPayload,
    OperationStatementPdfLine,
    OperationStatementPersonBlock,
    OperationStatementReferences,
)


def test_custody_operation_payload_to_template_context_structure():
    booking = date(2026, 3, 15)
    payload = OperationStatementPayload(
        operation_ref=OperationRefPayload(source_system="custody", source_id="550e8400-e29b-41d4-a716-446655440000"),
        operation_type="deposit",
        status="completed",
        title="Virement entrant",
        subtitle="Alice",
        amount=Decimal("100.00"),
        currency="EUR",
        direction="credit",
        booking_date=booking,
        generated_at=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        custody_pdf=OperationStatementCustodyPdfSection(
            period_heading="Transaction datée du 15 mars 2026",
            client_full_name="Test Client",
            address_line_1="1 rue Test",
            postal_code="75001",
            city="Paris",
            country="FR",
            account_currency="EUR",
            iban="FR7630001007941234567890185",
            bic="BNPAFRPP",
            account_number="12345678901",
            opening_balance=Decimal("900.00"),
            closing_balance=Decimal("1000.00"),
            money_in=Decimal("100.00"),
            money_out=None,
            lines=[
                OperationStatementPdfLine(
                    booking_date=booking,
                    description="Virement entrant — Alice\n\nID transaction : x",
                    amount_in=Decimal("100.00"),
                    amount_out=None,
                    balance_after=Decimal("1000.00"),
                )
            ],
        ),
    )

    ctx = custody_operation_payload_to_template_context(payload)
    assert ctx["layout"]["mode"] == "custody"
    assert ctx["presentation"]["badge"] == "Dépôt"
    assert ctx["presentation"]["primary_label"] == "Virement entrant"
    assert ctx["meta"]["period_heading"] == "Transaction datée du 15 mars 2026"
    assert ctx["client"]["full_name"] == "Test Client"
    assert ctx["summary"]["opening_balance_display"].startswith("900")
    assert len(ctx["transactions"]) == 1
    assert "+" in ctx["transactions"][0]["credit_display"]


def test_operation_statement_html_renders_from_mapper():
    booking = date(2026, 3, 15)
    payload = OperationStatementPayload(
        operation_ref=OperationRefPayload(source_system="custody", source_id="550e8400-e29b-41d4-a716-446655440000"),
        operation_type="deposit",
        status="completed",
        title="Virement entrant",
        amount=Decimal("50.00"),
        currency="EUR",
        direction="credit",
        booking_date=booking,
        generated_at=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        custody_pdf=OperationStatementCustodyPdfSection(
            period_heading="Transaction datée du 15 mars 2026",
            client_full_name="X",
            address_line_1="—",
            postal_code="—",
            city="—",
            country="—",
            account_currency="EUR",
            iban="—",
            bic="—",
            account_number="—",
            opening_balance=Decimal("0"),
            closing_balance=Decimal("50"),
            money_in=Decimal("50"),
            money_out=None,
            lines=[
                OperationStatementPdfLine(
                    booking_date=booking,
                    description="Desc",
                    amount_in=Decimal("50"),
                    amount_out=None,
                    balance_after=Decimal("50"),
                )
            ],
        ),
    )
    ctx = custody_operation_payload_to_template_context(payload)
    assert ctx["layout"]["mode"] == "custody"
    html = render_operation_statement_html(ctx)
    assert "Relevé d" in html and "opération" in html
    assert "operation_statement.css" in html
    assert "Contexte sur le compte" in html
    assert "opstmt-hero" in html


def test_exchange_operation_payload_to_template_context_no_balance_block():
    booking = date(2026, 3, 20)
    payload = OperationStatementPayload(
        operation_ref=OperationRefPayload(source_system="exchange", source_id="550e8400-e29b-41d4-a716-446655440001"),
        operation_type="exchange_buy",
        status="completed",
        title="Achat BTC",
        subtitle="5 000,00 EUR",
        amount=Decimal("5000"),
        currency="EUR",
        direction="debit",
        booking_date=booking,
        generated_at=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        custody_pdf=None,
        balance_context=OperationStatementBalanceContext(applicable=False),
        person=OperationStatementPersonBlock(
            full_name="Jane Doe",
            address_line_1="10 rue X",
            postal_code="75002",
            city="Paris",
            country="FR",
        ),
        execution_detail_rows=[
            OperationStatementDetailRow(label="Actif", value="BTC"),
            OperationStatementDetailRow(label="Sens", value="Achat"),
        ],
        asset_impacts=[
            OperationStatementAssetImpact(
                flow="out", asset="EUR", amount=Decimal("5000"), unit_kind="fiat"
            ),
            OperationStatementAssetImpact(
                flow="in", asset="BTC", amount=Decimal("0.1"), unit_kind="crypto"
            ),
        ],
        fees=[],
        references=OperationStatementReferences(
            order_id="550e8400-e29b-41d4-a716-446655440001",
            external_reference="EXT-1",
        ),
    )

    ctx = exchange_operation_payload_to_template_context(payload)
    assert ctx["layout"]["mode"] == "exchange"
    assert ctx["meta"]["hide_balance_summary"] is True
    assert len(ctx["asset_impact_rows"]) == 2
    assert ctx["transactions"] == []

    unified = operation_statement_payload_to_template_context(payload)
    assert unified["layout"]["mode"] == "exchange"
    ex_html = render_operation_statement_html(unified)
    assert "Flux de l" in ex_html and "opération" in ex_html
