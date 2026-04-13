"""SQLAlchemy models for Exclusive Offer Lending Products — Phase 2A.10 / 2A.12.

Table:
  - lending_pool_products: product layer on top of lending_pools
"""
import uuid

from sqlalchemy import Column, ForeignKey, Numeric, String, DateTime, Date, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class PackagedProduct(Base):
    """Table détenue par Prisma (Next.js) — modèle minimal pour que SQLAlchemy résolve la FK
    ``lending_pool_products.packaged_product_id`` vers ``public.packaged_products.id``.
    Ne pas utiliser pour écrire le catalogue depuis l’API Python (source de vérité : web/Prisma).
    """

    __tablename__ = "packaged_products"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)


class LendingPoolProduct(Base):
    __tablename__ = "lending_pool_products"
    __table_args__ = (
        Index("ix_lpp_pool_id", "lending_pool_id"),
        Index("ix_lpp_borrower", "borrower_client_id"),
        Index("ix_lpp_status", "status"),
        Index("ix_lpp_project_id", "project_id"),
        {"schema": "public"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    lending_pool_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.lending_pools.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    # Phase 2A.11: link to CMS project (Prisma projects table)
    project_id = Column(String(30), nullable=True, unique=True)
    # Product Registry (Prisma packaged_products) — optional 1:1, no business logic change
    packaged_product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.packaged_products.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    product_type = Column(String(50), nullable=False, server_default="exclusive_offer")

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    borrower_client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.pe_clients.id", ondelete="RESTRICT"),
        nullable=False,
    )

    asset = Column(String(20), nullable=False)

    target_size = Column(Numeric(30, 10), nullable=False)
    current_raised = Column(Numeric(30, 10), nullable=False, server_default="0")

    min_ticket = Column(Numeric(30, 10), nullable=True)
    max_ticket = Column(Numeric(30, 10), nullable=True)

    supply_apr_bps = Column(Numeric(10, 2), nullable=False, server_default="300")
    borrow_apr_bps = Column(Numeric(10, 2), nullable=False, server_default="500")

    use_of_funds = Column(Text, nullable=True)

    # Phase 2A.12: entry asset configuration (Bundle-style invest flow)
    entry_asset_default = Column(String(20), nullable=True)
    entry_assets_allowed = Column(JSONB, nullable=True)

    start_date = Column(Date, nullable=True)
    maturity_date = Column(Date, nullable=True)

    # draft → fundraising → funded → active → repaid → closed
    status = Column(String(30), nullable=False, server_default="draft")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
