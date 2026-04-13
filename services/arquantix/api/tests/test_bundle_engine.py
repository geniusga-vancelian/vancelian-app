"""Tests for Bundle Engine v1.

Coverage:
  - Schema / payload validation (product_code, frequencies, allocations, weights)
  - Service / transaction (happy path, rollback, audit, idempotency)
  - Router (RBAC, list, detail)
  - Catalog compatibility (frequencies from metadata)
"""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundles.schemas import (
    BundleAllocationCreate,
    BundleCreate,
    WEIGHT_TOLERANCE,
)
from services.portfolio_engine.bundles.service import (
    BundleEngineService,
    BundleNotFoundError,
    BundleValidationError,
)
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.products.catalog import CatalogService, _resolve_frequencies
from services.portfolio_engine.templates.models import PortfolioTemplate, TemplateAllocation
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.hardening.idempotency_models import IdempotencyKey


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bundle_service() -> BundleEngineService:
    return BundleEngineService()


@pytest.fixture
def catalog_service() -> CatalogService:
    return CatalogService()


@pytest.fixture
def spot_assets(db: Session) -> list[Asset]:
    """Create two spot-compatible assets with unique symbols to avoid collisions."""
    suffix = uuid.uuid4().hex[:6].upper()
    btc = Asset(
        id=uuid.uuid4(),
        symbol=f"TBTC_{suffix}",
        name="Test Bitcoin",
        asset_type="cryptocurrency",
    )
    eth = Asset(
        id=uuid.uuid4(),
        symbol=f"TETH_{suffix}",
        name="Test Ethereum",
        asset_type="cryptocurrency",
    )
    db.add_all([btc, eth])
    db.flush()
    return [btc, eth]


@pytest.fixture
def spot_instruments(db: Session, spot_assets: list[Asset]) -> list[Instrument]:
    """Create two spot instruments linked to test assets."""
    suffix = uuid.uuid4().hex[:6].upper()
    btc_instr = Instrument(
        id=uuid.uuid4(),
        asset_id=spot_assets[0].id,
        code=f"TBTC_SPOT_{suffix}",
        name="Test Bitcoin Spot",
        instrument_type="spot",
    )
    eth_instr = Instrument(
        id=uuid.uuid4(),
        asset_id=spot_assets[1].id,
        code=f"TETH_SPOT_{suffix}",
        name="Test Ethereum Spot",
        instrument_type="spot",
    )
    db.add_all([btc_instr, eth_instr])
    db.flush()
    return [btc_instr, eth_instr]


@pytest.fixture
def staking_instrument(db: Session, spot_assets: list[Asset]) -> Instrument:
    """Create a non-spot (staking) instrument."""
    suffix = uuid.uuid4().hex[:6].upper()
    instr = Instrument(
        id=uuid.uuid4(),
        asset_id=spot_assets[0].id,
        code=f"TBTC_STAKING_{suffix}",
        name="Test Bitcoin Staking",
        instrument_type="staking_position",
    )
    db.add(instr)
    db.flush()
    return instr


@pytest.fixture
def api_client(test_app, db: Session):
    """TestClient that shares the test db session with the router."""
    from database import get_db

    def _override():
        yield db

    test_app.dependency_overrides[get_db] = _override
    with TestClient(test_app) as c:
        yield c
    test_app.dependency_overrides.pop(get_db, None)


def _make_valid_payload(instruments: list[Instrument], **overrides) -> BundleCreate:
    """Helper to build a valid BundleCreate payload."""
    defaults = dict(
        name="Test Bundle",
        product_code="TEST_BUNDLE_01",
        description="A test bundle",
        risk_label="high",
        base_currency="USD",
        is_public=True,
        allocations=[
            BundleAllocationCreate(
                instrument_id=instruments[0].id,
                target_weight=Decimal("0.7"),
            ),
            BundleAllocationCreate(
                instrument_id=instruments[1].id,
                target_weight=Decimal("0.3"),
            ),
        ],
        available_rebalance_frequencies=["weekly", "monthly", "quarterly"],
    )
    defaults.update(overrides)
    return BundleCreate(**defaults)


# ===========================================================================
# 1. Schema / payload validation
# ===========================================================================

class TestBundleSchemaValidation:

    def test_valid_payload(self, spot_instruments):
        payload = _make_valid_payload(spot_instruments)
        assert payload.product_code == "TEST_BUNDLE_01"
        assert len(payload.allocations) == 2

    def test_invalid_product_code_lowercase(self, spot_instruments):
        with pytest.raises(ValidationError, match="product_code"):
            _make_valid_payload(spot_instruments, product_code="invalid_lowercase")

    def test_invalid_product_code_spaces(self, spot_instruments):
        with pytest.raises(ValidationError, match="product_code"):
            _make_valid_payload(spot_instruments, product_code="HAS SPACES")

    def test_invalid_product_code_too_long(self, spot_instruments):
        with pytest.raises(ValidationError):
            _make_valid_payload(spot_instruments, product_code="A" * 101)

    def test_unsupported_frequency_rejected(self, spot_instruments):
        with pytest.raises(ValidationError, match="Unsupported rebalance frequency"):
            _make_valid_payload(
                spot_instruments,
                available_rebalance_frequencies=["daily"],
            )

    def test_duplicate_frequency_rejected(self, spot_instruments):
        with pytest.raises(ValidationError, match="Duplicate rebalance frequency"):
            _make_valid_payload(
                spot_instruments,
                available_rebalance_frequencies=["weekly", "weekly"],
            )

    def test_empty_frequencies_rejected(self, spot_instruments):
        with pytest.raises(ValidationError, match="must not be empty"):
            _make_valid_payload(
                spot_instruments,
                available_rebalance_frequencies=[],
            )

    def test_duplicate_instrument_rejected(self, spot_instruments):
        with pytest.raises(ValidationError, match="Duplicate instrument_id"):
            _make_valid_payload(
                spot_instruments,
                allocations=[
                    BundleAllocationCreate(
                        instrument_id=spot_instruments[0].id,
                        target_weight=Decimal("0.5"),
                    ),
                    BundleAllocationCreate(
                        instrument_id=spot_instruments[0].id,
                        target_weight=Decimal("0.5"),
                    ),
                ],
            )

    def test_invalid_total_weight_rejected(self, spot_instruments):
        with pytest.raises(ValidationError, match="Sum of target_weight"):
            _make_valid_payload(
                spot_instruments,
                allocations=[
                    BundleAllocationCreate(
                        instrument_id=spot_instruments[0].id,
                        target_weight=Decimal("0.5"),
                    ),
                    BundleAllocationCreate(
                        instrument_id=spot_instruments[1].id,
                        target_weight=Decimal("0.2"),
                    ),
                ],
            )

    def test_weight_within_tolerance_accepted(self, spot_instruments):
        payload = _make_valid_payload(
            spot_instruments,
            allocations=[
                BundleAllocationCreate(
                    instrument_id=spot_instruments[0].id,
                    target_weight=Decimal("0.701"),
                ),
                BundleAllocationCreate(
                    instrument_id=spot_instruments[1].id,
                    target_weight=Decimal("0.301"),
                ),
            ],
        )
        total = sum(a.target_weight for a in payload.allocations)
        assert abs(total - Decimal("1")) <= WEIGHT_TOLERANCE

    def test_empty_allocations_rejected(self, spot_instruments):
        with pytest.raises(ValidationError):
            _make_valid_payload(spot_instruments, allocations=[])

    def test_min_gt_target_rejected(self, spot_instruments):
        with pytest.raises(ValidationError, match="min_weight must be <= target_weight"):
            BundleAllocationCreate(
                instrument_id=spot_instruments[0].id,
                target_weight=Decimal("0.5"),
                min_weight=Decimal("0.6"),
            )

    def test_max_lt_target_rejected(self, spot_instruments):
        with pytest.raises(ValidationError, match="max_weight must be >= target_weight"):
            BundleAllocationCreate(
                instrument_id=spot_instruments[0].id,
                target_weight=Decimal("0.5"),
                max_weight=Decimal("0.4"),
            )


# ===========================================================================
# 2. Service / transaction tests
# ===========================================================================

class TestBundleEngineService:

    def test_create_bundle_happy_path(
        self, db: Session, bundle_service: BundleEngineService, spot_instruments,
    ):
        payload = _make_valid_payload(spot_instruments)
        result = bundle_service.create_bundle(db, payload, actor_type="admin", actor_id="test-user")
        db.flush()

        assert result.product_code == "TEST_BUNDLE_01"
        assert result.name == "Test Bundle"
        assert result.status == "active"
        assert result.is_public is True
        assert result.product_type == "crypto_bundle"
        assert result.template_code == "TEST_BUNDLE_01_DEFAULT"
        assert len(result.allocations) == 2
        assert result.available_rebalance_frequencies == ["weekly", "monthly", "quarterly"]

        product = db.query(ProductDefinition).filter_by(product_code="TEST_BUNDLE_01").first()
        assert product is not None
        assert product.status == "active"

        template = db.query(PortfolioTemplate).filter_by(product_id=product.id).first()
        assert template is not None

        allocs = db.query(TemplateAllocation).filter_by(template_id=template.id).all()
        assert len(allocs) == 2

    def test_create_bundle_writes_success_audit(
        self, db: Session, bundle_service: BundleEngineService, spot_instruments,
    ):
        payload = _make_valid_payload(spot_instruments)
        bundle_service.create_bundle(db, payload, actor_type="admin", actor_id="audit-test")
        db.flush()

        audits = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.action == "bundle_created",
                AuditEvent.entity_type == "bundle",
            )
            .all()
        )
        assert len(audits) >= 1
        audit = [a for a in audits if (a.metadata_ or {}).get("product_code") == "TEST_BUNDLE_01"]
        assert len(audit) == 1
        audit = audit[0]
        assert audit.actor_type == "admin"
        meta = audit.metadata_
        assert meta["outcome"] == "success"
        assert meta["product_code"] == "TEST_BUNDLE_01"
        assert meta["allocations_count"] == 2

    def test_create_bundle_duplicate_code_fails(
        self, db: Session, bundle_service: BundleEngineService, spot_instruments,
    ):
        payload = _make_valid_payload(spot_instruments)
        bundle_service.create_bundle(db, payload)
        db.flush()

        payload2 = _make_valid_payload(spot_instruments, product_code="TEST_BUNDLE_01")
        with pytest.raises(BundleValidationError, match="already exists"):
            bundle_service.create_bundle(db, payload2)

    def test_create_bundle_nonexistent_instrument_fails(
        self, db: Session, bundle_service: BundleEngineService, spot_instruments,
    ):
        fake_id = uuid.uuid4()
        payload = _make_valid_payload(
            spot_instruments,
            product_code="NONEXIST_TEST",
            allocations=[
                BundleAllocationCreate(instrument_id=fake_id, target_weight=Decimal("0.5")),
                BundleAllocationCreate(
                    instrument_id=spot_instruments[0].id, target_weight=Decimal("0.5"),
                ),
            ],
        )
        with pytest.raises(BundleValidationError, match="Instruments not found"):
            bundle_service.create_bundle(db, payload)

    def test_create_bundle_non_spot_rejected(
        self,
        db: Session,
        bundle_service: BundleEngineService,
        spot_instruments,
        staking_instrument,
    ):
        payload = _make_valid_payload(
            spot_instruments,
            product_code="STAKING_TEST",
            allocations=[
                BundleAllocationCreate(
                    instrument_id=spot_instruments[0].id, target_weight=Decimal("0.5"),
                ),
                BundleAllocationCreate(
                    instrument_id=staking_instrument.id, target_weight=Decimal("0.5"),
                ),
            ],
        )
        with pytest.raises(BundleValidationError, match="must be spot"):
            bundle_service.create_bundle(db, payload)

    def test_rollback_leaves_no_data(
        self, db: Session, bundle_service: BundleEngineService, spot_instruments,
    ):
        """If validation fails, the DB must remain unchanged."""
        count_before = db.query(ProductDefinition).count()

        fake_id = uuid.uuid4()
        payload = _make_valid_payload(
            spot_instruments,
            product_code="ROLLBACK_TEST",
            allocations=[
                BundleAllocationCreate(instrument_id=fake_id, target_weight=Decimal("0.5")),
                BundleAllocationCreate(
                    instrument_id=spot_instruments[0].id, target_weight=Decimal("0.5"),
                ),
            ],
        )
        with pytest.raises(BundleValidationError):
            bundle_service.create_bundle(db, payload)

        count_after = db.query(ProductDefinition).count()
        assert count_after == count_before

    def test_list_bundles(
        self, db: Session, bundle_service: BundleEngineService, spot_instruments,
    ):
        payload = _make_valid_payload(spot_instruments)
        bundle_service.create_bundle(db, payload)
        db.flush()

        result = bundle_service.list_bundles(db)
        assert result.total >= 1
        found = [b for b in result.items if b.product_code == "TEST_BUNDLE_01"]
        assert len(found) == 1
        bundle_item = found[0]
        assert bundle_item.product_type == "crypto_bundle"
        assert bundle_item.allocations_count == 2
        assert len(bundle_item.allocation_summary) == 2
        assert bundle_item.available_rebalance_frequencies == ["weekly", "monthly", "quarterly"]

    def test_get_bundle(
        self, db: Session, bundle_service: BundleEngineService, spot_instruments,
    ):
        payload = _make_valid_payload(spot_instruments)
        created = bundle_service.create_bundle(db, payload)
        db.flush()

        detail = bundle_service.get_bundle(db, created.id)
        assert detail.product_code == "TEST_BUNDLE_01"
        assert detail.template_code == "TEST_BUNDLE_01_DEFAULT"
        assert len(detail.allocations) == 2
        known_codes = {i.code for i in spot_instruments}
        assert detail.allocations[0].instrument_code in known_codes

    def test_get_bundle_not_found(
        self, db: Session, bundle_service: BundleEngineService,
    ):
        with pytest.raises(BundleNotFoundError):
            bundle_service.get_bundle(db, uuid.uuid4())

    def test_frequencies_stored_in_metadata(
        self, db: Session, bundle_service: BundleEngineService, spot_instruments,
    ):
        payload = _make_valid_payload(
            spot_instruments,
            available_rebalance_frequencies=["monthly", "quarterly"],
        )
        result = bundle_service.create_bundle(db, payload)
        db.flush()

        product = db.query(ProductDefinition).filter_by(id=result.id).first()
        assert product.metadata_["available_rebalance_frequencies"] == ["monthly", "quarterly"]


# ===========================================================================
# 3. Router tests
# ===========================================================================

class TestBundleRouter:

    def test_create_bundle_admin_allowed(
        self, api_client, db: Session, spot_instruments,
    ):
        payload = {
            "name": "Router Test Bundle",
            "product_code": f"ROUTER_TEST_{uuid.uuid4().hex[:8].upper()}",
            "allocations": [
                {"instrument_id": str(spot_instruments[0].id), "target_weight": 0.6},
                {"instrument_id": str(spot_instruments[1].id), "target_weight": 0.4},
            ],
            "available_rebalance_frequencies": ["weekly", "monthly"],
        }
        resp = api_client.post(
            "/api/portfolio-engine/admin/bundles",
            json=payload,
            headers={"X-Actor-Type": "admin", "X-Actor-Roles": "admin"},
        )
        assert resp.status_code == 201, resp.json()
        data = resp.json()
        assert data["product_code"] == payload["product_code"]
        assert data["status"] == "active"

    def test_create_bundle_ops_allowed(
        self, api_client, db: Session, spot_instruments,
    ):
        payload = {
            "name": "Ops Test Bundle",
            "product_code": f"OPS_TEST_{uuid.uuid4().hex[:8].upper()}",
            "allocations": [
                {"instrument_id": str(spot_instruments[0].id), "target_weight": 0.5},
                {"instrument_id": str(spot_instruments[1].id), "target_weight": 0.5},
            ],
        }
        resp = api_client.post(
            "/api/portfolio-engine/admin/bundles",
            json=payload,
            headers={"X-Actor-Type": "ops", "X-Actor-Roles": "ops"},
        )
        assert resp.status_code == 201, resp.json()

    def test_create_bundle_client_forbidden(self, api_client, spot_instruments):
        payload = {
            "name": "Client Attempt",
            "product_code": "CLIENT_ATTEMPT",
            "allocations": [
                {"instrument_id": str(spot_instruments[0].id), "target_weight": 1.0},
            ],
        }
        resp = api_client.post(
            "/api/portfolio-engine/admin/bundles",
            json=payload,
            headers={"X-Actor-Type": "client", "X-Actor-Roles": "client"},
        )
        assert resp.status_code == 403

    def test_create_bundle_advisor_forbidden(self, api_client, spot_instruments):
        payload = {
            "name": "Advisor Attempt",
            "product_code": "ADVISOR_ATTEMPT",
            "allocations": [
                {"instrument_id": str(spot_instruments[0].id), "target_weight": 1.0},
            ],
        }
        resp = api_client.post(
            "/api/portfolio-engine/admin/bundles",
            json=payload,
            headers={"X-Actor-Type": "advisor", "X-Actor-Roles": "advisor"},
        )
        assert resp.status_code == 403

    def test_list_bundles_admin(self, api_client):
        resp = api_client.get(
            "/api/portfolio-engine/admin/bundles",
            headers={"X-Actor-Type": "admin", "X-Actor-Roles": "admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_list_bundles_client_forbidden(self, api_client):
        resp = api_client.get(
            "/api/portfolio-engine/admin/bundles",
            headers={"X-Actor-Type": "client", "X-Actor-Roles": "client"},
        )
        assert resp.status_code == 403

    def test_get_bundle_detail(self, api_client, db: Session, spot_instruments):
        create_payload = {
            "name": "Detail Test",
            "product_code": f"DETAIL_{uuid.uuid4().hex[:8].upper()}",
            "allocations": [
                {"instrument_id": str(spot_instruments[0].id), "target_weight": 0.7},
                {"instrument_id": str(spot_instruments[1].id), "target_weight": 0.3},
            ],
        }
        create_resp = api_client.post(
            "/api/portfolio-engine/admin/bundles",
            json=create_payload,
            headers={"X-Actor-Type": "admin", "X-Actor-Roles": "admin"},
        )
        assert create_resp.status_code == 201, create_resp.json()
        bundle_id = create_resp.json()["id"]

        detail_resp = api_client.get(
            f"/api/portfolio-engine/admin/bundles/{bundle_id}",
            headers={"X-Actor-Type": "admin", "X-Actor-Roles": "admin"},
        )
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["product_code"] == create_payload["product_code"]
        assert len(detail["allocations"]) == 2

    def test_get_bundle_not_found(self, api_client):
        fake_id = str(uuid.uuid4())
        resp = api_client.get(
            f"/api/portfolio-engine/admin/bundles/{fake_id}",
            headers={"X-Actor-Type": "admin", "X-Actor-Roles": "admin"},
        )
        assert resp.status_code == 404

    def test_idempotency_replay(self, api_client, spot_instruments):
        idem_key = f"test-idem-{uuid.uuid4().hex[:8]}"
        code = f"IDEM_{uuid.uuid4().hex[:8].upper()}"
        payload = {
            "name": "Idempotent Bundle",
            "product_code": code,
            "allocations": [
                {"instrument_id": str(spot_instruments[0].id), "target_weight": 0.5},
                {"instrument_id": str(spot_instruments[1].id), "target_weight": 0.5},
            ],
        }
        headers = {
            "X-Actor-Type": "admin",
            "X-Actor-Roles": "admin",
            "Idempotency-Key": idem_key,
        }

        resp1 = api_client.post("/api/portfolio-engine/admin/bundles", json=payload, headers=headers)
        assert resp1.status_code == 201, resp1.json()

        resp2 = api_client.post("/api/portfolio-engine/admin/bundles", json=payload, headers=headers)
        assert resp2.status_code == 201
        assert resp2.json()["product_code"] == code

    def test_idempotency_conflict_unit(self, db: Session, bundle_service, spot_instruments):
        """Verify IdempotencyConflictError is raised when key reused with different payload."""
        from services.portfolio_engine.hardening.idempotency_service import (
            IdempotencyConflictError,
            IdempotencyService,
        )

        idem_key = f"conflict-{uuid.uuid4().hex[:8]}"
        scope = f"bundle_create:CODE_A"
        request_data_1 = {"name": "Bundle A", "product_code": "CODE_A"}
        request_data_2 = {"name": "Bundle B", "product_code": "CODE_B"}

        result = IdempotencyService.check_or_reserve(
            db,
            idempotency_key=idem_key,
            scope=scope,
            request_data=request_data_1,
        )
        assert result.replayed is False

        IdempotencyService.store_response(
            db,
            idempotency_key=idem_key,
            scope=scope,
            response_status=201,
            response_body={"id": "fake"},
        )
        db.flush()

        with pytest.raises(IdempotencyConflictError):
            IdempotencyService.check_or_reserve(
                db,
                idempotency_key=idem_key,
                scope=scope,
                request_data=request_data_2,
            )

    def test_validation_error_returns_422(self, api_client, spot_instruments):
        payload = {
            "name": "Bad Bundle",
            "product_code": "BAD",
            "allocations": [
                {"instrument_id": str(uuid.uuid4()), "target_weight": 1.0},
            ],
        }
        resp = api_client.post(
            "/api/portfolio-engine/admin/bundles",
            json=payload,
            headers={"X-Actor-Type": "admin", "X-Actor-Roles": "admin"},
        )
        assert resp.status_code == 422


# ===========================================================================
# 4. Catalog compatibility
# ===========================================================================

class TestCatalogFrequencies:

    def test_frequencies_from_metadata(self, db: Session):
        product = ProductDefinition(
            product_code=f"CAT_{uuid.uuid4().hex[:8].upper()}",
            name="Catalog Test",
            product_type="crypto_bundle",
            metadata_={"available_rebalance_frequencies": ["monthly"]},
        )
        db.add(product)
        db.flush()

        freqs = _resolve_frequencies(product)
        assert freqs == ["monthly"]

    def test_frequencies_fallback_when_missing(self, db: Session):
        product = ProductDefinition(
            product_code=f"CAT_FB_{uuid.uuid4().hex[:8].upper()}",
            name="Fallback Test",
            product_type="crypto_bundle",
            metadata_={},
        )
        db.add(product)
        db.flush()

        freqs = _resolve_frequencies(product)
        assert freqs == ["weekly", "monthly", "quarterly"]

    def test_frequencies_fallback_when_empty_list(self, db: Session):
        product = ProductDefinition(
            product_code=f"CAT_EL_{uuid.uuid4().hex[:8].upper()}",
            name="Empty List Test",
            product_type="crypto_bundle",
            metadata_={"available_rebalance_frequencies": []},
        )
        db.add(product)
        db.flush()

        freqs = _resolve_frequencies(product)
        assert freqs == ["weekly", "monthly", "quarterly"]

    def test_catalog_service_uses_metadata_frequencies(
        self, db: Session, catalog_service: CatalogService,
        spot_instruments, spot_assets,
    ):
        """E2E: a bundle created with specific frequencies appears in catalog with those frequencies."""
        svc = BundleEngineService()
        payload = _make_valid_payload(
            spot_instruments,
            product_code=f"CAT_E2E_{uuid.uuid4().hex[:8].upper()}",
            available_rebalance_frequencies=["quarterly"],
        )
        result = svc.create_bundle(db, payload)
        db.flush()

        detail = catalog_service.get_product_detail(db, result.id)
        assert detail is not None
        assert detail.available_rebalance_frequencies == ["quarterly"]


# ===========================================================================
# 5. Visibility (publish / unpublish)
# ===========================================================================

class TestBundleVisibility:

    def _create_bundle(self, db, svc, instruments, **kw):
        code = f"VIS_{uuid.uuid4().hex[:8].upper()}"
        kw.setdefault("is_public", False)
        payload = _make_valid_payload(instruments, product_code=code, **kw)
        result = svc.create_bundle(db, payload)
        db.flush()
        return result

    # ── Service-level tests ──

    def test_publish_sets_is_public_true(self, db: Session, bundle_service, spot_instruments):
        bundle = self._create_bundle(db, bundle_service, spot_instruments)
        product = db.query(ProductDefinition).filter(ProductDefinition.id == bundle.id).one()
        assert product.is_public is False

        result = bundle_service.set_visibility(db, bundle.id, is_public=True)
        db.flush()

        product = db.query(ProductDefinition).filter(ProductDefinition.id == bundle.id).one()
        assert product.is_public is True
        assert result["is_public"] is True
        assert result["action"] == "bundle_published"

    def test_unpublish_sets_is_public_false(self, db: Session, bundle_service, spot_instruments):
        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=True)
        product = db.query(ProductDefinition).filter(ProductDefinition.id == bundle.id).one()
        assert product.is_public is True

        result = bundle_service.set_visibility(db, bundle.id, is_public=False)
        db.flush()

        product = db.query(ProductDefinition).filter(ProductDefinition.id == bundle.id).one()
        assert product.is_public is False
        assert result["action"] == "bundle_unpublished"

    def test_publish_writes_audit_event(self, db: Session, bundle_service, spot_instruments):
        bundle = self._create_bundle(db, bundle_service, spot_instruments)
        bundle_service.set_visibility(db, bundle.id, is_public=True)
        db.flush()

        events = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.entity_id == str(bundle.id),
                AuditEvent.action == "bundle_published",
            )
            .all()
        )
        assert len(events) >= 1
        meta = events[0].metadata_
        assert meta["previous_is_public"] is False
        assert meta["new_is_public"] is True

    def test_unpublish_writes_audit_event(self, db: Session, bundle_service, spot_instruments):
        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=True)
        bundle_service.set_visibility(db, bundle.id, is_public=False)
        db.flush()

        events = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.entity_id == str(bundle.id),
                AuditEvent.action == "bundle_unpublished",
            )
            .all()
        )
        assert len(events) >= 1

    def test_visibility_not_found(self, db: Session, bundle_service):
        with pytest.raises(BundleNotFoundError):
            bundle_service.set_visibility(db, uuid.uuid4(), is_public=True)

    def test_visibility_idempotent(self, db: Session, bundle_service, spot_instruments):
        """Publishing an already-public bundle should succeed without error."""
        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=True)
        result = bundle_service.set_visibility(db, bundle.id, is_public=True)
        db.flush()
        assert result["is_public"] is True

    # ── Catalog coherence ──

    def test_unpublished_absent_from_catalog(
        self, db: Session, bundle_service, catalog_service, spot_instruments,
    ):
        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=True)
        db.flush()

        items = catalog_service.get_public_catalog(db, product_type="crypto_bundle")
        codes = [i.product_code for i in items]
        assert bundle.product_code in codes

        bundle_service.set_visibility(db, bundle.id, is_public=False)
        db.flush()

        items = catalog_service.get_public_catalog(db, product_type="crypto_bundle")
        codes = [i.product_code for i in items]
        assert bundle.product_code not in codes

    def test_published_visible_in_catalog(
        self, db: Session, bundle_service, catalog_service, spot_instruments,
    ):
        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=False)
        db.flush()

        items = catalog_service.get_public_catalog(db, product_type="crypto_bundle")
        codes = [i.product_code for i in items]
        assert bundle.product_code not in codes

        bundle_service.set_visibility(db, bundle.id, is_public=True)
        db.flush()

        items = catalog_service.get_public_catalog(db, product_type="crypto_bundle")
        codes = [i.product_code for i in items]
        assert bundle.product_code in codes

    def test_admin_list_shows_unpublished(self, db: Session, bundle_service, spot_instruments):
        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=False)
        db.flush()

        result = bundle_service.list_bundles(db)
        codes = [i.product_code for i in result.items]
        assert bundle.product_code in codes

    # ── Router-level RBAC tests ──

    def test_visibility_admin_allowed(self, api_client, bundle_service, spot_instruments, db):
        bundle = self._create_bundle(db, bundle_service, spot_instruments)
        db.flush()

        resp = api_client.patch(
            f"/api/portfolio-engine/admin/bundles/{bundle.id}/visibility",
            json={"is_public": True},
            headers={"X-Actor-Type": "admin", "X-Actor-Roles": "admin"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_public"] is True

    def test_visibility_ops_allowed(self, api_client, bundle_service, spot_instruments, db):
        bundle = self._create_bundle(db, bundle_service, spot_instruments)
        db.flush()

        resp = api_client.patch(
            f"/api/portfolio-engine/admin/bundles/{bundle.id}/visibility",
            json={"is_public": True},
            headers={"X-Actor-Type": "ops", "X-Actor-Roles": "ops"},
        )
        assert resp.status_code == 200

    def test_visibility_client_forbidden(self, api_client, bundle_service, spot_instruments, db):
        bundle = self._create_bundle(db, bundle_service, spot_instruments)
        db.flush()

        resp = api_client.patch(
            f"/api/portfolio-engine/admin/bundles/{bundle.id}/visibility",
            json={"is_public": True},
            headers={"X-Actor-Type": "client", "X-Actor-Roles": "client"},
        )
        assert resp.status_code == 403


# ===========================================================================
# 6. Subscription visibility guard
# ===========================================================================

class TestSubscriptionVisibilityGuard:

    def _create_bundle(self, db, svc, instruments, **kw):
        code = f"SUB_{uuid.uuid4().hex[:8].upper()}"
        kw.setdefault("is_public", False)
        payload = _make_valid_payload(instruments, product_code=code, **kw)
        result = svc.create_bundle(db, payload)
        db.flush()
        return result

    def _create_client(self, db: Session):
        from services.portfolio_engine.clients.models import Client
        client = Client(
            id=uuid.uuid4(),
            email=f"sub-test-{uuid.uuid4().hex[:8]}@test.com",
            status="active",
            kyc_status="approved",
        )
        db.add(client)
        db.flush()
        return client

    def test_cannot_subscribe_unpublished_bundle(
        self, db: Session, bundle_service, spot_instruments,
    ):
        """A client cannot subscribe to a bundle that is not published."""
        from services.portfolio_engine.subscriptions.service import (
            ProductNotAvailableError,
            SubscriptionService,
        )
        from services.portfolio_engine.subscriptions.schemas import SubscriptionCreate

        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=False)
        client = self._create_client(db)

        sub_svc = SubscriptionService()
        payload = SubscriptionCreate(
            client_id=client.id,
            product_id=bundle.id,
        )

        with pytest.raises(ProductNotAvailableError, match="not published"):
            sub_svc.create_subscription(db, payload)

    def test_can_subscribe_published_bundle(
        self, db: Session, bundle_service, spot_instruments,
    ):
        """A client can subscribe to a public, active bundle."""
        from services.portfolio_engine.subscriptions.service import SubscriptionService
        from services.portfolio_engine.subscriptions.schemas import SubscriptionCreate

        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=True)
        client = self._create_client(db)

        sub_svc = SubscriptionService()
        payload = SubscriptionCreate(
            client_id=client.id,
            product_id=bundle.id,
        )

        subscription = sub_svc.create_subscription(db, payload)
        db.flush()

        assert subscription is not None
        assert subscription.client_id == client.id
        assert subscription.product_id == bundle.id
        assert subscription.status == "pending"

    def test_cannot_subscribe_inactive_product(
        self, db: Session, bundle_service, spot_instruments,
    ):
        """A client cannot subscribe to a product whose status is not active."""
        from services.portfolio_engine.subscriptions.service import (
            ProductNotAvailableError,
            SubscriptionService,
        )
        from services.portfolio_engine.subscriptions.schemas import SubscriptionCreate

        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=True)
        client = self._create_client(db)

        product = db.query(ProductDefinition).filter(ProductDefinition.id == bundle.id).one()
        product.status = "inactive"
        db.flush()

        sub_svc = SubscriptionService()
        payload = SubscriptionCreate(
            client_id=client.id,
            product_id=bundle.id,
        )

        with pytest.raises(ProductNotAvailableError, match="status"):
            sub_svc.create_subscription(db, payload)

    def test_subscribe_via_router_unpublished_returns_409(
        self, api_client, bundle_service, spot_instruments, db: Session,
    ):
        """Router returns 409 when trying to subscribe to an unpublished product."""
        bundle = self._create_bundle(db, bundle_service, spot_instruments, is_public=False)
        client = self._create_client(db)

        resp = api_client.post(
            "/api/portfolio-engine/subscriptions",
            json={
                "client_id": str(client.id),
                "product_id": str(bundle.id),
            },
        )
        assert resp.status_code == 409
        assert "not available" in resp.json()["detail"].lower()
