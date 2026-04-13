"""Pool-based Interest Engine — Phase 2A.7.

Daily accrual engine that:
  1. Iterates active pools with non-zero borrowed amounts
  2. Computes interest using pool rates (borrow_rate_bps, supply_rate_bps)
  3. Distributes to lenders pro-rata based on pool_allocations
  4. Records borrower interest due
  5. Creates daily snapshots for audit
  6. Updates PositionAtom.accrued_income for valuation

Formulas:
  daily_borrow_rate = borrow_rate_bps / 10_000 / 365
  daily_supply_rate = supply_rate_bps / 10_000 / 365

  interest_generated    = total_borrowed × daily_borrow_rate
  interest_to_lenders   = total_borrowed × daily_supply_rate
  platform_fee          = interest_generated - interest_to_lenders

  lender_share          = lender_allocated / total_borrowed
  lender_interest       = interest_to_lenders × lender_share

Safety:
  - Double accrual prevented by unique index (pool_id, date) / (client_id, pool_id, date)
  - Interest < 0 impossible (rates are positive, amounts are positive)
  - Rounding: ROUND_HALF_UP on 10 decimals
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.portfolios.models import Portfolio

from .pool_models import LendingPool, PoolBorrowPosition, PoolAllocation, PoolSupplyCommitment
from .interest_models import PoolInterestSnapshot, LenderInterestAccrual, BorrowerInterestAccrual

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_PRECISION = Decimal("0.0000000001")  # 10 decimals
_BPS_DIVISOR = Decimal("10000")
_DAYS_PER_YEAR = Decimal("365")


class InterestEngineError(Exception):
    pass


class InterestEngine:
    """Daily interest accrual engine for pool-based lending."""

    def run_daily_accrual(
        self,
        db: Session,
        *,
        accrual_date: Optional[date] = None,
    ) -> dict:
        """Run daily interest accrual for all active pools.

        Args:
            accrual_date: Date to accrue for (defaults to today UTC).

        Returns summary with per-pool results.
        """
        if accrual_date is None:
            accrual_date = datetime.now(timezone.utc).date()

        pools = db.query(LendingPool).filter(LendingPool.status == "active").all()

        results = []
        total_generated = _ZERO
        total_to_lenders = _ZERO
        total_platform_fee = _ZERO

        for pool in pools:
            total_borrowed = Decimal(str(pool.total_borrowed))
            if total_borrowed <= 0:
                continue

            # Check for duplicate accrual
            existing = db.query(PoolInterestSnapshot).filter(
                PoolInterestSnapshot.pool_id == pool.id,
                PoolInterestSnapshot.date == accrual_date,
            ).first()
            if existing:
                logger.info("Skipping pool %s (%s) — already accrued for %s", pool.id, pool.asset, accrual_date)
                continue

            pool_result = self._accrue_pool(db, pool, accrual_date)
            results.append(pool_result)
            total_generated += Decimal(str(pool_result["interest_generated"]))
            total_to_lenders += Decimal(str(pool_result["interest_to_lenders"]))
            total_platform_fee += Decimal(str(pool_result["platform_fee"]))

        db.flush()

        return {
            "accrual_date": accrual_date.isoformat(),
            "pools_processed": len(results),
            "total_interest_generated": float(total_generated),
            "total_interest_to_lenders": float(total_to_lenders),
            "total_platform_fee": float(total_platform_fee),
            "pools": results,
        }

    def _accrue_pool(self, db: Session, pool: LendingPool, accrual_date: date) -> dict:
        """Accrue interest for a single pool on a given date."""
        total_borrowed = Decimal(str(pool.total_borrowed))
        borrow_rate_bps = Decimal(str(pool.borrow_rate_bps))
        supply_rate_bps = Decimal(str(pool.supply_rate_bps))

        daily_borrow_rate = borrow_rate_bps / _BPS_DIVISOR / _DAYS_PER_YEAR
        daily_supply_rate = supply_rate_bps / _BPS_DIVISOR / _DAYS_PER_YEAR

        interest_generated = (total_borrowed * daily_borrow_rate).quantize(_PRECISION, rounding=ROUND_HALF_UP)
        interest_to_lenders = (total_borrowed * daily_supply_rate).quantize(_PRECISION, rounding=ROUND_HALF_UP)
        platform_fee = interest_generated - interest_to_lenders

        # Snapshot
        snapshot = PoolInterestSnapshot(
            pool_id=pool.id,
            date=accrual_date,
            total_borrowed=total_borrowed,
            borrow_rate_bps=borrow_rate_bps,
            supply_rate_bps=supply_rate_bps,
            interest_generated=interest_generated,
            interest_to_lenders=interest_to_lenders,
            platform_fee=platform_fee,
        )
        db.add(snapshot)
        db.flush()

        # Lender distribution (pro-rata based on allocations)
        lender_results = self._distribute_to_lenders(
            db, pool, accrual_date, total_borrowed, interest_to_lenders,
        )

        # Borrower accrual
        borrower_results = self._accrue_borrowers(
            db, pool, accrual_date, daily_borrow_rate,
        )

        logger.info(
            "Pool %s (%s) accrual %s: generated=%.10f to_lenders=%.10f fee=%.10f lenders=%d borrowers=%d",
            pool.id, pool.asset, accrual_date,
            interest_generated, interest_to_lenders, platform_fee,
            len(lender_results), len(borrower_results),
        )

        return {
            "pool_id": str(pool.id),
            "asset": pool.asset,
            "total_borrowed": float(total_borrowed),
            "borrow_rate_bps": float(borrow_rate_bps),
            "supply_rate_bps": float(supply_rate_bps),
            "interest_generated": float(interest_generated),
            "interest_to_lenders": float(interest_to_lenders),
            "platform_fee": float(platform_fee),
            "lenders_count": len(lender_results),
            "borrowers_count": len(borrower_results),
        }

    def _distribute_to_lenders(
        self,
        db: Session,
        pool: LendingPool,
        accrual_date: date,
        total_borrowed: Decimal,
        interest_to_lenders: Decimal,
    ) -> list[dict]:
        """Distribute interest to lenders pro-rata based on their allocations."""
        # Aggregate allocations per lender
        active_borrows = db.query(PoolBorrowPosition).filter(
            PoolBorrowPosition.pool_id == pool.id,
            PoolBorrowPosition.status == "active",
        ).all()
        borrow_ids = [b.id for b in active_borrows]

        if not borrow_ids:
            return []

        allocations = db.query(PoolAllocation).filter(
            PoolAllocation.borrow_position_id.in_(borrow_ids),
        ).all()

        # Group by lender (via commitment → client_id)
        lender_totals: dict[UUID, Decimal] = {}
        for alloc in allocations:
            commitment = db.query(PoolSupplyCommitment).filter(
                PoolSupplyCommitment.id == alloc.supply_commitment_id,
            ).first()
            if not commitment:
                continue
            cid = commitment.client_id
            lender_totals[cid] = lender_totals.get(cid, _ZERO) + Decimal(str(alloc.amount))

        results = []
        for lender_id, allocated in lender_totals.items():
            if allocated <= 0:
                continue

            share = allocated / total_borrowed
            interest_earned = (interest_to_lenders * share).quantize(_PRECISION, rounding=ROUND_HALF_UP)

            # Record accrual
            accrual = LenderInterestAccrual(
                client_id=lender_id,
                pool_id=pool.id,
                date=accrual_date,
                allocated_amount=allocated,
                interest_earned=interest_earned,
            )
            db.add(accrual)

            # Update PositionAtom.accrued_income
            self._update_lending_atom_accrued(db, lender_id, pool.asset, interest_earned)

            results.append({
                "client_id": str(lender_id),
                "allocated_amount": float(allocated),
                "share": float(share),
                "interest_earned": float(interest_earned),
            })

        db.flush()
        return results

    def _accrue_borrowers(
        self,
        db: Session,
        pool: LendingPool,
        accrual_date: date,
        daily_borrow_rate: Decimal,
    ) -> list[dict]:
        """Record interest due for each active borrower."""
        borrows = db.query(PoolBorrowPosition).filter(
            PoolBorrowPosition.pool_id == pool.id,
            PoolBorrowPosition.status == "active",
        ).all()

        results = []
        for borrow in borrows:
            borrowed = Decimal(str(borrow.borrowed_amount))
            interest_due = (borrowed * daily_borrow_rate).quantize(_PRECISION, rounding=ROUND_HALF_UP)

            accrual = BorrowerInterestAccrual(
                client_id=borrow.client_id,
                pool_id=pool.id,
                date=accrual_date,
                borrowed_amount=borrowed,
                interest_due=interest_due,
            )
            db.add(accrual)

            # Update PositionAtom.accrued_income (borrowing atom)
            self._update_borrowing_atom_accrued(db, borrow.client_id, pool.asset, interest_due)

            results.append({
                "client_id": str(borrow.client_id),
                "borrowed_amount": float(borrowed),
                "interest_due": float(interest_due),
            })

        db.flush()
        return results

    # ── PositionAtom accrued_income updates ───────────────────────

    @staticmethod
    def _update_lending_atom_accrued(
        db: Session, client_id: UUID, asset: str, interest_increment: Decimal,
    ) -> None:
        """Add interest_increment to the lending PositionAtom.accrued_income."""
        from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, _resolve_or_create_instrument
        from services.portfolio_engine.positions.enums import PositionType

        portfolio = ensure_direct_portfolio(db, client_id)
        instrument = _resolve_or_create_instrument(db, asset)

        atom = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == instrument.id,
            PositionAtom.position_type == PositionType.LENDING.value,
            PositionAtom.status == "open",
        ).first()
        if atom:
            atom.accrued_income = Decimal(str(atom.accrued_income or 0)) + interest_increment
            db.flush()

    @staticmethod
    def _update_borrowing_atom_accrued(
        db: Session, client_id: UUID, asset: str, interest_increment: Decimal,
    ) -> None:
        """Add interest_increment to the borrowing PositionAtom.accrued_income."""
        from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, _resolve_or_create_instrument
        from services.portfolio_engine.positions.enums import PositionType

        portfolio = ensure_direct_portfolio(db, client_id)
        instrument = _resolve_or_create_instrument(db, asset)

        atom = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == instrument.id,
            PositionAtom.position_type == PositionType.BORROWING.value,
            PositionAtom.status == "open",
        ).first()
        if atom:
            atom.accrued_income = Decimal(str(atom.accrued_income or 0)) + interest_increment
            db.flush()

    # ── Query helpers ─────────────────────────────────────────────

    def get_total_accrued_interest(
        self, db: Session, client_id: UUID, pool_id: UUID, *, role: str = "lender",
    ) -> Decimal:
        """Sum of all accrued interest for a client in a pool."""
        if role == "lender":
            rows = db.query(LenderInterestAccrual).filter(
                LenderInterestAccrual.client_id == client_id,
                LenderInterestAccrual.pool_id == pool_id,
            ).all()
            return sum(Decimal(str(r.interest_earned)) for r in rows)
        else:
            rows = db.query(BorrowerInterestAccrual).filter(
                BorrowerInterestAccrual.client_id == client_id,
                BorrowerInterestAccrual.pool_id == pool_id,
            ).all()
            return sum(Decimal(str(r.interest_due)) for r in rows)

    def get_snapshots(
        self, db: Session, pool_id: UUID, *, limit: int = 30,
    ) -> list[PoolInterestSnapshot]:
        return (
            db.query(PoolInterestSnapshot)
            .filter(PoolInterestSnapshot.pool_id == pool_id)
            .order_by(PoolInterestSnapshot.date.desc())
            .limit(limit)
            .all()
        )
