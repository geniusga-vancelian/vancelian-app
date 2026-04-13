"""Tests for Portfolio Engine — Ledger Entries module."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.ledger_accounts.models import LedgerAccount
from services.portfolio_engine.ledger_entries.models import LedgerEntry
from services.portfolio_engine.ledger_entries.repository import LedgerEntryRepository
from services.portfolio_engine.ledger_entries.service import (
    AccountNotFoundError,
    AssetMismatchError,
    CurrencyMismatchError,
    InactiveAccountError,
    LedgerEntryNotFoundError,
    LedgerEntryService,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db: Session) -> Client:
    c = Client(id=uuid.uuid4(), email=f"le-{uuid.uuid4().hex[:8]}@test.com", status="active", kyc_status="approved")
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def account_client_eur(db: Session, client: Client) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), client_id=client.id, account_type="client",
        account_code=f"CLI-{uuid.uuid4().hex[:8]}-EUR", label="Client EUR",
        currency="EUR", balance=Decimal("10000"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def account_rl_eur(db: Session) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), account_type="rl_internal",
        account_code=f"RL-{uuid.uuid4().hex[:8]}-EUR", label="R/L EUR",
        currency="EUR", balance=Decimal("0"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def account_treasury_btc(db: Session) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), account_type="treasury",
        account_code=f"TREASURY-{uuid.uuid4().hex[:8]}-BTC", label="Treasury BTC",
        currency="BTC", balance=Decimal("100"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


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
def account_client_eur_with_asset(db: Session, client: Client, asset_eur: Asset) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), client_id=client.id, account_type="client",
        account_code=f"CLI-A-{uuid.uuid4().hex[:8]}-EUR", label="Client EUR (with asset)",
        currency="EUR", asset_id=asset_eur.id, balance=Decimal("10000"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def account_rl_eur_with_asset(db: Session, asset_eur: Asset) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), account_type="rl_internal",
        account_code=f"RL-A-{uuid.uuid4().hex[:8]}-EUR", label="R/L EUR (with asset)",
        currency="EUR", asset_id=asset_eur.id, balance=Decimal("0"), status="active", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def account_frozen(db: Session) -> LedgerAccount:
    la = LedgerAccount(
        id=uuid.uuid4(), account_type="client",
        account_code=f"FROZEN-{uuid.uuid4().hex[:8]}", label="Frozen Account",
        currency="EUR", balance=Decimal("0"), status="frozen", metadata_={},
    )
    db.add(la)
    db.flush()
    return la


@pytest.fixture
def service() -> LedgerEntryService:
    return LedgerEntryService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestLedgerEntryRepository:

    def test_create(self, db: Session, account_client_eur: LedgerAccount):
        entry = LedgerEntryRepository.create(db, data={
            "account_id": account_client_eur.id,
            "entry_type": "debit",
            "amount": Decimal("1000"),
            "currency": "EUR",
            "reference_type": "deposit",
            "effective_at": datetime.now(timezone.utc),
            "metadata_": {},
        })
        assert entry.id is not None
        assert entry.entry_type == "debit"
        assert entry.amount == Decimal("1000")

    def test_get_by_id(self, db: Session, account_client_eur: LedgerAccount):
        entry = LedgerEntryRepository.create(db, data={
            "account_id": account_client_eur.id,
            "entry_type": "credit",
            "amount": Decimal("500"),
            "currency": "EUR",
            "reference_type": "withdrawal",
            "effective_at": datetime.now(timezone.utc),
            "metadata_": {},
        })
        found = LedgerEntryRepository.get_by_id(db, entry.id)
        assert found is not None
        assert found.amount == Decimal("500")

    def test_get_by_id_not_found(self, db: Session):
        assert LedgerEntryRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_by_account(self, db: Session, account_client_eur: LedgerAccount):
        for i in range(3):
            LedgerEntryRepository.create(db, data={
                "account_id": account_client_eur.id,
                "entry_type": "debit",
                "amount": Decimal(str(100 * (i + 1))),
                "currency": "EUR",
                "reference_type": "deposit",
                "effective_at": datetime.now(timezone.utc),
                "metadata_": {},
            })
        items, total = LedgerEntryRepository.list(db, account_id=account_client_eur.id)
        assert total == 3

    def test_list_by_reference_type(self, db: Session, account_client_eur: LedgerAccount):
        LedgerEntryRepository.create(db, data={
            "account_id": account_client_eur.id,
            "entry_type": "debit",
            "amount": Decimal("100"),
            "currency": "EUR",
            "reference_type": "fee",
            "effective_at": datetime.now(timezone.utc),
            "metadata_": {},
        })
        items, total = LedgerEntryRepository.list(db, reference_type="fee")
        assert total >= 1
        assert all(e.reference_type == "fee" for e in items)


# ---------------------------------------------------------------------------
# Service tests — double-entry posting
# ---------------------------------------------------------------------------

class TestLedgerEntryService:

    def test_post_double_entry(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount, account_rl_eur: LedgerAccount):
        initial_client_balance = Decimal(str(account_client_eur.balance))
        initial_rl_balance = Decimal(str(account_rl_eur.balance))
        amount = Decimal("5000")

        debit_entry, credit_entry = service.post_double_entry(
            db,
            debit_account_id=account_rl_eur.id,
            credit_account_id=account_client_eur.id,
            amount=amount,
            currency="EUR",
            reference_type="trade",
            effective_at=datetime.now(timezone.utc),
            description="EUR to R/L for BTC purchase",
        )

        assert debit_entry.entry_type == "debit"
        assert credit_entry.entry_type == "credit"
        assert debit_entry.amount == amount
        assert credit_entry.amount == amount
        assert debit_entry.counterpart_entry_id == credit_entry.id
        assert credit_entry.counterpart_entry_id == debit_entry.id
        assert debit_entry.reference_type == "trade"

        db.refresh(account_rl_eur)
        db.refresh(account_client_eur)
        assert Decimal(str(account_rl_eur.balance)) == initial_rl_balance + amount
        assert Decimal(str(account_client_eur.balance)) == initial_client_balance - amount

    def test_post_double_entry_balance_invariant(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount, account_rl_eur: LedgerAccount):
        """Multiple postings: balance always equals SUM(debits) - SUM(credits)."""
        service.post_double_entry(
            db, debit_account_id=account_rl_eur.id, credit_account_id=account_client_eur.id,
            amount=Decimal("1000"), currency="EUR", reference_type="trade",
            effective_at=datetime.now(timezone.utc),
        )
        service.post_double_entry(
            db, debit_account_id=account_rl_eur.id, credit_account_id=account_client_eur.id,
            amount=Decimal("2000"), currency="EUR", reference_type="trade",
            effective_at=datetime.now(timezone.utc),
        )

        db.refresh(account_rl_eur)
        entries, _ = service.list_entries(db, account_id=account_rl_eur.id)
        computed_balance = sum(
            Decimal(str(e.amount)) if e.entry_type == "debit" else -Decimal(str(e.amount))
            for e in entries
        )
        assert Decimal(str(account_rl_eur.balance)) == computed_balance

    def test_post_double_entry_zero_amount(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount, account_rl_eur: LedgerAccount):
        with pytest.raises(ValueError, match="positive"):
            service.post_double_entry(
                db, debit_account_id=account_rl_eur.id, credit_account_id=account_client_eur.id,
                amount=Decimal("0"), currency="EUR", reference_type="trade",
                effective_at=datetime.now(timezone.utc),
            )

    def test_post_double_entry_negative_amount(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount, account_rl_eur: LedgerAccount):
        with pytest.raises(ValueError, match="positive"):
            service.post_double_entry(
                db, debit_account_id=account_rl_eur.id, credit_account_id=account_client_eur.id,
                amount=Decimal("-100"), currency="EUR", reference_type="trade",
                effective_at=datetime.now(timezone.utc),
            )

    def test_post_double_entry_account_not_found(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount):
        with pytest.raises(AccountNotFoundError):
            service.post_double_entry(
                db, debit_account_id=uuid.uuid4(), credit_account_id=account_client_eur.id,
                amount=Decimal("100"), currency="EUR", reference_type="deposit",
                effective_at=datetime.now(timezone.utc),
            )

    def test_post_double_entry_currency_mismatch(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount, account_treasury_btc: LedgerAccount):
        with pytest.raises(CurrencyMismatchError):
            service.post_double_entry(
                db, debit_account_id=account_client_eur.id, credit_account_id=account_treasury_btc.id,
                amount=Decimal("100"), currency="EUR", reference_type="trade",
                effective_at=datetime.now(timezone.utc),
            )

    def test_post_double_entry_frozen_account(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount, account_frozen: LedgerAccount):
        with pytest.raises(InactiveAccountError):
            service.post_double_entry(
                db, debit_account_id=account_frozen.id, credit_account_id=account_client_eur.id,
                amount=Decimal("100"), currency="EUR", reference_type="deposit",
                effective_at=datetime.now(timezone.utc),
            )

    def test_post_double_entry_with_reference_id(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount, account_rl_eur: LedgerAccount):
        ref_id = uuid.uuid4()
        debit_entry, credit_entry = service.post_double_entry(
            db, debit_account_id=account_rl_eur.id, credit_account_id=account_client_eur.id,
            amount=Decimal("100"), currency="EUR", reference_type="trade",
            reference_id=ref_id, effective_at=datetime.now(timezone.utc),
        )
        assert debit_entry.reference_id == ref_id
        assert credit_entry.reference_id == ref_id

    def test_get_entry(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount, account_rl_eur: LedgerAccount):
        debit_entry, _ = service.post_double_entry(
            db, debit_account_id=account_rl_eur.id, credit_account_id=account_client_eur.id,
            amount=Decimal("100"), currency="EUR", reference_type="deposit",
            effective_at=datetime.now(timezone.utc),
        )
        found = service.get_entry(db, debit_entry.id)
        assert found.id == debit_entry.id

    def test_get_entry_not_found(self, db: Session, service: LedgerEntryService):
        with pytest.raises(LedgerEntryNotFoundError):
            service.get_entry(db, uuid.uuid4())

    def test_list_entries(self, db: Session, service: LedgerEntryService, account_client_eur: LedgerAccount, account_rl_eur: LedgerAccount):
        service.post_double_entry(
            db, debit_account_id=account_rl_eur.id, credit_account_id=account_client_eur.id,
            amount=Decimal("100"), currency="EUR", reference_type="trade",
            effective_at=datetime.now(timezone.utc),
        )
        items, total = service.list_entries(db, account_id=account_client_eur.id)
        assert total >= 1
        assert all(e.account_id == account_client_eur.id for e in items)


# ---------------------------------------------------------------------------
# Service tests — asset_id alignment
# ---------------------------------------------------------------------------

class TestLedgerEntryAssetId:

    def test_post_double_entry_with_explicit_asset_id(
        self, db: Session, service: LedgerEntryService,
        account_client_eur_with_asset: LedgerAccount, account_rl_eur_with_asset: LedgerAccount,
        asset_eur: Asset,
    ):
        debit_entry, credit_entry = service.post_double_entry(
            db,
            debit_account_id=account_rl_eur_with_asset.id,
            credit_account_id=account_client_eur_with_asset.id,
            amount=Decimal("1000"), currency="EUR", reference_type="trade",
            effective_at=datetime.now(timezone.utc),
            asset_id=asset_eur.id,
        )
        assert debit_entry.asset_id == asset_eur.id
        assert credit_entry.asset_id == asset_eur.id
        assert debit_entry.currency == "EUR"

    def test_post_double_entry_asset_id_resolved_from_account(
        self, db: Session, service: LedgerEntryService,
        account_client_eur_with_asset: LedgerAccount, account_rl_eur_with_asset: LedgerAccount,
        asset_eur: Asset,
    ):
        debit_entry, credit_entry = service.post_double_entry(
            db,
            debit_account_id=account_rl_eur_with_asset.id,
            credit_account_id=account_client_eur_with_asset.id,
            amount=Decimal("500"), currency="EUR", reference_type="deposit",
            effective_at=datetime.now(timezone.utc),
        )
        assert debit_entry.asset_id == asset_eur.id
        assert credit_entry.asset_id == asset_eur.id

    def test_post_double_entry_no_asset_on_legacy_accounts(
        self, db: Session, service: LedgerEntryService,
        account_client_eur: LedgerAccount, account_rl_eur: LedgerAccount,
    ):
        """Legacy accounts without asset_id produce entries with asset_id=None."""
        debit_entry, credit_entry = service.post_double_entry(
            db,
            debit_account_id=account_rl_eur.id,
            credit_account_id=account_client_eur.id,
            amount=Decimal("200"), currency="EUR", reference_type="trade",
            effective_at=datetime.now(timezone.utc),
        )
        assert debit_entry.asset_id is None
        assert credit_entry.asset_id is None
        assert debit_entry.currency == "EUR"

    def test_post_double_entry_asset_mismatch_rejected(
        self, db: Session, service: LedgerEntryService,
        account_client_eur_with_asset: LedgerAccount, account_rl_eur_with_asset: LedgerAccount,
        asset_btc: Asset,
    ):
        """Passing asset_id that conflicts with account asset_id is rejected."""
        with pytest.raises(AssetMismatchError):
            service.post_double_entry(
                db,
                debit_account_id=account_rl_eur_with_asset.id,
                credit_account_id=account_client_eur_with_asset.id,
                amount=Decimal("100"), currency="EUR", reference_type="trade",
                effective_at=datetime.now(timezone.utc),
                asset_id=asset_btc.id,
            )

    def test_post_double_entry_existing_callers_unbroken(
        self, db: Session, service: LedgerEntryService,
        account_client_eur: LedgerAccount, account_rl_eur: LedgerAccount,
    ):
        """Existing callers that omit asset_id continue to work exactly as before."""
        debit_entry, credit_entry = service.post_double_entry(
            db,
            debit_account_id=account_rl_eur.id,
            credit_account_id=account_client_eur.id,
            amount=Decimal("300"), currency="EUR", reference_type="deposit",
            effective_at=datetime.now(timezone.utc),
        )
        assert debit_entry.id is not None
        assert credit_entry.id is not None
        assert debit_entry.currency == "EUR"
        assert debit_entry.counterpart_entry_id == credit_entry.id
