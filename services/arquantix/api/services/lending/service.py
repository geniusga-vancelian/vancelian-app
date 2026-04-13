"""P2P Internal Lending Service — Phase 2A.

Handles the full loan lifecycle:
  create → accept → activate → repay

Invariants:
  1. Conservation: total spot + lending_positions = constant
  2. Double-entry ledger on every movement
  3. Symmetry: lending_position == borrowing_position (same principal)
  4. Separation: lending/borrowing never leak into crypto_positions valuation
  5. Spot invariant: trading / bundles remain unchanged
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.models import CryptoPosition
from services.exchange.repository import CryptoPositionRepository
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, _resolve_or_create_instrument
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.ledger_entries.service import LedgerEntryService

from .enums import LoanStatus, VALID_TRANSITIONS
from .models import Loan, LoanInterestAccrual

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_ROUND = Decimal("0.0000000001")
_DAYS_PER_YEAR = Decimal("365")
_BPS = Decimal("10000")


class LendingError(Exception):
    pass


class InsufficientBalanceError(LendingError):
    pass


class InvalidStateTransitionError(LendingError):
    pass


class LoanNotFoundError(LendingError):
    pass


class UnauthorizedError(LendingError):
    pass


class LendingService:

    def __init__(self) -> None:
        self._ledger_svc = LedgerEntryService()

    # ── helpers ────────────────────────────────────────────────────

    @staticmethod
    def _validate_transition(current: str, target: LoanStatus) -> None:
        current_enum = LoanStatus(current)
        allowed = VALID_TRANSITIONS.get(current_enum, frozenset())
        if target not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition from {current} to {target.value}"
            )

    @staticmethod
    def _get_loan(db: Session, loan_id: UUID) -> Loan:
        loan = db.query(Loan).filter(Loan.id == loan_id).first()
        if loan is None:
            raise LoanNotFoundError(f"Loan {loan_id} not found")
        return loan

    @staticmethod
    def _compute_interest(principal: Decimal, rate_bps: int, elapsed_days: int) -> Decimal:
        """Simple interest: principal × (rate_bps / 10000) × (elapsed_days / 365)."""
        rate = Decimal(str(rate_bps)) / _BPS
        time_frac = Decimal(str(elapsed_days)) / _DAYS_PER_YEAR
        return (principal * rate * time_frac).quantize(_ROUND, rounding=ROUND_HALF_UP)

    @staticmethod
    def _compute_platform_fee(interest: Decimal, fee_bps: int) -> Decimal:
        """Platform fee on accrued interest."""
        fee_rate = Decimal(str(fee_bps)) / _BPS
        return (interest * fee_rate).quantize(_ROUND, rounding=ROUND_HALF_UP)

    # ── 1. CREATE ─────────────────────────────────────────────────

    def create_loan(
        self,
        db: Session,
        *,
        lender_client_id: UUID,
        borrower_client_id: UUID,
        asset: str,
        principal: Decimal,
        interest_rate_bps: int,
        platform_fee_bps: int = 0,
        duration_days: int,
    ) -> Loan:
        """Create a loan offer (status=pending). No balance changes yet."""
        from services.compliance.eligibility_service import EligibilityService
        EligibilityService.require_eligible_by_client_id(db, lender_client_id)

        if lender_client_id == borrower_client_id:
            raise LendingError("Lender and borrower must be different clients")
        if principal <= 0:
            raise LendingError("Principal must be positive")

        loan = Loan(
            lender_client_id=lender_client_id,
            borrower_client_id=borrower_client_id,
            asset=asset.upper(),
            principal=principal,
            interest_rate_bps=interest_rate_bps,
            platform_fee_bps=platform_fee_bps,
            duration_days=duration_days,
            status=LoanStatus.PENDING.value,
        )
        db.add(loan)
        db.flush()
        logger.info("Loan %s created: %s %s from %s → %s", loan.id, principal, asset, lender_client_id, borrower_client_id)
        return loan

    # ── 2. ACCEPT ─────────────────────────────────────────────────

    def accept_loan(self, db: Session, loan_id: UUID, borrower_client_id: UUID) -> Loan:
        """Borrower accepts a pending loan."""
        loan = self._get_loan(db, loan_id)
        if loan.borrower_client_id != borrower_client_id:
            raise UnauthorizedError("Only the designated borrower can accept this loan")
        self._validate_transition(loan.status, LoanStatus.ACCEPTED)
        loan.status = LoanStatus.ACCEPTED.value
        db.flush()
        logger.info("Loan %s accepted by borrower %s", loan_id, borrower_client_id)
        return loan

    # ── 3. ACTIVATE (CRITICAL — atomic) ──────────────────────────

    def activate_loan(self, db: Session, loan_id: UUID) -> Loan:
        """Atomically activate a loan: transfer spot + create positions.

        Must be called inside an existing DB transaction (caller commits).
        Steps:
          1. Verify lender has sufficient spot balance
          2. Debit lender crypto_position
          3. Credit borrower crypto_position
          4. Create lending PositionAtom (lender)
          5. Create borrowing PositionAtom (borrower)
          6. Create ledger entries (audit)
          7. Loan status → active
        """
        loan = self._get_loan(db, loan_id)
        self._validate_transition(loan.status, LoanStatus.ACTIVE)

        principal = Decimal(str(loan.principal))
        asset = loan.asset

        # Step 1: verify lender balance
        lender_pos = CryptoPositionRepository.get_or_create_for_update(
            db, loan.lender_client_id, asset,
        )
        lender_balance = Decimal(str(lender_pos.balance))
        if lender_balance < principal:
            raise InsufficientBalanceError(
                f"Lender balance {lender_balance} < principal {principal} for {asset}"
            )

        # Step 2: debit lender
        lender_pos.balance = lender_balance - principal
        lender_pos.available_balance = Decimal(str(lender_pos.available_balance)) - principal

        # Step 3: credit borrower
        borrower_pos = CryptoPositionRepository.get_or_create_for_update(
            db, loan.borrower_client_id, asset,
        )
        borrower_pos.balance = Decimal(str(borrower_pos.balance)) + principal
        borrower_pos.available_balance = Decimal(str(borrower_pos.available_balance)) + principal

        # Step 4: create lending position (lender)
        lender_portfolio = ensure_direct_portfolio(db, loan.lender_client_id)
        instrument = _resolve_or_create_instrument(db, asset)
        now = datetime.now(timezone.utc)

        lending_atom = PositionAtom(
            portfolio_id=lender_portfolio.id,
            instrument_id=instrument.id,
            position_type=PositionType.LENDING.value,
            status="open",
            quantity=principal,
            available_quantity=_ZERO,
            locked_quantity=principal,
            cost_basis=principal,
            opened_at=now,
            metadata_={"loan_id": str(loan.id), "counterparty": str(loan.borrower_client_id)},
        )
        db.add(lending_atom)
        db.flush()

        # Step 5: create borrowing position (borrower)
        borrower_portfolio = ensure_direct_portfolio(db, loan.borrower_client_id)

        borrowing_atom = PositionAtom(
            portfolio_id=borrower_portfolio.id,
            instrument_id=instrument.id,
            position_type=PositionType.BORROWING.value,
            status="open",
            quantity=principal,
            available_quantity=_ZERO,
            locked_quantity=principal,
            cost_basis=principal,
            opened_at=now,
            metadata_={"loan_id": str(loan.id), "counterparty": str(loan.lender_client_id)},
        )
        db.add(borrowing_atom)
        db.flush()

        # Step 6: ledger audit trail
        self._record_activation_ledger(db, loan, now)

        # Step 7: finalize
        loan.status = LoanStatus.ACTIVE.value
        loan.start_at = now
        loan.end_at = now + timedelta(days=loan.duration_days)
        loan.lender_position_atom_id = lending_atom.id
        loan.borrower_position_atom_id = borrowing_atom.id
        db.flush()

        logger.info(
            "Loan %s ACTIVATED: %s %s transferred %s → %s",
            loan.id, principal, asset, loan.lender_client_id, loan.borrower_client_id,
        )
        return loan

    def _record_activation_ledger(self, db: Session, loan: Loan, effective_at: datetime) -> None:
        """Best-effort ledger entries for loan activation audit trail."""
        try:
            from services.portfolio_engine.ledger_accounts.models import LedgerAccount
            lender_acct = (
                db.query(LedgerAccount)
                .filter(LedgerAccount.owner_id == loan.lender_client_id, LedgerAccount.status == "active")
                .first()
            )
            borrower_acct = (
                db.query(LedgerAccount)
                .filter(LedgerAccount.owner_id == loan.borrower_client_id, LedgerAccount.status == "active")
                .first()
            )
            if lender_acct and borrower_acct:
                self._ledger_svc.post_double_entry(
                    db,
                    debit_account_id=lender_acct.id,
                    credit_account_id=borrower_acct.id,
                    amount=Decimal(str(loan.principal)),
                    currency=loan.asset,
                    reference_type="loan_activation",
                    reference_id=loan.id,
                    effective_at=effective_at,
                    description=f"P2P loan activation: {loan.principal} {loan.asset}",
                    metadata={"loan_id": str(loan.id)},
                )
        except Exception:
            logger.warning("Ledger entries for loan %s skipped (no accounts)", loan.id, exc_info=True)

    # ── 4. REPAY ──────────────────────────────────────────────────

    def compute_repayment(self, db: Session, loan_id: UUID) -> dict:
        """Compute repayment amounts without executing."""
        loan = self._get_loan(db, loan_id)
        if loan.status != LoanStatus.ACTIVE.value:
            raise LendingError(f"Loan is not active (status={loan.status})")

        principal = Decimal(str(loan.principal))
        now = datetime.now(timezone.utc)
        elapsed = (now - loan.start_at).days if loan.start_at else 0
        elapsed = max(elapsed, 1)

        interest = self._compute_interest(principal, loan.interest_rate_bps, elapsed)
        platform_fee = self._compute_platform_fee(interest, loan.platform_fee_bps)
        borrower_pays = principal + interest
        lender_receives = principal + interest - platform_fee

        return {
            "loan_id": loan.id,
            "principal": principal,
            "interest": interest,
            "platform_fee": platform_fee,
            "lender_receives": lender_receives,
            "borrower_pays": borrower_pays,
            "elapsed_days": elapsed,
        }

    def repay_loan(self, db: Session, loan_id: UUID, borrower_client_id: UUID) -> dict:
        """Full repayment: borrower pays principal + interest.

        Steps:
          1. Compute interest + fees
          2. Verify borrower has sufficient balance
          3. Debit borrower crypto_position (principal + interest)
          4. Credit lender crypto_position (principal + interest - platform_fee)
          5. Close lending + borrowing positions
          6. Create ledger entries
          7. Loan status → repaid
        """
        loan = self._get_loan(db, loan_id)
        if loan.borrower_client_id != borrower_client_id:
            raise UnauthorizedError("Only the borrower can repay this loan")
        self._validate_transition(loan.status, LoanStatus.REPAID)

        repayment = self.compute_repayment(db, loan_id)
        principal = repayment["principal"]
        interest = repayment["interest"]
        platform_fee = repayment["platform_fee"]
        borrower_pays = repayment["borrower_pays"]
        lender_receives = repayment["lender_receives"]
        asset = loan.asset
        now = datetime.now(timezone.utc)

        # Step 2: verify borrower balance
        borrower_pos = CryptoPositionRepository.get_or_create_for_update(
            db, loan.borrower_client_id, asset,
        )
        borrower_balance = Decimal(str(borrower_pos.balance))
        if borrower_balance < borrower_pays:
            raise InsufficientBalanceError(
                f"Borrower balance {borrower_balance} < repayment {borrower_pays} for {asset}"
            )

        # Step 3: debit borrower
        borrower_pos.balance = borrower_balance - borrower_pays
        borrower_pos.available_balance = Decimal(str(borrower_pos.available_balance)) - borrower_pays

        # Step 4: credit lender
        lender_pos = CryptoPositionRepository.get_or_create_for_update(
            db, loan.lender_client_id, asset,
        )
        lender_pos.balance = Decimal(str(lender_pos.balance)) + lender_receives
        lender_pos.available_balance = Decimal(str(lender_pos.available_balance)) + lender_receives

        # Step 5: close positions
        if loan.lender_position_atom_id:
            lending_atom = db.query(PositionAtom).filter(PositionAtom.id == loan.lender_position_atom_id).first()
            if lending_atom:
                lending_atom.status = "closed"
                lending_atom.closed_at = now
                lending_atom.realized_pnl = interest - platform_fee
                lending_atom.accrued_income = interest
        if loan.borrower_position_atom_id:
            borrowing_atom = db.query(PositionAtom).filter(PositionAtom.id == loan.borrower_position_atom_id).first()
            if borrowing_atom:
                borrowing_atom.status = "closed"
                borrowing_atom.closed_at = now
                borrowing_atom.realized_pnl = -interest

        # Step 6: ledger audit
        self._record_repayment_ledger(db, loan, repayment, now)

        # Step 7: update interest accrual record
        accrual = LoanInterestAccrual(
            loan_id=loan.id,
            accrued_amount=interest,
            last_accrual_at=now,
        )
        db.add(accrual)

        # Step 8: finalize
        loan.status = LoanStatus.REPAID.value
        loan.repaid_at = now
        db.flush()

        logger.info(
            "Loan %s REPAID: borrower paid %s %s (principal=%s, interest=%s, fee=%s)",
            loan.id, borrower_pays, asset, principal, interest, platform_fee,
        )
        return repayment

    def _record_repayment_ledger(self, db: Session, loan: Loan, repayment: dict, effective_at: datetime) -> None:
        """Best-effort ledger entries for repayment."""
        try:
            from services.portfolio_engine.ledger_accounts.models import LedgerAccount
            borrower_acct = (
                db.query(LedgerAccount)
                .filter(LedgerAccount.owner_id == loan.borrower_client_id, LedgerAccount.status == "active")
                .first()
            )
            lender_acct = (
                db.query(LedgerAccount)
                .filter(LedgerAccount.owner_id == loan.lender_client_id, LedgerAccount.status == "active")
                .first()
            )
            if borrower_acct and lender_acct:
                self._ledger_svc.post_double_entry(
                    db,
                    debit_account_id=borrower_acct.id,
                    credit_account_id=lender_acct.id,
                    amount=repayment["borrower_pays"],
                    currency=loan.asset,
                    reference_type="loan_repayment",
                    reference_id=loan.id,
                    effective_at=effective_at,
                    description=f"P2P loan repayment: {repayment['borrower_pays']} {loan.asset}",
                    metadata={
                        "loan_id": str(loan.id),
                        "principal": str(repayment["principal"]),
                        "interest": str(repayment["interest"]),
                        "platform_fee": str(repayment["platform_fee"]),
                    },
                )
        except Exception:
            logger.warning("Ledger entries for loan repayment %s skipped", loan.id, exc_info=True)

    # ── QUERIES ───────────────────────────────────────────────────

    def get_loan(self, db: Session, loan_id: UUID) -> Loan:
        return self._get_loan(db, loan_id)

    def list_loans(
        self,
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Loan], int]:
        from sqlalchemy import or_
        query = db.query(Loan)
        if client_id:
            query = query.filter(
                or_(Loan.lender_client_id == client_id, Loan.borrower_client_id == client_id)
            )
        if status:
            query = query.filter(Loan.status == status)
        total = query.count()
        items = query.order_by(Loan.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def reject_loan(self, db: Session, loan_id: UUID, borrower_client_id: UUID) -> Loan:
        """Borrower rejects a pending loan."""
        loan = self._get_loan(db, loan_id)
        if loan.borrower_client_id != borrower_client_id:
            raise UnauthorizedError("Only the designated borrower can reject this loan")
        self._validate_transition(loan.status, LoanStatus.REJECTED)
        loan.status = LoanStatus.REJECTED.value
        db.flush()
        logger.info("Loan %s rejected by %s", loan_id, borrower_client_id)
        return loan

    def cancel_loan(self, db: Session, loan_id: UUID, lender_client_id: UUID) -> Loan:
        """Lender cancels a pending/accepted loan (before activation)."""
        loan = self._get_loan(db, loan_id)
        if loan.lender_client_id != lender_client_id:
            raise UnauthorizedError("Only the lender can cancel this loan")
        self._validate_transition(loan.status, LoanStatus.CANCELLED)
        loan.status = LoanStatus.CANCELLED.value
        db.flush()
        logger.info("Loan %s cancelled by lender %s", loan_id, lender_client_id)
        return loan

    # ── ROLE-BASED QUERIES (Phase 2A.6) ───────────────────────────

    def list_loans_by_role(
        self,
        db: Session,
        *,
        client_id: UUID,
        role: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Loan], int]:
        """List loans filtered by role (lender or borrower)."""
        query = db.query(Loan)
        if role == "lender":
            query = query.filter(Loan.lender_client_id == client_id)
        elif role == "borrower":
            query = query.filter(Loan.borrower_client_id == client_id)
        else:
            from sqlalchemy import or_
            query = query.filter(
                or_(Loan.lender_client_id == client_id, Loan.borrower_client_id == client_id)
            )
        if status:
            query = query.filter(Loan.status == status)
        total = query.count()
        items = query.order_by(Loan.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def get_client_summary(self, db: Session, client_id: UUID) -> dict:
        """Build a lending summary for a client (dashboard-ready).

        Returns counts, values, and detailed active/pending loans.
        """
        from sqlalchemy import text
        from .valuation import get_lending_positions, get_borrowing_positions

        # Active loans as lender
        active_lender, _ = self.list_loans_by_role(
            db, client_id=client_id, role="lender", status="active",
        )
        # Active loans as borrower
        active_borrower, _ = self.list_loans_by_role(
            db, client_id=client_id, role="borrower", status="active",
        )
        # Pending offers received
        pending_received, _ = self.list_loans_by_role(
            db, client_id=client_id, role="borrower", status="pending",
        )

        # Resolve counterparty emails
        all_counterparty_ids = set()
        for loan in active_lender:
            all_counterparty_ids.add(loan.borrower_client_id)
        for loan in active_borrower + pending_received:
            all_counterparty_ids.add(loan.lender_client_id)

        email_map: dict = {}
        if all_counterparty_ids:
            rows = db.execute(
                text("SELECT id, email FROM pe_clients WHERE id = ANY(:ids)"),
                {"ids": list(all_counterparty_ids)},
            ).fetchall()
            email_map = {row[0]: row[1] for row in rows}

        def _enrich(loan: Loan, role: str) -> dict:
            counterparty_id = loan.borrower_client_id if role == "lender" else loan.lender_client_id
            return {
                "id": loan.id,
                "role": role,
                "counterparty_id": counterparty_id,
                "counterparty_email": email_map.get(counterparty_id),
                "asset": loan.asset,
                "principal": loan.principal,
                "market_value_eur": None,
                "status": loan.status,
                "start_at": loan.start_at,
                "created_at": loan.created_at,
            }

        # Market values from valuation layer
        lending_positions = get_lending_positions(db, client_id)
        borrowing_positions = get_borrowing_positions(db, client_id)
        total_lent_eur = sum(p["market_value_eur"] for p in lending_positions)
        total_borrowed_eur = sum(abs(p["market_value_eur"]) for p in borrowing_positions)

        enriched_lender = [_enrich(l, "lender") for l in active_lender]
        enriched_borrower = [_enrich(l, "borrower") for l in active_borrower]
        enriched_pending = [_enrich(l, "borrower") for l in pending_received]

        # Attach market values to active loans where possible
        lending_by_loan = {p["loan_id"]: p["market_value_eur"] for p in lending_positions}
        borrowing_by_loan = {p["loan_id"]: abs(p["market_value_eur"]) for p in borrowing_positions}
        for item in enriched_lender:
            item["market_value_eur"] = lending_by_loan.get(str(item["id"]))
        for item in enriched_borrower:
            item["market_value_eur"] = borrowing_by_loan.get(str(item["id"]))

        return {
            "client_id": client_id,
            "total_lent_count": len(active_lender),
            "total_borrowed_count": len(active_borrower),
            "total_lent_value_eur": round(total_lent_eur, 2),
            "total_borrowed_value_eur": round(total_borrowed_eur, 2),
            "active_loans_as_lender": enriched_lender,
            "active_loans_as_borrower": enriched_borrower,
            "pending_offers_received": enriched_pending,
        }
