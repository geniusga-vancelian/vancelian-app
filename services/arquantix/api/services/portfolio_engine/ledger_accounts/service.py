"""Service layer for Ledger Accounts module (Portfolio Engine — accounting layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..assets.models import Asset
from ..clients.models import Client
from ..wallets.models import WalletContainer
from .models import LedgerAccount
from .repository import LedgerAccountRepository
from .schemas import LedgerAccountCreate, LedgerAccountUpdate


class LedgerAccountNotFoundError(Exception):
    def __init__(self, account_id: UUID):
        self.account_id = account_id
        super().__init__(f"LedgerAccount {account_id} not found")


class DuplicateAccountCodeError(Exception):
    def __init__(self, account_code: str):
        self.account_code = account_code
        super().__init__(f"LedgerAccount with code '{account_code}' already exists")


class ClientReferenceError(Exception):
    def __init__(self, client_id: UUID):
        self.client_id = client_id
        super().__init__(f"Referenced client {client_id} does not exist")


class AssetReferenceError(Exception):
    def __init__(self, asset_id: UUID):
        self.asset_id = asset_id
        super().__init__(f"Referenced asset {asset_id} does not exist")


class WalletContainerReferenceError(Exception):
    def __init__(self, wallet_container_id: UUID):
        self.wallet_container_id = wallet_container_id
        super().__init__(f"Referenced wallet container {wallet_container_id} does not exist")


class LedgerAccountService:

    def __init__(self) -> None:
        self._repo = LedgerAccountRepository()

    @staticmethod
    def _validate_client_exists(db: Session, client_id: UUID) -> None:
        client = db.query(Client).filter(Client.id == client_id).first()
        if client is None:
            raise ClientReferenceError(client_id)

    @staticmethod
    def _validate_asset_exists(db: Session, asset_id: UUID) -> None:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if asset is None:
            raise AssetReferenceError(asset_id)

    @staticmethod
    def _validate_wallet_container_exists(db: Session, wc_id: UUID) -> None:
        wc = db.query(WalletContainer).filter(WalletContainer.id == wc_id).first()
        if wc is None:
            raise WalletContainerReferenceError(wc_id)

    def _validate_references(
        self,
        db: Session,
        client_id: Optional[UUID],
        asset_id: Optional[UUID],
        wallet_container_id: Optional[UUID],
    ) -> None:
        if client_id is not None:
            self._validate_client_exists(db, client_id)
        if asset_id is not None:
            self._validate_asset_exists(db, asset_id)
        if wallet_container_id is not None:
            self._validate_wallet_container_exists(db, wallet_container_id)

    def create_account(self, db: Session, payload: LedgerAccountCreate) -> LedgerAccount:
        existing = self._repo.get_by_code(db, payload.account_code)
        if existing is not None:
            raise DuplicateAccountCodeError(payload.account_code)
        self._validate_references(db, payload.client_id, payload.asset_id, payload.wallet_container_id)
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_account(self, db: Session, account_id: UUID) -> LedgerAccount:
        account = self._repo.get_by_id(db, account_id)
        if account is None:
            raise LedgerAccountNotFoundError(account_id)
        return account

    def list_accounts(
        self,
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        account_type: Optional[str] = None,
        currency: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[LedgerAccount], int]:
        return self._repo.list(
            db, client_id=client_id, account_type=account_type,
            currency=currency, status=status, skip=skip, limit=limit,
        )

    def update_account(self, db: Session, account_id: UUID, payload: LedgerAccountUpdate) -> LedgerAccount:
        account = self.get_account(db, account_id)
        data = payload.model_dump(exclude_unset=True)
        if "wallet_container_id" in data and data["wallet_container_id"] is not None:
            self._validate_wallet_container_exists(db, data["wallet_container_id"])
        return self._repo.update(db, account, data=data)
