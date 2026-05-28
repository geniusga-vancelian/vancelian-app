"""Tests — valorisation stablecoin bundle (USDC 1:1 USD)."""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from services.portfolio_engine.bundle_execution.bundle_position_valuation import (
    resolve_bundle_position_market_values,
)


def test_usdc_cash_leg_valued_one_to_one_usd(db):
    valuation = resolve_bundle_position_market_values(
        db,
        symbol="USDC",
        quantity=Decimal("15"),
        instrument_id=uuid4(),
        eurusdt_rate=Decimal("1.08"),
    )
    assert valuation["market_value_usd"] == Decimal("15.00")
    assert valuation["market_value"] == Decimal("13.89")
    assert valuation["price_usd"] == Decimal("1")


def test_volatile_asset_still_uses_market_data(db, monkeypatch):
    instrument_id = uuid4()

    def _fake_price(_db, _instrument_id):
        return {"price": "50000"}

    monkeypatch.setattr(
        "services.portfolio_engine.bundle_execution.bundle_position_valuation.get_instrument_price",
        _fake_price,
    )

    valuation = resolve_bundle_position_market_values(
        db,
        symbol="CBBTC",
        quantity=Decimal("0.001"),
        instrument_id=instrument_id,
        eurusdt_rate=Decimal("1.08"),
    )
    assert valuation["market_value_usd"] == Decimal("50.00")
    assert valuation["price_usd"] == Decimal("50000")
