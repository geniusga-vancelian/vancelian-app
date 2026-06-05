"""Tests — minimum investissement bundle."""
from decimal import Decimal

import pytest

from services.portfolio_engine.bundle_execution.lifi_base_config import (
    BUNDLE_MIN_FUNDING_USDC,
    minimum_bundle_funding_amount,
)
from services.portfolio_engine.bundles.orchestrator import (
    BundleOrchestrator,
    BundleOrchestratorError,
)


def test_bundle_min_funding_usdc_constant():
    assert BUNDLE_MIN_FUNDING_USDC == Decimal("20")


def test_minimum_bundle_funding_amount_stablecoins():
    minimum, label = minimum_bundle_funding_amount("USDC")
    assert minimum == Decimal("20")
    assert label == "USDC"

    minimum_eurc, label_eurc = minimum_bundle_funding_amount("EURC")
    assert minimum_eurc == Decimal("20")
    assert label_eurc == "EURC"


def test_orchestrator_rejects_funding_below_min():
    with pytest.raises(BundleOrchestratorError) as exc:
        BundleOrchestrator._validate_funding_amount("USDC", Decimal("19.99"))
    assert "funding_amount_below_min" in str(exc.value)
    assert "20" in str(exc.value)


def test_orchestrator_accepts_funding_at_min():
    BundleOrchestrator._validate_funding_amount("USDC", Decimal("20"))
