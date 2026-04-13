"""Exclusive Offer Lending Product Service — Phase 2A.10.

Product layer on top of lending pools that enables:
  - Single-borrower, multi-lender "exclusive offer" pools
  - Fundraising lifecycle (draft → fundraising → funded → active → repaid → closed)
  - Subscription with min/max ticket enforcement + cap
  - Automatic borrow activation when target is reached

This service delegates all financial operations to the existing
PoolLendingService and RepaymentEngine — it never touches atoms or ledger directly.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .offer_models import LendingPoolProduct
from .pool_models import LendingPool, PoolSupplyCommitment, PoolBorrowPosition
from .pool_service import PoolLendingService

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_BPS_TO_PCT = Decimal("100")
_ROUND = Decimal("0.01")

_VALID_STATUSES = {"draft", "fundraising", "funded", "active", "repaid", "closed"}


class OfferError(Exception):
    pass

class OfferNotFoundError(OfferError):
    pass

class InvalidOfferStatusError(OfferError):
    pass

class SubscriptionError(OfferError):
    pass

class BorrowerRestrictionError(OfferError):
    pass


class OfferService:

    _pool_svc = PoolLendingService()

    @staticmethod
    def _resolve_borrower_pe_client_id(db: Session, borrower_ref: UUID) -> UUID:
        """Retourne l’identifiant **portfolio** ``pe_clients.id`` (FK prêt / offres).

        Côté produit, l’admin parle de **Customer** (Customer 360) : c’est ``persons.id``.
        Les tables lending référencent toujours le **client portefeuille** ``pe_clients``
        (comptes, custody, positions) — ce n’est pas un second « type » de client :
        une Personne liée a une ligne ``pe_clients`` (souvent 1:1 via ``person_id`` /
        ``persons.client_id``).

        Références acceptées (dans l’ordre) :

        1. UUID déjà égal à ``pe_clients.id`` ;
        2. ``persons.id`` avec ``pe_clients.person_id`` pointant dessus ;
        3. ``persons.id`` avec ``persons.client_id`` renseigné (lien inverse explicite).
        """
        from database import Person
        from services.portfolio_engine.clients.models import Client

        client = db.query(Client).filter(Client.id == borrower_ref).first()
        if client:
            return client.id
        client = db.query(Client).filter(Client.person_id == borrower_ref).first()
        if client:
            return client.id
        person = db.query(Person).filter(Person.id == borrower_ref).first()
        if person and person.client_id:
            linked = db.query(Client).filter(Client.id == person.client_id).first()
            if linked:
                return linked.id
        raise OfferError(
            f"Emprunteur introuvable pour {borrower_ref} : pas de client portefeuille (pe_clients) "
            f"lié à cette référence. Utilisez l’UUID **Customer** (personne, fiche Customer 360) "
            f"d’un profil qui a déjà un client portfolio, ou directement ``pe_clients.id``."
        )

    # ── CREATE ────────────────────────────────────────────────────

    def create_product(
        self,
        db: Session,
        *,
        title: str,
        asset: str,
        borrower_client_id: UUID,
        target_size: Decimal,
        supply_apr_bps: Decimal = Decimal("300"),
        borrow_apr_bps: Decimal = Decimal("500"),
        min_ticket: Optional[Decimal] = None,
        max_ticket: Optional[Decimal] = None,
        description: Optional[str] = None,
        use_of_funds: Optional[str] = None,
        start_date: Optional[date] = None,
        maturity_date: Optional[date] = None,
        project_id: Optional[str] = None,
        packaged_product_id: Optional[UUID] = None,
        entry_asset_default: Optional[str] = None,
        entry_assets_allowed: Optional[list[str]] = None,
    ) -> LendingPoolProduct:
        """Create a new exclusive offer product with its dedicated pool."""
        if target_size <= 0:
            raise OfferError("target_size must be positive")
        if min_ticket and max_ticket and min_ticket > max_ticket:
            raise OfferError("min_ticket > max_ticket")
        if project_id and packaged_product_id:
            raise OfferError("Cannot set both project_id and packaged_product_id on a lending product")

        asset = asset.upper()

        pool = LendingPool(
            asset=asset,
            status="active",
            supply_rate_bps=supply_apr_bps,
            borrow_rate_bps=borrow_apr_bps,
        )
        db.add(pool)
        db.flush()

        resolved_entry_default = (entry_asset_default or asset).upper()
        if entry_assets_allowed:
            resolved_entry_allowed = [a.upper() for a in entry_assets_allowed]
        else:
            resolved_entry_allowed = self._all_investable_assets(db)
        if resolved_entry_default not in resolved_entry_allowed:
            resolved_entry_allowed.insert(0, resolved_entry_default)

        product = LendingPoolProduct(
            lending_pool_id=pool.id,
            project_id=project_id,
            packaged_product_id=packaged_product_id,
            product_type="exclusive_offer",
            title=title,
            description=description,
            borrower_client_id=borrower_client_id,
            asset=asset,
            target_size=target_size,
            current_raised=_ZERO,
            min_ticket=min_ticket,
            max_ticket=max_ticket,
            supply_apr_bps=supply_apr_bps,
            borrow_apr_bps=borrow_apr_bps,
            use_of_funds=use_of_funds,
            entry_asset_default=resolved_entry_default,
            entry_assets_allowed=resolved_entry_allowed,
            start_date=start_date,
            maturity_date=maturity_date,
            status="draft",
        )
        db.add(product)
        db.flush()

        logger.info(
            "Created product %s '%s' for %s — target %s %s, borrower %s",
            product.id, title, asset, target_size, asset, borrower_client_id,
        )
        return product

    # ── LIFECYCLE TRANSITIONS ────────────────────────────────────

    def open_fundraising(self, db: Session, product_id: UUID) -> LendingPoolProduct:
        """Transition: draft → fundraising."""
        product = self._get_product(db, product_id)
        if product.status != "draft":
            raise InvalidOfferStatusError(
                f"Cannot open fundraising from status '{product.status}' (expected 'draft')"
            )
        product.status = "fundraising"
        db.flush()
        logger.info("Product %s → fundraising", product_id)
        return product

    def _transition_to_funded(self, db: Session, product: LendingPoolProduct) -> None:
        """Auto-transition: fundraising → funded when target reached."""
        if product.status != "fundraising":
            return
        raised = Decimal(str(product.current_raised))
        target = Decimal(str(product.target_size))
        if raised >= target:
            product.status = "funded"
            db.flush()
            logger.info("Product %s → funded (raised %s >= target %s)", product.id, raised, target)

    def activate_product(self, db: Session, product_id: UUID) -> dict:
        """Transition: funded → active — triggers automatic borrow for the borrower.

        The entire raised amount is borrowed by the designated borrower_client_id
        using the existing borrow_from_pool() mechanism.
        """
        product = self._get_product(db, product_id)
        if product.status not in ("funded", "fundraising"):
            raise InvalidOfferStatusError(
                f"Cannot activate from status '{product.status}' (expected 'funded' or 'fundraising')"
            )

        raised = Decimal(str(product.current_raised))
        target = Decimal(str(product.target_size))
        if raised < target and product.status == "fundraising":
            raise InvalidOfferStatusError(
                f"Cannot activate: raised {raised} < target {target}"
            )

        if product.status == "fundraising":
            product.status = "funded"
            db.flush()

        pool = db.query(LendingPool).filter(LendingPool.id == product.lending_pool_id).first()

        borrow_result = self._pool_svc.borrow_from_pool(
            db,
            borrower_client_id=product.borrower_client_id,
            asset=product.asset,
            amount=raised,
        )

        product.status = "active"
        if product.start_date is None:
            product.start_date = date.today()
        db.flush()

        logger.info("Product %s → active, borrowed %s %s", product_id, raised, product.asset)
        return {
            "product_id": str(product.id),
            "status": product.status,
            "borrow_result": borrow_result,
        }

    def mark_repaid(self, db: Session, product_id: UUID) -> LendingPoolProduct:
        """Transition: active → repaid (called after repayment engine completes)."""
        product = self._get_product(db, product_id)
        if product.status != "active":
            raise InvalidOfferStatusError(f"Cannot mark repaid from '{product.status}'")
        product.status = "repaid"
        db.flush()
        logger.info("Product %s → repaid", product_id)
        return product

    def close_product(self, db: Session, product_id: UUID) -> LendingPoolProduct:
        """Transition: repaid → closed."""
        product = self._get_product(db, product_id)
        if product.status != "repaid":
            raise InvalidOfferStatusError(f"Cannot close from '{product.status}'")
        product.status = "closed"
        db.flush()
        logger.info("Product %s → closed", product_id)
        return product

    # ── SUBSCRIBE (LENDER) ───────────────────────────────────────

    def subscribe(
        self,
        db: Session,
        *,
        product_id: UUID,
        lender_client_id: UUID,
        amount: Decimal,
    ) -> PoolSupplyCommitment:
        """Lender subscribes to an exclusive offer.

        Validates:
          - Product status == fundraising
          - min_ticket <= amount <= max_ticket
          - current_raised + amount <= target_size
          - Lender != borrower

        Then delegates to pool_supply commitment.
        """
        from services.compliance.eligibility_service import EligibilityService
        EligibilityService.require_eligible_by_client_id(db, lender_client_id)

        product = self._get_product(db, product_id)

        if product.status != "fundraising":
            raise SubscriptionError(
                f"Product not open for subscription (status={product.status})"
            )

        if lender_client_id == product.borrower_client_id:
            raise SubscriptionError("Borrower cannot subscribe to their own offer")

        if amount <= 0:
            raise SubscriptionError("Amount must be positive")

        # Min/max ticket
        if product.min_ticket and amount < Decimal(str(product.min_ticket)):
            raise SubscriptionError(
                f"Amount {amount} below minimum ticket {product.min_ticket}"
            )
        if product.max_ticket and amount > Decimal(str(product.max_ticket)):
            raise SubscriptionError(
                f"Amount {amount} exceeds maximum ticket {product.max_ticket}"
            )

        # Cap check
        raised = Decimal(str(product.current_raised))
        target = Decimal(str(product.target_size))
        remaining = target - raised
        if amount > remaining:
            raise SubscriptionError(
                f"Amount {amount} exceeds remaining capacity {remaining}"
            )

        commitment = self._pool_svc.create_supply_commitment(
            db,
            client_id=lender_client_id,
            asset=product.asset,
            amount=amount,
            pool_id=product.lending_pool_id,
        )

        # Update raised amount
        product.current_raised = raised + amount
        db.flush()

        # Auto-transition to funded if target reached
        self._transition_to_funded(db, product)

        logger.info(
            "Subscription %s: %s %s by lender %s to product %s (raised: %s/%s)",
            commitment.id, amount, product.asset, lender_client_id,
            product_id, product.current_raised, product.target_size,
        )
        return commitment

    # ── BORROW GUARD ─────────────────────────────────────────────

    @staticmethod
    def check_borrow_allowed(db: Session, pool_id: UUID, borrower_client_id: UUID) -> None:
        """Enforce single-borrower restriction for product-linked pools.

        Called from borrow_from_pool to reject unauthorized borrowers.
        Returns silently if pool has no product (regular pool).
        """
        product = db.query(LendingPoolProduct).filter(
            LendingPoolProduct.lending_pool_id == pool_id,
        ).first()
        if product is None:
            return
        if borrower_client_id != product.borrower_client_id:
            raise BorrowerRestrictionError(
                f"Pool is linked to exclusive offer '{product.title}' — "
                f"only borrower {product.borrower_client_id} is allowed"
            )

    # ── QUERIES ──────────────────────────────────────────────────

    def list_products(
        self,
        db: Session,
        *,
        status: Optional[str] = None,
        asset: Optional[str] = None,
    ) -> list[dict]:
        """List all products (optionally filtered)."""
        q = db.query(LendingPoolProduct)
        if status:
            q = q.filter(LendingPoolProduct.status == status)
        if asset:
            q = q.filter(LendingPoolProduct.asset == asset.upper())
        products = q.order_by(LendingPoolProduct.created_at.desc()).all()

        return [self._product_to_dict(db, p) for p in products]

    def get_product_detail(self, db: Session, product_id: UUID) -> dict:
        product = self._get_product(db, product_id)
        return self._product_to_dict(db, product)

    def get_user_subscriptions(self, db: Session, client_id: UUID) -> list[dict]:
        """All offers a lender has subscribed to, with their position details."""
        from .product_surface import _get_price_eur, get_fx_rate, _bps_to_pct
        from services.market_data.fx import usdt_to_eur

        commitments = db.query(PoolSupplyCommitment).filter(
            PoolSupplyCommitment.client_id == client_id,
        ).all()

        pool_ids = {c.pool_id for c in commitments}
        products_by_pool = {}
        for pid in pool_ids:
            p = db.query(LendingPoolProduct).filter(
                LendingPoolProduct.lending_pool_id == pid,
            ).first()
            if p:
                products_by_pool[pid] = p

        if not products_by_pool:
            return []

        eurusdt_rate = get_fx_rate(db)
        results = []
        for c in commitments:
            product = products_by_pool.get(c.pool_id)
            if not product:
                continue

            committed = Decimal(str(c.amount))
            _, price_eur = _get_price_eur(db, product.asset, eurusdt_rate)
            value_eur = float((committed * price_eur).quantize(_ROUND, rounding=ROUND_HALF_UP))

            results.append({
                "product_id": str(product.id),
                "title": product.title,
                "asset": product.asset,
                "committed": float(committed),
                "status": product.status,
                "supply_apr": _bps_to_pct(Decimal(str(product.supply_apr_bps))),
                "value_eur": value_eur,
                "commitment_status": c.status,
            })

        return results

    # ── PROJECT PROVISIONING (Phase 2A.11.5) ───────────────────

    def create_from_project(
        self,
        db: Session,
        *,
        project_id: str,
        borrower_client_id: UUID,
        asset: str,
        target_size: Decimal,
        title: str = "",
        supply_apr_bps: Decimal = Decimal("300"),
        borrow_apr_bps: Decimal = Decimal("500"),
        min_ticket: Optional[Decimal] = None,
        max_ticket: Optional[Decimal] = None,
    ) -> LendingPoolProduct:
        """One-click provisioning: create pool + product + link from a CMS project."""
        existing = db.query(LendingPoolProduct).filter(
            LendingPoolProduct.project_id == project_id,
        ).first()
        if existing:
            raise OfferError(f"Project {project_id} already has a lending product ({existing.id})")

        borrower_pe_id = self._resolve_borrower_pe_client_id(db, borrower_client_id)

        try:
            product = self.create_product(
                db,
                title=title or f"Offer-{project_id}",
                asset=asset,
                borrower_client_id=borrower_pe_id,
                target_size=target_size,
                supply_apr_bps=supply_apr_bps,
                borrow_apr_bps=borrow_apr_bps,
                min_ticket=min_ticket,
                max_ticket=max_ticket,
                project_id=project_id,
            )
        except Exception as exc:
            db.rollback()
            raise OfferError(f"Failed to create lending product: {exc}")
        logger.info("Created product %s from project %s", product.id, project_id)
        return product

    def _sync_packaged_product_registry_engine(
        self,
        db: Session,
        *,
        packaged_product_id: UUID,
        lending_product_id: Optional[UUID],
    ) -> None:
        """Aligne packaged_products.engine_* avec le lien lending (table Prisma / même DB)."""
        from sqlalchemy import text as sa_text

        if lending_product_id is None:
            db.execute(
                sa_text(
                    """
                    UPDATE packaged_products
                    SET engine_type = NULL,
                        engine_reference_id = NULL,
                        updated_at = now()
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": str(packaged_product_id)},
            )
        else:
            db.execute(
                sa_text(
                    """
                    UPDATE packaged_products
                    SET engine_type = 'LENDING'::"PackagedEngineType",
                        engine_reference_id = :ref,
                        updated_at = now()
                    WHERE id = CAST(:id AS uuid)
                    """
                ),
                {"id": str(packaged_product_id), "ref": str(lending_product_id)},
            )
        db.flush()

    def create_from_packaged_product(
        self,
        db: Session,
        *,
        packaged_product_id: UUID,
        borrower_client_id: UUID,
        asset: str,
        target_size: Decimal,
        title: str = "",
        supply_apr_bps: Decimal = Decimal("300"),
        borrow_apr_bps: Decimal = Decimal("500"),
        min_ticket: Optional[Decimal] = None,
        max_ticket: Optional[Decimal] = None,
    ) -> LendingPoolProduct:
        """Provisioning lending depuis Product Registry (sans project_id). Réutilise create_product."""
        from sqlalchemy import text as sa_text

        row = db.execute(
            sa_text(
                "SELECT product_type::text FROM packaged_products WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(packaged_product_id)},
        ).fetchone()
        if not row:
            raise OfferError(f"Packaged product {packaged_product_id} not found")
        ptype = (row[0] or "").strip()
        if ptype != "EXCLUSIVE_OFFER":
            raise OfferError(
                f"Lending engine requires packaged product type EXCLUSIVE_OFFER (got {ptype})"
            )

        existing = db.query(LendingPoolProduct).filter(
            LendingPoolProduct.packaged_product_id == packaged_product_id,
        ).first()
        if existing:
            raise OfferError(
                f"Packaged product already linked to lending product {existing.id}"
            )

        eng = db.execute(
            sa_text(
                "SELECT engine_reference_id FROM packaged_products WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(packaged_product_id)},
        ).fetchone()
        if eng and eng[0]:
            raise OfferError(
                "Packaged product already has engine_reference_id; clear engine state before creating"
            )

        borrower_pe_id = self._resolve_borrower_pe_client_id(db, borrower_client_id)

        try:
            product = self.create_product(
                db,
                title=title or f"Offer-{str(packaged_product_id)[:8]}",
                asset=asset,
                borrower_client_id=borrower_pe_id,
                target_size=target_size,
                supply_apr_bps=supply_apr_bps,
                borrow_apr_bps=borrow_apr_bps,
                min_ticket=min_ticket,
                max_ticket=max_ticket,
                project_id=None,
                packaged_product_id=packaged_product_id,
            )
            self._sync_packaged_product_registry_engine(
                db,
                packaged_product_id=packaged_product_id,
                lending_product_id=product.id,
            )
        except OfferError:
            raise
        except Exception as exc:
            db.rollback()
            raise OfferError(f"Failed to create lending product: {exc}") from exc

        logger.info(
            "Created lending product %s from packaged product %s",
            product.id,
            packaged_product_id,
        )
        return product

    # ── ADMIN CUSTODY VIEWS (Phase 2A.11.5) ──────────────────

    def get_admin_pool_list(self, db: Session) -> list[dict]:
        """All exclusive offer pools for admin custody view."""
        products = db.query(LendingPoolProduct).order_by(
            LendingPoolProduct.created_at.desc()
        ).all()

        result = []
        for p in products:
            pool = db.query(LendingPool).filter(LendingPool.id == p.lending_pool_id).first()
            investors = self._get_investors_count(db, p.lending_pool_id)
            raised = Decimal(str(p.current_raised))
            target = Decimal(str(p.target_size))
            progress = float((raised / target * Decimal("100")).quantize(_ROUND)) if target > 0 else 0.0
            utilization = float(pool.utilization_rate) if pool else 0.0

            result.append({
                "product_id": str(p.id),
                "pool_id": str(p.lending_pool_id),
                "project_id": p.project_id,
                "title": p.title,
                "asset": p.asset,
                "borrower_client_id": str(p.borrower_client_id),
                "raised": float(raised),
                "target": float(target),
                "progress_pct": progress,
                "investors_count": investors,
                "utilization": utilization,
                "supply_apr": float((Decimal(str(p.supply_apr_bps)) / _BPS_TO_PCT).quantize(_ROUND)),
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })
        return result

    def get_admin_pool_detail(self, db: Session, pool_id: UUID) -> dict:
        """Full admin detail view for a single pool — lenders, borrower, audit."""
        from .pool_models import PoolAllocation
        from .interest_models import LenderInterestAccrual, BorrowerInterestAccrual

        pool = db.query(LendingPool).filter(LendingPool.id == pool_id).first()
        if not pool:
            raise OfferNotFoundError(f"Pool {pool_id} not found")

        product = db.query(LendingPoolProduct).filter(
            LendingPoolProduct.lending_pool_id == pool_id,
        ).first()

        # Pool overview
        overview = {
            "pool_id": str(pool.id),
            "asset": pool.asset,
            "total_committed": float(pool.total_committed),
            "total_borrowed": float(pool.total_borrowed),
            "available_liquidity": float(Decimal(str(pool.total_committed)) - Decimal(str(pool.total_borrowed))),
            "utilization_rate": float(pool.utilization_rate),
            "supply_rate_bps": float(pool.supply_rate_bps),
            "borrow_rate_bps": float(pool.borrow_rate_bps),
        }

        # Product info
        product_info = None
        if product:
            product_info = self._product_to_dict(db, product)

        # Lenders
        commitments = db.query(PoolSupplyCommitment).filter(
            PoolSupplyCommitment.pool_id == pool_id,
        ).order_by(PoolSupplyCommitment.created_at).all()

        lenders = []
        for c in commitments:
            allocated = db.query(
                PoolAllocation
            ).filter(
                PoolAllocation.supply_commitment_id == c.id,
            ).all()
            total_allocated = sum(Decimal(str(a.amount)) for a in allocated)

            accruals = db.query(LenderInterestAccrual).filter(
                LenderInterestAccrual.client_id == c.client_id,
                LenderInterestAccrual.pool_id == pool_id,
            ).all()
            total_interest = sum(Decimal(str(a.interest_earned)) for a in accruals)

            lenders.append({
                "client_id": str(c.client_id),
                "commitment_id": str(c.id),
                "committed": float(c.amount),
                "allocated": float(total_allocated),
                "available": float(c.available_amount),
                "accrued_interest": float(total_interest),
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })

        # Borrower
        borrow_positions = db.query(PoolBorrowPosition).filter(
            PoolBorrowPosition.pool_id == pool_id,
        ).all()

        borrowers = []
        for bp in borrow_positions:
            accruals = db.query(BorrowerInterestAccrual).filter(
                BorrowerInterestAccrual.client_id == bp.client_id,
                BorrowerInterestAccrual.pool_id == pool_id,
            ).all()
            total_interest_due = sum(Decimal(str(a.interest_due)) for a in accruals)
            borrowed = Decimal(str(bp.borrowed_amount))

            borrowers.append({
                "client_id": str(bp.client_id),
                "borrow_position_id": str(bp.id),
                "borrowed": float(borrowed),
                "accrued_interest_due": float(total_interest_due),
                "total_due": float(borrowed + total_interest_due),
                "status": bp.status,
                "created_at": bp.created_at.isoformat() if bp.created_at else None,
            })

        # Allocations audit
        allocations = db.query(PoolAllocation).filter(
            PoolAllocation.supply_commitment_id.in_([c.id for c in commitments])
        ).order_by(PoolAllocation.created_at).all() if commitments else []

        allocation_audit = [{
            "allocation_id": str(a.id),
            "supply_commitment_id": str(a.supply_commitment_id),
            "borrow_position_id": str(a.borrow_position_id),
            "amount": float(a.amount),
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in allocations]

        return {
            "overview": overview,
            "product": product_info,
            "lenders": lenders,
            "borrowers": borrowers,
            "allocations": allocation_audit,
            "summary": {
                "total_lenders": len(lenders),
                "total_borrowed_positions": len(borrowers),
                "total_allocations": len(allocations),
            },
        }

    # ── PROJECT LINK (Phase 2A.11) ─────────────────────────────

    def link_project(self, db: Session, product_id: UUID, project_id: str) -> LendingPoolProduct:
        """Link a lending product to a CMS project (1-to-1)."""
        product = self._get_product(db, product_id)
        existing = db.query(LendingPoolProduct).filter(
            LendingPoolProduct.project_id == project_id,
        ).first()
        if existing and existing.id != product.id:
            raise OfferError(f"Project {project_id} already linked to product {existing.id}")
        product.project_id = project_id
        db.flush()
        logger.info("Product %s linked to project %s", product_id, project_id)
        return product

    def unlink_project(self, db: Session, product_id: UUID) -> LendingPoolProduct:
        """Remove the CMS project link from a lending product."""
        product = self._get_product(db, product_id)
        product.project_id = None
        db.flush()
        return product

    def get_lending_data_for_projects(self, db: Session) -> dict[str, dict]:
        """Return lending data keyed by project_id for enriching the CMS projects API.

        Returns { project_id: { apy, raised, target, progress, investorsCount, ... } }
        """
        products = db.query(LendingPoolProduct).filter(
            LendingPoolProduct.project_id.isnot(None),
            LendingPoolProduct.status != "closed",
        ).all()

        result: dict[str, dict] = {}
        for p in products:
            pid = p.project_id
            if not pid:
                continue
            raised = Decimal(str(p.current_raised))
            target = Decimal(str(p.target_size))
            progress = (
                float((raised / target * Decimal("100")).quantize(_ROUND))
                if target > 0 else 0.0
            )
            investors = self._get_investors_count(db, p.lending_pool_id)

            duration_months = None
            if p.start_date and p.maturity_date:
                delta = p.maturity_date - (p.start_date if p.start_date <= date.today() else date.today())
                duration_months = max(1, round(delta.days / 30))

            entry_default = p.entry_asset_default or p.asset
            entry_allowed = p.entry_assets_allowed or [entry_default]
            result[pid] = {
                "lending_product_id": str(p.id),
                "apy": float((Decimal(str(p.supply_apr_bps)) / _BPS_TO_PCT).quantize(_ROUND)),
                "raised": float(raised),
                "target": float(target),
                "progress": progress,
                "investorsCount": investors,
                "durationMonths": duration_months,
                "asset": p.asset,
                "status": p.status,
                "isInvestable": p.status == "fundraising",
                "min_ticket": float(p.min_ticket) if p.min_ticket else None,
                "max_ticket": float(p.max_ticket) if p.max_ticket else None,
                "entry_asset_default": entry_default,
                "entry_assets_allowed": entry_allowed,
            }
        return result

    @staticmethod
    def _get_investors_count(db: Session, pool_id) -> int:
        """Count distinct lenders who have committed to this pool."""
        from sqlalchemy import func as sa_func
        count = db.query(sa_func.count(PoolSupplyCommitment.client_id.distinct())).filter(
            PoolSupplyCommitment.pool_id == pool_id,
        ).scalar()
        return count or 0

    # ── PRIVATE HELPERS ──────────────────────────────────────────

    @staticmethod
    def _all_investable_assets(db: Session) -> list[str]:
        """Return all assets a client can use to invest (fiat + crypto).

        Reads active instruments from market_data_instruments, extracts the
        base ticker (e.g. BTCUSDT → BTC), and prepends EUR as fiat entry.
        """
        from sqlalchemy import text as sa_text
        rows = db.execute(
            sa_text("SELECT symbol FROM market_data_instruments WHERE is_active = 'true' ORDER BY symbol")
        ).fetchall()
        assets: list[str] = ["EUR"]
        for (symbol,) in rows:
            ticker = symbol.upper().replace("USDT", "")
            if ticker and ticker != "EUR" and ticker not in assets:
                assets.append(ticker)
        return assets

    def _get_product(self, db: Session, product_id: UUID) -> LendingPoolProduct:
        product = db.query(LendingPoolProduct).filter(
            LendingPoolProduct.id == product_id,
        ).first()
        if product is None:
            raise OfferNotFoundError(f"Product {product_id} not found")
        return product

    def _product_to_dict(self, db: Session, p: LendingPoolProduct) -> dict:
        raised = Decimal(str(p.current_raised))
        target = Decimal(str(p.target_size))
        progress = (
            float((raised / target * Decimal("100")).quantize(_ROUND))
            if target > 0 else 0.0
        )
        investors = self._get_investors_count(db, p.lending_pool_id)
        entry_default = p.entry_asset_default or p.asset
        entry_allowed = p.entry_assets_allowed or [entry_default]
        return {
            "product_id": str(p.id),
            "pool_id": str(p.lending_pool_id),
            "project_id": p.project_id,
            "packaged_product_id": str(p.packaged_product_id) if p.packaged_product_id else None,
            "product_type": p.product_type,
            "title": p.title,
            "description": p.description,
            "borrower_client_id": str(p.borrower_client_id),
            "asset": p.asset,
            "target_size": float(target),
            "current_raised": float(raised),
            "remaining": float(target - raised),
            "progress_pct": progress,
            "investors_count": investors,
            "min_ticket": float(p.min_ticket) if p.min_ticket else None,
            "max_ticket": float(p.max_ticket) if p.max_ticket else None,
            "supply_apr": float((Decimal(str(p.supply_apr_bps)) / _BPS_TO_PCT).quantize(_ROUND)),
            "borrow_apr": float((Decimal(str(p.borrow_apr_bps)) / _BPS_TO_PCT).quantize(_ROUND)),
            "entry_asset_default": entry_default,
            "entry_assets_allowed": entry_allowed,
            "use_of_funds": p.use_of_funds,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "maturity_date": p.maturity_date.isoformat() if p.maturity_date else None,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
