"""
Tests for smart Yahoo HTML ingestion with conflict detection
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataBarD1, get_db
from services.market_data.ingest_service import (
    analyze_ingest_conflicts,
    apply_ingest,
    BarRow,
    ConflictMismatch,
)
from services.market_data.yahoo_html_parser import ParsedBar


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
    """Create a test instrument"""
    instrument = MarketDataInstrument(
        symbol="TEST",
        name="Test Instrument",
        asset_class="crypto",
        weekend_tradable="true",
        provider="yahoo",
        provider_symbol="TEST-USD",
        is_active="true",
    )
    db_session.add(instrument)
    db_session.commit()
    db_session.refresh(instrument)
    return instrument


def test_analyze_no_existing_data(db_session: Session, test_instrument):
    """Test analysis when no existing data"""
    incoming = [
        ParsedBar(date(2025, 1, 1), Decimal("100"), Decimal("110"), Decimal("95"), Decimal("105"), 1000),
        ParsedBar(date(2025, 1, 2), Decimal("105"), Decimal("115"), Decimal("100"), Decimal("110"), 1200),
    ]
    
    analysis = analyze_ingest_conflicts(db_session, test_instrument.id, incoming, source="yahoo")
    
    assert analysis.incoming_count == 2
    assert analysis.existing_count == 0
    assert analysis.overlap_count == 0
    assert analysis.mismatch_count == 0
    assert analysis.delta_count == 2
    assert not analysis.has_conflict


def test_analyze_coherent_overlap(db_session: Session, test_instrument):
    """Test analysis with coherent overlap (no conflicts)"""
    # Insert existing bars
    existing_bars = [
        MarketDataBarD1(
            instrument_id=test_instrument.id,
            date=date(2025, 1, 1),
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("95"),
            close=Decimal("105"),
            volume=1000,
            source="yahoo",
        ),
        MarketDataBarD1(
            instrument_id=test_instrument.id,
            date=date(2025, 1, 2),
            open=Decimal("105"),
            high=Decimal("115"),
            low=Decimal("100"),
            close=Decimal("110"),
            volume=1200,
            source="yahoo",
        ),
    ]
    for bar in existing_bars:
        db_session.add(bar)
    db_session.commit()
    
    # Incoming data with same values (coherent)
    incoming = [
        ParsedBar(date(2025, 1, 1), Decimal("100"), Decimal("110"), Decimal("95"), Decimal("105"), 1000),
        ParsedBar(date(2025, 1, 2), Decimal("105"), Decimal("115"), Decimal("100"), Decimal("110"), 1200),
        ParsedBar(date(2025, 1, 3), Decimal("110"), Decimal("120"), Decimal("105"), Decimal("115"), 1300),  # New
    ]
    
    analysis = analyze_ingest_conflicts(db_session, test_instrument.id, incoming, source="yahoo")
    
    assert analysis.incoming_count == 3
    assert analysis.existing_count == 2
    assert analysis.overlap_count == 2
    assert analysis.mismatch_count == 0
    assert analysis.delta_count == 1  # Only date 2025-01-03 is new
    assert not analysis.has_conflict


def test_analyze_conflict_detection(db_session: Session, test_instrument):
    """Test conflict detection when values differ"""
    # Insert existing bar
    existing = MarketDataBarD1(
        instrument_id=test_instrument.id,
        date=date(2025, 1, 1),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=1000,
        source="yahoo",
    )
    db_session.add(existing)
    db_session.commit()
    
    # Incoming with different close price
    incoming = [
        ParsedBar(date(2025, 1, 1), Decimal("100"), Decimal("110"), Decimal("95"), Decimal("107"), 1000),  # close differs
    ]
    
    analysis = analyze_ingest_conflicts(db_session, test_instrument.id, incoming, source="yahoo")
    
    assert analysis.overlap_count == 1
    assert analysis.mismatch_count == 1
    assert len(analysis.mismatches) > 0
    assert analysis.has_conflict
    
    # Check mismatch details
    mismatch = analysis.mismatches[0]
    assert mismatch.field == "close"
    assert mismatch.existing_value == Decimal("105")
    assert mismatch.incoming_value == Decimal("107")


def test_apply_insert_delta_only(db_session: Session, test_instrument):
    """Test apply mode: insert_delta_only"""
    # Insert existing bar
    existing = MarketDataBarD1(
        instrument_id=test_instrument.id,
        date=date(2025, 1, 1),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=1000,
        source="yahoo",
    )
    db_session.add(existing)
    db_session.commit()
    
    # Incoming with overlap + new dates
    incoming = [
        ParsedBar(date(2025, 1, 1), Decimal("100"), Decimal("110"), Decimal("95"), Decimal("105"), 1000),  # Existing
        ParsedBar(date(2025, 1, 2), Decimal("105"), Decimal("115"), Decimal("100"), Decimal("110"), 1200),  # New
        ParsedBar(date(2025, 1, 3), Decimal("110"), Decimal("120"), Decimal("105"), Decimal("115"), 1300),  # New
    ]
    
    result = apply_ingest(db_session, test_instrument.id, incoming, "insert_delta_only", source="yahoo")
    
    assert result['inserted_count'] == 2  # Only new dates
    assert result['updated_count'] == 0
    assert result['deleted_count'] == 0
    
    # Verify: existing bar unchanged, new bars inserted
    all_bars = db_session.query(MarketDataBarD1).filter(
        MarketDataBarD1.instrument_id == test_instrument.id
    ).order_by(MarketDataBarD1.date).all()
    
    assert len(all_bars) == 3
    assert all_bars[0].close == Decimal("105")  # Unchanged
    assert all_bars[1].close == Decimal("110")  # New
    assert all_bars[2].close == Decimal("115")  # New


def test_apply_overwrite_overlap(db_session: Session, test_instrument):
    """Test apply mode: overwrite_overlap"""
    # Insert existing bar
    existing = MarketDataBarD1(
        instrument_id=test_instrument.id,
        date=date(2025, 1, 1),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=1000,
        source="yahoo",
    )
    db_session.add(existing)
    db_session.commit()
    
    # Incoming with different values for overlap + new dates
    incoming = [
        ParsedBar(date(2025, 1, 1), Decimal("100"), Decimal("110"), Decimal("95"), Decimal("107"), 1000),  # Overwrite
        ParsedBar(date(2025, 1, 2), Decimal("105"), Decimal("115"), Decimal("100"), Decimal("110"), 1200),  # New
    ]
    
    result = apply_ingest(db_session, test_instrument.id, incoming, "overwrite_overlap", source="yahoo")
    
    assert result['inserted_count'] == 1  # New date
    assert result['updated_count'] == 1  # Overwritten overlap
    assert result['deleted_count'] == 0
    
    # Verify: existing bar updated, new bar inserted
    all_bars = db_session.query(MarketDataBarD1).filter(
        MarketDataBarD1.instrument_id == test_instrument.id
    ).order_by(MarketDataBarD1.date).all()
    
    assert len(all_bars) == 2
    assert all_bars[0].close == Decimal("107")  # Updated
    assert all_bars[1].close == Decimal("110")  # New


def test_apply_overwrite_all_range(db_session: Session, test_instrument):
    """Test apply mode: overwrite_all_range"""
    # Insert existing bars
    existing_bars = [
        MarketDataBarD1(
            instrument_id=test_instrument.id,
            date=date(2025, 1, 1),
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("95"),
            close=Decimal("105"),
            volume=1000,
            source="yahoo",
        ),
        MarketDataBarD1(
            instrument_id=test_instrument.id,
            date=date(2025, 1, 2),
            open=Decimal("105"),
            high=Decimal("115"),
            low=Decimal("100"),
            close=Decimal("110"),
            volume=1200,
            source="yahoo",
        ),
        MarketDataBarD1(
            instrument_id=test_instrument.id,
            date=date(2025, 1, 5),  # Outside range
            open=Decimal("120"),
            high=Decimal("130"),
            low=Decimal("115"),
            close=Decimal("125"),
            volume=1400,
            source="yahoo",
        ),
    ]
    for bar in existing_bars:
        db_session.add(bar)
    db_session.commit()
    
    # Incoming data for range 2025-01-01 to 2025-01-03
    incoming = [
        ParsedBar(date(2025, 1, 1), Decimal("200"), Decimal("210"), Decimal("195"), Decimal("205"), 2000),
        ParsedBar(date(2025, 1, 2), Decimal("205"), Decimal("215"), Decimal("200"), Decimal("210"), 2200),
        ParsedBar(date(2025, 1, 3), Decimal("210"), Decimal("220"), Decimal("205"), Decimal("215"), 2300),
    ]
    
    result = apply_ingest(db_session, test_instrument.id, incoming, "overwrite_all_range", source="yahoo")
    
    assert result['inserted_count'] == 3
    assert result['updated_count'] == 0
    assert result['deleted_count'] == 2  # Deleted 2025-01-01 and 2025-01-02 (in range)
    
    # Verify: bars in range deleted and replaced, bar outside range untouched
    all_bars = db_session.query(MarketDataBarD1).filter(
        MarketDataBarD1.instrument_id == test_instrument.id
    ).order_by(MarketDataBarD1.date).all()
    
    assert len(all_bars) == 4  # 3 new + 1 outside range
    assert all_bars[0].close == Decimal("205")  # New
    assert all_bars[1].close == Decimal("210")  # New
    assert all_bars[2].close == Decimal("215")  # New
    assert all_bars[3].close == Decimal("125")  # Outside range, untouched


def test_decimal_quantize_comparison():
    """Test that decimal comparison uses quantize"""
    bar1 = BarRow(date(2025, 1, 1), Decimal("100.0000001"), Decimal("110"), Decimal("95"), Decimal("105"), 1000)
    bar2 = BarRow(date(2025, 1, 1), Decimal("100.0000002"), Decimal("110"), Decimal("95"), Decimal("105"), 1000)
    
    # Should be equal after quantize (within precision)
    assert bar1 == bar2
    
    # But different if difference > precision
    bar3 = BarRow(date(2025, 1, 1), Decimal("100.00001"), Decimal("110"), Decimal("95"), Decimal("105"), 1000)
    assert bar1 != bar3

