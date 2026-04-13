"""Product catalog endpoint — mounted at /product-catalog to avoid conflict with /products/{product_id}."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from .catalog import CatalogService, ProductCatalogResponse

router = APIRouter()
_catalog = CatalogService()


@router.get("", response_model=ProductCatalogResponse)
def get_product_catalog(
    product_type: Optional[str] = Query(None, description="Filter by product_type"),
    db: Session = Depends(get_db),
):
    """Public catalog for Flutter app — active, public products with allocation summaries."""
    items = _catalog.get_public_catalog(db, product_type=product_type)
    return ProductCatalogResponse(items=items, total=len(items))
