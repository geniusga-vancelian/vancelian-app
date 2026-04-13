"""Service layer for Settlement module (Portfolio Engine — settlement layer).

Settlement is the ONLY writer of ledger entries. Trades and orders never write
ledger entries directly. Every financial movement flows through:

    Trade/Order → SettlementInstruction → (settle) → LedgerEntry

Core business fields (from_account_id, to_account_id, asset_id, amount) are
immutable after creation.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from ..assets.models import Asset
from ..ledger_accounts.models import LedgerAccount
from ..ledger_entries.service import LedgerEntryService
from ..orders.models import Order
from ..trades.models import Trade
from .enums import SettlementStatus, VALID_TRANSITIONS
from .models import SettlementInstruction
from .repository import SettlementRepository
from .schemas import SettlementCreate, SettlementLeg


class SettlementNotFoundError(Exception):
    def __init__(self, settlement_id: UUID):
        self.settlement_id = settlement_id
        super().__init__(f"SettlementInstruction {settlement_id} not found")


class InvalidSettlementTransitionError(Exception):
    def __init__(self, current: str, target: str):
        super().__init__(f"Cannot transition from '{current}' to '{target}'")


class FromAccountReferenceError(Exception):
    def __init__(self, account_id: UUID):
        super().__init__(f"Referenced from_account {account_id} does not exist")


class ToAccountReferenceError(Exception):
    def __init__(self, account_id: UUID):
        super().__init__(f"Referenced to_account {account_id} does not exist")


class AssetReferenceError(Exception):
    def __init__(self, asset_id: UUID):
        super().__init__(f"Referenced asset {asset_id} does not exist")


class OrderReferenceError(Exception):
    def __init__(self, order_id: UUID):
        super().__init__(f"Referenced order {order_id} does not exist")


class TradeReferenceError(Exception):
    def __init__(self, trade_id: UUID):
        super().__init__(f"Referenced trade {trade_id} does not exist")


class SameAccountError(Exception):
    def __init__(self):
        super().__init__("from_account_id and to_account_id must be different")


class SettlementService:

    def __init__(self) -> None:
        self._repo = SettlementRepository()
        self._ledger_service = LedgerEntryService()

    @staticmethod
    def _validate_account_exists(db: Session, account_id: UUID, direction: str) -> LedgerAccount:
        account = db.query(LedgerAccount).filter(LedgerAccount.id == account_id).first()
        if account is None:
            if direction == "from":
                raise FromAccountReferenceError(account_id)
            raise ToAccountReferenceError(account_id)
        return account

    @staticmethod
    def _validate_asset_exists(db: Session, asset_id: UUID) -> Asset:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if asset is None:
            raise AssetReferenceError(asset_id)
        return asset

    @staticmethod
    def _validate_order_exists(db: Session, order_id: UUID) -> None:
        if db.query(Order).filter(Order.id == order_id).first() is None:
            raise OrderReferenceError(order_id)

    @staticmethod
    def _validate_trade_exists(db: Session, trade_id: UUID) -> None:
        if db.query(Trade).filter(Trade.id == trade_id).first() is None:
            raise TradeReferenceError(trade_id)

    def create_settlement(self, db: Session, payload: SettlementCreate) -> SettlementInstruction:
        """Create a settlement instruction. Does NOT write ledger entries."""
        if payload.from_account_id == payload.to_account_id:
            raise SameAccountError()

        self._validate_account_exists(db, payload.from_account_id, "from")
        self._validate_account_exists(db, payload.to_account_id, "to")
        self._validate_asset_exists(db, payload.asset_id)

        if payload.order_id is not None:
            self._validate_order_exists(db, payload.order_id)
        if payload.trade_id is not None:
            self._validate_trade_exists(db, payload.trade_id)

        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_settlement(self, db: Session, settlement_id: UUID) -> SettlementInstruction:
        instruction = self._repo.get_by_id(db, settlement_id)
        if instruction is None:
            raise SettlementNotFoundError(settlement_id)
        return instruction

    def list_settlements(
        self,
        db: Session,
        *,
        order_id: Optional[UUID] = None,
        trade_id: Optional[UUID] = None,
        settlement_group_id: Optional[UUID] = None,
        settlement_type: Optional[str] = None,
        status: Optional[str] = None,
        from_account_id: Optional[UUID] = None,
        to_account_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[SettlementInstruction], int]:
        return self._repo.list(
            db,
            order_id=order_id,
            trade_id=trade_id,
            settlement_group_id=settlement_group_id,
            settlement_type=settlement_type,
            status=status,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            skip=skip,
            limit=limit,
        )

    def _transition(
        self, db: Session, settlement_id: UUID, target: SettlementStatus, **kwargs
    ) -> SettlementInstruction:
        instruction = self.get_settlement(db, settlement_id)
        current = SettlementStatus(instruction.status)
        if target not in VALID_TRANSITIONS.get(current, set()):
            raise InvalidSettlementTransitionError(instruction.status, target.value)
        return self._repo.update_status(db, instruction, status=target.value, **kwargs)

    def mark_scheduled(
        self, db: Session, settlement_id: UUID, scheduled_at: datetime
    ) -> SettlementInstruction:
        return self._transition(
            db, settlement_id, SettlementStatus.SCHEDULED, scheduled_at=scheduled_at
        )

    def mark_in_progress(self, db: Session, settlement_id: UUID) -> SettlementInstruction:
        return self._transition(db, settlement_id, SettlementStatus.IN_PROGRESS)

    def fail(
        self, db: Session, settlement_id: UUID, reason: str
    ) -> SettlementInstruction:
        return self._transition(
            db,
            settlement_id,
            SettlementStatus.FAILED,
            failed_at=datetime.now(timezone.utc),
            failure_reason=reason,
        )

    def settle(
        self,
        db: Session,
        settlement_id: UUID,
        *,
        external_reference: Optional[str] = None,
    ) -> SettlementInstruction:
        """Settle a settlement instruction: write ledger entries and update balances.

        Resolves currency from the from_account (both accounts must share the
        same currency, enforced by LedgerEntryService).
        """
        instruction = self.get_settlement(db, settlement_id)
        current = SettlementStatus(instruction.status)
        allowed = {SettlementStatus.PENDING, SettlementStatus.IN_PROGRESS}
        if current not in allowed:
            raise InvalidSettlementTransitionError(
                instruction.status, SettlementStatus.SETTLED.value
            )

        from_account = self._validate_account_exists(db, instruction.from_account_id, "from")

        self._ledger_service.post_double_entry(
            db,
            debit_account_id=instruction.from_account_id,
            credit_account_id=instruction.to_account_id,
            amount=Decimal(str(instruction.amount)),
            currency=from_account.currency,
            reference_type="settlement",
            reference_id=instruction.id,
            effective_at=datetime.now(timezone.utc),
            description=f"Settlement {instruction.id} — {instruction.settlement_type}",
            asset_id=instruction.asset_id,
        )

        update_kwargs = {
            "settled_at": datetime.now(timezone.utc),
        }
        if external_reference is not None:
            update_kwargs["external_reference"] = external_reference

        return self._repo.update_status(
            db, instruction, status=SettlementStatus.SETTLED.value, **update_kwargs
        )

    def create_trade_settlements(
        self,
        db: Session,
        *,
        trade_id: UUID,
        order_id: Optional[UUID] = None,
        legs: list[SettlementLeg],
        settlement_group_id: Optional[UUID] = None,
    ) -> list[SettlementInstruction]:
        """Create settlement instructions for a trade. Each leg becomes one instruction.

        The caller is responsible for providing explicit account IDs for each leg.
        No automatic account resolution is performed.

        Args:
            trade_id: The trade that generated these settlement obligations.
            order_id: The originating order (optional).
            legs: List of SettlementLeg describing each FROM→TO movement.
            settlement_group_id: Optional grouping key. Auto-generated if None.
        """
        self._validate_trade_exists(db, trade_id)
        if order_id is not None:
            self._validate_order_exists(db, order_id)

        group_id = settlement_group_id or uuid4()
        instructions: list[SettlementInstruction] = []

        for leg in legs:
            payload = SettlementCreate(
                order_id=order_id,
                trade_id=trade_id,
                settlement_group_id=group_id,
                settlement_type=leg.settlement_type,
                from_account_id=leg.from_account_id,
                to_account_id=leg.to_account_id,
                asset_id=leg.asset_id,
                amount=leg.amount,
                scheduled_at=leg.scheduled_at,
            )
            instruction = self.create_settlement(db, payload)
            instructions.append(instruction)

        return instructions
