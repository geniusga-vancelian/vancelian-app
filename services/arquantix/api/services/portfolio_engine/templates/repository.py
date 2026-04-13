"""Repository layer for pe_portfolio_templates and pe_template_allocations
(Portfolio Engine — Templates module)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import PortfolioTemplate, TemplateAllocation


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DuplicateTemplateCodeError(Exception):
    """Raised when attempting to create a template with a code that already exists."""

    def __init__(self, template_code: str):
        self.template_code = template_code
        super().__init__(f"Template with code '{template_code}' already exists")


class DuplicateTemplateAllocationError(Exception):
    """Raised when an allocation for this instrument already exists in the template."""
    pass


# ---------------------------------------------------------------------------
# PortfolioTemplate repository
# ---------------------------------------------------------------------------

class PortfolioTemplateRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> PortfolioTemplate:
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        template = PortfolioTemplate(**data)
        db.add(template)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise DuplicateTemplateCodeError(data.get("template_code", ""))
        return template

    @staticmethod
    def get_by_id(db: Session, template_id: UUID) -> Optional[PortfolioTemplate]:
        return db.query(PortfolioTemplate).filter(PortfolioTemplate.id == template_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        product_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[PortfolioTemplate], int]:
        query = db.query(PortfolioTemplate)
        if product_id is not None:
            query = query.filter(PortfolioTemplate.product_id == product_id)
        total = query.count()
        items = query.order_by(PortfolioTemplate.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, template: PortfolioTemplate, *, data: dict) -> PortfolioTemplate:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(template, col_name, value)
        db.flush()
        return template


# ---------------------------------------------------------------------------
# TemplateAllocation repository
# ---------------------------------------------------------------------------

class TemplateAllocationRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> TemplateAllocation:
        allocation = TemplateAllocation(**data)
        db.add(allocation)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            if "uq_pe_template_allocations_" in str(exc.orig):
                raise DuplicateTemplateAllocationError(
                    "An allocation for this instrument already exists in the template"
                ) from exc
            raise
        return allocation

    @staticmethod
    def get_by_id(db: Session, allocation_id: UUID) -> Optional[TemplateAllocation]:
        return db.query(TemplateAllocation).filter(TemplateAllocation.id == allocation_id).first()

    @staticmethod
    def list_by_template(
        db: Session,
        template_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TemplateAllocation], int]:
        query = db.query(TemplateAllocation).filter(TemplateAllocation.template_id == template_id)
        total = query.count()
        items = query.order_by(TemplateAllocation.allocation_priority.asc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, allocation: TemplateAllocation, *, data: dict) -> TemplateAllocation:
        for key, value in data.items():
            setattr(allocation, key, value)
        db.flush()
        return allocation

    @staticmethod
    def delete(db: Session, allocation: TemplateAllocation) -> None:
        db.delete(allocation)
        db.flush()
