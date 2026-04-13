"""Shared helpers for Envelope Entry Wallet hardening tests.

Provides:
  - DB fixture pattern (dotenv + SessionLocal + rollback)
  - Client/product/balance setup
  - ExchangeService mock (deterministic buy/swap with crypto_positions side-effects)
  - Snapshot helpers for before/after state comparison
"""
from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Optional

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

# ── Deterministic exchange rates for reproducible tests ─────────
MOCK_EUR_USDC_PRICE = Decimal("0.87")
MOCK_BTC_USDC_PRICE = Decimal("62000")
MOCK_FEE_BPS = Decimal("0")

_ZERO = Decimal("0")


# ── DB fixture ──────────────────────────────────────────────────

@pytest.fixture
def db():
    from dotenv import load_dotenv
    env_dir = Path(__file__).resolve().parent.parent
    load_dotenv(env_dir / ".env.local")
    load_dotenv(env_dir / ".env")
    from database import SessionLocal
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


# ── Client helpers ──────────────────────────────────────────────

def create_client(db: Session, email: str):
    row = db.execute(
        text("SELECT id FROM pe_clients WHERE email = :e"), {"e": email},
    ).first()
    if row:
        class _C: pass
        c = _C(); c.id = row[0]; c.email = email
        return c
    cid = uuid.uuid4()
    db.execute(text(
        "INSERT INTO pe_clients (id, email, status, reference_currency, created_at, updated_at) "
        "VALUES (:id, :e, 'active', 'EUR', now(), now())"
    ), {"id": cid, "e": email})
    db.flush()
    class _C: pass
    c = _C(); c.id = cid; c.email = email
    return c


# ── Balance helpers ─────────────────────────────────────────────

def set_crypto_balance(db: Session, client_id, asset: str, amount):
    from services.exchange.repository import CryptoPositionRepository
    pos = CryptoPositionRepository.get_or_create_for_update(db, client_id, asset)
    pos.balance = Decimal(str(amount))
    pos.available_balance = Decimal(str(amount))
    db.flush()
    return pos


def get_crypto_balance(db: Session, client_id, asset: str) -> dict:
    from services.exchange.repository import CryptoPositionRepository
    pos = CryptoPositionRepository.get_or_create_for_update(db, client_id, asset)
    return {
        "balance": Decimal(str(pos.balance)),
        "available_balance": Decimal(str(pos.available_balance)),
    }


def set_eur_custody_balance(db: Session, client_id, amount):
    """Set up a EUR custody account + balance for a client."""
    acct_id = db.execute(text(
        "SELECT id FROM custody_accounts WHERE client_id = :cid AND currency = 'EUR' LIMIT 1"
    ), {"cid": str(client_id)}).scalar()

    if acct_id is None:
        acct_id = uuid.uuid4()
        provider_id = db.execute(text(
            "SELECT id FROM custody_providers LIMIT 1"
        )).scalar()
        if provider_id is None:
            provider_id = uuid.uuid4()
            db.execute(text(
                "INSERT INTO custody_providers (id, name, provider_type, status, created_at, updated_at) "
                "VALUES (:id, 'test_provider', 'bank', 'active', now(), now())"
            ), {"id": provider_id})
            db.flush()

        db.execute(text(
            "INSERT INTO custody_accounts (id, provider_id, account_type, currency, client_id, "
            "iban, status, created_at, updated_at) "
            "VALUES (:id, :pid, 'client', 'EUR', :cid, :iban, 'active', now(), now())"
        ), {
            "id": acct_id, "pid": provider_id, "cid": str(client_id),
            "iban": f"FR76300010{uuid.uuid4().hex[:14]}",
        })
        db.flush()

    bal_exists = db.execute(text(
        "SELECT id FROM custody_account_balances WHERE account_id = :aid LIMIT 1"
    ), {"aid": str(acct_id)}).scalar()

    if bal_exists:
        db.execute(text(
            "UPDATE custody_account_balances SET available_balance = :amt WHERE account_id = :aid"
        ), {"amt": str(amount), "aid": str(acct_id)})
    else:
        db.execute(text(
            "INSERT INTO custody_account_balances (id, account_id, available_balance, pending_balance, currency) "
            "VALUES (:id, :aid, :amt, 0, 'EUR')"
        ), {"id": uuid.uuid4(), "aid": str(acct_id), "amt": str(amount)})
    db.flush()
    return acct_id


# ── Product helpers ─────────────────────────────────────────────

def _create_isolated_pool(db: Session, asset: str):
    """Create a pool with a unique synthetic asset to avoid clashing with existing data."""
    from services.lending.pool_models import LendingPool
    tag = uuid.uuid4().hex[:8].upper()
    pool_asset = f"{asset}_{tag}"
    pool = LendingPool(
        asset=pool_asset,
        status="active",
        supply_rate_bps=Decimal("300"),
        borrow_rate_bps=Decimal("500"),
    )
    db.add(pool)
    db.flush()
    return pool, pool_asset


def create_fundraising_product(
    db: Session,
    borrower_client_id,
    asset: str = "USDC",
    target_size=Decimal("1000000"),
    entry_assets_allowed=None,
    min_ticket=None,
    max_ticket=None,
):
    """Create an isolated fundraising product with its own pool.

    Uses a unique synthetic asset name (e.g. USDC_a1b2c3d4) internally to
    avoid unique constraint clashes with existing production data, but the
    product behaves identically to a real USDC product for envelope testing.
    """
    from services.lending.offer_models import LendingPoolProduct

    pool, pool_asset = _create_isolated_pool(db, asset)

    resolved_allowed = [pool_asset]
    if entry_assets_allowed:
        resolved_allowed = []
        for a in entry_assets_allowed:
            if a.upper() == asset.upper():
                resolved_allowed.append(pool_asset)
            else:
                resolved_allowed.append(a.upper())

    product = LendingPoolProduct(
        lending_pool_id=pool.id,
        title=f"Test Offer {uuid.uuid4().hex[:6]}",
        asset=pool_asset,
        borrower_client_id=borrower_client_id,
        target_size=target_size,
        current_raised=Decimal("0"),
        status="fundraising",
        supply_apr_bps=Decimal("300"),
        borrow_apr_bps=Decimal("500"),
        min_ticket=min_ticket,
        max_ticket=max_ticket,
        entry_asset_default=pool_asset,
        entry_assets_allowed=resolved_allowed,
    )
    db.add(product)
    db.flush()
    return product


# ── Exchange mock ───────────────────────────────────────────────

class MockExchangeService:
    """Deterministic exchange service that performs the minimal crypto_positions
    side-effects needed by the orchestrator flow, without requiring market data,
    custody infrastructure, or settlement accounts."""

    def __init__(
        self,
        eur_usdc_price=MOCK_EUR_USDC_PRICE,
        btc_usdc_price=MOCK_BTC_USDC_PRICE,
        fee_bps=MOCK_FEE_BPS,
    ):
        self._eur_usdc_price = eur_usdc_price
        self._btc_usdc_price = btc_usdc_price
        self._fee_bps = fee_bps
        self.buy_calls: list[dict] = []
        self.swap_calls: list[dict] = []

    def buy(self, db, payload, actor):
        from services.exchange.repository import CryptoPositionRepository
        asset = payload.asset.upper()
        price = self._eur_usdc_price
        precision = 6
        quant = Decimal(10) ** -precision
        volume_raw = (payload.fiat_amount / price).quantize(quant, rounding=ROUND_DOWN)
        fee = (volume_raw * self._fee_bps / Decimal("10000")).quantize(quant, rounding=ROUND_DOWN)
        client_crypto = volume_raw - fee
        pos = CryptoPositionRepository.get_or_create_for_update(db, payload.client_id, asset)
        CryptoPositionRepository.credit(db, pos, client_crypto)
        result = {
            "status": "completed",
            "order_id": uuid.uuid4(),
            "amount_crypto": client_crypto,
            "price": price,
            "fee_amount": fee,
            "fee_bps": self._fee_bps,
            "currency": payload.currency,
        }
        self.buy_calls.append(result)
        return result

    def swap(self, db, client_id, payload, actor):
        from services.exchange.repository import CryptoPositionRepository
        from_asset = payload.from_asset.upper()
        to_asset = payload.to_asset.upper()
        btc_usdc = self._btc_usdc_price
        precision_from = 8
        precision_to = 6
        quant_to = Decimal(10) ** -precision_to
        eur_value = payload.amount_from * btc_usdc * self._eur_usdc_price
        fee_eur = (eur_value * self._fee_bps / Decimal("10000")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        net_eur = eur_value - fee_eur
        amount_to = (net_eur / self._eur_usdc_price / btc_usdc * payload.amount_from * btc_usdc
                     ).quantize(quant_to, rounding=ROUND_DOWN)
        amount_to = (payload.amount_from * btc_usdc).quantize(quant_to, rounding=ROUND_DOWN)
        pos_from = CryptoPositionRepository.get_or_create_for_update(db, client_id, from_asset)
        CryptoPositionRepository.debit(db, pos_from, payload.amount_from)
        pos_to = CryptoPositionRepository.get_or_create_for_update(db, client_id, to_asset)
        CryptoPositionRepository.credit(db, pos_to, amount_to)
        result = {
            "status": "completed",
            "swap_group_id": uuid.uuid4(),
            "sell_order_id": uuid.uuid4(),
            "buy_order_id": uuid.uuid4(),
            "amount_to": amount_to,
            "from_asset": from_asset,
            "to_asset": to_asset,
        }
        self.swap_calls.append(result)
        return result

    def preview_buy(self, db, asset, fiat_amount, currency):
        price = self._eur_usdc_price
        quant = Decimal("0.000001")
        gross = (fiat_amount / price).quantize(quant, rounding=ROUND_DOWN)
        fee = (gross * self._fee_bps / Decimal("10000")).quantize(quant, rounding=ROUND_DOWN)
        return {
            "estimated_price": float(price),
            "estimated_crypto_gross": float(gross),
            "estimated_crypto_net": float(gross - fee),
            "fee_amount": float(fee),
        }

    def preview_swap(self, db, payload):
        amount_to = (payload.amount_from * self._btc_usdc_price).quantize(
            Decimal("0.000001"), rounding=ROUND_DOWN,
        )
        return {
            "estimated_to_amount": float(amount_to),
            "fee_in_reference_currency": 0.0,
            "estimated_reference_value_gross": float(payload.amount_from * self._btc_usdc_price * self._eur_usdc_price),
            "estimated_reference_value_net": float(payload.amount_from * self._btc_usdc_price * self._eur_usdc_price),
            "from_price_in_ref_ccy": float(self._btc_usdc_price * self._eur_usdc_price),
            "to_price_in_ref_ccy": float(self._eur_usdc_price),
        }


def create_orchestrator_with_mock(mock_exchange=None):
    """Create a LendingInvestOrchestrator with a mocked ExchangeService."""
    from services.lending.invest_orchestrator import LendingInvestOrchestrator
    orch = LendingInvestOrchestrator()
    if mock_exchange is None:
        mock_exchange = MockExchangeService()
    orch._exchange = mock_exchange
    return orch, mock_exchange


# ── Snapshot helpers ────────────────────────────────────────────

def snapshot_crypto(db: Session, client_id) -> dict:
    """Capture all crypto_positions for a client."""
    from services.exchange.repository import CryptoPositionRepository
    positions = CryptoPositionRepository.list_by_client(db, client_id)
    return {
        p.asset: {
            "balance": Decimal(str(p.balance)),
            "available_balance": Decimal(str(p.available_balance)),
        }
        for p in positions
    }


def snapshot_envelopes(db: Session, client_id) -> list[dict]:
    from services.lending.envelope_models import InvestmentEnvelope
    envs = db.query(InvestmentEnvelope).filter(
        InvestmentEnvelope.client_id == client_id,
    ).all()
    result = []
    for e in envs:
        entries = []
        for entry in e.entries:
            entries.append({
                "entry_asset": entry.entry_asset,
                "entry_amount": Decimal(str(entry.entry_amount)),
                "target_asset": entry.target_asset,
                "converted_amount": Decimal(str(entry.converted_amount)),
                "conversion_type": entry.conversion_type,
                "conversion_fee": Decimal(str(entry.conversion_fee)),
                "net_allocated": Decimal(str(entry.net_allocated)),
                "commitment_id": entry.commitment_id,
                "fx_rate": Decimal(str(entry.fx_rate)) if entry.fx_rate else None,
            })
        result.append({
            "id": e.id,
            "type": e.type,
            "reference_id": e.reference_id,
            "status": e.status,
            "entries": entries,
        })
    return result


def snapshot_commitments(db: Session, client_id) -> list[dict]:
    from services.lending.pool_models import PoolSupplyCommitment
    comms = db.query(PoolSupplyCommitment).filter(
        PoolSupplyCommitment.client_id == client_id,
    ).all()
    return [
        {
            "id": c.id,
            "asset": c.asset,
            "amount": Decimal(str(c.amount)),
            "available_amount": Decimal(str(c.available_amount)),
            "status": c.status,
        }
        for c in comms
    ]


def count_envelopes(db: Session, client_id) -> int:
    from services.lending.envelope_models import InvestmentEnvelope
    return db.query(InvestmentEnvelope).filter(
        InvestmentEnvelope.client_id == client_id,
    ).count()


def count_entries(db: Session, client_id) -> int:
    from services.lending.envelope_models import InvestmentEnvelope, InvestmentEnvelopeEntry
    return (
        db.query(InvestmentEnvelopeEntry)
        .join(InvestmentEnvelope)
        .filter(InvestmentEnvelope.client_id == client_id)
        .count()
    )
