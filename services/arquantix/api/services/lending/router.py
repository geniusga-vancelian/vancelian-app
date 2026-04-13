"""API routes for P2P Internal Lending (Phase 2A + 2A.6)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from .schemas import (
    CreateLoanRequest,
    AcceptLoanRequest,
    RepayLoanRequest,
    LoanResponse,
    LoanRepaymentSummary,
    LendingSummaryResponse,
)
from .service import (
    LendingService,
    LendingError,
    InsufficientBalanceError,
    InvalidStateTransitionError,
    LoanNotFoundError,
    UnauthorizedError,
)
from services.portfolio_engine.provisioning.errors import ClientNotEligibleError

router = APIRouter(prefix="/api/lending", tags=["P2P Lending"])
_svc = LendingService()


@router.post("/loans", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
def create_loan(payload: CreateLoanRequest, db: Session = Depends(get_db)):
    """Create a new loan offer (status=pending).

    For V1 (no interest): interest_rate_bps and duration_days default to 0 and 30.
    """
    try:
        loan = _svc.create_loan(
            db,
            lender_client_id=payload.lender_client_id,
            borrower_client_id=payload.borrower_client_id,
            asset=payload.asset,
            principal=payload.principal,
            interest_rate_bps=payload.interest_rate_bps,
            platform_fee_bps=payload.platform_fee_bps,
            duration_days=payload.duration_days,
        )
        db.commit()
        db.refresh(loan)
        return loan
    except ClientNotEligibleError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except LendingError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/loans", response_model=list[LoanResponse])
def list_loans(
    client_id: Optional[UUID] = Query(None),
    role: Optional[str] = Query(None, description="Filter by role: lender or borrower"),
    loan_status: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List loans, optionally filtered by client, role, and/or status.

    ?role=lender  → loans where client is lender
    ?role=borrower → loans where client is borrower
    """
    if client_id and role:
        loans, _ = _svc.list_loans_by_role(
            db, client_id=client_id, role=role, status=loan_status, skip=skip, limit=limit,
        )
    else:
        loans, _ = _svc.list_loans(db, client_id=client_id, status=loan_status, skip=skip, limit=limit)
    return loans


@router.get("/summary")
def get_lending_summary(
    client_id: UUID = Query(..., description="Client UUID"),
    db: Session = Depends(get_db),
):
    """Dashboard summary: active loans, pending offers, market values."""
    return _svc.get_client_summary(db, client_id)


@router.get("/loans/{loan_id}", response_model=LoanResponse)
def get_loan(loan_id: UUID, db: Session = Depends(get_db)):
    """Get a single loan by ID."""
    try:
        return _svc.get_loan(db, loan_id)
    except LoanNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/loans/{loan_id}/accept", response_model=LoanResponse)
def accept_loan(loan_id: UUID, payload: AcceptLoanRequest, db: Session = Depends(get_db)):
    """Borrower accepts a pending loan."""
    try:
        loan = _svc.accept_loan(db, loan_id, payload.borrower_client_id)
        db.commit()
        db.refresh(loan)
        return loan
    except (LoanNotFoundError,) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (UnauthorizedError,) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except (InvalidStateTransitionError, LendingError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/loans/{loan_id}/reject", response_model=LoanResponse)
def reject_loan(loan_id: UUID, payload: AcceptLoanRequest, db: Session = Depends(get_db)):
    """Borrower rejects a pending loan."""
    try:
        loan = _svc.reject_loan(db, loan_id, payload.borrower_client_id)
        db.commit()
        db.refresh(loan)
        return loan
    except (LoanNotFoundError,) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (UnauthorizedError,) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except (InvalidStateTransitionError, LendingError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/loans/{loan_id}/cancel", response_model=LoanResponse)
def cancel_loan(loan_id: UUID, db: Session = Depends(get_db)):
    """Lender cancels a pending/accepted loan. Requires lender_client_id in query."""
    lender_id = None
    try:
        loan = _svc.get_loan(db, loan_id)
        lender_id = loan.lender_client_id
        loan = _svc.cancel_loan(db, loan_id, lender_id)
        db.commit()
        db.refresh(loan)
        return loan
    except (LoanNotFoundError,) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (InvalidStateTransitionError, LendingError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/loans/{loan_id}/activate", response_model=LoanResponse)
def activate_loan(loan_id: UUID, db: Session = Depends(get_db)):
    """Activate an accepted loan (atomic: transfer spot + create positions)."""
    try:
        loan = _svc.activate_loan(db, loan_id)
        db.commit()
        db.refresh(loan)
        return loan
    except (LoanNotFoundError,) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InsufficientBalanceError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except (InvalidStateTransitionError, LendingError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/loans/{loan_id}/repayment-preview", response_model=LoanRepaymentSummary)
def preview_repayment(loan_id: UUID, db: Session = Depends(get_db)):
    """Preview repayment amounts without executing."""
    try:
        return _svc.compute_repayment(db, loan_id)
    except (LoanNotFoundError,) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except LendingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/loans/{loan_id}/repay", response_model=LoanRepaymentSummary)
def repay_loan(loan_id: UUID, payload: RepayLoanRequest, db: Session = Depends(get_db)):
    """Full loan repayment by the borrower."""
    try:
        result = _svc.repay_loan(db, loan_id, payload.borrower_client_id)
        db.commit()
        return result
    except (LoanNotFoundError,) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (UnauthorizedError,) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except InsufficientBalanceError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except (InvalidStateTransitionError, LendingError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
