"""Pool Repayment & Settlement Engine — Phase 2A.8.

Full repayment flow:
  1. Compute total_due = principal + accrued_interest
  2. Verify borrower balance
  3. Debit borrower spot
  4. Split interest: to_lenders + platform_fee
  5. Credit lenders (principal + interest pro-rata)
  6. Close/reduce positions (PositionAtom)
  7. Mark borrow_position as repaid
  8. Update pool stats

Invariants:
  1. Conservation: borrower_payment = sum(lender_received) + platform_fee
  2. Symmetry: lending == borrowing == 0 after full repay
  3. No active allocations after repay
  4. Pool total_borrowed accurate
  5. Idempotent: cannot repay twice
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.repository import CryptoPositionRepository
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, _resolve_or_create_instrument
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

from .pool_models import LendingPool, PoolBorrowPosition, PoolAllocation, PoolSupplyCommitment
from .pool_service import PoolLendingService, PoolError, InsufficientBalanceError

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_PRECISION = Decimal("0.0000000001")


class RepaymentError(PoolError):
    pass


class BorrowPositionNotFoundError(RepaymentError):
    pass


class RepaymentEngine:
    """Full repayment engine for pool-based borrows."""

    def repay_borrow_position(
        self,
        db: Session,
        *,
        borrow_position_id: UUID,
    ) -> dict:
        """Full repayment of a single borrow position.

        Atomic transaction:
          1. Fetch borrow position + validate
          2. Compute total_due = principal + accrued_interest
          3. Verify borrower balance
          4. Debit borrower spot
          5. Split interest → lenders + platform
          6. Credit each lender (principal + interest)
          7. Close/reduce PositionAtoms
          8. Mark borrow_position repaid
          9. Update pool stats
        """

        # ── 1. Fetch & validate ──────────────────────────────────────
        borrow_pos = db.query(PoolBorrowPosition).filter(
            PoolBorrowPosition.id == borrow_position_id,
        ).first()
        if borrow_pos is None:
            raise BorrowPositionNotFoundError(f"Borrow position {borrow_position_id} not found")
        if borrow_pos.status != "active":
            raise RepaymentError(f"Borrow position is not active (status={borrow_pos.status})")

        pool = db.query(LendingPool).filter(LendingPool.id == borrow_pos.pool_id).first()
        if not pool:
            raise RepaymentError("Pool not found")

        borrower_id = borrow_pos.client_id
        asset = borrow_pos.asset
        principal = Decimal(str(borrow_pos.borrowed_amount))

        # ── 2. Compute accrued interest ──────────────────────────────
        instrument = _resolve_or_create_instrument(db, asset)
        borrower_portfolio = ensure_direct_portfolio(db, borrower_id)

        borrowing_atom = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == borrower_portfolio.id,
            PositionAtom.instrument_id == instrument.id,
            PositionAtom.position_type == PositionType.BORROWING.value,
            PositionAtom.status == "open",
        ).first()

        if borrowing_atom is None:
            raise RepaymentError("No open borrowing PositionAtom found")

        atom_quantity = Decimal(str(borrowing_atom.quantity))
        atom_accrued = Decimal(str(borrowing_atom.accrued_income or 0))

        # Pro-rata: this borrow's share of the total accrued interest
        if atom_quantity > 0:
            borrow_share = principal / atom_quantity
        else:
            borrow_share = Decimal("1")
        borrower_interest = (atom_accrued * borrow_share).quantize(_PRECISION, rounding=ROUND_HALF_UP)
        total_due = principal + borrower_interest

        # ── 3. Verify borrower balance ───────────────────────────────
        borrower_pos = CryptoPositionRepository.get_or_create_for_update(db, borrower_id, asset)
        borrower_balance = Decimal(str(borrower_pos.balance))
        if borrower_balance < total_due:
            raise InsufficientBalanceError(
                f"Borrower balance {borrower_balance} < total_due {total_due} for {asset}"
            )

        # ── 4. Debit borrower spot ───────────────────────────────────
        borrower_pos.balance = borrower_balance - total_due
        borrower_pos.available_balance = Decimal(str(borrower_pos.available_balance)) - total_due
        db.flush()

        # ── 5. Interest split ────────────────────────────────────────
        borrow_rate = Decimal(str(pool.borrow_rate_bps))
        supply_rate = Decimal(str(pool.supply_rate_bps))

        if borrow_rate > 0 and borrower_interest > 0:
            interest_to_lenders = (borrower_interest * supply_rate / borrow_rate).quantize(
                _PRECISION, rounding=ROUND_HALF_UP,
            )
        else:
            interest_to_lenders = _ZERO
        platform_fee = borrower_interest - interest_to_lenders

        # ── 6. Credit lenders (principal + interest pro-rata) ────────
        allocations = db.query(PoolAllocation).filter(
            PoolAllocation.borrow_position_id == borrow_pos.id,
        ).all()

        lender_details = []
        for alloc in allocations:
            commitment = db.query(PoolSupplyCommitment).filter(
                PoolSupplyCommitment.id == alloc.supply_commitment_id,
            ).first()
            if not commitment:
                continue

            lender_id = commitment.client_id
            alloc_amount = Decimal(str(alloc.amount))

            # Lender's share of interest
            if principal > 0:
                lender_interest_share = (interest_to_lenders * alloc_amount / principal).quantize(
                    _PRECISION, rounding=ROUND_HALF_UP,
                )
            else:
                lender_interest_share = _ZERO

            lender_total = alloc_amount + lender_interest_share

            # Credit lender spot
            lender_pos = CryptoPositionRepository.get_or_create_for_update(db, lender_id, asset)
            lender_pos.balance = Decimal(str(lender_pos.balance)) + lender_total
            lender_pos.available_balance = Decimal(str(lender_pos.available_balance)) + lender_total
            db.flush()

            # ── 7a. Reduce lending PositionAtom ──────────────────────
            lender_portfolio = ensure_direct_portfolio(db, lender_id)
            lending_atom = db.query(PositionAtom).filter(
                PositionAtom.portfolio_id == lender_portfolio.id,
                PositionAtom.instrument_id == instrument.id,
                PositionAtom.position_type == PositionType.LENDING.value,
                PositionAtom.status == "open",
            ).first()

            if lending_atom:
                old_qty = Decimal(str(lending_atom.quantity))
                old_accrued = Decimal(str(lending_atom.accrued_income or 0))

                new_qty = old_qty - alloc_amount
                if old_qty > 0:
                    accrued_reduction = (old_accrued * alloc_amount / old_qty).quantize(
                        _PRECISION, rounding=ROUND_HALF_UP,
                    )
                else:
                    accrued_reduction = old_accrued

                lending_atom.quantity = max(new_qty, _ZERO)
                lending_atom.locked_quantity = max(
                    Decimal(str(lending_atom.locked_quantity)) - alloc_amount, _ZERO,
                )
                lending_atom.accrued_income = max(old_accrued - accrued_reduction, _ZERO)

                if new_qty <= _ZERO:
                    lending_atom.status = "closed"
                    lending_atom.closed_at = datetime.now(timezone.utc)

                db.flush()

            lender_details.append({
                "client_id": str(lender_id),
                "principal_returned": float(alloc_amount),
                "interest_earned": float(lender_interest_share),
                "total_received": float(lender_total),
            })

        # ── 7b. Reduce borrowing PositionAtom ────────────────────────
        new_atom_qty = atom_quantity - principal
        new_atom_accrued = atom_accrued - borrower_interest

        borrowing_atom.quantity = max(new_atom_qty, _ZERO)
        borrowing_atom.locked_quantity = max(
            Decimal(str(borrowing_atom.locked_quantity)) - principal, _ZERO,
        )
        borrowing_atom.accrued_income = max(new_atom_accrued, _ZERO)

        if new_atom_qty <= _ZERO:
            borrowing_atom.status = "closed"
            borrowing_atom.closed_at = datetime.now(timezone.utc)

        db.flush()

        # ── 8. Mark borrow position repaid ───────────────────────────
        borrow_pos.status = "repaid"
        db.flush()

        # ── 9. Update pool stats ─────────────────────────────────────
        PoolLendingService._update_pool_stats(db, pool)

        logger.info(
            "Repayment %s: %s %s principal + %s interest, %d lenders settled, fee=%s",
            borrow_pos.id, principal, asset, borrower_interest,
            len(lender_details), platform_fee,
        )

        return {
            "borrow_position_id": str(borrow_pos.id),
            "asset": asset,
            "principal": float(principal),
            "accrued_interest": float(borrower_interest),
            "total_paid": float(total_due),
            "interest_to_lenders": float(interest_to_lenders),
            "platform_fee": float(platform_fee),
            "lenders_settled": len(lender_details),
            "lender_details": lender_details,
            "pool_total_borrowed_after": float(pool.total_borrowed),
        }
