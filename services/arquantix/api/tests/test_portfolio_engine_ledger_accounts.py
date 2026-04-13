"""Tests for Portfolio Engine — Ledger Accounts module."""
import uuid

import pytest
from sqlalchemy.orm import Session

from conftest import make_linked_client
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.wallets.models import WalletContainer
from services.portfolio_engine.ledger_accounts.models import LedgerAccount
from services.portfolio_engine.ledger_accounts.repository import LedgerAccountRepository
from services.portfolio_engine.ledger_accounts.service import (
    AssetReferenceError,
    ClientReferenceError,
    DuplicateAccountCodeError,
    LedgerAccountNotFoundError,
    LedgerAccountService,
    WalletContainerReferenceError,
)
from services.portfolio_engine.ledger_accounts.schemas import LedgerAccountCreate, LedgerAccountUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db: Session) -> Client:
    return make_linked_client(db, email=f"ledger-{uuid.uuid4().hex[:8]}@test.com", status="active", kyc_status="approved")


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol=f"BTC-{uuid.uuid4().hex[:6]}", name="Bitcoin", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def portfolio(db: Session, client: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=client.id, portfolio_type="bundle_portfolio",
        name="Test PF", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def wallet_container(db: Session, portfolio: Portfolio) -> WalletContainer:
    w = WalletContainer(
        id=uuid.uuid4(), client_id=portfolio.client_id, portfolio_id=portfolio.id,
        wallet_type="cash_wallet", status="active", metadata_={},
    )
    db.add(w)
    db.flush()
    return w


@pytest.fixture
def ledger_account(db: Session, client: Client) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), client_id=client.id, account_type="client",
        account_code=f"CLI-{uuid.uuid4().hex[:8]}-EUR", label="Client EUR Account",
        currency="EUR", status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def service() -> LedgerAccountService:
    return LedgerAccountService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestLedgerAccountRepository:

    def test_create(self, db: Session, client: Client):
        code = f"TEST-{uuid.uuid4().hex[:8]}"
        la = LedgerAccountRepository.create(
            db,
            data={
                "client_id": client.id,
                "account_type": "client",
                "account_code": code,
                "label": "Test Account",
                "currency": "EUR",
                "status": "active",
                "metadata_": {},
            },
        )
        assert la.id is not None
        assert la.account_code == code
        assert la.account_type == "client"

    def test_get_by_id(self, db: Session, ledger_account: LedgerAccount):
        found = LedgerAccountRepository.get_by_id(db, ledger_account.id)
        assert found is not None
        assert found.account_code == ledger_account.account_code

    def test_get_by_id_not_found(self, db: Session):
        assert LedgerAccountRepository.get_by_id(db, uuid.uuid4()) is None

    def test_get_by_code(self, db: Session, ledger_account: LedgerAccount):
        found = LedgerAccountRepository.get_by_code(db, ledger_account.account_code)
        assert found is not None
        assert found.id == ledger_account.id

    def test_list_all(self, db: Session, ledger_account: LedgerAccount):
        LedgerAccountRepository.create(
            db,
            data={
                "account_type": "treasury",
                "account_code": f"TREASURY-{uuid.uuid4().hex[:8]}",
                "label": "Treasury BTC",
                "currency": "BTC",
                "status": "active",
                "metadata_": {},
            },
        )
        items, total = LedgerAccountRepository.list(db)
        assert total >= 2

    def test_list_filter_by_client(self, db: Session, ledger_account: LedgerAccount, client: Client):
        items, total = LedgerAccountRepository.list(db, client_id=client.id)
        assert total >= 1
        assert all(a.client_id == client.id for a in items)

    def test_list_filter_by_account_type(self, db: Session, ledger_account: LedgerAccount):
        items, total = LedgerAccountRepository.list(db, account_type="client")
        assert total >= 1
        assert all(a.account_type == "client" for a in items)

    def test_list_filter_by_currency(self, db: Session, ledger_account: LedgerAccount):
        items, total = LedgerAccountRepository.list(db, currency="EUR")
        assert total >= 1
        assert all(a.currency == "EUR" for a in items)

    def test_update(self, db: Session, ledger_account: LedgerAccount):
        LedgerAccountRepository.update(db, ledger_account, data={"label": "Updated Label", "status": "frozen"})
        db.flush()
        refreshed = LedgerAccountRepository.get_by_id(db, ledger_account.id)
        assert refreshed.label == "Updated Label"
        assert refreshed.status == "frozen"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestLedgerAccountService:

    def test_create_account(self, db: Session, service: LedgerAccountService, client: Client):
        code = f"CLI-{uuid.uuid4().hex[:8]}-EUR"
        payload = LedgerAccountCreate(
            client_id=client.id, account_type="client", account_code=code,
            label="Client EUR", currency="EUR",
        )
        account = service.create_account(db, payload)
        assert account.account_code == code
        assert account.client_id == client.id
        assert account.balance == 0

    def test_create_account_minimal_internal(self, db: Session, service: LedgerAccountService):
        code = f"RL-{uuid.uuid4().hex[:8]}-EUR"
        payload = LedgerAccountCreate(
            account_type="rl_internal", account_code=code,
            label="R/L EUR", currency="EUR",
        )
        account = service.create_account(db, payload)
        assert account.client_id is None
        assert account.account_type == "rl_internal"

    def test_create_account_with_asset(self, db: Session, service: LedgerAccountService, client: Client, asset_btc: Asset):
        code = f"CLI-{uuid.uuid4().hex[:8]}-BTC"
        payload = LedgerAccountCreate(
            client_id=client.id, account_type="client", account_code=code,
            label="Client BTC", currency="BTC", asset_id=asset_btc.id,
        )
        account = service.create_account(db, payload)
        assert account.asset_id == asset_btc.id

    def test_create_account_with_wallet_container(self, db: Session, service: LedgerAccountService, client: Client, wallet_container: WalletContainer):
        code = f"CLI-{uuid.uuid4().hex[:8]}-EUR"
        payload = LedgerAccountCreate(
            client_id=client.id, account_type="client", account_code=code,
            label="Client EUR", currency="EUR", wallet_container_id=wallet_container.id,
        )
        account = service.create_account(db, payload)
        assert account.wallet_container_id == wallet_container.id

    def test_create_account_duplicate_code(self, db: Session, service: LedgerAccountService, ledger_account: LedgerAccount):
        payload = LedgerAccountCreate(
            account_type="treasury", account_code=ledger_account.account_code,
            label="Duplicate", currency="EUR",
        )
        with pytest.raises(DuplicateAccountCodeError):
            service.create_account(db, payload)

    def test_create_account_invalid_client(self, db: Session, service: LedgerAccountService):
        payload = LedgerAccountCreate(
            client_id=uuid.uuid4(), account_type="client",
            account_code=f"BAD-{uuid.uuid4().hex[:8]}", label="Bad", currency="EUR",
        )
        with pytest.raises(ClientReferenceError):
            service.create_account(db, payload)

    def test_create_account_invalid_asset(self, db: Session, service: LedgerAccountService):
        payload = LedgerAccountCreate(
            account_type="treasury", account_code=f"BAD-{uuid.uuid4().hex[:8]}",
            label="Bad", currency="BTC", asset_id=uuid.uuid4(),
        )
        with pytest.raises(AssetReferenceError):
            service.create_account(db, payload)

    def test_create_account_invalid_wallet_container(self, db: Session, service: LedgerAccountService):
        payload = LedgerAccountCreate(
            account_type="client", account_code=f"BAD-{uuid.uuid4().hex[:8]}",
            label="Bad", currency="EUR", wallet_container_id=uuid.uuid4(),
        )
        with pytest.raises(WalletContainerReferenceError):
            service.create_account(db, payload)

    def test_get_account(self, db: Session, service: LedgerAccountService, ledger_account: LedgerAccount):
        found = service.get_account(db, ledger_account.id)
        assert found.id == ledger_account.id

    def test_get_account_not_found(self, db: Session, service: LedgerAccountService):
        with pytest.raises(LedgerAccountNotFoundError):
            service.get_account(db, uuid.uuid4())

    def test_list_accounts(self, db: Session, service: LedgerAccountService, ledger_account: LedgerAccount):
        items, total = service.list_accounts(db)
        assert total >= 1

    def test_update_account(self, db: Session, service: LedgerAccountService, ledger_account: LedgerAccount):
        payload = LedgerAccountUpdate(label="Updated Label")
        updated = service.update_account(db, ledger_account.id, payload)
        assert updated.label == "Updated Label"

    def test_update_account_status(self, db: Session, service: LedgerAccountService, ledger_account: LedgerAccount):
        payload = LedgerAccountUpdate(status="frozen")
        updated = service.update_account(db, ledger_account.id, payload)
        assert updated.status == "frozen"

    def test_update_account_partial(self, db: Session, service: LedgerAccountService, ledger_account: LedgerAccount):
        original_label = ledger_account.label
        payload = LedgerAccountUpdate(status="frozen")
        updated = service.update_account(db, ledger_account.id, payload)
        assert updated.status == "frozen"
        assert updated.label == original_label

    def test_update_account_invalid_wallet_container(self, db: Session, service: LedgerAccountService, ledger_account: LedgerAccount):
        payload = LedgerAccountUpdate(wallet_container_id=uuid.uuid4())
        with pytest.raises(WalletContainerReferenceError):
            service.update_account(db, ledger_account.id, payload)
