"""
Tests for bundle resolver
"""
import pytest
from datetime import date
from sqlalchemy.orm import Session
from decimal import Decimal

from database import MarketDataBundle, BundleComponent, MarketDataInstrument
from services.bundles.resolver import resolve_bundle_effective_weights
from services.bundles.errors import BundleValidationError


def test_resolver_converts_percent_to_fraction_if_needed(db: Session):
    """Test that resolver converts percentage weights (0-100) to fractions (0-1)"""
    # Create a bundle with percentage weights
    bundle = MarketDataBundle(
        name="Test Bundle",
        asset_class="crypto",
        type="fixed_instruments",
        is_active="true",
    )
    db.add(bundle)
    db.flush()
    
    # Create instruments
    inst1 = MarketDataInstrument(symbol="BTC", name="Bitcoin", asset_class="crypto", is_active="true")
    inst2 = MarketDataInstrument(symbol="ETH", name="Ethereum", asset_class="crypto", is_active="true")
    db.add_all([inst1, inst2])
    db.flush()
    
    # Create components with percentage weights (80%, 20%)
    comp1 = BundleComponent(
        bundle_id=bundle.id,
        component_type="instrument",
        instrument_id=inst1.id,
        weight=Decimal("80.0"),  # 80% in DB
        position_order=0,
    )
    comp2 = BundleComponent(
        bundle_id=bundle.id,
        component_type="instrument",
        instrument_id=inst2.id,
        weight=Decimal("20.0"),  # 20% in DB
        position_order=1,
    )
    db.add_all([comp1, comp2])
    db.commit()
    
    # Resolve weights (should convert to fractions)
    weights = resolve_bundle_effective_weights(db, bundle.id, date.today())
    
    # Verify conversion: 80% -> 0.8, 20% -> 0.2
    assert weights[inst1.id] == pytest.approx(0.8, abs=1e-6)
    assert weights[inst2.id] == pytest.approx(0.2, abs=1e-6)
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)


def test_resolver_rejects_sum_not_one_after_conversion(db: Session):
    """Test that resolver rejects weights that don't sum to 1.0 after conversion"""
    # Create a bundle with invalid weights (sum != 100%)
    bundle = MarketDataBundle(
        name="Invalid Bundle",
        asset_class="crypto",
        type="fixed_instruments",
        is_active="true",
    )
    db.add(bundle)
    db.flush()
    
    # Create instruments
    inst1 = MarketDataInstrument(symbol="BTC", name="Bitcoin", asset_class="crypto", is_active="true")
    inst2 = MarketDataInstrument(symbol="ETH", name="Ethereum", asset_class="crypto", is_active="true")
    db.add_all([inst1, inst2])
    db.flush()
    
    # Create components with invalid weights (60%, 30% = 90% total)
    comp1 = BundleComponent(
        bundle_id=bundle.id,
        component_type="instrument",
        instrument_id=inst1.id,
        weight=Decimal("60.0"),  # 60% in DB
        position_order=0,
    )
    comp2 = BundleComponent(
        bundle_id=bundle.id,
        component_type="instrument",
        instrument_id=inst2.id,
        weight=Decimal("30.0"),  # 30% in DB (should be 40%)
        position_order=1,
    )
    db.add_all([comp1, comp2])
    db.commit()
    
    # Resolve weights should raise BundleValidationError
    with pytest.raises(BundleValidationError) as exc_info:
        resolve_bundle_effective_weights(db, bundle.id, date.today())
    
    # Verify error message mentions sum != 1.0
    assert "sum to" in str(exc_info.value.message).lower()
    assert "expected 1.0" in str(exc_info.value.message).lower()
    assert exc_info.value.bundle_id == bundle.id


def test_resolver_rejects_non_positive_weights(db: Session):
    """Test that resolver rejects non-positive weights"""
    # Create a bundle with negative weight
    bundle = MarketDataBundle(
        name="Invalid Bundle",
        asset_class="crypto",
        type="fixed_instruments",
        is_active="true",
    )
    db.add(bundle)
    db.flush()
    
    # Create instrument
    inst1 = MarketDataInstrument(symbol="BTC", name="Bitcoin", asset_class="crypto", is_active="true")
    db.add(inst1)
    db.flush()
    
    # Create component with negative weight
    comp1 = BundleComponent(
        bundle_id=bundle.id,
        component_type="instrument",
        instrument_id=inst1.id,
        weight=Decimal("-10.0"),  # Negative weight
        position_order=0,
    )
    db.add(comp1)
    db.commit()
    
    # Resolve weights should raise BundleValidationError
    with pytest.raises(BundleValidationError) as exc_info:
        resolve_bundle_effective_weights(db, bundle.id, date.today())
    
    # Verify error message mentions non-positive weight
    assert "non-positive" in str(exc_info.value.message).lower()
    assert exc_info.value.bundle_id == bundle.id

