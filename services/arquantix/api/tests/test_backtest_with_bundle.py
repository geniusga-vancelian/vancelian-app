"""
Integration tests for backtest with bundle support
"""
import pytest
from datetime import date
from sqlalchemy.orm import Session

from database import get_db, MarketDataInstrument, MarketDataBarD1, Bundle, BundleComponent
from services.backtest.schemas import BacktestCreateRequest
from services.backtest.routes import run_backtest
from auth import AdminUser


@pytest.fixture
def db_session():
    """Get database session"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_instrument(db_session: Session):
    """Create a test instrument with bars"""
    instrument = MarketDataInstrument(
        symbol="TEST",
        name="Test Instrument",
        asset_class="crypto",
        weekend_tradable="true",
        provider="binance",
        provider_symbol="TEST-USD",
        is_active="true",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    
    # Add a few bars
    for i in range(10):
        bar = MarketDataBarD1(
            instrument_id=instrument.id,
            date=date(2024, 1, 1 + i),
            open=100.0 + i,
            high=110.0 + i,
            low=90.0 + i,
            close=105.0 + i,
            volume=1000 + i * 100,
            source="binance",
        )
        db_session.add(bar)
    
    db_session.commit()
    return instrument


@pytest.fixture
def test_bundle(db_session: Session, test_instrument):
    """Create a test bundle"""
    bundle = Bundle(
        name="Test Bundle",
        asset_class="crypto",
        type="fixed_instruments",
        is_active="true",
    )
    db_session.add(bundle)
    db_session.commit()
    db_session.refresh(bundle)
    
    # Add component
    component = BundleComponent(
        bundle_id=bundle.id,
        component_type="instrument",
        instrument_id=test_instrument.id,
        weight=100.0,
    )
    db_session.add(component)
    db_session.commit()
    
    return bundle


def test_backtest_create_request_with_bundle_id():
    """Test that BacktestCreateRequest accepts bundle_id without instrument_ids"""
    request = BacktestCreateRequest(
        start_date="2024-01-01",
        end_date="2024-12-31",
        bundle_id=1,
        strategy={"type": "equal_weight"},
    )
    assert request.bundle_id == 1
    assert request.instrument_ids is None


def test_backtest_create_request_with_instrument_ids():
    """Test that BacktestCreateRequest accepts instrument_ids without bundle_id"""
    request = BacktestCreateRequest(
        start_date="2024-01-01",
        end_date="2024-12-31",
        instrument_ids=[1, 2, 3],
        strategy={"type": "equal_weight"},
    )
    assert request.bundle_id is None
    assert request.instrument_ids == [1, 2, 3]


def test_backtest_create_request_rejects_missing_both():
    """Test that BacktestCreateRequest rejects when neither bundle_id nor instrument_ids provided"""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError) as exc_info:
        BacktestCreateRequest(
            start_date="2024-01-01",
            end_date="2024-12-31",
            strategy={"type": "equal_weight"},
        )
    
    errors = exc_info.value.errors()
    assert any("bundle_id or instrument_ids" in str(err.get("msg", "")).lower() for err in errors)


def test_backtest_create_request_accepts_both():
    """Test that BacktestCreateRequest accepts both bundle_id and instrument_ids (bundle_id takes precedence)"""
    request = BacktestCreateRequest(
        start_date="2024-01-01",
        end_date="2024-12-31",
        bundle_id=1,
        instrument_ids=[1, 2, 3],  # Will be ignored if bundle_id is set
        strategy={"type": "equal_weight"},
    )
    assert request.bundle_id == 1
    assert request.instrument_ids == [1, 2, 3]  # Still present but backend will use bundle_id

