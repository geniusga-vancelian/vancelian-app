"""Tests for swap quote staleness / missing hardening.

Verifies that preview_swap and swap reject when:
  1. Source quote stale
  2. Target quote stale
  3. Source quote missing
  4. Target quote missing
  5. Source quote missing timestamp
  6. Target quote missing timestamp
  7. No side effects on rejection
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote
from services.exchange.assets import ASSET_PRECISION, set_settlement_wallet_balance
from services.exchange.models import ExchangeOrder

from conftest import custody_admin_headers, make_linked_client, mobile_auth_headers

BTC_PRICE = 85_000.0
ETH_PRICE = 2_300.0
EURUSDT = 1.08

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-stale@example.com",
    "X-Actor-Roles": "admin",
}


@pytest.fixture(autouse=True)
def _no_binance_quote_refresh(monkeypatch):
    """Ces tests pilotent les quotes en base ; sans cela Binance REST repopule après DELETE."""
    def _noop(_db, _symbols):
        return None

    monkeypatch.setattr(
        "services.exchange.service.refresh_binance_quotes_for_provider_symbols",
        _noop,
    )


def _unique_email() -> str:
    return f"stale-{uuid.uuid4().hex[:8]}@example.com"


def _create_provider(http: TestClient) -> dict:
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


def _create_client_account(http: TestClient, provider_id: str, client_id: str, db: Session) -> dict:
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


def _create_settlement_account(http: TestClient, provider_id: str, db: Session) -> dict:
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


def _fund_client(http: TestClient, client_id: str, amount: float, db: Session) -> None:
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


def _full_setup(http: TestClient, db: Session, initial_eur: float = 50_000.0):
    provider = _create_provider(http)
    pe_client = make_linked_client(db, email=_unique_email())
    _create_client_account(http, provider["id"], str(pe_client.id), db)
    _create_settlement_account(http, provider["id"], db)
    if initial_eur > 0:
        _fund_client(http, str(pe_client.id), initial_eur, db)
    return pe_client


def _buy_btc(http: TestClient, client_id: str, fiat_amount: float) -> dict:
    ref = f"stale-buy-{uuid.uuid4().hex[:8]}"
    res = http.post(
        "/api/exchange/buy",
        json={
            "client_id": client_id,
            "asset": "BTC",
            "fiat_amount": fiat_amount,
            "currency": "EUR",
            "external_reference": ref,
            "price": BTC_PRICE,
        },
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "completed", data
    return data


def _ensure_crypto_custody_bootstrap(client: TestClient) -> None:
    client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)


def _set_settlement_wallet_actual_balance(client: TestClient, asset: str, balance: str) -> None:
    list_res = client.get("/api/admin/exchange/crypto-custody", headers=ADMIN_HEADERS)
    for account in list_res.json().get("accounts", []):
        if account.get("asset") == asset and account.get("account_type") == "settlement_wallet":
            aid = account.get("id")
            if aid and not str(aid).startswith("wallet-"):
                client.post(
                    f"/api/admin/exchange/crypto-custody/{aid}/set-actual-balance",
                    json={"actual_balance": balance},
                    headers=ADMIN_HEADERS,
                )
                return


# ---------------------------------------------------------------------------
# Quote helpers
# ---------------------------------------------------------------------------


def _get_or_create_instrument(db: Session, provider_symbol: str) -> MarketDataInstrument:
    inst = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.provider_symbol == provider_symbol,
    ).first()
    if not inst:
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
    return inst


def _upsert_quote(
    db: Session,
    provider_symbol: str,
    price: float,
    *,
    quote_time: datetime | None = None,
    bid: float | None = None,
    ask: float | None = None,
) -> MarketDataLatestQuote:
    """Insert or update a latest quote. Returns the row."""
    inst = _get_or_create_instrument(db, provider_symbol)
    quote = db.query(MarketDataLatestQuote).filter(
        MarketDataLatestQuote.instrument_id == inst.id,
    ).first()
    now = datetime.now(timezone.utc)
    qt = quote_time if quote_time is not None else now
    if quote:
        quote.last_price = price
        quote.bid_price = bid if bid is not None else price * 0.999
        quote.ask_price = ask if ask is not None else price * 1.001
        quote.quote_time = qt
        quote.updated_at = now
    else:
        quote = MarketDataLatestQuote(
            instrument_id=inst.id,
            provider="binance",
            provider_symbol=provider_symbol,
            last_price=price,
            bid_price=bid if bid is not None else price * 0.999,
            ask_price=ask if ask is not None else price * 1.001,
            quote_time=qt,
            updated_at=now,
        )
        db.add(quote)
    db.flush()
    return quote


def _delete_quote(db: Session, provider_symbol: str) -> None:
    """Remove the latest quote for an instrument entirely."""
    inst = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.provider_symbol == provider_symbol,
    ).first()
    if inst:
        db.query(MarketDataLatestQuote).filter(
            MarketDataLatestQuote.instrument_id == inst.id,
        ).delete()
        db.flush()


def _seed_all_fresh(db: Session) -> None:
    """Seed all quotes fresh (BTC, ETH, EURUSDT)."""
    _upsert_quote(db, "BTCUSDT", BTC_PRICE)
    _upsert_quote(db, "ETHUSDT", ETH_PRICE)
    _upsert_quote(db, "EURUSDT", EURUSDT)


def _make_stale(db: Session, provider_symbol: str) -> None:
    """Make a quote 120s old (beyond MAX_QUOTE_AGE_SECONDS=60)."""
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    _upsert_quote(
        db,
        provider_symbol,
        BTC_PRICE if "BTC" in provider_symbol else ETH_PRICE if "ETH" in provider_symbol else EURUSDT,
        quote_time=stale_time,
    )


def _remove_timestamp(db: Session, provider_symbol: str) -> None:
    """Set quote_time to NULL."""
    inst = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.provider_symbol == provider_symbol,
    ).first()
    if inst:
        quote = db.query(MarketDataLatestQuote).filter(
            MarketDataLatestQuote.instrument_id == inst.id,
        ).first()
        if quote:
            quote.quote_time = None
            db.flush()


def _setup_env(http: TestClient, db: Session) -> tuple[str, dict]:
    """Full setup: client + BTC position. Returns (client_id, mobile auth headers)."""
    _ensure_crypto_custody_bootstrap(http)
    for asset in ("BTC", "ETH", "SOL", "XRP", "ADA"):
        _set_settlement_wallet_actual_balance(http, asset, "100000")
    set_settlement_wallet_balance("ETH", Decimal("1000"))
    pe_client = _full_setup(http, db, initial_eur=50_000.0)
    auth = mobile_auth_headers(db, pe_client)
    _buy_btc(http, str(pe_client.id), 5_000.0)
    return str(pe_client.id), auth


def _count_orders(db: Session, client_id: str) -> int:
    from uuid import UUID
    return db.query(ExchangeOrder).filter(ExchangeOrder.client_id == UUID(client_id)).count()


# ===================================================================
# Test 1 — Source quote stale
# ===================================================================

def _assert_error(res, expected_code: int, expected_error_code: str) -> None:
    assert res.status_code == expected_code, f"Expected {expected_code}, got {res.status_code}: {res.text}"
    detail = res.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("error_code") == expected_error_code, f"Expected {expected_error_code}, got {detail}"
    else:
        assert expected_error_code in str(detail), f"Expected {expected_error_code} in {detail}"


def test_swap_source_quote_stale_preview(client: TestClient, db: Session):
    """preview_swap rejected when source quote is stale."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    _make_stale(db, "BTCUSDT")

    res = client.post(
        "/api/app/exchange/swap/preview",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "MARKET_QUOTE_STALE")


def test_swap_source_quote_stale_exec(client: TestClient, db: Session):
    """swap rejected when source quote is stale — no side effects."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    orders_before = _count_orders(db, cid)
    _make_stale(db, "BTCUSDT")

    res = client.post(
        "/api/app/exchange/swap",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "MARKET_QUOTE_STALE")
    assert _count_orders(db, cid) == orders_before


# ===================================================================
# Test 2 — Target quote stale
# ===================================================================

def test_swap_target_quote_stale_preview(client: TestClient, db: Session):
    """preview_swap rejected when target quote is stale."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    _make_stale(db, "ETHUSDT")

    res = client.post(
        "/api/app/exchange/swap/preview",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "MARKET_QUOTE_STALE")


def test_swap_target_quote_stale_exec(client: TestClient, db: Session):
    """swap rejected when target quote is stale — no side effects."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    orders_before = _count_orders(db, cid)
    _make_stale(db, "ETHUSDT")

    res = client.post(
        "/api/app/exchange/swap",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "MARKET_QUOTE_STALE")
    assert _count_orders(db, cid) == orders_before


# ===================================================================
# Test 3 — Source quote missing
# ===================================================================

def test_swap_source_quote_missing_preview(client: TestClient, db: Session):
    """preview_swap rejected when source quote is absent."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    _delete_quote(db, "BTCUSDT")

    res = client.post(
        "/api/app/exchange/swap/preview",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "PRICE_UNAVAILABLE")


def test_swap_source_quote_missing_exec(client: TestClient, db: Session):
    """swap rejected when source quote is absent — no side effects."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    orders_before = _count_orders(db, cid)
    _delete_quote(db, "BTCUSDT")

    res = client.post(
        "/api/app/exchange/swap",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "PRICE_UNAVAILABLE")
    assert _count_orders(db, cid) == orders_before


# ===================================================================
# Test 4 — Target quote missing
# ===================================================================

def test_swap_target_quote_missing_preview(client: TestClient, db: Session):
    """preview_swap rejected when target quote is absent."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    _delete_quote(db, "ETHUSDT")

    res = client.post(
        "/api/app/exchange/swap/preview",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "PRICE_UNAVAILABLE")


def test_swap_target_quote_missing_exec(client: TestClient, db: Session):
    """swap rejected when target quote is absent — no side effects."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    orders_before = _count_orders(db, cid)
    _delete_quote(db, "ETHUSDT")

    res = client.post(
        "/api/app/exchange/swap",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "PRICE_UNAVAILABLE")
    assert _count_orders(db, cid) == orders_before


# ===================================================================
# Test 5 — Source quote missing timestamp
# ===================================================================

def test_swap_source_no_timestamp_preview(client: TestClient, db: Session):
    """preview_swap rejected when source quote has no quote_time."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    _remove_timestamp(db, "BTCUSDT")

    res = client.post(
        "/api/app/exchange/swap/preview",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "MARKET_QUOTE_STALE")


def test_swap_source_no_timestamp_exec(client: TestClient, db: Session):
    """swap rejected when source quote has no quote_time — no side effects."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    orders_before = _count_orders(db, cid)
    _remove_timestamp(db, "BTCUSDT")

    res = client.post(
        "/api/app/exchange/swap",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "MARKET_QUOTE_STALE")
    assert _count_orders(db, cid) == orders_before


# ===================================================================
# Test 6 — Target quote missing timestamp
# ===================================================================

def test_swap_target_no_timestamp_preview(client: TestClient, db: Session):
    """preview_swap rejected when target quote has no quote_time."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    _remove_timestamp(db, "ETHUSDT")

    res = client.post(
        "/api/app/exchange/swap/preview",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "MARKET_QUOTE_STALE")


def test_swap_target_no_timestamp_exec(client: TestClient, db: Session):
    """swap rejected when target quote has no quote_time — no side effects."""
    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)
    orders_before = _count_orders(db, cid)
    _remove_timestamp(db, "ETHUSDT")

    res = client.post(
        "/api/app/exchange/swap",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "MARKET_QUOTE_STALE")
    assert _count_orders(db, cid) == orders_before


# ===================================================================
# Test 7 — No side effects on rejection (comprehensive)
# ===================================================================

def test_swap_stale_no_side_effects(client: TestClient, db: Session):
    """After a rejected swap (stale source), positions and orders are unchanged."""
    from services.exchange.models import CryptoPosition

    cid, auth = _setup_env(client, db)
    _seed_all_fresh(db)

    from uuid import UUID
    pos_before = (
        db.query(CryptoPosition)
        .filter(CryptoPosition.client_id == UUID(cid), CryptoPosition.asset == "BTC")
        .first()
    )
    btc_balance_before = Decimal(str(pos_before.balance)) if pos_before else Decimal("0")
    orders_before = _count_orders(db, cid)

    eth_pos_before = (
        db.query(CryptoPosition)
        .filter(CryptoPosition.client_id == UUID(cid), CryptoPosition.asset == "ETH")
        .first()
    )
    eth_balance_before = Decimal(str(eth_pos_before.balance)) if eth_pos_before else Decimal("0")

    # Make source stale
    _make_stale(db, "BTCUSDT")

    res = client.post(
        "/api/app/exchange/swap",
        json={"from_asset": "BTC", "to_asset": "ETH", "amount_from": 0.01},
        headers=auth,
    )
    _assert_error(res, 503, "MARKET_QUOTE_STALE")

    # Verify no side effects
    pos_after = (
        db.query(CryptoPosition)
        .filter(CryptoPosition.client_id == UUID(cid), CryptoPosition.asset == "BTC")
        .first()
    )
    btc_balance_after = Decimal(str(pos_after.balance)) if pos_after else Decimal("0")
    assert btc_balance_after == btc_balance_before

    eth_pos_after = (
        db.query(CryptoPosition)
        .filter(CryptoPosition.client_id == UUID(cid), CryptoPosition.asset == "ETH")
        .first()
    )
    eth_balance_after = Decimal(str(eth_pos_after.balance)) if eth_pos_after else Decimal("0")
    assert eth_balance_after == eth_balance_before

    assert _count_orders(db, cid) == orders_before

    # No swap_group_id should have been created
    swap_groups = (
        db.query(ExchangeOrder.swap_group_id)
        .filter(
            ExchangeOrder.client_id == UUID(cid),
            ExchangeOrder.swap_group_id.isnot(None),
        )
        .all()
    )
    assert len(swap_groups) == 0
