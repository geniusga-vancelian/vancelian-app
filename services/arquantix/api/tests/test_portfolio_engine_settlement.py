"""Tests for Portfolio Engine — Settlement module."""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.ledger_accounts.models import LedgerAccount
from services.portfolio_engine.ledger_entries.models import LedgerEntry
from services.portfolio_engine.orders.models import Order
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.settlement.enums import SettlementStatus, SettlementType
from services.portfolio_engine.settlement.models import SettlementInstruction
from services.portfolio_engine.settlement.repository import SettlementRepository
from services.portfolio_engine.settlement.schemas import SettlementCreate, SettlementLeg
from services.portfolio_engine.settlement.service import (
    AssetReferenceError,
    FromAccountReferenceError,
    InvalidSettlementTransitionError,
    SameAccountError,
    SettlementNotFoundError,
    SettlementService,
    ToAccountReferenceError,
    TradeReferenceError,
)
from services.portfolio_engine.trades.models import Trade


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_active(db: Session) -> Client:
    c = Client(id=uuid.uuid4(), email=f"sett-{uuid.uuid4().hex[:8]}@test.com", status="active", kyc_status="approved")
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def asset_eur(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol=f"EUR-{uuid.uuid4().hex[:6]}", name="Euro", asset_type="fiat", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol=f"BTC-{uuid.uuid4().hex[:6]}", name="Bitcoin", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def account_client_eur(db: Session, client_active: Client, asset_eur: Asset) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), client_id=client_active.id, account_type="client",
        account_code=f"CLI-{uuid.uuid4().hex[:8]}-EUR", label="Client EUR",
        currency="EUR", asset_id=asset_eur.id, balance=Decimal("10000"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def account_rl_eur(db: Session, asset_eur: Asset) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), account_type="rl_internal",
        account_code=f"RL-{uuid.uuid4().hex[:8]}-EUR", label="R/L EUR",
        currency="EUR", asset_id=asset_eur.id, balance=Decimal("0"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def account_treasury_btc(db: Session, asset_btc: Asset) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), account_type="treasury",
        account_code=f"TREAS-{uuid.uuid4().hex[:8]}-BTC", label="Treasury BTC",
        currency="BTC", asset_id=asset_btc.id, balance=Decimal("100"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def account_client_btc(db: Session, client_active: Client, asset_btc: Asset) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), client_id=client_active.id, account_type="client",
        account_code=f"CLI-{uuid.uuid4().hex[:8]}-BTC", label="Client BTC",
        currency="BTC", asset_id=asset_btc.id, balance=Decimal("0"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def account_fee_eur(db: Session, asset_eur: Asset) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), account_type="fee",
        account_code=f"FEE-{uuid.uuid4().hex[:8]}-EUR", label="Fee EUR",
        currency="EUR", asset_id=asset_eur.id, balance=Decimal("0"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def account_frozen(db: Session, asset_eur: Asset) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), account_type="client",
        account_code=f"FROZEN-{uuid.uuid4().hex[:8]}", label="Frozen Account",
        currency="EUR", asset_id=asset_eur.id, balance=Decimal("5000"), status="frozen", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_btc.id, code=f"BTC-SPOT-{uuid.uuid4().hex[:6]}",
        name="BTC Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def portfolio(db: Session, client_active: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=client_active.id, portfolio_type="bundle_portfolio",
        name="Settlement Test PF", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def order_accepted(db: Session, client_active: Client, portfolio: Portfolio, instrument_btc: Instrument) -> Order:
    o = Order(
        id=uuid.uuid4(), client_id=client_active.id, portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id, order_type="market", side="buy",
        quantity=Decimal("0.14"), currency="EUR", status="accepted", metadata_={},
    )
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def trade(db: Session, order_accepted: Order, instrument_btc: Instrument) -> Trade:
    t = Trade(
        id=uuid.uuid4(), order_id=order_accepted.id, instrument_id=instrument_btc.id,
        side="buy", quantity=Decimal("0.14"), price=Decimal("68500"),
        gross_amount=Decimal("9590"), fee_amount=Decimal("15"), net_amount=Decimal("9605"),
        currency="EUR", counterparty="binance", executed_at=datetime.now(timezone.utc),
        metadata_={},
    )
    db.add(t)
    db.flush()
    return t


@pytest.fixture
def service() -> SettlementService:
    return SettlementService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestSettlementRepository:

    def test_create(self, db: Session, account_client_eur, account_rl_eur, asset_eur):
        s = SettlementRepository.create(db, data={
            "settlement_type": "internal",
            "from_account_id": account_client_eur.id,
            "to_account_id": account_rl_eur.id,
            "asset_id": asset_eur.id,
            "amount": Decimal("5000"),
            "metadata_": {},
        })
        assert s.id is not None
        assert s.status == "pending"
        assert s.amount == Decimal("5000")

    def test_get_by_id(self, db: Session, account_client_eur, account_rl_eur, asset_eur):
        s = SettlementRepository.create(db, data={
            "settlement_type": "internal",
            "from_account_id": account_client_eur.id,
            "to_account_id": account_rl_eur.id,
            "asset_id": asset_eur.id,
            "amount": Decimal("1000"),
            "metadata_": {},
        })
        found = SettlementRepository.get_by_id(db, s.id)
        assert found is not None
        assert found.settlement_type == "internal"

    def test_get_by_id_not_found(self, db: Session):
        assert SettlementRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_by_status(self, db: Session, account_client_eur, account_rl_eur, asset_eur):
        for _ in range(3):
            SettlementRepository.create(db, data={
                "settlement_type": "internal",
                "from_account_id": account_client_eur.id,
                "to_account_id": account_rl_eur.id,
                "asset_id": asset_eur.id,
                "amount": Decimal("100"),
                "metadata_": {},
            })
        items, total = SettlementRepository.list(db, status="pending")
        assert total >= 3

    def test_update_status(self, db: Session, account_client_eur, account_rl_eur, asset_eur):
        s = SettlementRepository.create(db, data={
            "settlement_type": "internal",
            "from_account_id": account_client_eur.id,
            "to_account_id": account_rl_eur.id,
            "asset_id": asset_eur.id,
            "amount": Decimal("500"),
            "metadata_": {},
        })
        updated = SettlementRepository.update_status(db, s, status="settled", settled_at=datetime.now(timezone.utc))
        assert updated.status == "settled"
        assert updated.settled_at is not None


# ---------------------------------------------------------------------------
# Service tests — create & get & list
# ---------------------------------------------------------------------------

class TestSettlementServiceCRUD:

    def test_create_settlement(self, db: Session, service, account_client_eur, account_rl_eur, asset_eur):
        payload = SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("5000"),
        )
        s = service.create_settlement(db, payload)
        assert s.id is not None
        assert s.status == "pending"
        assert s.settlement_type == "internal"

    def test_create_settlement_with_order_and_trade(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur, order_accepted, trade
    ):
        payload = SettlementCreate(
            order_id=order_accepted.id,
            trade_id=trade.id,
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("9590"),
        )
        s = service.create_settlement(db, payload)
        assert s.order_id == order_accepted.id
        assert s.trade_id == trade.id

    def test_create_settlement_same_account_rejected(self, db: Session, service, account_client_eur, asset_eur):
        payload = SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_client_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("100"),
        )
        with pytest.raises(SameAccountError):
            service.create_settlement(db, payload)

    def test_create_settlement_from_account_not_found(self, db: Session, service, account_rl_eur, asset_eur):
        payload = SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=uuid.uuid4(),
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("100"),
        )
        with pytest.raises(FromAccountReferenceError):
            service.create_settlement(db, payload)

    def test_create_settlement_to_account_not_found(self, db: Session, service, account_client_eur, asset_eur):
        payload = SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=uuid.uuid4(),
            asset_id=asset_eur.id,
            amount=Decimal("100"),
        )
        with pytest.raises(ToAccountReferenceError):
            service.create_settlement(db, payload)

    def test_create_settlement_asset_not_found(self, db: Session, service, account_client_eur, account_rl_eur):
        payload = SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=uuid.uuid4(),
            amount=Decimal("100"),
        )
        with pytest.raises(AssetReferenceError):
            service.create_settlement(db, payload)

    def test_create_settlement_trade_not_found(self, db: Session, service, account_client_eur, account_rl_eur, asset_eur):
        payload = SettlementCreate(
            trade_id=uuid.uuid4(),
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("100"),
        )
        with pytest.raises(TradeReferenceError):
            service.create_settlement(db, payload)

    def test_get_settlement(self, db: Session, service, account_client_eur, account_rl_eur, asset_eur):
        payload = SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("1000"),
        )
        created = service.create_settlement(db, payload)
        found = service.get_settlement(db, created.id)
        assert found.id == created.id

    def test_get_settlement_not_found(self, db: Session, service):
        with pytest.raises(SettlementNotFoundError):
            service.get_settlement(db, uuid.uuid4())

    def test_list_settlements(self, db: Session, service, account_client_eur, account_rl_eur, asset_eur):
        for _ in range(3):
            service.create_settlement(db, SettlementCreate(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_client_eur.id,
                to_account_id=account_rl_eur.id,
                asset_id=asset_eur.id,
                amount=Decimal("100"),
            ))
        items, total = service.list_settlements(db, from_account_id=account_client_eur.id)
        assert total >= 3


# ---------------------------------------------------------------------------
# Service tests — settle (ledger integration)
# ---------------------------------------------------------------------------

class TestSettlementServiceSettle:

    def test_settle_writes_exactly_two_ledger_entries(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("5000"),
        ))
        service.settle(db, s.id)

        entries = db.query(LedgerEntry).filter(
            LedgerEntry.reference_type == "settlement",
            LedgerEntry.reference_id == s.id,
        ).all()
        assert len(entries) == 2
        types = {e.entry_type for e in entries}
        assert types == {"debit", "credit"}

    def test_settle_uses_settlement_reference_type(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("1000"),
        ))
        service.settle(db, s.id)

        entries = db.query(LedgerEntry).filter(
            LedgerEntry.reference_type == "settlement",
            LedgerEntry.reference_id == s.id,
        ).all()
        for e in entries:
            assert e.reference_type == "settlement"
            assert e.reference_id == s.id

    def test_settle_writes_asset_id_on_ledger_entries(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("2000"),
        ))
        service.settle(db, s.id)

        entries = db.query(LedgerEntry).filter(
            LedgerEntry.reference_type == "settlement",
            LedgerEntry.reference_id == s.id,
        ).all()
        assert len(entries) == 2
        for e in entries:
            assert e.asset_id == asset_eur.id
            assert e.currency == "EUR"

    def test_settle_updates_balances_consistently(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        initial_client = Decimal(str(account_client_eur.balance))
        initial_rl = Decimal(str(account_rl_eur.balance))
        amount = Decimal("3000")

        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=amount,
        ))
        service.settle(db, s.id)

        db.refresh(account_client_eur)
        db.refresh(account_rl_eur)
        assert Decimal(str(account_client_eur.balance)) == initial_client + amount
        assert Decimal(str(account_rl_eur.balance)) == initial_rl - amount

    def test_settle_marks_status_and_timestamp(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("500"),
        ))
        settled = service.settle(db, s.id)
        assert settled.status == "settled"
        assert settled.settled_at is not None

    def test_settle_with_external_reference(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.BANK_TRANSFER,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("2000"),
        ))
        settled = service.settle(db, s.id, external_reference="WIRE-12345")
        assert settled.external_reference == "WIRE-12345"

    def test_settle_already_settled_rejected(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("500"),
        ))
        service.settle(db, s.id)
        with pytest.raises(InvalidSettlementTransitionError):
            service.settle(db, s.id)

    def test_settle_from_in_progress(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.LP_SETTLEMENT,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("1000"),
            scheduled_at=datetime.now(timezone.utc),
        ))
        service.mark_scheduled(db, s.id, datetime.now(timezone.utc))
        service.mark_in_progress(db, s.id)
        settled = service.settle(db, s.id)
        assert settled.status == "settled"

        entries = db.query(LedgerEntry).filter(
            LedgerEntry.reference_type == "settlement",
            LedgerEntry.reference_id == s.id,
        ).all()
        assert len(entries) == 2

    def test_settle_frozen_account_rejected(
        self, db: Session, service, account_frozen, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_frozen.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("500"),
        ))
        from services.portfolio_engine.ledger_entries.service import InactiveAccountError
        with pytest.raises(InactiveAccountError):
            service.settle(db, s.id)


# ---------------------------------------------------------------------------
# Service tests — fail
# ---------------------------------------------------------------------------

class TestSettlementServiceFail:

    def test_fail_does_not_write_ledger_entries(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("1000"),
        ))
        service.fail(db, s.id, "Insufficient LP liquidity")

        entries = db.query(LedgerEntry).filter(
            LedgerEntry.reference_type == "settlement",
            LedgerEntry.reference_id == s.id,
        ).all()
        assert len(entries) == 0

    def test_fail_sets_reason_and_timestamp(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.BANK_TRANSFER,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("1000"),
        ))
        failed = service.fail(db, s.id, "Wire rejected by bank")
        assert failed.status == "failed"
        assert failed.failure_reason == "Wire rejected by bank"
        assert failed.failed_at is not None

    def test_fail_already_settled_rejected(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("500"),
        ))
        service.settle(db, s.id)
        with pytest.raises(InvalidSettlementTransitionError):
            service.fail(db, s.id, "Too late")

    def test_fail_already_failed_rejected(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("500"),
        ))
        service.fail(db, s.id, "First failure")
        with pytest.raises(InvalidSettlementTransitionError):
            service.fail(db, s.id, "Second failure")


# ---------------------------------------------------------------------------
# Service tests — status transitions
# ---------------------------------------------------------------------------

class TestSettlementStatusTransitions:

    def test_full_deferred_lifecycle(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        """pending → scheduled → in_progress → settled"""
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.LP_SETTLEMENT,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("2000"),
        ))
        assert s.status == "pending"

        scheduled = service.mark_scheduled(db, s.id, datetime.now(timezone.utc) + timedelta(hours=8))
        assert scheduled.status == "scheduled"
        assert scheduled.scheduled_at is not None

        started = service.mark_in_progress(db, s.id)
        assert started.status == "in_progress"

        settled = service.settle(db, s.id, external_reference="LP-BATCH-20260315")
        assert settled.status == "settled"
        assert settled.external_reference == "LP-BATCH-20260315"

    def test_invalid_transition_pending_to_in_progress(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("100"),
        ))
        with pytest.raises(InvalidSettlementTransitionError):
            service.mark_in_progress(db, s.id)

    def test_invalid_transition_scheduled_to_settled(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.LP_SETTLEMENT,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("100"),
        ))
        service.mark_scheduled(db, s.id, datetime.now(timezone.utc))
        with pytest.raises(InvalidSettlementTransitionError):
            service.settle(db, s.id)


# ---------------------------------------------------------------------------
# Service tests — immutable core fields
# ---------------------------------------------------------------------------

class TestSettlementImmutability:

    def test_core_fields_not_changed_after_settle(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        s = service.create_settlement(db, SettlementCreate(
            settlement_type=SettlementType.INTERNAL,
            from_account_id=account_client_eur.id,
            to_account_id=account_rl_eur.id,
            asset_id=asset_eur.id,
            amount=Decimal("777"),
        ))
        original_from = s.from_account_id
        original_to = s.to_account_id
        original_asset = s.asset_id
        original_amount = s.amount

        service.settle(db, s.id)
        db.refresh(s)

        assert s.from_account_id == original_from
        assert s.to_account_id == original_to
        assert s.asset_id == original_asset
        assert s.amount == original_amount


# ---------------------------------------------------------------------------
# Service tests — trade integration
# ---------------------------------------------------------------------------

class TestSettlementTradeIntegration:

    def test_create_trade_settlements(
        self, db: Session, service, trade, order_accepted,
        account_client_eur, account_rl_eur, account_treasury_btc, account_client_btc,
        account_fee_eur, asset_eur, asset_btc,
    ):
        legs = [
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_client_eur.id,
                to_account_id=account_rl_eur.id,
                asset_id=asset_eur.id,
                amount=Decimal("9590"),
            ),
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_treasury_btc.id,
                to_account_id=account_client_btc.id,
                asset_id=asset_btc.id,
                amount=Decimal("0.14"),
            ),
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_client_eur.id,
                to_account_id=account_fee_eur.id,
                asset_id=asset_eur.id,
                amount=Decimal("15"),
            ),
        ]

        instructions = service.create_trade_settlements(
            db, trade_id=trade.id, order_id=order_accepted.id, legs=legs,
        )
        assert len(instructions) == 3

        group_ids = {s.settlement_group_id for s in instructions}
        assert len(group_ids) == 1
        assert None not in group_ids

        for s in instructions:
            assert s.trade_id == trade.id
            assert s.order_id == order_accepted.id
            assert s.status == "pending"

    def test_create_trade_settlements_auto_group_id(
        self, db: Session, service, trade, account_client_eur, account_rl_eur, asset_eur
    ):
        legs = [
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_client_eur.id,
                to_account_id=account_rl_eur.id,
                asset_id=asset_eur.id,
                amount=Decimal("1000"),
            ),
        ]
        instructions = service.create_trade_settlements(db, trade_id=trade.id, legs=legs)
        assert instructions[0].settlement_group_id is not None

    def test_create_trade_settlements_explicit_group_id(
        self, db: Session, service, trade, account_client_eur, account_rl_eur, asset_eur
    ):
        group_id = uuid.uuid4()
        legs = [
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_client_eur.id,
                to_account_id=account_rl_eur.id,
                asset_id=asset_eur.id,
                amount=Decimal("1000"),
            ),
        ]
        instructions = service.create_trade_settlements(
            db, trade_id=trade.id, legs=legs, settlement_group_id=group_id,
        )
        assert instructions[0].settlement_group_id == group_id

    def test_create_trade_settlements_trade_not_found(
        self, db: Session, service, account_client_eur, account_rl_eur, asset_eur
    ):
        legs = [
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_client_eur.id,
                to_account_id=account_rl_eur.id,
                asset_id=asset_eur.id,
                amount=Decimal("1000"),
            ),
        ]
        with pytest.raises(TradeReferenceError):
            service.create_trade_settlements(db, trade_id=uuid.uuid4(), legs=legs)

    def test_settle_all_trade_legs(
        self, db: Session, service, trade, order_accepted,
        account_client_eur, account_rl_eur, account_treasury_btc, account_client_btc,
        asset_eur, asset_btc,
    ):
        """Settle all legs of a trade and verify ledger entries."""
        initial_client_eur = Decimal(str(account_client_eur.balance))
        initial_rl_eur = Decimal(str(account_rl_eur.balance))
        initial_treasury_btc = Decimal(str(account_treasury_btc.balance))
        initial_client_btc = Decimal(str(account_client_btc.balance))

        legs = [
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_client_eur.id,
                to_account_id=account_rl_eur.id,
                asset_id=asset_eur.id,
                amount=Decimal("9590"),
            ),
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_treasury_btc.id,
                to_account_id=account_client_btc.id,
                asset_id=asset_btc.id,
                amount=Decimal("0.14"),
            ),
        ]
        instructions = service.create_trade_settlements(
            db, trade_id=trade.id, order_id=order_accepted.id, legs=legs,
        )

        for s in instructions:
            service.settle(db, s.id)

        db.refresh(account_client_eur)
        db.refresh(account_rl_eur)
        db.refresh(account_treasury_btc)
        db.refresh(account_client_btc)

        assert Decimal(str(account_client_eur.balance)) == initial_client_eur + Decimal("9590")
        assert Decimal(str(account_rl_eur.balance)) == initial_rl_eur - Decimal("9590")
        assert Decimal(str(account_treasury_btc.balance)) == initial_treasury_btc + Decimal("0.14")
        assert Decimal(str(account_client_btc.balance)) == initial_client_btc - Decimal("0.14")

        all_entries = db.query(LedgerEntry).filter(
            LedgerEntry.reference_type == "settlement",
        ).all()
        trade_entries = [e for e in all_entries if e.reference_id in {s.id for s in instructions}]
        assert len(trade_entries) == 4


# ---------------------------------------------------------------------------
# Service tests — settlement_group_id grouping
# ---------------------------------------------------------------------------

class TestSettlementGrouping:

    def test_group_id_groups_related_instructions(
        self, db: Session, service, trade,
        account_client_eur, account_rl_eur, account_treasury_btc, account_client_btc,
        asset_eur, asset_btc,
    ):
        legs = [
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_client_eur.id,
                to_account_id=account_rl_eur.id,
                asset_id=asset_eur.id,
                amount=Decimal("5000"),
            ),
            SettlementLeg(
                settlement_type=SettlementType.INTERNAL,
                from_account_id=account_treasury_btc.id,
                to_account_id=account_client_btc.id,
                asset_id=asset_btc.id,
                amount=Decimal("0.07"),
            ),
        ]
        instructions = service.create_trade_settlements(db, trade_id=trade.id, legs=legs)
        group_id = instructions[0].settlement_group_id

        items, total = service.list_settlements(db, settlement_group_id=group_id)
        assert total == 2
        assert all(s.settlement_group_id == group_id for s in items)
