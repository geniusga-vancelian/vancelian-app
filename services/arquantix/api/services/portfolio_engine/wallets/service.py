"""Service layer for Wallet Containers module (Portfolio Engine — ledger layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..instruments.models import Instrument
from ..portfolios.models import Portfolio
from .models import WalletContainer
from .repository import WalletContainerRepository
from .schemas import WalletCreate, WalletUpdate


class WalletNotFoundError(Exception):
    def __init__(self, wallet_id: UUID):
        self.wallet_id = wallet_id
        super().__init__(f"WalletContainer {wallet_id} not found")


class PortfolioReferenceError(Exception):
    """Raised when the referenced portfolio_id does not exist."""

    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Referenced portfolio {portfolio_id} does not exist")


class InstrumentReferenceError(Exception):
    """Raised when the referenced instrument_id does not exist."""

    def __init__(self, instrument_id: UUID):
        self.instrument_id = instrument_id
        super().__init__(f"Referenced instrument {instrument_id} does not exist")


class WalletContainerService:

    def __init__(self) -> None:
        self._repo = WalletContainerRepository()

    @staticmethod
    def _validate_portfolio_exists(db: Session, portfolio_id: UUID) -> None:
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise PortfolioReferenceError(portfolio_id)

    @staticmethod
    def _validate_instrument_exists(db: Session, instrument_id: UUID) -> None:
        instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
        if instrument is None:
            raise InstrumentReferenceError(instrument_id)

    def _validate_references(self, db: Session, portfolio_id: Optional[UUID], instrument_id: Optional[UUID]) -> None:
        if portfolio_id is not None:
            self._validate_portfolio_exists(db, portfolio_id)
        if instrument_id is not None:
            self._validate_instrument_exists(db, instrument_id)

    def create_wallet(self, db: Session, payload: WalletCreate) -> WalletContainer:
        # TODO: validate client_id exists when the clients module is implemented.
        self._validate_references(db, payload.portfolio_id, payload.instrument_id)
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_wallet(self, db: Session, wallet_id: UUID) -> WalletContainer:
        wallet = self._repo.get_by_id(db, wallet_id)
        if wallet is None:
            raise WalletNotFoundError(wallet_id)
        return wallet

    def list_wallets(
        self,
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        portfolio_id: Optional[UUID] = None,
        wallet_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[WalletContainer], int]:
        return self._repo.list(
            db, client_id=client_id, portfolio_id=portfolio_id,
            wallet_type=wallet_type, status=status, skip=skip, limit=limit,
        )

    def update_wallet(self, db: Session, wallet_id: UUID, payload: WalletUpdate) -> WalletContainer:
        wallet = self.get_wallet(db, wallet_id)
        data = payload.model_dump(exclude_unset=True)
        if "portfolio_id" in data and data["portfolio_id"] is not None:
            self._validate_portfolio_exists(db, data["portfolio_id"])
        if "instrument_id" in data and data["instrument_id"] is not None:
            self._validate_instrument_exists(db, data["instrument_id"])
        return self._repo.update(db, wallet, data=data)
