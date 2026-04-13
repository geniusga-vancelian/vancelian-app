"""Service layer for Position Atoms module (Portfolio Engine — position layer).

Includes the Position Engine (apply_trade) which derives portfolio positions
from confirmed trades. Positions are mutable derived state; trades are immutable
source of truth.

Only PositionAtomService.apply_trade() may modify positions based on trades.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..instruments.models import Instrument
from ..orders.models import Order
from ..portfolios.models import Portfolio
from ..sleeves.models import Sleeve
from ..trades.models import Trade
from ..wallets.models import WalletContainer
from .models import PositionAtom
from .repository import PositionAtomRepository
from .enums import PositionType, ALLOWED_POSITION_TYPES
from .schemas import PositionCreate, PositionUpdate


class PositionNotFoundError(Exception):
    def __init__(self, position_id: UUID):
        self.position_id = position_id
        super().__init__(f"PositionAtom {position_id} not found")


class InsufficientPositionError(Exception):
    def __init__(self, portfolio_id: UUID, instrument_id: UUID, available: Decimal, requested: Decimal):
        super().__init__(
            f"Insufficient position for instrument {instrument_id} in portfolio {portfolio_id}: "
            f"available={available}, requested={requested}"
        )


class NoOpenPositionError(Exception):
    def __init__(self, portfolio_id: UUID, instrument_id: UUID):
        super().__init__(
            f"No open position for instrument {instrument_id} in portfolio {portfolio_id}"
        )


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


class SleeveReferenceError(Exception):
    """Raised when the referenced sleeve_id does not exist."""

    def __init__(self, sleeve_id: UUID):
        self.sleeve_id = sleeve_id
        super().__init__(f"Referenced sleeve {sleeve_id} does not exist")


class WalletReferenceError(Exception):
    """Raised when the referenced wallet_id does not exist."""

    def __init__(self, wallet_id: UUID):
        self.wallet_id = wallet_id
        super().__init__(f"Referenced wallet container {wallet_id} does not exist")


class ParentPositionReferenceError(Exception):
    """Raised when the referenced parent_position_id does not exist."""

    def __init__(self, parent_position_id: UUID):
        self.parent_position_id = parent_position_id
        super().__init__(f"Referenced parent position {parent_position_id} does not exist")


class SleevePortfolioMismatchError(Exception):
    """Raised when sleeve_id does not belong to the specified portfolio_id."""

    def __init__(self, sleeve_id: UUID, portfolio_id: UUID):
        self.sleeve_id = sleeve_id
        self.portfolio_id = portfolio_id
        super().__init__(
            f"Sleeve {sleeve_id} does not belong to portfolio {portfolio_id}"
        )


class PositionAtomService:

    def __init__(self) -> None:
        self._repo = PositionAtomRepository()

    @staticmethod
    def _validate_portfolio_exists(db: Session, portfolio_id: UUID) -> None:
        if db.query(Portfolio).filter(Portfolio.id == portfolio_id).first() is None:
            raise PortfolioReferenceError(portfolio_id)

    @staticmethod
    def _validate_instrument_exists(db: Session, instrument_id: UUID) -> None:
        if db.query(Instrument).filter(Instrument.id == instrument_id).first() is None:
            raise InstrumentReferenceError(instrument_id)

    @staticmethod
    def _validate_sleeve_exists(db: Session, sleeve_id: UUID) -> None:
        if db.query(Sleeve).filter(Sleeve.id == sleeve_id).first() is None:
            raise SleeveReferenceError(sleeve_id)

    @staticmethod
    def _validate_wallet_exists(db: Session, wallet_id: UUID) -> None:
        if db.query(WalletContainer).filter(WalletContainer.id == wallet_id).first() is None:
            raise WalletReferenceError(wallet_id)

    @staticmethod
    def _validate_parent_position_exists(db: Session, parent_position_id: UUID) -> None:
        if db.query(PositionAtom).filter(PositionAtom.id == parent_position_id).first() is None:
            raise ParentPositionReferenceError(parent_position_id)

    @staticmethod
    def _validate_sleeve_belongs_to_portfolio(db: Session, sleeve_id: UUID, portfolio_id: UUID) -> None:
        sleeve = db.query(Sleeve).filter(Sleeve.id == sleeve_id).first()
        if sleeve is not None and sleeve.portfolio_id != portfolio_id:
            raise SleevePortfolioMismatchError(sleeve_id, portfolio_id)

    def _validate_references(self, db: Session, data: dict) -> None:
        self._validate_portfolio_exists(db, data["portfolio_id"])
        self._validate_instrument_exists(db, data["instrument_id"])
        if data.get("sleeve_id") is not None:
            self._validate_sleeve_exists(db, data["sleeve_id"])
            self._validate_sleeve_belongs_to_portfolio(db, data["sleeve_id"], data["portfolio_id"])
        if data.get("wallet_id") is not None:
            self._validate_wallet_exists(db, data["wallet_id"])
        if data.get("parent_position_id") is not None:
            self._validate_parent_position_exists(db, data["parent_position_id"])
        # TODO: validate strategy_instance_id when the strategies module is implemented.

    def create_position(self, db: Session, payload: PositionCreate) -> PositionAtom:
        data = payload.model_dump()
        pt = data.get("position_type")
        if pt not in ALLOWED_POSITION_TYPES:
            raise ValueError(
                f"position_type '{pt}' is not allowed. "
                f"Allowed: {sorted(t.value for t in ALLOWED_POSITION_TYPES)}"
            )
        self._validate_references(db, data)
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_position(self, db: Session, position_id: UUID) -> PositionAtom:
        position = self._repo.get_by_id(db, position_id)
        if position is None:
            raise PositionNotFoundError(position_id)
        return position

    def list_positions(
        self,
        db: Session,
        *,
        portfolio_id: Optional[UUID] = None,
        sleeve_id: Optional[UUID] = None,
        wallet_id: Optional[UUID] = None,
        instrument_id: Optional[UUID] = None,
        position_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PositionAtom], int]:
        return self._repo.list(
            db, portfolio_id=portfolio_id, sleeve_id=sleeve_id,
            wallet_id=wallet_id, instrument_id=instrument_id,
            position_type=position_type, status=status,
            skip=skip, limit=limit,
        )

    def update_position(self, db: Session, position_id: UUID, payload: PositionUpdate) -> PositionAtom:
        position = self.get_position(db, position_id)
        data = payload.model_dump(exclude_unset=True)
        if "position_type" in data:
            pt = data["position_type"]
            if pt not in ALLOWED_POSITION_TYPES:
                raise ValueError(
                    f"position_type '{pt}' is not allowed. "
                    f"Allowed: {sorted(t.value for t in ALLOWED_POSITION_TYPES)}"
                )
        if "sleeve_id" in data and data["sleeve_id"] is not None:
            self._validate_sleeve_exists(db, data["sleeve_id"])
            portfolio_id = data.get("portfolio_id", position.portfolio_id)
            self._validate_sleeve_belongs_to_portfolio(db, data["sleeve_id"], portfolio_id)
        if "wallet_id" in data and data["wallet_id"] is not None:
            self._validate_wallet_exists(db, data["wallet_id"])
        if "parent_position_id" in data and data["parent_position_id"] is not None:
            self._validate_parent_position_exists(db, data["parent_position_id"])
        # TODO: validate strategy_instance_id on update when the strategies module is implemented.
        return self._repo.update(db, position, data=data)

    # ------------------------------------------------------------------
    # Position Engine — trade-derived position management
    # ------------------------------------------------------------------
    # TODO (Phase 5): add idempotence guard via last_trade_id or a
    # trade-application journal to prevent double-counting if
    # apply_trade() is called twice for the same trade.
    # ------------------------------------------------------------------

    def apply_trade(self, db: Session, trade: Trade) -> PositionAtom:
        """Derive position state from a confirmed trade.

        This is the single writer for trade-derived position updates.
        Uses SELECT FOR UPDATE to prevent concurrent modification.
        """
        order = db.query(Order).filter(Order.id == trade.order_id).first()
        if order is None:
            raise PortfolioReferenceError(trade.order_id)
        portfolio_id = order.portfolio_id

        trade_qty = Decimal(str(trade.quantity))
        trade_price = Decimal(str(trade.price))

        position = self._repo.find_open(
            db, portfolio_id, trade.instrument_id, for_update=True
        )

        if trade.side == "buy":
            position = self._apply_buy(
                db, position, portfolio_id, trade.instrument_id,
                trade_qty, trade_price, trade.executed_at,
            )
        elif trade.side == "sell":
            position = self._apply_sell(
                db, position, portfolio_id, trade.instrument_id,
                trade_qty, trade_price, trade.executed_at,
            )

        db.flush()
        return position

    def _apply_buy(
        self,
        db: Session,
        position: Optional[PositionAtom],
        portfolio_id: UUID,
        instrument_id: UUID,
        qty: Decimal,
        price: Decimal,
        executed_at: datetime,
    ) -> PositionAtom:
        if position is None:
            return self._repo.create(db, data={
                "portfolio_id": portfolio_id,
                "instrument_id": instrument_id,
                "position_type": PositionType.SPOT,
                "status": "open",
                "quantity": qty,
                "available_quantity": qty,
                "average_entry_price": price,
                "realized_pnl": Decimal("0"),
                "opened_at": executed_at,
                "metadata_": {},
            })

        old_qty = Decimal(str(position.quantity))
        old_avg = Decimal(str(position.average_entry_price or 0))

        new_qty = old_qty + qty
        if old_qty == 0 or old_avg == 0:
            new_avg = price
        else:
            new_avg = (old_avg * old_qty + price * qty) / new_qty

        position.quantity = new_qty
        position.available_quantity = new_qty
        position.average_entry_price = new_avg
        return position

    def _apply_sell(
        self,
        db: Session,
        position: Optional[PositionAtom],
        portfolio_id: UUID,
        instrument_id: UUID,
        qty: Decimal,
        price: Decimal,
        executed_at: datetime,
    ) -> PositionAtom:
        if position is None:
            raise NoOpenPositionError(portfolio_id, instrument_id)

        current_qty = Decimal(str(position.quantity))
        if qty > current_qty:
            raise InsufficientPositionError(
                portfolio_id, instrument_id, current_qty, qty
            )

        avg_price = Decimal(str(position.average_entry_price or 0))
        realized_pnl_delta = qty * (price - avg_price)
        current_realized = Decimal(str(position.realized_pnl or 0))

        new_qty = current_qty - qty
        position.quantity = new_qty
        position.available_quantity = new_qty
        position.realized_pnl = current_realized + realized_pnl_delta

        if new_qty == 0:
            position.status = "closed"
            position.closed_at = executed_at

        return position
