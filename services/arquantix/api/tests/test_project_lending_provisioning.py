"""Tests for Project-driven Lending Provisioning + Admin Pools — Phase 2A.11.5.

Covers:
  A. create_from_project — one-click provisioning
  B. Duplicate rejection
  C. Admin pool list
  D. Admin pool detail (lenders, borrower, allocations)
  E. Edge cases (empty pool, pool with activity)
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text


@pytest.fixture
def db():
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    from database import SessionLocal
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def _create_client(db: Session, email: str):
    row = db.execute(text("SELECT id FROM pe_clients WHERE email = :e"), {"e": email}).first()
    if row:
        class _C: pass
        c = _C(); c.id = row[0]; c.email = email
        return c
    cid = uuid.uuid4()
    db.execute(text(
        "INSERT INTO pe_clients (id, email, status, reference_currency, created_at, updated_at) "
        "VALUES (:id, :e, 'active', 'EUR', now(), now())"
    ), {"id": cid, "e": email})
    db.flush()
    class _C: pass
    c = _C(); c.id = cid; c.email = email
    return c


def _set_balance(db, client_id, asset, amount):
    from services.exchange.repository import CryptoPositionRepository
    pos = CryptoPositionRepository.get_or_create_for_update(db, client_id, asset)
    pos.balance = Decimal(str(amount))
    pos.available_balance = Decimal(str(amount))
    db.flush()


# ---------------------------------------------------------------------------
# A. CREATE FROM PROJECT
# ---------------------------------------------------------------------------

class TestCreateFromProject:

    def test_create_from_project_success(self, db):
        borrower = _create_client(db, "prov_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="USDC",
            target_size=Decimal("100000"),
            title="Solar Project",
            supply_apr_bps=Decimal("800"),
        )

        assert product.project_id == project_id
        assert product.title == "Solar Project"
        assert product.asset == "USDC"
        assert product.status == "draft"
        assert product.borrower_client_id == borrower.id

    def test_create_from_project_auto_title(self, db):
        borrower = _create_client(db, "prov_auto_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="BTC",
            target_size=Decimal("50"),
        )

        assert product.title.startswith("Offer-")
        assert project_id in product.title

    def test_create_from_project_sets_pool(self, db):
        borrower = _create_client(db, "prov_pool_borrower@test.com")
        from services.lending.offer_service import OfferService
        from services.lending.pool_models import LendingPool
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="ETH",
            target_size=Decimal("500"),
            supply_apr_bps=Decimal("600"),
            borrow_apr_bps=Decimal("900"),
        )

        pool = db.query(LendingPool).filter(LendingPool.id == product.lending_pool_id).first()
        assert pool is not None
        assert pool.asset == "ETH"
        assert float(pool.supply_rate_bps) == 600.0


# ---------------------------------------------------------------------------
# B. DUPLICATE REJECTION
# ---------------------------------------------------------------------------

class TestDuplicateRejection:

    def test_duplicate_project_rejected(self, db):
        borrower = _create_client(db, "prov_dup_borrower@test.com")
        from services.lending.offer_service import OfferService, OfferError
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="USDC",
            target_size=Decimal("100000"),
        )

        with pytest.raises(OfferError, match="already has a lending product"):
            svc.create_from_project(
                db,
                project_id=project_id,
                borrower_client_id=borrower.id,
                asset="BTC",
                target_size=Decimal("50000"),
            )


# ---------------------------------------------------------------------------
# C. ADMIN POOL LIST
# ---------------------------------------------------------------------------

class TestAdminPoolList:

    def test_admin_pool_list_includes_created(self, db):
        borrower = _create_client(db, "admin_list_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="USDC",
            target_size=Decimal("50000"),
            title="Admin List Test",
        )

        pools = svc.get_admin_pool_list(db)
        pool_ids = [p["product_id"] for p in pools]
        assert str(product.id) in pool_ids

        entry = next(p for p in pools if p["product_id"] == str(product.id))
        assert entry["title"] == "Admin List Test"
        assert entry["project_id"] == project_id
        assert entry["status"] == "draft"

    def test_admin_pool_list_has_required_fields(self, db):
        borrower = _create_client(db, "admin_fields_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="BTC",
            target_size=Decimal("10"),
        )

        pools = svc.get_admin_pool_list(db)
        entry = next(p for p in pools if p["project_id"] == project_id)

        required_fields = [
            "product_id", "pool_id", "project_id", "title", "asset",
            "borrower_client_id", "raised", "target", "progress_pct",
            "investors_count", "utilization", "supply_apr", "status",
        ]
        for field in required_fields:
            assert field in entry, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# D. ADMIN POOL DETAIL
# ---------------------------------------------------------------------------

class TestAdminPoolDetail:

    def test_admin_pool_detail_empty_pool(self, db):
        borrower = _create_client(db, "detail_empty_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="ETH",
            target_size=Decimal("100"),
        )

        detail = svc.get_admin_pool_detail(db, product.lending_pool_id)

        assert detail["overview"]["pool_id"] == str(product.lending_pool_id)
        assert detail["overview"]["asset"] == "ETH"
        assert detail["product"]["product_id"] == str(product.id)
        assert detail["lenders"] == []
        assert detail["borrowers"] == []
        assert detail["allocations"] == []
        assert detail["summary"]["total_lenders"] == 0

    def test_admin_pool_detail_with_lenders(self, db):
        borrower = _create_client(db, "detail_lender_borrower@test.com")
        lender1 = _create_client(db, "detail_lender1@test.com")
        lender2 = _create_client(db, "detail_lender2@test.com")
        _set_balance(db, lender1.id, "USDC", 50000)
        _set_balance(db, lender2.id, "USDC", 50000)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="USDC",
            target_size=Decimal("80000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender1.id, amount=Decimal("30000"))
        svc.subscribe(db, product_id=product.id, lender_client_id=lender2.id, amount=Decimal("20000"))

        detail = svc.get_admin_pool_detail(db, product.lending_pool_id)

        assert detail["summary"]["total_lenders"] == 2
        assert len(detail["lenders"]) == 2

        lender_ids = {l["client_id"] for l in detail["lenders"]}
        assert str(lender1.id) in lender_ids
        assert str(lender2.id) in lender_ids

        l1 = next(l for l in detail["lenders"] if l["client_id"] == str(lender1.id))
        assert l1["committed"] == 30000.0

    def test_admin_pool_detail_with_active_borrow(self, db):
        borrower = _create_client(db, "detail_active_borrower@test.com")
        lender = _create_client(db, "detail_active_lender@test.com")
        _set_balance(db, lender.id, "USDC", 100000)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="USDC",
            target_size=Decimal("50000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("50000"))
        svc.activate_product(db, product.id)

        detail = svc.get_admin_pool_detail(db, product.lending_pool_id)

        assert detail["summary"]["total_borrowed_positions"] >= 1
        assert len(detail["borrowers"]) >= 1
        assert detail["borrowers"][0]["borrowed"] == 50000.0
        assert detail["summary"]["total_allocations"] >= 1


# ---------------------------------------------------------------------------
# E. EDGE CASES
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_nonexistent_pool_raises(self, db):
        from services.lending.offer_service import OfferService, OfferNotFoundError
        svc = OfferService()

        with pytest.raises(OfferNotFoundError):
            svc.get_admin_pool_detail(db, uuid.uuid4())

    def test_product_detail_after_provisioning(self, db):
        borrower = _create_client(db, "edge_detail_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_from_project(
            db,
            project_id=project_id,
            borrower_client_id=borrower.id,
            asset="BTC",
            target_size=Decimal("5"),
            title="Edge Case Test",
        )

        detail = svc.get_product_detail(db, product.id)
        assert detail["project_id"] == project_id
        assert detail["title"] == "Edge Case Test"
        assert detail["investors_count"] == 0
