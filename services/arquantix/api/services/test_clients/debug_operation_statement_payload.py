"""
Payload factice pour ``?debug_sample=true`` — design / QA sans lecture DB.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from pdf.operation_statement_schema import (
    OperationRefPayload,
    OperationStatementAssetImpact,
    OperationStatementBalanceContext,
    OperationStatementDetailRow,
    OperationStatementFeeItem,
    OperationStatementPayload,
    OperationStatementPersonBlock,
    OperationStatementReferences,
)


def build_debug_operation_statement_payload() -> OperationStatementPayload:
    """Achat spot BTC vs EUR — montants élevés, plusieurs jambes, frais, méta longues."""
    oid = str(uuid4())
    return OperationStatementPayload(
        operation_ref=OperationRefPayload(source_system="exchange", source_id=oid),
        operation_type="exchange_buy",
        status="completed",
        title="Achat Bitcoin (spot)",
        subtitle="Contrepartie EUR — exécution sur carnet d’ordres (exemple design)",
        amount=Decimal("125000.00"),
        currency="EUR",
        direction="debit",
        booking_date=date.today(),
        generated_at=datetime.now(timezone.utc),
        custody_pdf=None,
        balance_context=OperationStatementBalanceContext(applicable=False),
        person=OperationStatementPersonBlock(
            full_name="Jean Dupont — profil de test design très long pour vérifier les retours à la ligne",
            address_line_1="42 avenue des Champs-Élysées, bâtiment B, étage 7",
            postal_code="75008",
            city="Paris",
            country="FR",
        ),
        execution_detail_rows=[
            OperationStatementDetailRow(
                label="Contrepartie / lieu d’exécution",
                value="Binance Europe Services Limited — carnet centralisé (exemple)",
            ),
            OperationStatementDetailRow(
                label="Prix moyen indicatif",
                value="98 250,45 EUR pour 1,00000000 BTC (arrondi affichage)",
            ),
            OperationStatementDetailRow(
                label="Référence interne",
                value="DBG-SAMPLE-2026-04-13 — chaîne volontairement longue pour stresser le gabarit PDF",
            ),
        ],
        asset_impacts=[
            OperationStatementAssetImpact(
                flow="out",
                asset="EUR",
                amount=Decimal("125000.00"),
                unit_kind="fiat",
            ),
            OperationStatementAssetImpact(
                flow="in",
                asset="BTC",
                amount=Decimal("1.27384921"),
                unit_kind="crypto",
            ),
            OperationStatementAssetImpact(
                flow="out",
                asset="EUR",
                amount=Decimal("15.50"),
                unit_kind="fiat",
            ),
        ],
        fees=[
            OperationStatementFeeItem(amount=Decimal("12.75"), asset="EUR"),
            OperationStatementFeeItem(amount=Decimal("0.00005"), asset="BTC"),
        ],
        references=OperationStatementReferences(
            order_id=oid,
            external_reference="EXT-REF-DEBUG-SAMPLE-VERY-LONG-IDENTIFIER-123456789",
        ),
        metadata_snapshot={
            "debug_sample": True,
            "purpose": "design_iteration",
            "note": "Aucune donnée réelle — payload statique pour tests UI/PDF.",
        },
    )
