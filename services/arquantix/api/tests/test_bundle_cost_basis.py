"""Tests reference_cost_basis_eur — pas de confusion USDC/EUR."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from services.portfolio_engine.bundle_execution.bundle_cost_basis import reference_cost_basis_eur


def test_usdc_amount_converted_to_eur_reference(db):
    # EURUSDT = USDT par 1 EUR (ex. ~1.16) → 100 USDC ≈ 86 EUR
    with patch(
        "services.portfolio_engine.bundle_execution.bundle_cost_basis.get_eurusdt_rate",
        return_value=Decimal("1.163"),
    ):
        out = reference_cost_basis_eur(db, "USDC", Decimal("100"))
    assert out == Decimal("85.98")


def test_eur_amount_unchanged(db):
    out = reference_cost_basis_eur(db, "EUR", Decimal("100"))
    assert out == Decimal("100.00")


def test_eurc_amount_unchanged(db):
    out = reference_cost_basis_eur(db, "EURC", Decimal("50"))
    assert out == Decimal("50.00")
