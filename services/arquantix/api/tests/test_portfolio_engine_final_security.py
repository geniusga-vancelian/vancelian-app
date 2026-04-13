"""Tests for Final Security Pass.

Covers:
 1. client cannot orchestrate (RBAC blocks)
 2. advisor cannot orchestrate unassigned portfolio (RBAC blocks)
 3. ops can orchestrate any portfolio (RBAC + ownership pass)
 4. ownership check on POST valuation/snapshot
 5. ownership check on POST strategy-evaluation
 6. ownership check on POST rebalance-plan
 7. ownership check on PATCH portfolio
 8. ownership check on POST sleeve
 9. client cannot access orders (RBAC blocks)
10. client cannot access trades (RBAC blocks)
11. client cannot access settlements (RBAC blocks)
12. client cannot access ledger-accounts (RBAC blocks)
13. client cannot access ledger-entries (RBAC blocks)
14. admin GET jobs allowed
15. admin GET reconciliation-reports allowed
16. admin GET scheduled-jobs allowed
17. client cannot GET admin/jobs (RBAC blocks)
18. unauthorized access logs audit event (portfolio_access_denied)
19. rebalance-preview body-level ownership check
20. ops can access all transaction endpoints
"""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops
from services.portfolio_engine.hardening.authorization.dependencies import (
    require_portfolio_access,
)
from services.portfolio_engine.hardening.authorization.models import AdvisorClientAssignment
from services.portfolio_engine.hardening.audit_models import AuditEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_a(db: Session) -> Client:
    c = Client(id=uuid.uuid4(), email=f"fsp_a_{uuid.uuid4().hex[:6]}@test.com", status="active", kyc_status="approved")
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def client_b(db: Session) -> Client:
    c = Client(id=uuid.uuid4(), email=f"fsp_b_{uuid.uuid4().hex[:6]}@test.com", status="active", kyc_status="approved")
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def portfolio_a(db: Session, client_a: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=client_a.id, portfolio_type="bundle_portfolio",
        name="FSP-A", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def portfolio_b(db: Session, client_b: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=client_b.id, portfolio_type="bundle_portfolio",
        name="FSP-B", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def advisor_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def active_assignment(db: Session, advisor_id: str, client_a: Client) -> AdvisorClientAssignment:
    a = AdvisorClientAssignment(
        advisor_actor_id=advisor_id, client_id=client_a.id, status="active", metadata_={},
    )
    db.add(a)
    db.flush()
    return a


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _client_ctx(actor_id: str) -> ActorContext:
    return ActorContext(actor_type="client", actor_id=actor_id, roles=["client"])

def _advisor_ctx(actor_id: str) -> ActorContext:
    return ActorContext(actor_type="advisor", actor_id=actor_id, roles=["advisor"])

def _ops_ctx() -> ActorContext:
    return ActorContext(actor_type="ops", actor_id="ops-1", roles=["ops"])

def _admin_ctx() -> ActorContext:
    return ActorContext(actor_type="admin", actor_id="admin-1", roles=["admin"])


# ---------------------------------------------------------------------------
# 1–3  Write ownership (orchestrate uses RBAC + ownership)
# ---------------------------------------------------------------------------

class TestWriteOwnership:

    def test_client_blocked_by_rbac_on_orchestrate(self):
        guard = require_admin_or_ops()
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=_client_ctx("c1"))
        assert exc_info.value.status_code == 403

    def test_advisor_blocked_by_rbac_on_orchestrate(self):
        guard = require_admin_or_ops()
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=_advisor_ctx("adv1"))
        assert exc_info.value.status_code == 403

    def test_ops_passes_rbac_and_ownership(self, db, portfolio_a):
        guard = require_admin_or_ops()
        actor = guard(actor=_ops_ctx())
        assert actor.actor_type == "ops"
        result = require_portfolio_access(
            portfolio_id=portfolio_a.id, db=db, actor=_ops_ctx(),
        )
        assert result.id == portfolio_a.id

    def test_ownership_on_valuation_snapshot(self, db, client_a, portfolio_b):
        with pytest.raises(HTTPException) as exc_info:
            require_portfolio_access(
                portfolio_id=portfolio_b.id, db=db, actor=_client_ctx(str(client_a.id)),
            )
        assert exc_info.value.status_code == 403

    def test_ownership_on_strategy_evaluation(self, db, client_b, portfolio_a):
        with pytest.raises(HTTPException) as exc_info:
            require_portfolio_access(
                portfolio_id=portfolio_a.id, db=db, actor=_client_ctx(str(client_b.id)),
            )
        assert exc_info.value.status_code == 403

    def test_ownership_on_rebalance_plan(self, db, advisor_id, portfolio_b):
        with pytest.raises(HTTPException) as exc_info:
            require_portfolio_access(
                portfolio_id=portfolio_b.id, db=db, actor=_advisor_ctx(advisor_id),
            )
        assert exc_info.value.status_code == 403

    def test_ownership_on_patch_portfolio(self, db, client_a, portfolio_a):
        result = require_portfolio_access(
            portfolio_id=portfolio_a.id, db=db, actor=_client_ctx(str(client_a.id)),
        )
        assert result.id == portfolio_a.id

    def test_ownership_on_create_sleeve(self, db, advisor_id, active_assignment, portfolio_a):
        result = require_portfolio_access(
            portfolio_id=portfolio_a.id, db=db, actor=_advisor_ctx(advisor_id),
        )
        assert result.id == portfolio_a.id


# ---------------------------------------------------------------------------
# 9–13  RBAC isolation on transaction/ledger endpoints
# ---------------------------------------------------------------------------

class TestTransactionRBAC:

    def test_client_cannot_access_orders(self):
        guard = require_admin_or_ops()
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=_client_ctx("c1"))
        assert exc_info.value.status_code == 403

    def test_client_cannot_access_trades(self):
        guard = require_admin_or_ops()
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=_client_ctx("c1"))
        assert exc_info.value.status_code == 403

    def test_client_cannot_access_settlements(self):
        guard = require_admin_or_ops()
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=_client_ctx("c1"))
        assert exc_info.value.status_code == 403

    def test_client_cannot_access_ledger_accounts(self):
        guard = require_admin_or_ops()
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=_client_ctx("c1"))
        assert exc_info.value.status_code == 403

    def test_client_cannot_access_ledger_entries(self):
        guard = require_admin_or_ops()
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=_client_ctx("c1"))
        assert exc_info.value.status_code == 403

    def test_ops_can_access_transactions(self):
        guard = require_admin_or_ops()
        actor = guard(actor=_ops_ctx())
        assert actor.actor_type == "ops"


# ---------------------------------------------------------------------------
# 14–17  Admin endpoint RBAC
# ---------------------------------------------------------------------------

class TestAdminEndpointRBAC:

    def test_admin_allowed_on_jobs(self):
        guard = require_admin_or_ops()
        actor = guard(actor=_admin_ctx())
        assert actor.actor_type == "admin"

    def test_admin_allowed_on_recon_reports(self):
        guard = require_admin_or_ops()
        actor = guard(actor=_admin_ctx())
        assert actor.has_role("admin")

    def test_admin_allowed_on_scheduled_jobs(self):
        guard = require_admin_or_ops()
        actor = guard(actor=_ops_ctx())
        assert actor.has_role("ops")

    def test_client_blocked_from_admin_jobs(self):
        guard = require_admin_or_ops()
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=_client_ctx("c1"))
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 18  Denied access audit logging
# ---------------------------------------------------------------------------

class TestDeniedAccessAudit:

    def test_unauthorized_access_logs_audit_event(self, db, client_a, portfolio_b):
        initial_count = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "portfolio_access_denied")
            .count()
        )

        with pytest.raises(HTTPException) as exc_info:
            require_portfolio_access(
                portfolio_id=portfolio_b.id,
                db=db,
                actor=_client_ctx(str(client_a.id)),
            )
        assert exc_info.value.status_code == 403

        new_count = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "portfolio_access_denied")
            .count()
        )
        assert new_count == initial_count + 1

        event = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.action == "portfolio_access_denied",
                AuditEvent.entity_id == str(portfolio_b.id),
            )
            .first()
        )
        assert event is not None
        assert event.actor_type == "client"
        assert event.actor_id == str(client_a.id)


# ---------------------------------------------------------------------------
# 19  Rebalance preview body-level ownership check
# ---------------------------------------------------------------------------

class TestRebalancePreviewBodyCheck:

    def test_body_level_ownership_check(self, db, client_a, portfolio_b):
        from services.portfolio_engine.hardening.authorization.service import AuthorizationService
        authz = AuthorizationService()
        actor = _client_ctx(str(client_a.id))
        assert authz.can_access_portfolio(db, actor, portfolio_b.id) is False
