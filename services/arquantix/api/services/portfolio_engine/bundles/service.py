"""Bundle Engine v1 — transactional service.

All mutations happen within a single SQLAlchemy session (flushed, not committed).
The caller (router) is responsible for commit/rollback.

Success audit is written inside the transaction.
Failure audit must be written outside the rolled-back transaction (separate session).
"""
import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..assets.models import Asset
from ..instruments.models import Instrument
from ..products.models import ProductDefinition
from ..subscriptions.models import ProductSubscription
from ..templates.models import PortfolioTemplate, TemplateAllocation
from ..hardening.audit_service import AuditService
from .schemas import (
    BundleAllocationDetail,
    BundleAllocationSummary,
    BundleCreate,
    BundleDetailResponse,
    BundleListItem,
    BundleListResponse,
    WEIGHT_TOLERANCE,
)

logger = logging.getLogger(__name__)

BUNDLE_PRODUCT_TYPE = "crypto_bundle"
BUNDLE_PORTFOLIO_TYPE = "bundle_portfolio"


class BundleValidationError(Exception):
    """Raised when payload validation fails before any DB write."""
    pass


class BundleNotFoundError(Exception):
    def __init__(self, bundle_id: UUID):
        self.bundle_id = bundle_id
        super().__init__(f"Bundle {bundle_id} not found")


class BundleHasSubscriptionsError(Exception):
    def __init__(self, bundle_id: UUID, count: int):
        self.bundle_id = bundle_id
        self.count = count
        super().__init__(
            f"Bundle {bundle_id} has {count} subscription(s) and cannot be deleted. "
            f"All subscriptions must be removed before deletion."
        )


class BundleEngineService:

    def create_bundle(
        self,
        db: Session,
        payload: BundleCreate,
        *,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> BundleDetailResponse:
        """Create a complete bundle atomically within the current session.

        Writes product + template + allocations + success audit via flush().
        Does NOT commit — the router must commit on success or rollback on failure.
        """

        # ── 1. Pre-validate product_code uniqueness ──
        existing = (
            db.query(ProductDefinition)
            .filter(ProductDefinition.product_code == payload.product_code)
            .first()
        )
        if existing is not None:
            raise BundleValidationError(
                f"Product code '{payload.product_code}' already exists"
            )

        # ── 2. Validate available_rebalance_frequencies ──
        # (already done by Pydantic schema, but belt-and-suspenders)

        # ── 3. Validate allocations ──
        instrument_ids = [a.instrument_id for a in payload.allocations]

        # 3a. No duplicate instruments (already in schema, double-check)
        if len(instrument_ids) != len(set(instrument_ids)):
            raise BundleValidationError("Duplicate instrument_id in allocations")

        # 3b. All instruments exist
        instruments = (
            db.query(Instrument)
            .filter(Instrument.id.in_(instrument_ids))
            .all()
        )
        found_ids = {i.id for i in instruments}
        missing = set(instrument_ids) - found_ids
        if missing:
            raise BundleValidationError(
                f"Instruments not found: {[str(m) for m in missing]}"
            )

        # 3c. All instruments must be spot
        non_spot = [i for i in instruments if i.instrument_type != "spot"]
        if non_spot:
            codes = [i.code for i in non_spot]
            raise BundleValidationError(
                f"All instruments must be spot. Non-spot found: {codes}"
            )

        # 3c-bis. All target assets must be exchangeable
        from services.exchange.assets import SUPPORTED_ASSETS as _EXCHANGE_SUPPORTED
        _asset_ids = {i.asset_id for i in instruments}
        _assets = db.query(Asset).filter(Asset.id.in_(_asset_ids)).all()
        _asset_symbols = {a.symbol.upper() for a in _assets}
        _non_exchangeable = _asset_symbols - _EXCHANGE_SUPPORTED
        if _non_exchangeable:
            raise BundleValidationError(
                f"All target assets must be exchangeable. "
                f"Unsupported by Exchange Engine: {sorted(_non_exchangeable)}"
            )

        # 3d. Weights valid (individual bounds already in schema)
        total_weight = sum(a.target_weight for a in payload.allocations)
        if abs(total_weight - Decimal("1")) > WEIGHT_TOLERANCE:
            raise BundleValidationError(
                f"Sum of target_weight must be 1.0 ± {WEIGHT_TOLERANCE} "
                f"(got {total_weight})"
            )

        # Build lookup maps
        instrument_map = {i.id: i for i in instruments}
        asset_ids = {i.asset_id for i in instruments}
        assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
        asset_map = {a.id: a for a in assets}

        # ── 4. Create ProductDefinition (draft) ──
        product_metadata = dict(payload.metadata)
        product_metadata["available_rebalance_frequencies"] = (
            payload.available_rebalance_frequencies
        )
        product_metadata.setdefault("short_description", payload.description or payload.name)
        product_metadata["entry_asset_default"] = payload.entry_asset_default
        product_metadata["entry_assets_allowed"] = payload.entry_assets_allowed

        product = ProductDefinition(
            product_code=payload.product_code,
            name=payload.name,
            description=payload.description or f"Bundle: {payload.name}",
            product_type=BUNDLE_PRODUCT_TYPE,
            risk_label=payload.risk_label,
            base_currency=payload.base_currency,
            is_public=False,
            status="draft",
            metadata_=product_metadata,
        )
        db.add(product)
        db.flush()

        # ── 5. Create exactly one PortfolioTemplate ──
        template_code = f"{payload.product_code}_DEFAULT"
        template = PortfolioTemplate(
            product_id=product.id,
            template_code=template_code,
            provisioned_portfolio_type=BUNDLE_PORTFOLIO_TYPE,
            name=f"{payload.name} — Default Template",
            description=payload.description,
            base_currency=payload.base_currency,
            risk_profile=payload.risk_label,
            metadata_={},
        )
        db.add(template)
        db.flush()

        # ── 6. Create all TemplateAllocations ──
        allocation_rows: list[TemplateAllocation] = []
        for alloc_payload in payload.allocations:
            alloc = TemplateAllocation(
                template_id=template.id,
                instrument_id=alloc_payload.instrument_id,
                target_weight=alloc_payload.target_weight,
                min_weight=alloc_payload.min_weight,
                max_weight=alloc_payload.max_weight,
                allocation_priority=alloc_payload.allocation_priority,
            )
            db.add(alloc)
            allocation_rows.append(alloc)
        db.flush()

        # ── 7. Activate product ──
        product.status = "active"
        product.is_public = payload.is_public
        db.flush()

        # ── 8. Success audit (inside transaction — will be committed with data) ──
        allocation_summary = []
        for alloc_payload in payload.allocations:
            instr = instrument_map[alloc_payload.instrument_id]
            asset = asset_map.get(instr.asset_id)
            allocation_summary.append({
                "instrument_id": str(alloc_payload.instrument_id),
                "instrument_code": instr.code,
                "asset_symbol": asset.symbol if asset else "?",
                "target_weight": str(alloc_payload.target_weight),
            })

        AuditService.log_success(
            db,
            entity_type="bundle",
            entity_id=str(product.id),
            action="bundle_created",
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=request_id,
            metadata={
                "product_id": str(product.id),
                "product_code": payload.product_code,
                "template_id": str(template.id),
                "template_code": template_code,
                "allocations_count": len(payload.allocations),
                "allocation_summary": allocation_summary,
                "available_rebalance_frequencies": payload.available_rebalance_frequencies,
            },
        )

        # ── 9. Build response ──
        alloc_details: list[BundleAllocationDetail] = []
        for row, alloc_payload in zip(allocation_rows, payload.allocations):
            instr = instrument_map[alloc_payload.instrument_id]
            asset = asset_map.get(instr.asset_id)
            alloc_details.append(BundleAllocationDetail(
                id=row.id,
                instrument_id=instr.id,
                instrument_code=instr.code,
                instrument_name=instr.name,
                asset_symbol=asset.symbol if asset else "?",
                target_weight=row.target_weight,
                min_weight=row.min_weight,
                max_weight=row.max_weight,
                allocation_priority=row.allocation_priority,
            ))

        return BundleDetailResponse(
            id=product.id,
            product_code=product.product_code,
            name=product.name,
            description=product.description,
            product_type=product.product_type,
            risk_label=product.risk_label,
            base_currency=product.base_currency,
            is_public=product.is_public,
            status=product.status,
            template_id=template.id,
            template_code=template.template_code,
            allocations=alloc_details,
            available_rebalance_frequencies=payload.available_rebalance_frequencies,
            metadata=product_metadata,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    def list_bundles(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> BundleListResponse:
        """List bundles filtered explicitly by product_type."""
        query = (
            db.query(ProductDefinition)
            .filter(ProductDefinition.product_type == BUNDLE_PRODUCT_TYPE)
        )
        total = query.count()
        products = (
            query.order_by(ProductDefinition.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        items: list[BundleListItem] = []
        for p in products:
            template = (
                db.query(PortfolioTemplate)
                .filter(PortfolioTemplate.product_id == p.id)
                .first()
            )
            alloc_summary: list[BundleAllocationSummary] = []
            allocations_count = 0

            if template is not None:
                rows = (
                    db.query(TemplateAllocation, Instrument, Asset)
                    .join(Instrument, TemplateAllocation.instrument_id == Instrument.id)
                    .join(Asset, Instrument.asset_id == Asset.id)
                    .filter(TemplateAllocation.template_id == template.id)
                    .order_by(TemplateAllocation.target_weight.desc())
                    .all()
                )
                allocations_count = len(rows)
                alloc_summary = [
                    BundleAllocationSummary(
                        instrument_id=ta.instrument_id,
                        instrument_code=instr.code,
                        asset_symbol=asset.symbol,
                        target_weight=ta.target_weight,
                    )
                    for ta, instr, asset in rows
                ]

            meta = p.metadata_ or {}
            freqs = meta.get("available_rebalance_frequencies", [])

            items.append(BundleListItem(
                id=p.id,
                product_code=p.product_code,
                name=p.name,
                status=p.status,
                is_public=p.is_public,
                product_type=p.product_type,
                template_id=template.id if template else None,
                allocations_count=allocations_count,
                allocation_summary=alloc_summary,
                available_rebalance_frequencies=freqs,
            ))

        return BundleListResponse(items=items, total=total)

    def get_bundle(self, db: Session, bundle_id: UUID) -> BundleDetailResponse:
        """Get a single bundle by product ID, with full detail."""
        product = (
            db.query(ProductDefinition)
            .filter(
                ProductDefinition.id == bundle_id,
                ProductDefinition.product_type == BUNDLE_PRODUCT_TYPE,
            )
            .first()
        )
        if product is None:
            raise BundleNotFoundError(bundle_id)

        template = (
            db.query(PortfolioTemplate)
            .filter(PortfolioTemplate.product_id == product.id)
            .first()
        )
        if template is None:
            raise BundleNotFoundError(bundle_id)

        rows = (
            db.query(TemplateAllocation, Instrument, Asset)
            .join(Instrument, TemplateAllocation.instrument_id == Instrument.id)
            .join(Asset, Instrument.asset_id == Asset.id)
            .filter(TemplateAllocation.template_id == template.id)
            .order_by(TemplateAllocation.target_weight.desc())
            .all()
        )

        alloc_details = [
            BundleAllocationDetail(
                id=ta.id,
                instrument_id=ta.instrument_id,
                instrument_code=instr.code,
                instrument_name=instr.name,
                asset_symbol=asset.symbol,
                target_weight=ta.target_weight,
                min_weight=ta.min_weight,
                max_weight=ta.max_weight,
                allocation_priority=ta.allocation_priority,
            )
            for ta, instr, asset in rows
        ]

        meta = product.metadata_ or {}
        freqs = meta.get("available_rebalance_frequencies", [])

        return BundleDetailResponse(
            id=product.id,
            product_code=product.product_code,
            name=product.name,
            description=product.description,
            product_type=product.product_type,
            risk_label=product.risk_label,
            base_currency=product.base_currency,
            is_public=product.is_public,
            status=product.status,
            template_id=template.id,
            template_code=template.template_code,
            allocations=alloc_details,
            available_rebalance_frequencies=freqs,
            metadata=meta,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    def set_visibility(
        self,
        db: Session,
        bundle_id: UUID,
        *,
        is_public: bool,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> dict:
        """Set bundle visibility (publish / unpublish).

        Updates ProductDefinition.is_public. Does NOT commit.
        Writes audit event inside the transaction.
        """
        product = (
            db.query(ProductDefinition)
            .filter(
                ProductDefinition.id == bundle_id,
                ProductDefinition.product_type == BUNDLE_PRODUCT_TYPE,
            )
            .first()
        )
        if product is None:
            raise BundleNotFoundError(bundle_id)

        previous_visibility = product.is_public
        product.is_public = is_public
        db.flush()

        action = "bundle_published" if is_public else "bundle_unpublished"
        AuditService.log_success(
            db,
            entity_type="bundle",
            entity_id=str(bundle_id),
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=request_id,
            metadata={
                "product_id": str(bundle_id),
                "product_code": product.product_code,
                "previous_is_public": previous_visibility,
                "new_is_public": is_public,
            },
        )

        return {
            "id": str(product.id),
            "product_code": product.product_code,
            "is_public": product.is_public,
            "action": action,
        }

    def delete_bundle(
        self,
        db: Session,
        bundle_id: UUID,
        *,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> dict:
        """Delete a bundle if no active subscriptions exist.

        Deletes: TemplateAllocations → PortfolioTemplate → ProductDefinition.
        Does NOT commit — the router must commit on success or rollback on failure.
        """
        product = (
            db.query(ProductDefinition)
            .filter(
                ProductDefinition.id == bundle_id,
                ProductDefinition.product_type == BUNDLE_PRODUCT_TYPE,
            )
            .first()
        )
        if product is None:
            raise BundleNotFoundError(bundle_id)

        total_subs = (
            db.query(ProductSubscription)
            .filter(ProductSubscription.product_id == bundle_id)
            .count()
        )
        if total_subs > 0:
            raise BundleHasSubscriptionsError(bundle_id, total_subs)

        product_code = product.product_code
        product_name = product.name

        template = (
            db.query(PortfolioTemplate)
            .filter(PortfolioTemplate.product_id == product.id)
            .first()
        )

        if template is not None:
            db.query(TemplateAllocation).filter(
                TemplateAllocation.template_id == template.id
            ).delete(synchronize_session="fetch")
            db.delete(template)

        db.delete(product)
        db.flush()

        AuditService.log_success(
            db,
            entity_type="bundle",
            entity_id=str(bundle_id),
            action="bundle_deleted",
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=request_id,
            metadata={
                "product_id": str(bundle_id),
                "product_code": product_code,
                "product_name": product_name,
            },
        )

        return {
            "deleted": True,
            "product_id": str(bundle_id),
            "product_code": product_code,
        }
