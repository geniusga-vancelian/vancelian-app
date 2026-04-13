"""
Unit tests for Bundle validation with discriminated union
Tests for InstrumentComponentBase and BundleComponentBase discriminated union
"""
import pytest
from decimal import Decimal
from pydantic import ValidationError

from services.bundles.schemas import (
    BundleCreate,
    InstrumentComponentBase,
    BundleComponentBase,
    BundleComponentIn,
)


# Test 1: Create fixed bundle with instrument component (OK)
def test_create_fixed_bundle_instrument_ok():
    """Test 1: Create fixed bundle with instrument component - should succeed"""
    request = BundleCreate(
        name="Test Bundle",
        asset_class="crypto",
        type="fixed_instruments",
        components=[
            {
                "component_type": "instrument",
                "instrument_code": "BTCUSD",
                "weight": Decimal("100.0"),
                "position_order": 0,
            }
        ],
    )
    assert request.name == "Test Bundle"
    assert len(request.components) == 1
    comp = request.components[0]
    assert comp.component_type == "instrument"
    assert isinstance(comp, InstrumentComponentBase)
    assert comp.instrument_code == "BTCUSD"
    assert comp.weight == Decimal("100.0")
    # Verify child_bundle_id is NOT present
    assert not hasattr(comp, "child_bundle_id") or comp.child_bundle_id is None


# Test 2: Reject instrument component with child_bundle_id present
def test_reject_instrument_component_with_bundle_id():
    """Test 2: Reject instrument component if child_bundle_id is present - should fail"""
    with pytest.raises(ValidationError) as exc_info:
        BundleCreate(
            name="Test Bundle",
            asset_class="crypto",
            type="fixed_instruments",
            components=[
                {
                    "component_type": "instrument",
                    "instrument_code": "BTCUSD",
                    "child_bundle_id": 1,  # Should be rejected
                    "weight": Decimal("100.0"),
                }
            ],
        )
    
    errors = exc_info.value.errors()
    # Should have an error about extra field or XOR violation
    assert any(
        "child_bundle_id" in str(err.get("loc", [])).lower() or 
        "extra" in str(err.get("msg", "")).lower() or
        "forbidden" in str(err.get("msg", "")).lower()
        for err in errors
    ), f"Expected error about child_bundle_id, got: {errors}"


# Test 3: Reject instrument component with instrument_code missing/null
def test_reject_instrument_component_missing_instrument_code():
    """Test 3: Reject instrument component if instrument_code is missing or null - should fail"""
    # Test with None
    with pytest.raises(ValidationError) as exc_info:
        BundleCreate(
            name="Test Bundle",
            asset_class="crypto",
            type="fixed_instruments",
            components=[
                {
                    "component_type": "instrument",
                    # instrument_code missing
                    "weight": Decimal("100.0"),
                }
            ],
        )
    
    errors = exc_info.value.errors()
    assert any(
        "instrument_code" in str(err.get("loc", [])).lower() or
        "required" in str(err.get("msg", "")).lower()
        for err in errors
    ), f"Expected error about missing instrument_code, got: {errors}"
    
    # Test with empty string
    with pytest.raises(ValidationError) as exc_info2:
        BundleCreate(
            name="Test Bundle",
            asset_class="crypto",
            type="fixed_instruments",
            components=[
                {
                    "component_type": "instrument",
                    "instrument_code": "",  # Empty string should be rejected
                    "weight": Decimal("100.0"),
                }
            ],
        )
    
    errors2 = exc_info2.value.errors()
    assert any(
        "instrument_code" in str(err.get("loc", [])).lower() or
        "null" in str(err.get("msg", "")).lower() or
        "empty" in str(err.get("msg", "")).lower()
        for err in errors2
    ), f"Expected error about empty instrument_code, got: {errors2}"


# Test 4: Create composite bundle with bundle components (OK)
def test_create_composite_bundle_ok():
    """Test 4: Create composite bundle with bundle components - should succeed"""
    # This test assumes we can create bundles, which requires DB access
    # For unit testing, we just validate the schema structure
    request = BundleCreate(
        name="Composite Bundle",
        asset_class="crypto",
        type="composite_fixed",
        components=[
            {
                "component_type": "bundle",
                "child_bundle_id": 1,
                "weight": Decimal("100.0"),
                "position_order": 0,
            }
        ],
    )
    assert request.name == "Composite Bundle"
    assert request.type == "composite_fixed"
    assert len(request.components) == 1
    comp = request.components[0]
    assert comp.component_type == "bundle"
    assert isinstance(comp, BundleComponentBase)
    assert comp.child_bundle_id == 1
    assert comp.weight == Decimal("100.0")
    # Verify instrument_code is NOT present
    assert not hasattr(comp, "instrument_code") or comp.instrument_code is None


# Test 5: Reject bundle component with instrument_code present
def test_reject_bundle_component_with_instrument_code():
    """Test 5: Reject bundle component if instrument_code is present - should fail"""
    with pytest.raises(ValidationError) as exc_info:
        BundleCreate(
            name="Test Bundle",
            asset_class="crypto",
            type="composite_fixed",
            components=[
                {
                    "component_type": "bundle",
                    "child_bundle_id": 1,
                    "instrument_code": "BTCUSD",  # Should be rejected
                    "weight": Decimal("100.0"),
                }
            ],
        )
    
    errors = exc_info.value.errors()
    # Should have an error about extra field
    assert any(
        "instrument_code" in str(err.get("loc", [])).lower() or
        "extra" in str(err.get("msg", "")).lower() or
        "forbidden" in str(err.get("msg", "")).lower()
        for err in errors
    ), f"Expected error about instrument_code, got: {errors}"


# Test 6: Reject nulls (child_bundle_id=null, instrument_code=null)
def test_reject_nulls():
    """Test 6: Reject null values for required fields - should fail"""
    # Test instrument component with null instrument_code (via missing field)
    with pytest.raises(ValidationError) as exc_info:
        BundleCreate(
            name="Test Bundle",
            asset_class="crypto",
            type="fixed_instruments",
            components=[
                {
                    "component_type": "instrument",
                    "instrument_code": None,  # Explicit null
                    "weight": Decimal("100.0"),
                }
            ],
        )
    
    errors = exc_info.value.errors()
    assert any(
        "instrument_code" in str(err.get("loc", [])).lower() or
        "null" in str(err.get("msg", "")).lower() or
        "required" in str(err.get("msg", "")).lower()
        for err in errors
    ), f"Expected error about null instrument_code, got: {errors}"
    
    # Test bundle component with null child_bundle_id
    with pytest.raises(ValidationError) as exc_info2:
        BundleCreate(
            name="Test Bundle",
            asset_class="crypto",
            type="composite_fixed",
            components=[
                {
                    "component_type": "bundle",
                    "child_bundle_id": None,  # Explicit null
                    "weight": Decimal("100.0"),
                }
            ],
        )
    
    errors2 = exc_info2.value.errors()
    assert any(
        "child_bundle_id" in str(err.get("loc", [])).lower() or
        "null" in str(err.get("msg", "")).lower() or
        "required" in str(err.get("msg", "")).lower() or
        "greater than" in str(err.get("msg", "")).lower()
        for err in errors2
    ), f"Expected error about null child_bundle_id, got: {errors2}"


# Additional test: Verify discriminated union works correctly
def test_discriminated_union_selection():
    """Test that Pydantic correctly selects the right variant based on component_type"""
    # Instrument variant
    inst_comp_dict = {
        "component_type": "instrument",
        "instrument_code": "BTCUSD",
        "weight": Decimal("100.0"),  # Must sum to 100%
    }
    # This should create an InstrumentComponentBase instance when used in BundleCreate
    request1 = BundleCreate(
        name="Test",
        asset_class="crypto",
        type="fixed_instruments",
        components=[inst_comp_dict],
    )
    assert isinstance(request1.components[0], InstrumentComponentBase)
    
    # Bundle variant
    bundle_comp_dict = {
        "component_type": "bundle",
        "child_bundle_id": 1,
        "weight": Decimal("100.0"),  # Must sum to 100%
    }
    request2 = BundleCreate(
        name="Test",
        asset_class="crypto",
        type="composite_fixed",
        components=[bundle_comp_dict],
    )
    assert isinstance(request2.components[0], BundleComponentBase)

