"""Products API endpoints (Portfolio Engine — catalog layer)."""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from .catalog import CatalogService, ProductCatalogResponse, ProductDetailResponse
from .chart_history import get_product_chart_history
from .repository import DuplicateProductCodeError
from .schemas import ProductCreate, ProductListResponse, ProductRead, ProductUpdate
from .service import ProductNotFoundError, ProductService

router = APIRouter()

_service = ProductService()
_catalog = CatalogService()


@router.get("", response_model=ProductListResponse)
def list_products(
    product_type: Optional[str] = Query(None, description="Filter by product_type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    is_public: Optional[bool] = Query(None, description="Filter by visibility"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    items, total = _service.list_products(
        db,
        product_type=product_type,
        status=status_filter,
        is_public=is_public,
        skip=skip,
        limit=limit,
    )
    return ProductListResponse(
        items=[ProductRead.model_validate(p) for p in items],
        total=total,
    )


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
):
    try:
        product = _service.create_product(db, payload)
        db.commit()
        db.refresh(product)
        return ProductRead.model_validate(product)
    except DuplicateProductCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        product = _service.get_product(db, product_id)
        return ProductRead.model_validate(product)
    except ProductNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


@router.get("/{product_id}/detail", response_model=ProductDetailResponse)
def get_product_detail(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    """Admin enriched view — product + template + allocations summary."""
    detail = _catalog.get_product_detail(db, product_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return detail


@router.get("/{product_id}/chart-history")
def get_product_chart(
    product_id: UUID,
    period: str = Query("1a", description="UI period: 1j, 1s, 1m, 1a, 5a"),
    db: Session = Depends(get_db),
):
    """Weighted performance chart for a bundle product.

    Computes a composite index (base=100) from each constituent asset's
    price history, weighted by the template allocation.
    Public endpoint for Flutter app.
    """
    result = get_product_chart_history(db, product_id=product_id, period=period)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or no chart data available",
        )
    return result


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
):
    try:
        product = _service.update_product(db, product_id, payload)
        db.commit()
        db.refresh(product)
        return ProductRead.model_validate(product)
    except ProductNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    except DuplicateProductCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
