"""
Tests for CPPI bundle validation error handling
"""
import pytest
from datetime import date, timedelta
import pandas as pd
from decimal import Decimal
from sqlalchemy.orm import Session

from database import MarketDataBundle, BundleComponent, MarketDataInstrument, BacktestRun, MarketDataBarD1
from services.backtest.executor import execute_backtest
from services.bundles.errors import BundleValidationError


def test_cppi_returns_422_when_bundle_invalid(db: Session):
    """Test that CPPI returns 422 error when bundle weights are invalid"""
    # Create a bundle with invalid weights (sum != 100%)
    bundle = MarketDataBundle(
        name="Invalid CPPI Bundle",
        asset_class="crypto",
        type="fixed_instruments",
        is_active="true",
    )
    db.add(bundle)
    db.flush()
    
    # Create instruments (use unique symbols to avoid conflicts)
    import uuid
    unique_suffix = str(uuid.uuid4())[:8]
    inst1 = MarketDataInstrument(symbol=f"BTC_{unique_suffix}", name="Bitcoin", asset_class="crypto", is_active="true")
    inst2 = MarketDataInstrument(symbol=f"ETH_{unique_suffix}", name="Ethereum", asset_class="crypto", is_active="true")
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
    db.flush()
    
    # Create minimal price data so executor can proceed to validation
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()
    current_date = start_date
    while current_date <= end_date:
        # Skip weekends
        if current_date.weekday() < 5:
            bar1 = MarketDataBarD1(
                instrument_id=inst1.id,
                date=current_date,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=1000.0,
            )
            bar2 = MarketDataBarD1(
                instrument_id=inst2.id,
                date=current_date,
                open=50.0,
                high=51.0,
                low=49.0,
                close=50.0,
                volume=2000.0,
            )
            db.add_all([bar1, bar2])
        current_date += timedelta(days=1)
    db.commit()
    
    backtest_run = BacktestRun(
        name="CPPI Invalid Bundle Test",
        start_date=start_date,
        end_date=end_date,
        rebalance="weekly",
        strategy_type="CPPI",
        strategy_params_json={
            "floor_ratio": 0.90,
            "multiplier": 4.0,
            "risky_cap": 1.0,
            "core_min": 0.0,
            "core_yield": 0.035,
            "day_count": 365,
        },
        fees_bps=0.0,
        slippage_bps=0.0,
        allow_weekend_trading="true",
        instrument_ids_json=[inst1.id, inst2.id],
        bundle_id=str(bundle.id),
        status="PENDING",
    )
    db.add(backtest_run)
    db.commit()
    
    # Execute backtest should raise ValueError with bundle validation error
    with pytest.raises(ValueError) as exc_info:
        execute_backtest(
            db=db,
            run_id=backtest_run.id,
            instrument_ids=[inst1.id, inst2.id],
            start_date=start_date,
            end_date=end_date,
            strategy_type="CPPI",
            rebalance="weekly",
            fees_bps=0.0,
            slippage_bps=0.0,
            allow_weekend_trading=True,
            bundle_allocations=None,
            strategy_params_json={
                "floor_ratio": 0.90,
                "multiplier": 4.0,
                "risky_cap": 1.0,
                "core_min": 0.0,
                "core_yield": 0.035,
                "day_count": 365,
            },
        )
    
    # Verify error message contains bundle validation message
    error_msg = str(exc_info.value)
    assert "Invalid bundle allocation" in error_msg
    assert "weights must sum" in error_msg.lower()
    
    # Verify backtest run status is FAILED
    db.refresh(backtest_run)
    assert backtest_run.status == "FAILED"
    assert "Invalid bundle allocation" in backtest_run.error_message

