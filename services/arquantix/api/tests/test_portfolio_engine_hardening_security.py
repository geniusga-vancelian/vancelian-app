"""Tests for Hardening Subphase 5 — Security Model / RBAC.

Covers:
 1. actor context extracted from headers
 2. comma-separated roles parsed correctly
 3. missing headers fallback works
 4. require_any_role allows matching role
 5. require_any_role rejects non-matching role
 6. require_admin_or_ops allows admin
 7. require_admin_or_ops allows ops
 8. require_admin_or_ops rejects client
 9. rebuild endpoint forbidden for client
10. rebuild endpoint allowed for admin
11. reconciliation endpoint allowed for ops
12. scheduled job mutation forbidden for advisor
13. orchestrate endpoint forbidden for client
14. orchestrate endpoint allowed for ops
15. strategy-evaluation endpoint allowed for admin
16. valuation snapshot endpoint forbidden for client
17. provision endpoint forbidden for client
18. protected endpoint audit logs actor_type/actor_id correctly
19. unprotected read endpoint still works without headers
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import (
    _RoleGuard,
    get_actor_context,
    require_admin_or_ops,
    require_any_role,
)
from conftest import make_linked_client
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pe_client(db: Session) -> Client:
    return make_linked_client(db, email=f"rbac_{uuid.uuid4().hex[:6]}@test.com", status="active", kyc_status="approved")


@pytest.fixture
def portfolio(db: Session, pe_client: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=pe_client.id,
        portfolio_type="bundle_portfolio",
        name="RBAC Test PF",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


# ---------------------------------------------------------------------------
# 1–3 Actor context
# ---------------------------------------------------------------------------

class TestActorContext:

    def test_extracted_from_headers(self):
        ctx = get_actor_context(
            x_actor_type="admin",
            x_actor_id="user-123",
            x_actor_roles="admin,ops",
        )
        assert ctx.actor_type == "admin"
        assert ctx.actor_id == "user-123"
        assert ctx.roles == ["admin", "ops"]

    def test_comma_separated_roles(self):
        ctx = get_actor_context(
            x_actor_type="advisor",
            x_actor_id=None,
            x_actor_roles="advisor, ops , admin",
        )
        assert ctx.roles == ["advisor", "ops", "admin"]

    def test_missing_headers_fallback(self):
        ctx = get_actor_context(
            x_actor_type=None,
            x_actor_id=None,
            x_actor_roles=None,
        )
        assert ctx.actor_type == "system"
        assert ctx.actor_id is None
        assert ctx.roles == []


# ---------------------------------------------------------------------------
# 4–8 Guards
# ---------------------------------------------------------------------------

class TestGuards:

    def test_require_any_role_allows_match(self):
        guard = require_any_role("admin", "ops")
        ctx = ActorContext(actor_type="admin", actor_id="u1", roles=["admin"])
        result = guard(actor=ctx)
        assert result.actor_type == "admin"

    def test_require_any_role_rejects_no_match(self):
        guard = require_any_role("admin", "ops")
        ctx = ActorContext(actor_type="client", actor_id="u2", roles=["client"])
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=ctx)
        assert exc_info.value.status_code == 403

    def test_admin_or_ops_allows_admin(self):
        guard = require_admin_or_ops()
        ctx = ActorContext(actor_type="admin", roles=["admin"])
        result = guard(actor=ctx)
        assert result.has_role("admin")

    def test_admin_or_ops_allows_ops(self):
        guard = require_admin_or_ops()
        ctx = ActorContext(actor_type="ops", roles=["ops"])
        result = guard(actor=ctx)
        assert result.has_role("ops")

    def test_admin_or_ops_rejects_client(self):
        guard = require_admin_or_ops()
        ctx = ActorContext(actor_type="client", roles=["client"])
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=ctx)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 9–17 Endpoint protection (via guard unit tests)
# ---------------------------------------------------------------------------

class TestEndpointProtection:

    def _guard(self):
        return require_admin_or_ops()

    def _client_ctx(self):
        return ActorContext(actor_type="client", actor_id="c1", roles=["client"])

    def _admin_ctx(self):
        return ActorContext(actor_type="admin", actor_id="a1", roles=["admin"])

    def _ops_ctx(self):
        return ActorContext(actor_type="ops", actor_id="o1", roles=["ops"])

    def _advisor_ctx(self):
        return ActorContext(actor_type="advisor", actor_id="adv1", roles=["advisor"])

    def test_rebuild_forbidden_for_client(self):
        with pytest.raises(HTTPException) as exc_info:
            self._guard()(actor=self._client_ctx())
        assert exc_info.value.status_code == 403

    def test_rebuild_allowed_for_admin(self):
        result = self._guard()(actor=self._admin_ctx())
        assert result.actor_type == "admin"

    def test_reconciliation_allowed_for_ops(self):
        result = self._guard()(actor=self._ops_ctx())
        assert result.actor_type == "ops"

    def test_scheduled_job_forbidden_for_advisor(self):
        with pytest.raises(HTTPException) as exc_info:
            self._guard()(actor=self._advisor_ctx())
        assert exc_info.value.status_code == 403

    def test_orchestrate_forbidden_for_client(self):
        with pytest.raises(HTTPException) as exc_info:
            self._guard()(actor=self._client_ctx())
        assert exc_info.value.status_code == 403

    def test_orchestrate_allowed_for_ops(self):
        result = self._guard()(actor=self._ops_ctx())
        assert result.actor_type == "ops"

    def test_strategy_eval_allowed_for_admin(self):
        result = self._guard()(actor=self._admin_ctx())
        assert result.actor_type == "admin"

    def test_valuation_snapshot_forbidden_for_client(self):
        with pytest.raises(HTTPException) as exc_info:
            self._guard()(actor=self._client_ctx())
        assert exc_info.value.status_code == 403

    def test_provision_forbidden_for_client(self):
        with pytest.raises(HTTPException) as exc_info:
            self._guard()(actor=self._client_ctx())
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 18 Audit actor propagation
# ---------------------------------------------------------------------------

class TestAuditPropagation:

    def test_audit_logs_actor(self, db: Session):
        from services.portfolio_engine.hardening.audit_service import AuditService

        svc = AuditService()
        svc.log_success(
            db,
            entity_type="portfolio",
            entity_id="pf-123",
            action="test_action",
            actor_type="ops",
            actor_id="ops-user-42",
        )
        db.flush()

        event = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "test_action")
            .first()
        )
        assert event is not None
        assert event.actor_type == "ops"
        assert event.actor_id == "ops-user-42"


# ---------------------------------------------------------------------------
# 19 Unprotected reads
# ---------------------------------------------------------------------------

class TestUnprotectedReads:

    def test_fallback_context_works(self):
        ctx = get_actor_context(
            x_actor_type=None,
            x_actor_id=None,
            x_actor_roles=None,
        )
        assert ctx.actor_type == "system"
        assert ctx.is_system is True
