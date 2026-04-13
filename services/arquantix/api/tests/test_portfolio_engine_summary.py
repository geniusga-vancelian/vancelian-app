"""Tests for Portfolio Engine — Portfolio Summary read model."""
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.instruments.price_bridge import (
    MarketDataLinkMissingError,
    QuoteNotAvailableError,
)
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.summary.service import (
    PortfolioNotFoundForSummaryError,
    PortfolioSummaryService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def summary_svc() -> PortfolioSummaryService:
    return PortfolioSummaryService()


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_type="bundle_portfolio",
        name="Test Summary Portfolio",
        base_currency="USD",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol="SUM_BTC", name="Bitcoin", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def asset_eth(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol="SUM_ETH", name="Ethereum", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_btc.id,
        code="SUM_BTC-SPOT",
        name="BTC Spot",
        instrument_type="spot",
        metadata_={"market_data_instrument_id": 1},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_eth(db: Session, asset_eth: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_eth.id,
        code="SUM_ETH-SPOT",
        name="ETH Spot",
        instrument_type="spot",
        metadata_={"market_data_instrument_id": 2},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_no_link(db: Session, asset_btc: Asset) -> Instrument:
    """Instrument without a market_data_instrument_id link."""
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_btc.id,
        code="SUM_VAULT-X",
        name="Vault X",
        instrument_type="vault_units",
        metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def position_btc(db: Session, portfolio: Portfolio, instrument_btc: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id,
        position_type="spot",
        status="open",
        quantity=Decimal("0.500000"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def position_eth(db: Session, portfolio: Portfolio, instrument_eth: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_eth.id,
        position_type="spot",
        status="open",
        quantity=Decimal("10.000000"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def position_unpriced(db: Session, portfolio: Portfolio, instrument_no_link: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_no_link.id,
        position_type="vault_units",
        status="open",
        quantity=Decimal("1000.000000"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def closed_position(db: Session, portfolio: Portfolio, instrument_btc: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id,
        position_type="spot",
        status="closed",
        quantity=Decimal("1.000000"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


def _mock_get_instrument_price(db, instrument_id):
    """Side-effect for mocking get_instrument_price per instrument_id."""
    prices = getattr(_mock_get_instrument_price, "_prices", {})
    if str(instrument_id) in prices:
        return prices[str(instrument_id)]
    raise MarketDataLinkMissingError(instrument_id)


# ---------------------------------------------------------------------------
# Portfolio not found
# ---------------------------------------------------------------------------

class TestSummaryPortfolioNotFound:

    def test_portfolio_not_found(self, db: Session, summary_svc: PortfolioSummaryService):
        with pytest.raises(PortfolioNotFoundForSummaryError):
            summary_svc.get_summary(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# Empty portfolio
# ---------------------------------------------------------------------------

class TestSummaryEmptyPortfolio:

    def test_no_positions(self, db: Session, summary_svc: PortfolioSummaryService, portfolio: Portfolio):
        result = summary_svc.get_summary(db, portfolio.id)
        assert result.portfolio_id == portfolio.id
        assert result.portfolio_name == "Test Summary Portfolio"
        assert result.base_currency == "USD"
        assert result.total_market_value == "0"
        assert result.priced_positions_count == 0
        assert result.unpriced_positions_count == 0
        assert result.positions == []
        assert result.warnings == []


# ---------------------------------------------------------------------------
# Priced positions
# ---------------------------------------------------------------------------

class TestSummaryPricedPositions:

    @patch("services.portfolio_engine.summary.service.get_instrument_price")
    def test_single_priced_position(
        self, mock_price, db: Session, summary_svc: PortfolioSummaryService,
        portfolio: Portfolio, position_btc: PositionAtom, instrument_btc: Instrument,
    ):
        mock_price.return_value = {
            "instrument_id": str(instrument_btc.id),
            "instrument_code": "SUM_BTC-SPOT",
            "asset_symbol": "SUM_BTC",
            "price": "68000.00",
        }

        result = summary_svc.get_summary(db, portfolio.id)

        assert result.priced_positions_count == 1
        assert result.unpriced_positions_count == 0
        assert result.total_market_value == "34000.00"
        assert len(result.positions) == 1

        pos = result.positions[0]
        assert pos.position_id == position_btc.id
        assert pos.instrument_code == "SUM_BTC-SPOT"
        assert pos.price == "68000.00"
        assert pos.market_value == "34000.00"
        assert pos.allocation_weight == "1.000000"
        assert pos.pricing_status == "priced"

    @patch("services.portfolio_engine.summary.service.get_instrument_price")
    def test_multiple_priced_positions_allocation_weights(
        self, mock_price, db: Session, summary_svc: PortfolioSummaryService,
        portfolio: Portfolio,
        position_btc: PositionAtom, position_eth: PositionAtom,
        instrument_btc: Instrument, instrument_eth: Instrument,
    ):
        def price_side_effect(session, instr_id):
            if instr_id == instrument_btc.id:
                return {"price": "60000.00"}
            if instr_id == instrument_eth.id:
                return {"price": "4000.00"}
            raise MarketDataLinkMissingError(instr_id)

        mock_price.side_effect = price_side_effect

        result = summary_svc.get_summary(db, portfolio.id)

        # BTC: 0.5 * 60000 = 30000, ETH: 10 * 4000 = 40000, total = 70000
        assert result.total_market_value == "70000.00"
        assert result.priced_positions_count == 2
        assert result.unpriced_positions_count == 0

        weights = {p.instrument_code: p.allocation_weight for p in result.positions}
        assert weights["SUM_BTC-SPOT"] is not None
        assert weights["SUM_ETH-SPOT"] is not None

        btc_weight = Decimal(weights["SUM_BTC-SPOT"])
        eth_weight = Decimal(weights["SUM_ETH-SPOT"])
        assert btc_weight + eth_weight == Decimal("1.000000")


# ---------------------------------------------------------------------------
# Mixed priced + unpriced
# ---------------------------------------------------------------------------

class TestSummaryMixedPositions:

    @patch("services.portfolio_engine.summary.service.get_instrument_price")
    def test_mixed_priced_and_unpriced(
        self, mock_price, db: Session, summary_svc: PortfolioSummaryService,
        portfolio: Portfolio,
        position_btc: PositionAtom,
        position_unpriced: PositionAtom,
        instrument_btc: Instrument,
        instrument_no_link: Instrument,
    ):
        def price_side_effect(session, instr_id):
            if instr_id == instrument_btc.id:
                return {"price": "70000.00"}
            raise MarketDataLinkMissingError(instr_id)

        mock_price.side_effect = price_side_effect

        result = summary_svc.get_summary(db, portfolio.id)

        assert result.priced_positions_count == 1
        assert result.unpriced_positions_count == 1
        assert result.total_market_value == "35000.00"
        assert len(result.warnings) == 1
        assert "1 position could not be priced" in result.warnings[0]

        priced = [p for p in result.positions if p.pricing_status == "priced"]
        unpriced = [p for p in result.positions if p.pricing_status == "unpriced"]
        assert len(priced) == 1
        assert len(unpriced) == 1
        assert unpriced[0].price is None
        assert unpriced[0].market_value is None
        assert unpriced[0].allocation_weight is None


# ---------------------------------------------------------------------------
# All unpriced
# ---------------------------------------------------------------------------

class TestSummaryAllUnpriced:

    @patch("services.portfolio_engine.summary.service.get_instrument_price")
    def test_all_positions_unpriced(
        self, mock_price, db: Session, summary_svc: PortfolioSummaryService,
        portfolio: Portfolio,
        position_unpriced: PositionAtom,
    ):
        mock_price.side_effect = MarketDataLinkMissingError(uuid.uuid4())

        result = summary_svc.get_summary(db, portfolio.id)

        assert result.total_market_value == "0"
        assert result.priced_positions_count == 0
        assert result.unpriced_positions_count == 1
        assert len(result.warnings) == 1
        assert result.positions[0].pricing_status == "unpriced"
        assert result.positions[0].allocation_weight is None


# ---------------------------------------------------------------------------
# Closed positions excluded
# ---------------------------------------------------------------------------

class TestSummaryClosedPositionsExcluded:

    @patch("services.portfolio_engine.summary.service.get_instrument_price")
    def test_closed_positions_not_included(
        self, mock_price, db: Session, summary_svc: PortfolioSummaryService,
        portfolio: Portfolio,
        closed_position: PositionAtom,
    ):
        mock_price.return_value = {"price": "50000.00"}

        result = summary_svc.get_summary(db, portfolio.id)

        assert len(result.positions) == 0
        assert result.total_market_value == "0"


# ---------------------------------------------------------------------------
# Quote not available (bridge succeeds but no price)
# ---------------------------------------------------------------------------

class TestSummaryQuoteNotAvailable:

    @patch("services.portfolio_engine.summary.service.get_instrument_price")
    def test_quote_not_available_treated_as_unpriced(
        self, mock_price, db: Session, summary_svc: PortfolioSummaryService,
        portfolio: Portfolio,
        position_btc: PositionAtom,
    ):
        mock_price.side_effect = QuoteNotAvailableError(1)

        result = summary_svc.get_summary(db, portfolio.id)

        assert result.priced_positions_count == 0
        assert result.unpriced_positions_count == 1
        assert result.positions[0].pricing_status == "unpriced"
