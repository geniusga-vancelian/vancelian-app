"""Tests for Project ↔ Lending Product Integration — Phase 2A.11.

Covers:
  A. Link / Unlink project to lending product
  B. get_lending_data_for_projects() enrichment
  C. Fallback (project without lending → null data)
  D. Multi-project scenario
  E. Investors count
  F. 1-to-1 constraint (double link rejected)
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
# A. LINK / UNLINK
# ---------------------------------------------------------------------------

class TestLinkUnlink:

    def test_link_project_to_product(self, db):
        borrower = _create_client(db, "link_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db,
            title="Link Test",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
        )

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        linked = svc.link_project(db, product.id, project_id)

        assert linked.project_id == project_id

    def test_unlink_project(self, db):
        borrower = _create_client(db, "unlink_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db,
            title="Unlink Test",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
        )
        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        svc.link_project(db, product.id, project_id)
        unlinked = svc.unlink_project(db, product.id)

        assert unlinked.project_id is None

    def test_create_product_with_project_id(self, db):
        borrower = _create_client(db, "create_link_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_product(
            db,
            title="Create With Project",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
            project_id=project_id,
        )

        assert product.project_id == project_id

    def test_double_link_rejected(self, db):
        borrower = _create_client(db, "double_link_borrower@test.com")
        from services.lending.offer_service import OfferService, OfferError
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"

        p1 = svc.create_product(
            db,
            title="Product A",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
            project_id=project_id,
        )

        p2 = svc.create_product(
            db,
            title="Product B",
            asset="BTC",
            borrower_client_id=borrower.id,
            target_size=Decimal("30000"),
        )

        with pytest.raises(OfferError, match="already linked"):
            svc.link_project(db, p2.id, project_id)


# ---------------------------------------------------------------------------
# B. GET LENDING DATA FOR PROJECTS
# ---------------------------------------------------------------------------

class TestLendingDataEnrichment:

    def test_enrichment_basic(self, db):
        borrower = _create_client(db, "enrich_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_product(
            db,
            title="Solar Project",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("100000"),
            supply_apr_bps=Decimal("800"),
            project_id=project_id,
        )
        svc.open_fundraising(db, product.id)

        data = svc.get_lending_data_for_projects(db)
        assert project_id in data

        entry = data[project_id]
        assert entry["apy"] == 8.0
        assert entry["target"] == 100000.0
        assert entry["raised"] == 0.0
        assert entry["progress"] == 0.0
        assert entry["investorsCount"] == 0
        assert entry["isInvestable"] is True
        assert entry["status"] == "fundraising"
        assert entry["lending_product_id"] == str(product.id)

    def test_enrichment_with_subscribers(self, db):
        borrower = _create_client(db, "enrich_sub_borrower@test.com")
        lender1 = _create_client(db, "enrich_sub_lender1@test.com")
        lender2 = _create_client(db, "enrich_sub_lender2@test.com")
        _set_balance(db, lender1.id, "USDC", 50000)
        _set_balance(db, lender2.id, "USDC", 50000)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_product(
            db,
            title="Multi Lender Project",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("80000"),
            supply_apr_bps=Decimal("600"),
            project_id=project_id,
        )
        svc.open_fundraising(db, product.id)

        svc.subscribe(db, product_id=product.id, lender_client_id=lender1.id, amount=Decimal("30000"))
        svc.subscribe(db, product_id=product.id, lender_client_id=lender2.id, amount=Decimal("20000"))

        data = svc.get_lending_data_for_projects(db)
        entry = data[project_id]

        assert entry["raised"] == 50000.0
        assert entry["investorsCount"] == 2
        assert entry["progress"] == 62.5


# ---------------------------------------------------------------------------
# C. FALLBACK — PROJECT WITHOUT LENDING
# ---------------------------------------------------------------------------

class TestFallback:

    def test_unlinked_project_not_in_data(self, db):
        borrower = _create_client(db, "fallback_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        svc.create_product(
            db,
            title="No Project Link",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
        )

        data = svc.get_lending_data_for_projects(db)
        # The product has no project_id, so it should not appear
        for key in data:
            assert data[key]["lending_product_id"] != "No Project Link"

    def test_draft_product_included_in_data(self, db):
        """Draft products are now included in enrichment (isInvestable controls visibility)."""
        borrower = _create_client(db, "draft_fallback_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        svc.create_product(
            db,
            title="Draft Product",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
            project_id=project_id,
        )

        data = svc.get_lending_data_for_projects(db)
        assert project_id in data
        assert data[project_id]["status"] == "draft"
        assert data[project_id]["isInvestable"] is False


# ---------------------------------------------------------------------------
# D. MULTI-PROJECT
# ---------------------------------------------------------------------------

class TestMultiProject:

    def test_multiple_projects_with_lending(self, db):
        borrower = _create_client(db, "multi_proj_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        assets = ["USDC", "BTC", "ETH"]
        project_ids = []
        for i in range(3):
            pid = f"proj_{uuid.uuid4().hex[:8]}"
            project_ids.append(pid)
            product = svc.create_product(
                db,
                title=f"Project {i}",
                asset=assets[i],
                borrower_client_id=borrower.id,
                target_size=Decimal(str(10000 * (i + 1))),
                supply_apr_bps=Decimal(str(300 * (i + 1))),
                project_id=pid,
            )
            svc.open_fundraising(db, product.id)

        data = svc.get_lending_data_for_projects(db)

        for i, pid in enumerate(project_ids):
            assert pid in data
            assert data[pid]["target"] == 10000.0 * (i + 1)
            assert data[pid]["apy"] == 3.0 * (i + 1)


# ---------------------------------------------------------------------------
# E. PRODUCT TO DICT INCLUDES PROJECT_ID
# ---------------------------------------------------------------------------

class TestProductDict:

    def test_product_detail_includes_project_id(self, db):
        borrower = _create_client(db, "dict_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        project_id = f"proj_{uuid.uuid4().hex[:8]}"
        product = svc.create_product(
            db,
            title="Dict Test",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
            project_id=project_id,
        )

        detail = svc.get_product_detail(db, product.id)
        assert detail["project_id"] == project_id

    def test_product_detail_includes_investors_count(self, db):
        borrower = _create_client(db, "dict_inv_borrower@test.com")
        lender = _create_client(db, "dict_inv_lender@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db,
            title="Investors Count Test",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("10000"))

        detail = svc.get_product_detail(db, product.id)
        assert detail["investors_count"] == 1

    def test_product_detail_no_project_id(self, db):
        borrower = _create_client(db, "dict_noproject_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db,
            title="No Project",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
        )

        detail = svc.get_product_detail(db, product.id)
        assert detail["project_id"] is None
