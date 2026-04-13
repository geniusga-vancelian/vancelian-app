"""Product catalog service — provides enriched product views for Flutter app and admin.

Returns product details with template allocations summary and available rebalance frequencies.

Frequency resolution:
  Reads available_rebalance_frequencies from product.metadata_.
  Falls back to DEFAULT_REBALANCE_FREQUENCIES only when metadata key is absent.
"""
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from .models import ProductDefinition
from ..templates.models import PortfolioTemplate, TemplateAllocation
from ..instruments.models import Instrument
from ..assets.models import Asset

DEFAULT_REBALANCE_FREQUENCIES = ["weekly", "monthly", "quarterly"]


def _resolve_frequencies(product: ProductDefinition) -> list[str]:
    """Read available_rebalance_frequencies from product metadata.
    Fallback to DEFAULT_REBALANCE_FREQUENCIES if metadata key is absent."""
    meta = product.metadata_ or {}
    freqs = meta.get("available_rebalance_frequencies")
    if isinstance(freqs, list) and len(freqs) > 0:
        return freqs
    return DEFAULT_REBALANCE_FREQUENCIES


class AllocationSummaryItem(BaseModel):
    instrument_id: UUID
    instrument_code: str
    instrument_name: str
    asset_symbol: str
    target_weight: Decimal


class ProductCatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_code: str
    name: str
    description: Optional[str] = None
    product_type: str
    risk_label: Optional[str] = None
    base_currency: str
    status: str = "active"
    entry_asset_default: Optional[str] = None
    entry_assets_allowed: list[str] = Field(default_factory=list)
    allocations: list[AllocationSummaryItem] = Field(default_factory=list)
    available_rebalance_frequencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductCatalogResponse(BaseModel):
    items: list[ProductCatalogItem]
    total: int


class ProductDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_code: str
    name: str
    description: Optional[str] = None
    product_type: str
    risk_label: Optional[str] = None
    base_currency: str
    is_public: bool
    status: str
    template_id: Optional[UUID] = None
    template_code: Optional[str] = None
    allocations: list[AllocationSummaryItem] = Field(default_factory=list)
    available_rebalance_frequencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CatalogService:

    def get_public_catalog(
        self, db: Session, *, product_type: Optional[str] = None,
    ) -> list[ProductCatalogItem]:
        query = (
            db.query(ProductDefinition)
            .filter(
                ProductDefinition.is_public == True,
                ProductDefinition.status == "active",
            )
        )
        if product_type:
            query = query.filter(ProductDefinition.product_type == product_type)

        products = query.order_by(ProductDefinition.name).all()
        result = []
        for p in products:
            meta = p.metadata_ or {}
            allocations = self._get_allocations_for_product(db, p.id)
            entry_allowed_raw = meta.get("entry_assets_allowed")
            entry_allowed = (
                list(entry_allowed_raw)
                if isinstance(entry_allowed_raw, list)
                else []
            )
            result.append(ProductCatalogItem(
                id=p.id,
                product_code=p.product_code,
                name=p.name,
                description=p.description,
                product_type=p.product_type,
                risk_label=p.risk_label,
                base_currency=p.base_currency,
                status=p.status,
                entry_asset_default=meta.get("entry_asset_default"),
                entry_assets_allowed=entry_allowed,
                allocations=allocations,
                available_rebalance_frequencies=_resolve_frequencies(p),
                metadata=meta,
            ))
        return result

    def get_product_detail(self, db: Session, product_id: UUID) -> Optional[ProductDetailResponse]:
        product = db.query(ProductDefinition).filter(ProductDefinition.id == product_id).first()
        if product is None:
            return None

        template = (
            db.query(PortfolioTemplate)
            .filter(PortfolioTemplate.product_id == product_id)
            .first()
        )
        allocations = self._get_allocations_for_product(db, product_id)

        return ProductDetailResponse(
            id=product.id,
            product_code=product.product_code,
            name=product.name,
            description=product.description,
            product_type=product.product_type,
            risk_label=product.risk_label,
            base_currency=product.base_currency,
            is_public=product.is_public,
            status=product.status,
            template_id=template.id if template else None,
            template_code=template.template_code if template else None,
            allocations=allocations,
            available_rebalance_frequencies=_resolve_frequencies(product),
            metadata=product.metadata_ or {},
        )

    def _get_allocations_for_product(self, db: Session, product_id: UUID) -> list[AllocationSummaryItem]:
        template = (
            db.query(PortfolioTemplate)
            .filter(PortfolioTemplate.product_id == product_id)
            .first()
        )
        if template is None:
            return []

        rows = (
            db.query(TemplateAllocation, Instrument, Asset)
            .join(Instrument, TemplateAllocation.instrument_id == Instrument.id)
            .join(Asset, Instrument.asset_id == Asset.id)
            .filter(TemplateAllocation.template_id == template.id)
            .order_by(TemplateAllocation.target_weight.desc())
            .all()
        )
        return [
            AllocationSummaryItem(
                instrument_id=ta.instrument_id,
                instrument_code=instr.code,
                instrument_name=instr.name,
                asset_symbol=asset.symbol,
                target_weight=ta.target_weight,
            )
            for ta, instr, asset in rows
        ]
