"""Tests for Portfolio Engine — Products module."""
import uuid

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.products.repository import (
    DuplicateProductCodeError,
    ProductRepository,
)
from services.portfolio_engine.products.service import ProductNotFoundError, ProductService
from services.portfolio_engine.products.schemas import ProductCreate, ProductUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def product_bundle(db: Session) -> ProductDefinition:
    p = ProductDefinition(
        id=uuid.uuid4(),
        product_code="CRYPTO_BALANCED_01",
        name="CryptoBundle Balanced",
        description="A balanced crypto bundle",
        product_type="crypto_bundle",
        risk_label="moderate",
        base_currency="EUR",
        is_public=True,
        status="active",
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def product_service() -> ProductService:
    return ProductService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestProductRepository:

    def test_create(self, db: Session):
        p = ProductRepository.create(
            db,
            data={
                "product_code": "ETH_YIELD_01",
                "name": "ETH Yield Vault",
                "product_type": "yield_vault",
            },
        )
        assert p.id is not None
        assert p.product_code == "ETH_YIELD_01"
        assert p.name == "ETH Yield Vault"
        assert p.status == "draft"
        assert p.is_public is False

    def test_create_with_metadata(self, db: Session):
        p = ProductRepository.create(
            db,
            data={
                "product_code": "BTC_STRAT_01",
                "name": "BTC Strategy Portfolio",
                "product_type": "strategy_portfolio",
                "metadata": {"target_return": "8%"},
            },
        )
        assert p.metadata_ == {"target_return": "8%"}

    def test_create_duplicate_code(self, db: Session, product_bundle: ProductDefinition):
        with pytest.raises(DuplicateProductCodeError):
            ProductRepository.create(
                db,
                data={
                    "product_code": "CRYPTO_BALANCED_01",
                    "name": "Duplicate",
                    "product_type": "crypto_bundle",
                },
            )

    def test_get_by_id(self, db: Session, product_bundle: ProductDefinition):
        found = ProductRepository.get_by_id(db, product_bundle.id)
        assert found is not None
        assert found.product_code == "CRYPTO_BALANCED_01"

    def test_get_by_id_not_found(self, db: Session):
        assert ProductRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_all(self, db: Session, product_bundle: ProductDefinition):
        ProductRepository.create(
            db,
            data={
                "product_code": "ETH_YIELD_02",
                "name": "ETH Yield v2",
                "product_type": "yield_vault",
            },
        )
        items, total = ProductRepository.list(db)
        assert total >= 2

    def test_list_filter_by_product_type(self, db: Session, product_bundle: ProductDefinition):
        items, total = ProductRepository.list(db, product_type="crypto_bundle")
        assert total >= 1
        assert all(p.product_type == "crypto_bundle" for p in items)

    def test_list_filter_by_status(self, db: Session, product_bundle: ProductDefinition):
        items, total = ProductRepository.list(db, status="active")
        assert total >= 1
        assert all(p.status == "active" for p in items)

    def test_list_filter_by_is_public(self, db: Session, product_bundle: ProductDefinition):
        items, total = ProductRepository.list(db, is_public=True)
        assert total >= 1
        assert all(p.is_public is True for p in items)

    def test_update(self, db: Session, product_bundle: ProductDefinition):
        ProductRepository.update(db, product_bundle, data={"status": "suspended"})
        db.flush()
        refreshed = ProductRepository.get_by_id(db, product_bundle.id)
        assert refreshed.status == "suspended"

    def test_update_metadata(self, db: Session, product_bundle: ProductDefinition):
        ProductRepository.update(db, product_bundle, data={"metadata": {"fee": "1.5%"}})
        db.flush()
        refreshed = ProductRepository.get_by_id(db, product_bundle.id)
        assert refreshed.metadata_ == {"fee": "1.5%"}

    def test_update_code_duplicate(self, db: Session, product_bundle: ProductDefinition):
        ProductRepository.create(
            db,
            data={
                "product_code": "OTHER_PRODUCT",
                "name": "Other",
                "product_type": "savings_plan",
            },
        )
        with pytest.raises(DuplicateProductCodeError):
            ProductRepository.update(
                db, product_bundle, data={"product_code": "OTHER_PRODUCT"}
            )
            db.flush()


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestProductService:

    def test_create_product(self, db: Session, product_service: ProductService):
        payload = ProductCreate(
            product_code="SVC_PROD_01",
            name="Service Product",
            product_type="crypto_bundle",
        )
        p = product_service.create_product(db, payload)
        assert p.product_code == "SVC_PROD_01"
        assert p.status == "draft"
        assert p.base_currency == "EUR"

    def test_get_product(self, db: Session, product_service: ProductService, product_bundle: ProductDefinition):
        found = product_service.get_product(db, product_bundle.id)
        assert found.id == product_bundle.id

    def test_get_product_not_found(self, db: Session, product_service: ProductService):
        with pytest.raises(ProductNotFoundError):
            product_service.get_product(db, uuid.uuid4())

    def test_list_products(self, db: Session, product_service: ProductService, product_bundle: ProductDefinition):
        items, total = product_service.list_products(db)
        assert total >= 1

    def test_update_product(self, db: Session, product_service: ProductService, product_bundle: ProductDefinition):
        payload = ProductUpdate(risk_label="high")
        updated = product_service.update_product(db, product_bundle.id, payload)
        assert updated.risk_label == "high"
        assert updated.product_code == "CRYPTO_BALANCED_01"

    def test_update_product_partial(self, db: Session, product_service: ProductService, product_bundle: ProductDefinition):
        payload = ProductUpdate(status="archived")
        updated = product_service.update_product(db, product_bundle.id, payload)
        assert updated.status == "archived"
        assert updated.name == "CryptoBundle Balanced"


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestProductSchemas:

    def test_create_defaults(self):
        payload = ProductCreate(
            product_code="TEST_01",
            name="Test Product",
            product_type="crypto_bundle",
        )
        assert payload.status == "draft"
        assert payload.is_public is False
        assert payload.base_currency == "EUR"
        assert payload.metadata == {}

    def test_create_with_overrides(self):
        payload = ProductCreate(
            product_code="TEST_02",
            name="Test Product 2",
            product_type="yield_vault",
            status="active",
            is_public=True,
            base_currency="USD",
            risk_label="high",
        )
        assert payload.status == "active"
        assert payload.is_public is True
        assert payload.base_currency == "USD"
        assert payload.risk_label == "high"

    def test_update_partial(self):
        payload = ProductUpdate(status="suspended")
        dumped = payload.model_dump(exclude_unset=True)
        assert "status" in dumped
        assert "name" not in dumped
        assert "product_type" not in dumped
        assert "metadata" not in dumped
