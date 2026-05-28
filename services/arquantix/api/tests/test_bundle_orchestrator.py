"""Tests for BundleOrchestrator Phase 2 — True cash-leg entry wallet.

Matrix:
  1. EUR funding → BUY entry asset → cash leg created
  2. Allocation from cash leg via SWAPs to multiple target assets
  3. Partial failure → remainder stays in cash leg
  4. Direct entry-asset funding (no EUR conversion)
  5. Sync: cash leg + pe_atoms + exchange_orders
  6. Invariant D: pe_atoms ≤ crypto_positions
  7. Invariant E: cash_leg_cost + alloc_cost = total_cost
  8. Non-regression: BUY/SELL/SWAP/wallet stats/PnL unchanged
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote
from services.exchange.models import CryptoPosition, ExchangeOrder
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundles.orchestrator import (
    POSITION_TYPE_CASH,
    POSITION_TYPE_SPOT,
    BundleOrchestrator,
    BundleOrchestratorError,
)
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.products.models import ProductDefinition

from conftest import custody_admin_headers, make_linked_client, mobile_auth_headers

BTC_PRICE = 85_000.0
ETH_PRICE = 2_300.0
SOL_PRICE = 180.0
USDC_PRICE = 1.0

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-bundle-p2@example.com",
    "X-Actor-Roles": "admin",
}


@pytest.fixture(autouse=True)
def _force_exchange_bundle_provider(monkeypatch):
    """Phase 2 orchestrator tests ciblent le backend Exchange (pas LI.FI)."""
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "exchange")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _unique_email() -> str:
    return f"bundlep2-{uuid.uuid4().hex[:8]}@example.com"


def _create_provider(http) -> dict:
    res = http.post(
        "/api/admin/custody/providers",
        json={
            "name": f"Bank-{uuid.uuid4().hex[:6]}",
            "provider_type": "bank",
            "jurisdiction": "EU",
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_client_account(http, provider_id: str, client_id: str, db: Session) -> dict:
    res = http.post(
        "/api/admin/custody/accounts/client",
        json={
            "provider_id": provider_id,
            "account_type": "client_deposit_account",
            "currency": "EUR",
            "account_holder_name": "Test User",
            "client_id": client_id,
            "iban": f"DE{uuid.uuid4().hex[:16].upper()}",
        },
        headers=custody_admin_headers(db),
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_settlement_account(http, provider_id: str, db: Session) -> dict:
    res = http.post(
        "/api/admin/custody/accounts/settlement",
        json={
            "provider_id": provider_id,
            "account_type": "company_settlement_account",
            "currency": "EUR",
            "account_holder_name": "Vancelian SA",
            "is_master_account": True,
            "iban": f"DE{uuid.uuid4().hex[:16].upper()}",
        },
        headers=custody_admin_headers(db),
    )
    if res.status_code == 409:
        accs = http.get(
            "/api/admin/custody/accounts?account_type=company_settlement_account",
            headers=ADMIN_HEADERS,
        ).json()
        for a in accs.get("items", []):
            if a["is_master_account"] and a["currency"] == "EUR":
                return a
    assert res.status_code == 201, res.text
    return res.json()


def _fund_client(http, client_id: str, amount: float, db: Session) -> None:
    res = http.post(
        "/api/admin/custody/simulate-deposit",
        json={
            "client_id": client_id,
            "amount": amount,
            "currency": "EUR",
            "reference": f"FUND-{uuid.uuid4().hex[:8]}",
        },
        headers=custody_admin_headers(db),
    )
    assert res.status_code == 200, res.text


def _full_setup(http, db: Session, initial_eur: float = 50_000.0):
    provider = _create_provider(http)
    pe_client = make_linked_client(db, email=_unique_email())
    _create_client_account(http, provider["id"], str(pe_client.id), db)
    _create_settlement_account(http, provider["id"], db)
    if initial_eur > 0:
        _fund_client(http, str(pe_client.id), initial_eur, db)
    return pe_client


def _seed_market_data(db: Session) -> None:
    now = datetime.now(timezone.utc)
    for symbol, prov, price in [
        ("BTCUSDT", "BTCUSDT", BTC_PRICE),
        ("ETHUSDT", "ETHUSDT", ETH_PRICE),
        ("SOLUSDT", "SOLUSDT", SOL_PRICE),
        ("USDCUSDT", "USDCUSDT", USDC_PRICE),
        ("EURUSDT", "EURUSDT", 1.08),
    ]:
        inst = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.provider_symbol == prov,
        ).first()
        if not inst:
            inst = MarketDataInstrument(
                symbol=symbol, name=symbol, asset_class="crypto",
                provider="binance", provider_symbol=prov, is_active="true",
            )
            db.add(inst)
            db.flush()
        quote = db.query(MarketDataLatestQuote).filter(
            MarketDataLatestQuote.instrument_id == inst.id,
        ).first()
        if quote:
            quote.last_price = price
            quote.bid_price = price * 0.999
            quote.ask_price = price * 1.001
            quote.quote_time = now
            quote.updated_at = now
        else:
            quote = MarketDataLatestQuote(
                instrument_id=inst.id, provider="binance",
                provider_symbol=prov, last_price=price,
                bid_price=price * 0.999, ask_price=price * 1.001,
                quote_time=now, updated_at=now,
            )
            db.add(quote)
        db.flush()


def _ensure_crypto_custody_bootstrap(http) -> None:
    http.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)


def _create_pe_bundle_portfolio(
    db: Session,
    client_id: uuid.UUID,
    allocations: dict[str, Decimal],
    *,
    entry_asset_default: str = "USDC",
    entry_assets_allowed: list[str] | None = None,
) -> tuple[uuid.UUID, dict[str, uuid.UUID]]:
    """Create a PE bundle portfolio with target allocations."""
    suffix = uuid.uuid4().hex[:6].upper()

    product = ProductDefinition(
        id=uuid.uuid4(),
        product_code=f"BUNDLE_P2_{suffix}",
        name=f"Test Bundle P2 {suffix}",
        product_type="crypto_bundle",
        base_currency="EUR",
        is_public=True,
        status="active",
        metadata_={
            "available_rebalance_frequencies": ["monthly"],
            "entry_asset_default": entry_asset_default,
            "entry_assets_allowed": entry_assets_allowed or [entry_asset_default],
        },
    )
    db.add(product)
    db.flush()

    portfolio = Portfolio(
        id=uuid.uuid4(),
        client_id=client_id,
        origin_product_id=product.id,
        portfolio_type="bundle_portfolio",
        name=f"Test Bundle PF P2 {suffix}",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(portfolio)
    db.flush()

    instrument_map: dict[str, uuid.UUID] = {}
    for asset_symbol, weight in allocations.items():
        asset = db.query(Asset).filter(Asset.symbol == asset_symbol).first()
        if not asset:
            asset = Asset(
                id=uuid.uuid4(), symbol=asset_symbol,
                name=f"Test {asset_symbol}", asset_type="cryptocurrency",
            )
            db.add(asset)
            db.flush()

        instr = db.query(Instrument).filter(
            Instrument.asset_id == asset.id,
            Instrument.instrument_type == "spot",
        ).first()
        if not instr:
            instr = Instrument(
                id=uuid.uuid4(), asset_id=asset.id,
                code=f"{asset_symbol}_SPOT_{suffix}",
                name=f"{asset_symbol} Spot", instrument_type="spot",
            )
            db.add(instr)
            db.flush()
        instrument_map[asset_symbol] = instr.id

        alloc = TargetAllocation(
            id=uuid.uuid4(), portfolio_id=portfolio.id,
            instrument_id=instr.id, target_weight=weight,
        )
        db.add(alloc)

    db.flush()
    return portfolio.id, instrument_map


# ===========================================================================
# Tests
# ===========================================================================

class TestBundleOrchestratorPhase2:

    # ── Test 1: EUR funding → BUY USDC → cash leg created ──

    def test_eur_funding_creates_cash_leg(self, db: Session, client):
        """EUR funding buys USDC first, then a cash leg atom is created."""
        _seed_market_data(db)
        pe_client = _full_setup(client, db, initial_eur=10_000.0)
        _ensure_crypto_custody_bootstrap(client)
        client_uuid = pe_client.id

        portfolio_id, _ = _create_pe_bundle_portfolio(
            db, client_uuid,
            allocations={"BTC": Decimal("0.7"), "ETH": Decimal("0.3")},
        )

        orchestrator = BundleOrchestrator()
        result = orchestrator.invest_into_bundle(
            db,
            client_id=client_uuid,
            portfolio_id=portfolio_id,
            funding_asset="EUR",
            funding_amount=Decimal("1000"),
        )

        assert result["status"] == "completed"
        assert result["entry_asset"] == "USDC"
        assert result["funding"]["funding_path"] == "buy_entry_asset"
        assert result["funding"]["action"] == "fund_cash_leg_from_self_trading"
        assert result["funding"]["to"] == "USDC"
        assert result["total_entry_asset_received"] > 0

        # Verify cash leg atom exists
        cash_atoms = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
            PositionAtom.status == "open",
        ).all()
        assert len(cash_atoms) == 1

        # Verify USDC is in crypto_positions
        usdc_pos = db.query(CryptoPosition).filter(
            CryptoPosition.client_id == client_uuid,
            CryptoPosition.asset == "USDC",
        ).first()
        assert usdc_pos is not None

    # ── Test 2: Allocation from cash leg via SWAPs ──

    def test_allocation_from_cash_leg(self, db: Session, client):
        """After funding, USDC is swapped to BTC and ETH per target weights."""
        _seed_market_data(db)
        pe_client = _full_setup(client, db, initial_eur=10_000.0)
        _ensure_crypto_custody_bootstrap(client)
        client_uuid = pe_client.id

        portfolio_id, instr_map = _create_pe_bundle_portfolio(
            db, client_uuid,
            allocations={"BTC": Decimal("0.7"), "ETH": Decimal("0.3")},
        )

        orchestrator = BundleOrchestrator()
        result = orchestrator.invest_into_bundle(
            db,
            client_id=client_uuid,
            portfolio_id=portfolio_id,
            funding_asset="EUR",
            funding_amount=Decimal("2000"),
        )

        assert result["status"] == "completed"
        assert result["legs_succeeded"] == 2

        details = {d["asset"]: d for d in result["allocation_details"]}
        assert details["BTC"]["status"] == "completed"
        assert details["ETH"]["status"] == "completed"
        assert details["BTC"]["crypto_received"] > 0
        assert details["ETH"]["crypto_received"] > 0

        # Spot atoms should exist for BTC and ETH
        spot_atoms = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
            PositionAtom.status == "open",
        ).all()
        assert len(spot_atoms) == 2

    # ── Test 3: Partial failure → remainder in cash leg ──

    def test_partial_failure_remainder_in_cash_leg(self, db: Session, client):
        """If one swap leg fails, remaining USDC stays in cash leg."""
        _seed_market_data(db)
        pe_client = _full_setup(client, db, initial_eur=10_000.0)
        _ensure_crypto_custody_bootstrap(client)
        client_uuid = pe_client.id

        portfolio_id, _ = _create_pe_bundle_portfolio(
            db, client_uuid,
            allocations={
                "BTC": Decimal("0.5"),
                "ETH": Decimal("0.3"),
                "SOL": Decimal("0.2"),
            },
        )

        # Make SOL quote stale
        sol_inst = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.provider_symbol == "SOLUSDT",
        ).first()
        if sol_inst:
            sol_quote = db.query(MarketDataLatestQuote).filter(
                MarketDataLatestQuote.instrument_id == sol_inst.id,
            ).first()
            if sol_quote:
                sol_quote.quote_time = datetime.now(timezone.utc) - timedelta(seconds=120)
                db.flush()

        orchestrator = BundleOrchestrator()
        result = orchestrator.invest_into_bundle(
            db,
            client_id=client_uuid,
            portfolio_id=portfolio_id,
            funding_asset="EUR",
            funding_amount=Decimal("1000"),
        )

        assert result["status"] == "partial"
        assert result["legs_succeeded"] == 2
        assert result["legs_failed"] == 1
        assert result["cash_leg_remaining"] > 0

        details = {d["asset"]: d for d in result["allocation_details"]}
        assert details["SOL"]["status"] == "failed"

        # Cash leg should still have the unallocated portion
        cash_atom = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
            PositionAtom.status == "open",
        ).first()
        assert cash_atom is not None
        assert Decimal(str(cash_atom.quantity)) > 0

    # ── Test 4: Direct entry-asset funding (no EUR conversion) ──

    def test_direct_entry_asset_funding(self, db: Session, client):
        """Client already has USDC → no BUY step, direct allocation."""
        _seed_market_data(db)
        pe_client = _full_setup(client, db, initial_eur=10_000.0)
        auth = mobile_auth_headers(db, pe_client)
        _ensure_crypto_custody_bootstrap(client)
        client_uuid = pe_client.id

        # First buy USDC manually
        res = client.post(
            "/api/app/exchange/buy",
            json={"asset": "USDC", "amount_fiat": 5000},
            headers=auth,
        )
        assert res.status_code == 200, res.text

        usdc_pos = db.query(CryptoPosition).filter(
            CryptoPosition.client_id == client_uuid,
            CryptoPosition.asset == "USDC",
        ).first()
        usdc_balance = Decimal(str(usdc_pos.balance))
        assert usdc_balance > 0

        portfolio_id, _ = _create_pe_bundle_portfolio(
            db, client_uuid,
            allocations={"BTC": Decimal("0.6"), "ETH": Decimal("0.4")},
        )

        orchestrator = BundleOrchestrator()
        invest_amount = min(usdc_balance, Decimal("1000"))
        result = orchestrator.invest_into_bundle(
            db,
            client_id=client_uuid,
            portfolio_id=portfolio_id,
            funding_asset="USDC",
            funding_amount=invest_amount,
        )

        assert result["status"] == "completed"
        assert result["funding"]["funding_path"] == "direct_entry_asset"
        assert result["funding"]["action"] == "fund_cash_leg_from_self_trading"
        assert result["legs_succeeded"] == 2

    # ── Test 5: Sync — cash leg + pe_atoms + exchange_orders ──

    def test_sync_cash_leg_and_atoms(self, db: Session, client):
        """Orders are tagged, cash leg is debited, spot atoms are credited."""
        _seed_market_data(db)
        pe_client = _full_setup(client, db, initial_eur=10_000.0)
        _ensure_crypto_custody_bootstrap(client)
        client_uuid = pe_client.id

        portfolio_id, _ = _create_pe_bundle_portfolio(
            db, client_uuid,
            allocations={"BTC": Decimal("0.6"), "ETH": Decimal("0.4")},
        )

        orchestrator = BundleOrchestrator()
        result = orchestrator.invest_into_bundle(
            db,
            client_id=client_uuid,
            portfolio_id=portfolio_id,
            funding_asset="EUR",
            funding_amount=Decimal("3000"),
        )

        batch_id = result["batch_id"]

        # Verify funding order tagged
        funding_order = db.query(ExchangeOrder).filter(
            ExchangeOrder.external_reference == f"bundle-fund-{batch_id}",
        ).first()
        assert funding_order is not None
        assert funding_order.metadata_.get("bundle_id") == str(portfolio_id)
        assert funding_order.metadata_.get("bundle_action") == "funding"

        # Verify swap orders tagged
        alloc_orders = db.query(ExchangeOrder).filter(
            ExchangeOrder.client_id == client_uuid,
        ).all()
        swap_orders = [
            o for o in alloc_orders
            if (o.metadata_ or {}).get("bundle_action") == "allocation"
        ]
        assert len(swap_orders) >= 2  # At least sell+buy for each leg

        # Bundle status check
        status = BundleOrchestrator.get_bundle_status(db, portfolio_id, client_uuid)
        assert len(status["cash_legs"]) == 1
        assert len(status["allocated_positions"]) == 2

    # ── Test 6: Invariant D ──

    def test_invariant_d_holds(self, db: Session, client):
        """PE atoms ≤ crypto positions after bundle investment."""
        _seed_market_data(db)
        pe_client = _full_setup(client, db, initial_eur=10_000.0)
        _ensure_crypto_custody_bootstrap(client)
        client_uuid = pe_client.id

        portfolio_id, _ = _create_pe_bundle_portfolio(
            db, client_uuid,
            allocations={"BTC": Decimal("0.7"), "ETH": Decimal("0.3")},
        )

        orchestrator = BundleOrchestrator()
        result = orchestrator.invest_into_bundle(
            db,
            client_id=client_uuid,
            portfolio_id=portfolio_id,
            funding_asset="EUR",
            funding_amount=Decimal("5000"),
        )
        assert result["status"] == "completed"

        inv_d = BundleOrchestrator.check_invariant_d(db, client_uuid)
        assert inv_d["invariant_d_ok"] is True
        assert inv_d["violations"] == []

    # ── Test 7: Invariant E — cash + allocated = total ──

    def test_invariant_e_holds(self, db: Session, client):
        """Cash leg cost basis + allocated cost basis = total cost basis."""
        _seed_market_data(db)
        pe_client = _full_setup(client, db, initial_eur=10_000.0)
        _ensure_crypto_custody_bootstrap(client)
        client_uuid = pe_client.id

        portfolio_id, _ = _create_pe_bundle_portfolio(
            db, client_uuid,
            allocations={"BTC": Decimal("0.7"), "ETH": Decimal("0.3")},
        )

        orchestrator = BundleOrchestrator()
        result = orchestrator.invest_into_bundle(
            db,
            client_id=client_uuid,
            portfolio_id=portfolio_id,
            funding_asset="EUR",
            funding_amount=Decimal("2000"),
        )
        assert result["status"] == "completed"

        inv_e = BundleOrchestrator.check_invariant_e(db, portfolio_id)
        assert inv_e["invariant_e_ok"] is True
        assert inv_e["total_cost_basis"] > 0

    # ── Test 8: Non-regression ──

    def test_non_regression(self, db: Session, client):
        """BUY/SELL/SWAP/wallet stats still work after Phase 2 changes."""
        _seed_market_data(db)
        pe_client = _full_setup(client, db, initial_eur=10_000.0)
        auth = mobile_auth_headers(db, pe_client)
        _ensure_crypto_custody_bootstrap(client)

        # Standard BUY
        res = client.post(
            "/api/app/exchange/buy",
            json={"asset": "BTC", "amount_fiat": 500},
            headers=auth,
        )
        assert res.status_code == 200
        buy_data = res.json()
        assert buy_data["status"] == "completed"

        # Standard SELL
        res = client.post(
            "/api/app/exchange/sell",
            json={"asset": "BTC", "amount_crypto": float(buy_data["amount_crypto"])},
            headers=auth,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "completed"

        # BUY USDC (new asset)
        res = client.post(
            "/api/app/exchange/buy",
            json={"asset": "USDC", "amount_fiat": 100},
            headers=auth,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "completed"

        # Wallet statistics
        res = client.get("/api/app/wallet/statistics/BTC", headers=auth)
        assert res.status_code == 200
        assert "realized_pnl" in res.json()

        # Portfolio statistics
        res = client.get("/api/app/portfolio/statistics", headers=auth)
        assert res.status_code == 200
