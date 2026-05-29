"""Cost basis V2 — exécutions normalisées et WAC multi-devises."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote
from services.cost_basis.ingest import record_execution
from services.cost_basis.ingest_lifi import ingest_lifi_swap_settlement
from services.cost_basis.models import CostBasisExecution
from services.cost_basis.repository import CostBasisExecutionRepository
from services.cost_basis.valuation import build_frozen_valuation, build_crypto_cross_valuation
from services.cost_basis.wac import compute_wac_from_executions
from services.lifi.models import PersonWalletSwap

from conftest import make_linked_client


def _seed_eurusdt(db: Session, rate: float = 1.10) -> None:
    inst = (
        db.query(MarketDataInstrument)
        .filter(MarketDataInstrument.provider_symbol == "EURUSDT")
        .first()
    )
    if inst is None:
        inst = MarketDataInstrument(
            symbol="EURUSDT",
            name="EURUSDT",
            asset_class="fx",
            provider="binance",
            provider_symbol="EURUSDT",
            is_active="true",
        )
        db.add(inst)
        db.flush()
    quote = (
        db.query(MarketDataLatestQuote)
        .filter(MarketDataLatestQuote.instrument_id == inst.id)
        .first()
    )
    if quote is None:
        quote = MarketDataLatestQuote(
            instrument_id=inst.id,
            provider="binance",
            provider_symbol="EURUSDT",
            last_price=rate,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(quote)
    else:
        quote.last_price = rate
        quote.updated_at = datetime.now(timezone.utc)
    db.flush()


def _seed_crypto_quote(db: Session, provider_symbol: str, price: float) -> None:
    inst = (
        db.query(MarketDataInstrument)
        .filter(MarketDataInstrument.provider_symbol == provider_symbol)
        .first()
    )
    if inst is None:
        inst = MarketDataInstrument(
            symbol=provider_symbol,
            name=provider_symbol,
            asset_class="crypto",
            provider="binance",
            provider_symbol=provider_symbol,
            is_active="true",
        )
        db.add(inst)
        db.flush()
    quote = (
        db.query(MarketDataLatestQuote)
        .filter(MarketDataLatestQuote.instrument_id == inst.id)
        .first()
    )
    if quote is None:
        db.add(
            MarketDataLatestQuote(
                instrument_id=inst.id,
                provider="binance",
                provider_symbol=provider_symbol,
                last_price=price,
                updated_at=datetime.now(timezone.utc),
            )
        )
    else:
        quote.last_price = price
        quote.updated_at = datetime.now(timezone.utc)
    db.flush()


def test_usdc_to_aave_execution_price(db: Session):
    """Test 1 — USDC → AAVE : PRU USD ≈ 80.51."""
    _seed_eurusdt(db, 1.10)
    paid = Decimal("3.33335")
    received = Decimal("0.04140135")
    valuation = build_frozen_valuation(
        db,
        position_asset="AAVE",
        quantity=received,
        quote_asset="USDC",
        quote_amount=paid,
    )
    expected = paid / received
    assert abs(valuation.execution_price_usdc - expected) < Decimal("0.02")
    assert valuation.native_quote_asset == "USDC"
    derived_eur = float(valuation.execution_price_usdc / valuation.eurusd_rate_at_execution)
    assert float(valuation.execution_price_eur) == pytest.approx(derived_eur, rel=1e-3)


def test_eurc_to_btc_eur_exact_usd_derived(db: Session):
    """Test 2 — EURC → BTC : PRU EUR exact, USD dérivé au FX figé."""
    _seed_eurusdt(db, 1.25)
    paid = Decimal("1000")
    received = Decimal("0.01")
    valuation = build_frozen_valuation(
        db,
        position_asset="BTC",
        quantity=received,
        quote_asset="EURC",
        quote_amount=paid,
    )
    assert valuation.native_quote_asset == "EUR"
    assert abs(valuation.execution_price_eur - Decimal("100000")) < Decimal("1")
    assert valuation.execution_price_usdc == pytest.approx(
        float(valuation.execution_price_eur * valuation.eurusd_rate_at_execution),
        rel=1e-4,
    )


def test_eth_to_aave_cross_frozen_usd_eur(db: Session):
    """Test 3 — ETH → AAVE : notionnels USD/EUR figés."""
    _seed_eurusdt(db, 1.10)
    _seed_crypto_quote(db, "ETHUSDT", 3500.0)
    _seed_crypto_quote(db, "AAVEUSDT", 80.0)
    eth_amount = Decimal("0.5")
    aave_amount = Decimal("10")
    valuation = build_crypto_cross_valuation(
        db,
        position_asset="AAVE",
        quantity=aave_amount,
        from_asset="ETH",
        from_amount=eth_amount,
    )
    assert valuation.execution_notional_usdc > 0
    assert valuation.execution_notional_eur > 0
    assert valuation.eurusd_rate_at_execution == Decimal("1.10")


def test_idempotent_duplicate_provider_execution(db: Session):
    """Test 4 — double ingestion : une seule ligne."""
    pe = make_linked_client(db, email=f"cb-{uuid.uuid4().hex[:8]}@test.local")
    _seed_eurusdt(db)
    valuation = build_frozen_valuation(
        db,
        position_asset="AAVE",
        quantity=Decimal("0.04140135"),
        quote_asset="USDC",
        quote_amount=Decimal("3.33335"),
    )
    provider_id = f"lifi:test-swap:{uuid.uuid4()}:acquisition:AAVE"
    executed = datetime.now(timezone.utc)
    first = record_execution(
        db,
        client_id=pe.id,
        person_id=None,
        position_asset="AAVE",
        event_kind="acquisition",
        quantity=Decimal("0.04140135"),
        valuation=valuation,
        provider_source="lifi",
        provider_execution_id=provider_id,
        executed_at=executed,
        tx_hash="0xabc",
    )
    second = record_execution(
        db,
        client_id=pe.id,
        person_id=None,
        position_asset="AAVE",
        event_kind="acquisition",
        quantity=Decimal("0.04140135"),
        valuation=valuation,
        provider_source="lifi",
        provider_execution_id=provider_id,
        executed_at=executed,
        tx_hash="0xabc",
    )
    assert first is not None
    assert second is None
    rows = (
        db.query(CostBasisExecution)
        .filter(
            CostBasisExecution.client_id == pe.id,
            CostBasisExecution.provider_execution_id == provider_id,
        )
        .all()
    )
    assert len(rows) == 1


def test_wac_usdc_aave_avg_buy_price_usd(db: Session):
    pe = make_linked_client(db, email=f"cb-wac-{uuid.uuid4().hex[:8]}@test.local")
    _seed_eurusdt(db, 1.10)
    paid = Decimal("3.33335")
    received = Decimal("0.04140135")
    valuation = build_frozen_valuation(
        db,
        position_asset="AAVE",
        quantity=received,
        quote_asset="USDC",
        quote_amount=paid,
    )
    record_execution(
        db,
        client_id=pe.id,
        person_id=None,
        position_asset="AAVE",
        event_kind="acquisition",
        quantity=received,
        valuation=valuation,
        provider_source="lifi",
        provider_execution_id=f"lifi:{uuid.uuid4()}:acquisition:AAVE",
        executed_at=datetime.now(timezone.utc),
    )
    wac = compute_wac_from_executions(
        db,
        pe.id,
        "AAVE",
        position_size=received,
        current_price_eur=Decimal("70"),
        current_price_usd=Decimal("82.10"),
    )
    expected = paid / received
    assert abs(wac.avg_buy_price_usd - expected) < Decimal("0.05")
    assert wac.unrealized_pnl_usd > 0


def test_lifi_settlement_ingest_creates_execution(db: Session):
    pe = make_linked_client(db, email=f"cb-lifi-{uuid.uuid4().hex[:8]}@test.local")
    _seed_eurusdt(db)
    swap = PersonWalletSwap(
        id=uuid.uuid4(),
        person_id=pe.person_id,
        status="CONFIRMED",
        from_asset="USDC",
        to_asset="AAVE",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("3.33335"),
        estimated_receive=Decimal("0.04140135"),
        tx_hash="0xdeadbeef",
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(swap)
    db.flush()

    class _Wallet:
        pe_client_id = pe.id
        person_id = pe.person_id

    created = ingest_lifi_swap_settlement(db, swap, wallet=_Wallet(), amount_out=Decimal("0.04140135"))
    assert created == 1
    row = CostBasisExecutionRepository().find_by_provider(
        db,
        provider_source="lifi",
        provider_execution_id=f"lifi:{swap.id}:acquisition:AAVE",
    )
    assert row is not None
    assert abs(Decimal(str(row.execution_price_usdc)) - Decimal("80.51")) < Decimal("0.1")
