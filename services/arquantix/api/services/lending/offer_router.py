"""Exclusive Offer Lending Product API — Phase 2A.10 / 2A.12.

Endpoints for creating, listing, subscribing to, and managing exclusive offer products.
Includes invest flow endpoints (Phase 2A.12).
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from .offer_service import (
    OfferService,
    OfferError,
    OfferNotFoundError,
    InvalidOfferStatusError,
    SubscriptionError,
    BorrowerRestrictionError,
)
from .invest_orchestrator import (
    LendingInvestOrchestrator,
    LendingInvestError,
    FundingAssetNotAllowedError,
    ProductNotInvestableError,
)
from services.portfolio_engine.provisioning.errors import ClientNotEligibleError

router = APIRouter(prefix="/api/lending/products", tags=["Exclusive Offer Lending"])

_svc = OfferService()
_invest = LendingInvestOrchestrator()


# ── Schemas ──────────────────────────────────────────────────────

class CreateProductRequest(BaseModel):
    title: str
    asset: str
    borrower_client_id: UUID
    target_size: float = Field(gt=0)
    supply_apr_bps: float = 300
    borrow_apr_bps: float = 500
    min_ticket: Optional[float] = None
    max_ticket: Optional[float] = None
    description: Optional[str] = None
    use_of_funds: Optional[str] = None
    start_date: Optional[str] = None
    maturity_date: Optional[str] = None
    project_id: Optional[str] = None
    entry_asset_default: Optional[str] = None
    entry_assets_allowed: Optional[list[str]] = None


class LinkProjectRequest(BaseModel):
    project_id: str


class CreateFromProjectRequest(BaseModel):
    project_id: str
    borrower_client_id: UUID
    asset: str = "USDC"
    target_size: float = Field(gt=0)
    title: Optional[str] = None
    supply_apr_bps: float = 300
    borrow_apr_bps: float = 500
    min_ticket: Optional[float] = None
    max_ticket: Optional[float] = None


class CreateFromPackagedProductRequest(BaseModel):
    """Provisioning lending depuis Product Registry (packaged_products), sans project_id."""

    packaged_product_id: UUID
    borrower_client_id: UUID
    asset: str = "USDC"
    target_size: float = Field(gt=0)
    title: Optional[str] = None
    supply_apr_bps: float = 300
    borrow_apr_bps: float = 500
    min_ticket: Optional[float] = None
    max_ticket: Optional[float] = None


class SubscribeRequest(BaseModel):
    lender_client_id: UUID
    amount: float = Field(gt=0)


class InvestRequest(BaseModel):
    client_id: UUID
    funding_asset: str = Field(..., min_length=1, max_length=20)
    funding_amount: float = Field(..., gt=0)


# ── Endpoints ────────────────────────────────────────────────────

@router.post("")
def create_product(payload: CreateProductRequest, db: Session = Depends(get_db)):
    """Create a new exclusive offer product."""
    from datetime import date as date_type
    try:
        product = _svc.create_product(
            db,
            title=payload.title,
            asset=payload.asset,
            borrower_client_id=payload.borrower_client_id,
            target_size=Decimal(str(payload.target_size)),
            supply_apr_bps=Decimal(str(payload.supply_apr_bps)),
            borrow_apr_bps=Decimal(str(payload.borrow_apr_bps)),
            min_ticket=Decimal(str(payload.min_ticket)) if payload.min_ticket else None,
            max_ticket=Decimal(str(payload.max_ticket)) if payload.max_ticket else None,
            description=payload.description,
            use_of_funds=payload.use_of_funds,
            start_date=date_type.fromisoformat(payload.start_date) if payload.start_date else None,
            maturity_date=date_type.fromisoformat(payload.maturity_date) if payload.maturity_date else None,
            project_id=payload.project_id,
            entry_asset_default=payload.entry_asset_default,
            entry_assets_allowed=payload.entry_assets_allowed,
        )
        db.commit()
        return _svc.get_product_detail(db, product.id)
    except OfferError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{product_id}/open-fundraising")
def open_fundraising(product_id: UUID, db: Session = Depends(get_db)):
    """Transition: draft → fundraising."""
    try:
        product = _svc.open_fundraising(db, product_id)
        db.commit()
        return _svc.get_product_detail(db, product.id)
    except OfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidOfferStatusError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{product_id}/subscribe")
def subscribe(product_id: UUID, payload: SubscribeRequest, db: Session = Depends(get_db)):
    """Lender subscribes to an exclusive offer."""
    try:
        commitment = _svc.subscribe(
            db,
            product_id=product_id,
            lender_client_id=payload.lender_client_id,
            amount=Decimal(str(payload.amount)),
        )
        db.commit()
        product = _svc.get_product_detail(db, product_id)
        return {
            "commitment_id": str(commitment.id),
            "product": product,
        }
    except ClientNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except OfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SubscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{product_id}/activate")
def activate(product_id: UUID, db: Session = Depends(get_db)):
    """Transition: funded → active — triggers automatic borrow."""
    try:
        result = _svc.activate_product(db, product_id)
        db.commit()
        return result
    except OfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidOfferStatusError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{product_id}/mark-repaid")
def mark_repaid(product_id: UUID, db: Session = Depends(get_db)):
    """Transition: active → repaid."""
    try:
        product = _svc.mark_repaid(db, product_id)
        db.commit()
        return _svc.get_product_detail(db, product.id)
    except (OfferNotFoundError, InvalidOfferStatusError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{product_id}/close")
def close_product(product_id: UUID, db: Session = Depends(get_db)):
    """Transition: repaid → closed."""
    try:
        product = _svc.close_product(db, product_id)
        db.commit()
        return _svc.get_product_detail(db, product.id)
    except (OfferNotFoundError, InvalidOfferStatusError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("")
def list_products(
    asset: Optional[str] = None,
    product_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """List all exclusive offer products."""
    return {"products": _svc.list_products(db, status=product_status, asset=asset)}


@router.get("/{product_id}")
def get_product(product_id: UUID, db: Session = Depends(get_db)):
    """Get product detail."""
    try:
        return _svc.get_product_detail(db, product_id)
    except OfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/my-positions/list")
def my_positions(
    client_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    """Get all exclusive offer subscriptions for a client."""
    return {"positions": _svc.get_user_subscriptions(db, client_id)}


@router.post("/{product_id}/link-project")
def link_project(product_id: UUID, payload: LinkProjectRequest, db: Session = Depends(get_db)):
    """Link a lending product to a CMS project (1-to-1)."""
    try:
        product = _svc.link_project(db, product_id, payload.project_id)
        db.commit()
        return _svc.get_product_detail(db, product.id)
    except OfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except OfferError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.delete("/{product_id}/link-project")
def unlink_project(product_id: UUID, db: Session = Depends(get_db)):
    """Remove the CMS project link."""
    try:
        product = _svc.unlink_project(db, product_id)
        db.commit()
        return _svc.get_product_detail(db, product.id)
    except OfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/projects/lending-data")
def projects_lending_data(db: Session = Depends(get_db)):
    """Lending data for all linked projects — used by GET /api/projects to enrich CMS data."""
    return _svc.get_lending_data_for_projects(db)


# ── Phase 2A.12 — Invest Flow ─────────────────────────────────

@router.post("/{product_id}/invest/preview")
def invest_preview(product_id: UUID, payload: InvestRequest, db: Session = Depends(get_db)):
    """Preview an investment into an exclusive offer — read-only, zero side-effects."""
    try:
        return _invest.preview_invest(
            db,
            product_id=product_id,
            client_id=payload.client_id,
            funding_asset=payload.funding_asset,
            funding_amount=Decimal(str(payload.funding_amount)),
        )
    except OfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ProductNotInvestableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except FundingAssetNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{product_id}/invest")
def invest(product_id: UUID, payload: InvestRequest, db: Session = Depends(get_db)):
    """Invest into an exclusive offer — atomic execution."""
    try:
        result = _invest.invest_into_product(
            db,
            product_id=product_id,
            client_id=payload.client_id,
            funding_asset=payload.funding_asset,
            funding_amount=Decimal(str(payload.funding_amount)),
        )
        db.commit()
        return result
    except ClientNotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except OfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ProductNotInvestableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except FundingAssetNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (SubscriptionError, LendingInvestError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.exception("Invest error for product %s", product_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── Phase 2A.11.5 — Provisioning & Admin ──────────────────────

@router.post("/create-from-project")
def create_from_project(payload: CreateFromProjectRequest, db: Session = Depends(get_db)):
    """One-click: create pool + product + link from a CMS project."""
    try:
        product = _svc.create_from_project(
            db,
            project_id=payload.project_id,
            borrower_client_id=payload.borrower_client_id,
            asset=payload.asset,
            target_size=Decimal(str(payload.target_size)),
            title=payload.title or "",
            supply_apr_bps=Decimal(str(payload.supply_apr_bps)),
            borrow_apr_bps=Decimal(str(payload.borrow_apr_bps)),
            min_ticket=Decimal(str(payload.min_ticket)) if payload.min_ticket else None,
            max_ticket=Decimal(str(payload.max_ticket)) if payload.max_ticket else None,
        )
        db.commit()
        return _svc.get_product_detail(db, product.id)
    except OfferError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/create-from-packaged-product")
def create_from_packaged_product(
    payload: CreateFromPackagedProductRequest, db: Session = Depends(get_db),
):
    """One-click: pool + lending_pool_products + lien packaged_products (engine LENDING)."""
    try:
        product = _svc.create_from_packaged_product(
            db,
            packaged_product_id=payload.packaged_product_id,
            borrower_client_id=payload.borrower_client_id,
            asset=payload.asset,
            target_size=Decimal(str(payload.target_size)),
            title=payload.title or "",
            supply_apr_bps=Decimal(str(payload.supply_apr_bps)),
            borrow_apr_bps=Decimal(str(payload.borrow_apr_bps)),
            min_ticket=Decimal(str(payload.min_ticket)) if payload.min_ticket else None,
            max_ticket=Decimal(str(payload.max_ticket)) if payload.max_ticket else None,
        )
        db.commit()
        return _svc.get_product_detail(db, product.id)
    except OfferError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/admin/pools")
def admin_pool_list(db: Session = Depends(get_db)):
    """Admin custody: list all exclusive offer pools."""
    return {"pools": _svc.get_admin_pool_list(db)}


@router.get("/admin/pools/{pool_id}")
def admin_pool_detail(pool_id: UUID, db: Session = Depends(get_db)):
    """Admin custody: full detail of a pool — lenders, borrower, audit."""
    try:
        return _svc.get_admin_pool_detail(db, pool_id)
    except OfferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
