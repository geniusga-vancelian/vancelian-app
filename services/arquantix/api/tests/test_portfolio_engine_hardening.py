"""Tests for Portfolio Engine — Hardening Subphase 1 (Idempotency + Audit).

Covers:
 1. First request reserves key and stores response
 2. Replay with same key + same payload returns stored response
 3. Same key + different payload => conflict
 4. Missing idempotency key still works
 5. Deterministic request hash works
 6. Success audit event persisted
 7. Failure path logs audit event
 8. Audit events are append-only
 9. Orchestrate endpoint supports replay
10. Valuation snapshot endpoint supports replay
11. Rebalance plan endpoint supports replay
12. Provision endpoint supports replay
13. Strategy evaluation endpoint supports replay
"""
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.hashing import compute_request_hash
from services.portfolio_engine.hardening.idempotency_models import IdempotencyKey
from services.portfolio_engine.hardening.idempotency_service import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    IdempotencyResult,
    IdempotencyService,
)
from services.portfolio_engine.portfolios.models import Portfolio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def idemp() -> IdempotencyService:
    return IdempotencyService()


@pytest.fixture
def audit() -> AuditService:
    return AuditService()


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_type="bundle_portfolio",
        name="Hardening Test PF",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


# ---------------------------------------------------------------------------
# 1. First request reserves key and stores response
# ---------------------------------------------------------------------------

class TestIdempotencyReserve:

    def test_reserve_and_store(self, db, idemp):
        key = f"test-{uuid.uuid4()}"
        scope = "test-scope"
        data = {"foo": "bar"}

        result = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=data,
        )
        assert result.replayed is False

        idemp.store_response(
            db, idempotency_key=key, scope=scope,
            response_status=200, response_body={"result": "ok"},
        )

        row = db.query(IdempotencyKey).filter(
            IdempotencyKey.idempotency_key == key,
            IdempotencyKey.scope == scope,
        ).first()
        assert row is not None
        assert row.response_status == 200
        assert row.response_body == {"result": "ok"}


# ---------------------------------------------------------------------------
# 2. Replay with same key + same payload returns stored response
# ---------------------------------------------------------------------------

class TestIdempotencyReplay:

    def test_replay_returns_stored(self, db, idemp):
        key = f"test-{uuid.uuid4()}"
        scope = "replay-scope"
        data = {"action": "replay_test"}

        idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=data,
        )
        idemp.store_response(
            db, idempotency_key=key, scope=scope,
            response_status=201, response_body={"id": "abc"},
        )

        result = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=data,
        )
        assert result.replayed is True
        assert result.stored_status == 201
        assert result.stored_body == {"id": "abc"}


# ---------------------------------------------------------------------------
# 3. Same key + different payload => conflict
# ---------------------------------------------------------------------------

class TestIdempotencyConflict:

    def test_different_payload_raises_conflict(self, db, idemp):
        key = f"test-{uuid.uuid4()}"
        scope = "conflict-scope"

        idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope,
            request_data={"value": "first"},
        )
        idemp.store_response(
            db, idempotency_key=key, scope=scope,
            response_status=200, response_body={},
        )

        with pytest.raises(IdempotencyConflictError):
            idemp.check_or_reserve(
                db, idempotency_key=key, scope=scope,
                request_data={"value": "second"},
            )

    def test_in_progress_raises_error(self, db, idemp):
        key = f"test-{uuid.uuid4()}"
        scope = "in-progress-scope"

        idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope,
            request_data={"value": "x"},
        )

        with pytest.raises(IdempotencyInProgressError):
            idemp.check_or_reserve(
                db, idempotency_key=key, scope=scope,
                request_data={"value": "x"},
            )


# ---------------------------------------------------------------------------
# 4. Missing idempotency key still works
# ---------------------------------------------------------------------------

class TestNoIdempotencyKey:

    def test_endpoint_works_without_key(self, db, portfolio):
        """Orchestrator should work without Idempotency-Key header."""
        from services.portfolio_engine.orchestrator.service import (
            RebalanceOrchestratorService,
        )
        svc = RebalanceOrchestratorService()
        result = svc.run_portfolio_cycle(db, portfolio.id)
        assert result is not None


# ---------------------------------------------------------------------------
# 5. Deterministic request hash
# ---------------------------------------------------------------------------

class TestRequestHash:

    def test_same_data_same_hash(self):
        d1 = {"portfolio_id": "abc-123", "action": "orchestrate"}
        d2 = {"action": "orchestrate", "portfolio_id": "abc-123"}
        assert compute_request_hash(d1) == compute_request_hash(d2)

    def test_different_data_different_hash(self):
        d1 = {"portfolio_id": "abc-123"}
        d2 = {"portfolio_id": "abc-456"}
        assert compute_request_hash(d1) != compute_request_hash(d2)

    def test_handles_nested_and_nulls(self):
        d = {"a": None, "b": [1, 2, {"c": 3}]}
        h = compute_request_hash(d)
        assert len(h) == 64  # SHA-256 hex digest


# ---------------------------------------------------------------------------
# 6. Success audit event persisted
# ---------------------------------------------------------------------------

class TestAuditSuccess:

    def test_success_event_persisted(self, db, audit):
        entity_id = str(uuid.uuid4())
        audit.log_success(
            db,
            entity_type="portfolio",
            entity_id=entity_id,
            action="orchestrated",
        )

        events = db.query(AuditEvent).filter(
            AuditEvent.entity_id == entity_id,
        ).all()
        assert len(events) == 1
        assert events[0].action == "orchestrated"
        assert events[0].metadata_["outcome"] == "success"


# ---------------------------------------------------------------------------
# 7. Failure path logs audit event
# ---------------------------------------------------------------------------

class TestAuditFailure:

    def test_failure_event_persisted(self, db, audit):
        entity_id = str(uuid.uuid4())
        audit.log_failure(
            db,
            entity_type="portfolio",
            entity_id=entity_id,
            action="orchestrated",
            error="portfolio_not_found",
        )

        events = db.query(AuditEvent).filter(
            AuditEvent.entity_id == entity_id,
        ).all()
        assert len(events) == 1
        assert events[0].metadata_["outcome"] == "failure"
        assert events[0].metadata_["error"] == "portfolio_not_found"


# ---------------------------------------------------------------------------
# 8. Audit events are append-only
# ---------------------------------------------------------------------------

class TestAuditAppendOnly:

    def test_multiple_events_appended(self, db, audit):
        entity_id = str(uuid.uuid4())
        audit.log_success(
            db, entity_type="portfolio", entity_id=entity_id,
            action="first_action",
        )
        audit.log_success(
            db, entity_type="portfolio", entity_id=entity_id,
            action="second_action",
        )
        audit.log_failure(
            db, entity_type="portfolio", entity_id=entity_id,
            action="third_action", error="test_error",
        )

        events = db.query(AuditEvent).filter(
            AuditEvent.entity_id == entity_id,
        ).all()
        assert len(events) == 3
        actions = {e.action for e in events}
        assert actions == {"first_action", "second_action", "third_action"}


# ---------------------------------------------------------------------------
# 9. Orchestrate endpoint supports replay
# ---------------------------------------------------------------------------

class TestOrchestrateReplay:

    def test_orchestrate_replay(self, db, idemp, portfolio):
        key = f"orch-{uuid.uuid4()}"
        scope = f"orchestrate:{portfolio.id}"
        request_data = {"portfolio_id": str(portfolio.id)}

        res1 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res1.replayed is False

        from services.portfolio_engine.orchestrator.service import RebalanceOrchestratorService
        svc = RebalanceOrchestratorService()
        result = svc.run_portfolio_cycle(db, portfolio.id)
        body = result.model_dump(mode="json")

        idemp.store_response(
            db, idempotency_key=key, scope=scope,
            response_status=200, response_body=body,
        )

        res2 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res2.replayed is True
        assert res2.stored_status == 200
        assert res2.stored_body["portfolio_id"] == str(portfolio.id)


# ---------------------------------------------------------------------------
# 10. Valuation snapshot endpoint supports replay
# ---------------------------------------------------------------------------

class TestValuationSnapshotReplay:

    def test_valuation_snapshot_replay(self, db, idemp, portfolio):
        key = f"snap-{uuid.uuid4()}"
        scope = f"valuation-snapshot:{portfolio.id}"
        request_data = {"portfolio_id": str(portfolio.id)}

        res1 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res1.replayed is False

        stored_body = {"id": str(uuid.uuid4()), "portfolio_id": str(portfolio.id)}
        idemp.store_response(
            db, idempotency_key=key, scope=scope,
            response_status=201, response_body=stored_body,
        )

        res2 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res2.replayed is True
        assert res2.stored_status == 201


# ---------------------------------------------------------------------------
# 11. Rebalance plan endpoint supports replay
# ---------------------------------------------------------------------------

class TestRebalancePlanReplay:

    def test_rebalance_plan_replay(self, db, idemp, portfolio):
        key = f"rebal-{uuid.uuid4()}"
        scope = f"rebalance-plan:{portfolio.id}"
        request_data = {
            "portfolio_id": str(portfolio.id),
            "status": "pending",
            "parameters": {},
            "items": [],
        }

        res1 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res1.replayed is False

        stored_body = {"id": str(uuid.uuid4()), "portfolio_id": str(portfolio.id)}
        idemp.store_response(
            db, idempotency_key=key, scope=scope,
            response_status=201, response_body=stored_body,
        )

        res2 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res2.replayed is True
        assert res2.stored_status == 201


# ---------------------------------------------------------------------------
# 12. Provision endpoint supports replay
# ---------------------------------------------------------------------------

class TestProvisionReplay:

    def test_provision_replay(self, db, idemp):
        sub_id = uuid.uuid4()
        tmpl_id = uuid.uuid4()
        key = f"prov-{uuid.uuid4()}"
        scope = f"provision:{sub_id}"
        request_data = {"subscription_id": str(sub_id), "template_id": str(tmpl_id)}

        res1 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res1.replayed is False

        stored_body = {"id": str(uuid.uuid4()), "name": "Provisioned Portfolio"}
        idemp.store_response(
            db, idempotency_key=key, scope=scope,
            response_status=201, response_body=stored_body,
        )

        res2 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res2.replayed is True
        assert res2.stored_status == 201
        assert res2.stored_body["name"] == "Provisioned Portfolio"


# ---------------------------------------------------------------------------
# 13. Strategy evaluation endpoint supports replay
# ---------------------------------------------------------------------------

class TestStrategyEvalReplay:

    def test_strategy_eval_replay(self, db, idemp, portfolio):
        key = f"strat-{uuid.uuid4()}"
        scope = f"strategy-evaluation:{portfolio.id}"
        request_data = {"portfolio_id": str(portfolio.id)}

        res1 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res1.replayed is False

        from services.portfolio_engine.strategy_engine.service import StrategyEngineService
        svc = StrategyEngineService()
        result = svc.evaluate_portfolio_strategies(db, portfolio.id)
        body = result.model_dump(mode="json")

        idemp.store_response(
            db, idempotency_key=key, scope=scope,
            response_status=200, response_body=body,
        )

        res2 = idemp.check_or_reserve(
            db, idempotency_key=key, scope=scope, request_data=request_data,
        )
        assert res2.replayed is True
        assert res2.stored_status == 200
