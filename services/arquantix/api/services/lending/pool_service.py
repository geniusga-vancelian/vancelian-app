"""Pool-based P2P Lending Service — Phase 2A.6bis.

Implements:
  1. Supply commitment (lender reserves liquidity in pool)
  2. Borrow from pool (atomic FIFO allocation + position creation)
  3. Pool auto-provisioning (one pool per asset)

Key design:
  - Supply commitment = funds stay in spot but available_balance is REDUCED
  - Borrow = atomic: consume commitments FIFO → debit lenders → credit borrower → create positions
  - No interest in this phase

Invariants:
  1. No yield without borrow
  2. Conservation: total_spot + lending = constant
  3. Separation: commitment ≠ lending ≠ spot
  4. Traceability: every borrow → pool_allocations → supply commitments
  5. FIFO priority for lender selection
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.models import CryptoPosition
from services.exchange.repository import CryptoPositionRepository
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, _resolve_or_create_instrument
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

from .pool_models import LendingPool, PoolSupplyCommitment, PoolBorrowPosition, PoolAllocation

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")


class PoolError(Exception):
    pass

class InsufficientPoolLiquidityError(PoolError):
    pass

class InsufficientBalanceError(PoolError):
    pass

class CommitmentNotFoundError(PoolError):
    pass


class PoolLendingService:

    # ── Pool auto-provisioning ────────────────────────────────────

    @staticmethod
    def get_or_create_pool(db: Session, asset: str) -> LendingPool:
        """Return the pool for an asset, creating it if absent."""
        upper = asset.upper()
        pool = db.query(LendingPool).filter(
            LendingPool.asset == upper, LendingPool.status == "active",
        ).first()
        if pool:
            return pool
        pool = LendingPool(asset=upper, status="active")
        db.add(pool)
        db.flush()
        logger.info("Auto-created lending pool for %s: %s", upper, pool.id)
        return pool

    @staticmethod
    def _update_pool_stats(db: Session, pool: LendingPool) -> None:
        """Recalculate pool aggregates from commitments and borrows."""
        total_committed = _ZERO
        for c in db.query(PoolSupplyCommitment).filter(
            PoolSupplyCommitment.pool_id == pool.id,
            PoolSupplyCommitment.status.in_(["active", "partially_used"]),
        ).all():
            total_committed += Decimal(str(c.amount))

        total_borrowed = _ZERO
        for b in db.query(PoolBorrowPosition).filter(
            PoolBorrowPosition.pool_id == pool.id,
            PoolBorrowPosition.status == "active",
        ).all():
            total_borrowed += Decimal(str(b.borrowed_amount))

        pool.total_committed = total_committed
        pool.total_borrowed = total_borrowed
        pool.utilization_rate = (
            (total_borrowed / total_committed * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if total_committed > 0 else _ZERO
        )
        db.flush()

    # ── 1. SUPPLY COMMITMENT ─────────────────────────────────────

    def create_supply_commitment(
        self,
        db: Session,
        *,
        client_id: UUID,
        asset: str,
        amount: Decimal,
        pool_id: Optional[UUID] = None,
    ) -> PoolSupplyCommitment:
        """Lender commits liquidity to a pool.

        If *pool_id* is given, the commitment is placed in that specific pool
        (used by Exclusive Offers where each offer has its own dedicated pool).
        Otherwise, falls back to the shared get_or_create_pool(asset) pool.

        Effect:
          - Funds stay in spot (crypto_positions.balance unchanged)
          - available_balance is REDUCED (reserved)
          - No lending position yet — only created when a borrow consumes it
        """
        from services.compliance.eligibility_service import EligibilityService
        EligibilityService.require_eligible_by_client_id(db, client_id)

        if amount <= 0:
            raise PoolError("Amount must be positive")

        asset = asset.upper()
        if pool_id is not None:
            pool = db.query(LendingPool).filter(LendingPool.id == pool_id).first()
            if pool is None:
                raise PoolError(f"Pool {pool_id} not found")
        else:
            pool = self.get_or_create_pool(db, asset)

        # Verify lender has available balance
        pos = CryptoPositionRepository.get_or_create_for_update(db, client_id, asset)
        available = Decimal(str(pos.available_balance))
        if available < amount:
            raise InsufficientBalanceError(
                f"Available balance {available} < commitment {amount} for {asset}"
            )

        # Reserve: reduce available_balance (but keep balance intact)
        pos.available_balance = available - amount
        db.flush()

        commitment = PoolSupplyCommitment(
            pool_id=pool.id,
            client_id=client_id,
            asset=asset,
            amount=amount,
            reserved_amount=amount,
            available_amount=amount,
            status="active",
        )
        db.add(commitment)
        db.flush()

        self._update_pool_stats(db, pool)

        logger.info(
            "Supply commitment %s: %s %s from client %s to pool %s",
            commitment.id, amount, asset, client_id, pool.id,
        )
        return commitment

    def cancel_supply_commitment(
        self,
        db: Session,
        commitment_id: UUID,
        client_id: UUID,
    ) -> PoolSupplyCommitment:
        """Cancel an unused supply commitment, releasing reserved balance."""
        commitment = db.query(PoolSupplyCommitment).filter(
            PoolSupplyCommitment.id == commitment_id,
        ).first()
        if commitment is None:
            raise CommitmentNotFoundError(f"Commitment {commitment_id} not found")
        if commitment.client_id != client_id:
            raise PoolError("Only the commitment owner can cancel")
        if commitment.status not in ("active",):
            raise PoolError(f"Cannot cancel commitment in status {commitment.status}")

        # Release reserved balance
        pos = CryptoPositionRepository.get_or_create_for_update(db, client_id, commitment.asset)
        pos.available_balance = Decimal(str(pos.available_balance)) + Decimal(str(commitment.available_amount))
        db.flush()

        commitment.status = "cancelled"
        commitment.available_amount = _ZERO
        commitment.reserved_amount = _ZERO
        db.flush()

        pool = db.query(LendingPool).filter(LendingPool.id == commitment.pool_id).first()
        if pool:
            self._update_pool_stats(db, pool)

        logger.info("Supply commitment %s cancelled", commitment_id)
        return commitment

    # ── 2. BORROW FROM POOL ──────────────────────────────────────

    def borrow_from_pool(
        self,
        db: Session,
        *,
        borrower_client_id: UUID,
        asset: str,
        amount: Decimal,
    ) -> dict:
        """Borrow from the pool — atomic FIFO allocation.

        Transaction:
          1. Select available commitments (FIFO by created_at)
          2. Allocate amounts across commitments
          3. Debit lenders' spot balances (actual transfer)
          4. Credit borrower's spot balance
          5. Create lending PositionAtoms for each lender
          6. Create borrowing PositionAtom for borrower
          7. Create pool_allocations (audit trail)
          8. Update pool stats
        """
        from services.compliance.eligibility_service import EligibilityService
        EligibilityService.require_eligible_by_client_id(db, borrower_client_id)

        if amount <= 0:
            raise PoolError("Borrow amount must be positive")

        asset = asset.upper()
        pool = self.get_or_create_pool(db, asset)

        # Phase 2A.10: enforce single-borrower restriction for product-linked pools
        from .offer_service import OfferService
        OfferService.check_borrow_allowed(db, pool.id, borrower_client_id)

        # Step 1: find available commitments (FIFO)
        commitments = (
            db.query(PoolSupplyCommitment)
            .filter(
                PoolSupplyCommitment.pool_id == pool.id,
                PoolSupplyCommitment.available_amount > 0,
                PoolSupplyCommitment.status.in_(["active", "partially_used"]),
                PoolSupplyCommitment.client_id != borrower_client_id,
            )
            .order_by(PoolSupplyCommitment.created_at.asc())
            .all()
        )

        total_available = sum(Decimal(str(c.available_amount)) for c in commitments)
        if total_available < amount:
            raise InsufficientPoolLiquidityError(
                f"Pool liquidity {total_available} < requested {amount} for {asset}"
            )

        # Step 2: allocate FIFO
        allocations: list[tuple[PoolSupplyCommitment, Decimal]] = []
        remaining = amount
        for commitment in commitments:
            if remaining <= 0:
                break
            avail = Decimal(str(commitment.available_amount))
            take = min(avail, remaining)
            allocations.append((commitment, take))
            remaining -= take

        now = datetime.now(timezone.utc)
        instrument = _resolve_or_create_instrument(db, asset)

        # Step 6 (early): create or update borrowing position atom
        # (unique constraint: one open atom per portfolio+instrument)
        borrower_portfolio = ensure_direct_portfolio(db, borrower_client_id)
        borrowing_atom = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == borrower_portfolio.id,
            PositionAtom.instrument_id == instrument.id,
            PositionAtom.position_type == PositionType.BORROWING.value,
            PositionAtom.status == "open",
        ).first()
        if borrowing_atom:
            borrowing_atom.quantity = Decimal(str(borrowing_atom.quantity)) + amount
            borrowing_atom.locked_quantity = Decimal(str(borrowing_atom.locked_quantity)) + amount
            borrowing_atom.cost_basis = Decimal(str(borrowing_atom.cost_basis)) + amount
            db.flush()
        else:
            borrowing_atom = PositionAtom(
                portfolio_id=borrower_portfolio.id,
                instrument_id=instrument.id,
                position_type=PositionType.BORROWING.value,
                status="open",
                quantity=amount,
                available_quantity=_ZERO,
                locked_quantity=amount,
                cost_basis=amount,
                opened_at=now,
                metadata_={"pool_id": str(pool.id), "source": "pool_borrow"},
            )
            db.add(borrowing_atom)
            db.flush()

        # Create borrow position record
        borrow_position = PoolBorrowPosition(
            pool_id=pool.id,
            client_id=borrower_client_id,
            asset=asset,
            borrowed_amount=amount,
            status="active",
            borrowing_position_atom_id=borrowing_atom.id,
        )
        db.add(borrow_position)
        db.flush()

        # Step 4: credit borrower spot
        borrower_pos = CryptoPositionRepository.get_or_create_for_update(db, borrower_client_id, asset)
        borrower_pos.balance = Decimal(str(borrower_pos.balance)) + amount
        borrower_pos.available_balance = Decimal(str(borrower_pos.available_balance)) + amount
        db.flush()

        # Steps 3, 5, 7: process each allocation
        allocation_details = []
        for commitment, alloc_amount in allocations:
            lender_id = commitment.client_id

            # Step 3: debit lender spot (balance, not available_balance — already reserved)
            lender_pos = CryptoPositionRepository.get_or_create_for_update(db, lender_id, asset)
            lender_pos.balance = Decimal(str(lender_pos.balance)) - alloc_amount
            db.flush()

            # Update commitment
            commitment.available_amount = Decimal(str(commitment.available_amount)) - alloc_amount
            commitment.reserved_amount = Decimal(str(commitment.reserved_amount)) - alloc_amount
            if Decimal(str(commitment.available_amount)) <= 0:
                commitment.status = "fully_used"
            else:
                commitment.status = "partially_used"
            db.flush()

            # Step 5: create or update lending position atom for this lender
            # (unique constraint: one open atom per portfolio+instrument)
            lender_portfolio = ensure_direct_portfolio(db, lender_id)
            lending_atom = db.query(PositionAtom).filter(
                PositionAtom.portfolio_id == lender_portfolio.id,
                PositionAtom.instrument_id == instrument.id,
                PositionAtom.position_type == PositionType.LENDING.value,
                PositionAtom.status == "open",
            ).first()
            if lending_atom:
                lending_atom.quantity = Decimal(str(lending_atom.quantity)) + alloc_amount
                lending_atom.locked_quantity = Decimal(str(lending_atom.locked_quantity)) + alloc_amount
                lending_atom.cost_basis = Decimal(str(lending_atom.cost_basis)) + alloc_amount
                db.flush()
            else:
                lending_atom = PositionAtom(
                    portfolio_id=lender_portfolio.id,
                    instrument_id=instrument.id,
                    position_type=PositionType.LENDING.value,
                    status="open",
                    quantity=alloc_amount,
                    available_quantity=_ZERO,
                    locked_quantity=alloc_amount,
                    cost_basis=alloc_amount,
                    opened_at=now,
                    metadata_={
                        "pool_id": str(pool.id),
                        "borrow_position_id": str(borrow_position.id),
                        "source": "pool_allocation",
                    },
                )
                db.add(lending_atom)
                db.flush()

            # Step 7: audit trail
            allocation = PoolAllocation(
                supply_commitment_id=commitment.id,
                borrow_position_id=borrow_position.id,
                amount=alloc_amount,
                lending_position_atom_id=lending_atom.id,
            )
            db.add(allocation)
            db.flush()

            allocation_details.append({
                "lender_client_id": str(lender_id),
                "amount": float(alloc_amount),
                "commitment_id": str(commitment.id),
                "lending_atom_id": str(lending_atom.id),
            })

        # Step 8: update pool
        self._update_pool_stats(db, pool)

        logger.info(
            "Pool borrow %s: %s %s by %s, %d lenders allocated",
            borrow_position.id, amount, asset, borrower_client_id, len(allocations),
        )

        return {
            "borrow_position_id": borrow_position.id,
            "pool_id": pool.id,
            "asset": asset,
            "borrowed_amount": float(amount),
            "borrowing_atom_id": str(borrowing_atom.id),
            "allocations": allocation_details,
            "lenders_count": len(allocations),
        }

    # ── QUERIES ───────────────────────────────────────────────────

    def get_pool(self, db: Session, asset: str) -> Optional[LendingPool]:
        return db.query(LendingPool).filter(
            LendingPool.asset == asset.upper(), LendingPool.status == "active",
        ).first()

    def list_pools(self, db: Session) -> list[LendingPool]:
        return db.query(LendingPool).filter(LendingPool.status == "active").all()

    def list_commitments(
        self, db: Session, *, client_id: Optional[UUID] = None, pool_id: Optional[UUID] = None,
    ) -> list[PoolSupplyCommitment]:
        q = db.query(PoolSupplyCommitment)
        if client_id:
            q = q.filter(PoolSupplyCommitment.client_id == client_id)
        if pool_id:
            q = q.filter(PoolSupplyCommitment.pool_id == pool_id)
        return q.order_by(PoolSupplyCommitment.created_at.desc()).all()

    def list_borrow_positions(
        self, db: Session, *, client_id: Optional[UUID] = None, pool_id: Optional[UUID] = None,
    ) -> list[PoolBorrowPosition]:
        q = db.query(PoolBorrowPosition)
        if client_id:
            q = q.filter(PoolBorrowPosition.client_id == client_id)
        if pool_id:
            q = q.filter(PoolBorrowPosition.pool_id == pool_id)
        return q.order_by(PoolBorrowPosition.created_at.desc()).all()

    def get_pool_summary(self, db: Session, asset: str) -> dict:
        """Get pool status with all commitments and borrows."""
        pool = self.get_pool(db, asset)
        if not pool:
            return {"asset": asset.upper(), "exists": False}

        commitments = self.list_commitments(db, pool_id=pool.id)
        borrows = self.list_borrow_positions(db, pool_id=pool.id)

        return {
            "asset": pool.asset,
            "exists": True,
            "pool_id": str(pool.id),
            "total_committed": float(pool.total_committed),
            "total_borrowed": float(pool.total_borrowed),
            "available_liquidity": float(Decimal(str(pool.total_committed)) - Decimal(str(pool.total_borrowed))),
            "utilization_rate": float(pool.utilization_rate),
            "commitments_count": len(commitments),
            "active_borrows_count": sum(1 for b in borrows if b.status == "active"),
        }
