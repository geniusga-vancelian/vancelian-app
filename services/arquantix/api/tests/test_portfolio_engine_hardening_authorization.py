"""Tests for Authorization / Ownership Scoping — Subphase A.

Covers:
 1. client can access own portfolio
 2. client cannot access another portfolio
 3. advisor can access assigned client portfolio
 4. advisor cannot access unassigned portfolio
 5. suspended assignment denies access
 6. revoked assignment denies access
 7. ops can access any portfolio
 8. admin can access any portfolio
 9. system can access any portfolio
10. valuation endpoint returns portfolio for owning client
11. valuation endpoint raises 403 for other client
12. performance endpoint raises 403 for unauthorized advisor
13. drift endpoint returns portfolio for assigned advisor
14. orchestration-runs endpoint raises 403 for unauthorized client
15. strategy-signals endpoint returns portfolio for assigned advisor
16. admin/ops can create assignment
17. client cannot create assignment (guard rejects)
18. patch status works
19. list assignments works
20. portfolio list filtered for client
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from conftest import make_linked_client
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.orchestrator.models import OrchestrationRun
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops
from services.portfolio_engine.hardening.authorization.models import AdvisorClientAssignment
from services.portfolio_engine.hardening.authorization.service import AuthorizationService
from services.portfolio_engine.hardening.authorization.dependencies import (
    require_orchestration_run_portfolio_access,
    require_portfolio_access,
    require_position_portfolio_access,
)
from services.portfolio_engine.hardening.authorization.repository import (
    AdvisorClientAssignmentRepository,
)
from services.portfolio_engine.hardening.authorization.router import (
    create_assignment,
    list_assignments,
    update_assignment,
)
from services.portfolio_engine.hardening.authorization.schemas import (
    AdvisorClientAssignmentCreate,
    AdvisorClientAssignmentUpdate,
)
from services.portfolio_engine.portfolios.router import list_portfolios
from services.portfolio_engine.portfolios.service import PortfolioService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_a(db: Session) -> Client:
    return make_linked_client(db, email=f"a_{uuid.uuid4().hex[:6]}@test.com", status="active", kyc_status="approved")


@pytest.fixture
def client_b(db: Session) -> Client:
    return make_linked_client(db, email=f"b_{uuid.uuid4().hex[:6]}@test.com", status="active", kyc_status="approved")


@pytest.fixture
def portfolio_a(db: Session, client_a: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=client_a.id, portfolio_type="bundle_portfolio",
        name="PF-A", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def portfolio_b(db: Session, client_b: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=client_b.id, portfolio_type="bundle_portfolio",
        name="PF-B", base_currency="EUR", status="active", metadata_={},
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


@pytest.fixture
def authz() -> AuthorizationService:
    return AuthorizationService()


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


def _system_ctx() -> ActorContext:
    return ActorContext(actor_type="system", actor_id=None, roles=["system"])


def _make_position_for_portfolio(db: Session, portfolio_id) -> PositionAtom:
    asset = Asset(
        id=uuid.uuid4(),
        symbol=f"AUTHZ_{uuid.uuid4().hex[:6]}",
        name="Test",
        asset_type="crypto",
        metadata_={},
    )
    db.add(asset)
    db.flush()
    inst = Instrument(
        id=uuid.uuid4(),
        asset_id=asset.id,
        code=f"AUTHZ-SPOT-{uuid.uuid4().hex[:4]}",
        name="Spot",
        instrument_type="spot",
        metadata_={},
    )
    db.add(inst)
    db.flush()
    pos = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio_id,
        instrument_id=inst.id,
        position_type="spot",
        status="open",
        quantity=Decimal("1"),
        available_quantity=Decimal("1"),
        realized_pnl=Decimal("0"),
        metadata_={},
    )
    db.add(pos)
    db.flush()
    return pos


# ---------------------------------------------------------------------------
# 1–9  AuthorizationService
# ---------------------------------------------------------------------------

class TestAuthorizationService:

    def test_client_can_access_own_portfolio(self, db, authz, client_a, portfolio_a):
        assert authz.can_access_portfolio(db, _client_ctx(str(client_a.id)), portfolio_a.id) is True

    def test_client_cannot_access_other_portfolio(self, db, authz, client_a, portfolio_b):
        assert authz.can_access_portfolio(db, _client_ctx(str(client_a.id)), portfolio_b.id) is False

    def test_advisor_can_access_assigned_client_portfolio(
        self, db, authz, advisor_id, active_assignment, portfolio_a,
    ):
        assert authz.can_access_portfolio(db, _advisor_ctx(advisor_id), portfolio_a.id) is True

    def test_advisor_cannot_access_unassigned_portfolio(
        self, db, authz, advisor_id, active_assignment, portfolio_b,
    ):
        assert authz.can_access_portfolio(db, _advisor_ctx(advisor_id), portfolio_b.id) is False

    def test_suspended_assignment_denies_access(
        self, db, authz, advisor_id, client_a, portfolio_a,
    ):
        a = AdvisorClientAssignment(
            advisor_actor_id=advisor_id, client_id=client_a.id,
            status="suspended", metadata_={},
        )
        db.add(a)
        db.flush()
        assert authz.can_access_portfolio(db, _advisor_ctx(advisor_id), portfolio_a.id) is False

    def test_revoked_assignment_denies_access(
        self, db, authz, advisor_id, client_a, portfolio_a,
    ):
        a = AdvisorClientAssignment(
            advisor_actor_id=advisor_id, client_id=client_a.id,
            status="revoked", metadata_={},
        )
        db.add(a)
        db.flush()
        assert authz.can_access_portfolio(db, _advisor_ctx(advisor_id), portfolio_a.id) is False

    def test_ops_can_access_any_portfolio(self, db, authz, portfolio_b):
        assert authz.can_access_portfolio(db, _ops_ctx(), portfolio_b.id) is True

    def test_admin_can_access_any_portfolio(self, db, authz, portfolio_b):
        assert authz.can_access_portfolio(db, _admin_ctx(), portfolio_b.id) is True

    def test_system_can_access_any_portfolio(self, db, authz, portfolio_b):
        assert authz.can_access_portfolio(db, _system_ctx(), portfolio_b.id) is True


# ---------------------------------------------------------------------------
# 10–15  Ownership dependencies / endpoint integration
# ---------------------------------------------------------------------------

class TestOwnershipDependencies:

    def test_valuation_returns_portfolio_for_owning_client(
        self, db, client_a, portfolio_a,
    ):
        result = require_portfolio_access(
            portfolio_id=portfolio_a.id,
            db=db,
            actor=_client_ctx(str(client_a.id)),
        )
        assert result.id == portfolio_a.id

    def test_valuation_raises_403_for_other_client(
        self, db, client_a, portfolio_b,
    ):
        with pytest.raises(HTTPException) as exc_info:
            require_portfolio_access(
                portfolio_id=portfolio_b.id,
                db=db,
                actor=_client_ctx(str(client_a.id)),
            )
        assert exc_info.value.status_code == 403

    def test_performance_raises_403_for_unauthorized_advisor(
        self, db, advisor_id, portfolio_b,
    ):
        with pytest.raises(HTTPException) as exc_info:
            require_portfolio_access(
                portfolio_id=portfolio_b.id,
                db=db,
                actor=_advisor_ctx(advisor_id),
            )
        assert exc_info.value.status_code == 403

    def test_drift_returns_portfolio_for_assigned_advisor(
        self, db, advisor_id, active_assignment, portfolio_a,
    ):
        result = require_portfolio_access(
            portfolio_id=portfolio_a.id,
            db=db,
            actor=_advisor_ctx(advisor_id),
        )
        assert result.id == portfolio_a.id

    def test_orchestration_runs_raises_403_for_unauthorized_client(
        self, db, client_b, portfolio_a,
    ):
        with pytest.raises(HTTPException) as exc_info:
            require_portfolio_access(
                portfolio_id=portfolio_a.id,
                db=db,
                actor=_client_ctx(str(client_b.id)),
            )
        assert exc_info.value.status_code == 403

    def test_strategy_signals_returns_portfolio_for_assigned_advisor(
        self, db, advisor_id, active_assignment, portfolio_a,
    ):
        result = require_portfolio_access(
            portfolio_id=portfolio_a.id,
            db=db,
            actor=_advisor_ctx(advisor_id),
        )
        assert result.id == portfolio_a.id

    def test_nonexistent_portfolio_raises_404(self, db, client_a):
        with pytest.raises(HTTPException) as exc_info:
            require_portfolio_access(
                portfolio_id=uuid.uuid4(),
                db=db,
                actor=_client_ctx(str(client_a.id)),
            )
        assert exc_info.value.status_code == 404

    def test_position_access_resolves_portfolio_for_owning_client(
        self, db, client_a, portfolio_a,
    ):
        pos = _make_position_for_portfolio(db, portfolio_a.id)
        result = require_position_portfolio_access(
            position_id=pos.id,
            db=db,
            actor=_client_ctx(str(client_a.id)),
        )
        assert result.id == pos.id

    def test_position_access_raises_403_for_other_client(
        self, db, client_a, portfolio_b,
    ):
        pos = _make_position_for_portfolio(db, portfolio_b.id)
        with pytest.raises(HTTPException) as exc_info:
            require_position_portfolio_access(
                position_id=pos.id,
                db=db,
                actor=_client_ctx(str(client_a.id)),
            )
        assert exc_info.value.status_code == 403

    def test_orchestration_run_access_for_owning_client(
        self, db, client_a, portfolio_a,
    ):
        run = OrchestrationRun(
            id=uuid.uuid4(),
            portfolio_id=portfolio_a.id,
            mode="test",
            signals_detected=0,
            actions_taken=0,
            status="completed",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()
        result = require_orchestration_run_portfolio_access(
            run_id=run.id,
            db=db,
            actor=_client_ctx(str(client_a.id)),
        )
        assert result.id == run.id

    def test_orchestration_run_access_raises_403_for_other_client(
        self, db, client_a, portfolio_b,
    ):
        run = OrchestrationRun(
            id=uuid.uuid4(),
            portfolio_id=portfolio_b.id,
            mode="test",
            signals_detected=0,
            actions_taken=0,
            status="completed",
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()
        with pytest.raises(HTTPException) as exc_info:
            require_orchestration_run_portfolio_access(
                run_id=run.id,
                db=db,
                actor=_client_ctx(str(client_a.id)),
            )
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# 16–19  Admin assignment endpoints
# ---------------------------------------------------------------------------

class TestAdminAssignmentEndpoints:

    def test_admin_can_create_assignment(self, db, client_a):
        advisor = str(uuid.uuid4())
        body = AdvisorClientAssignmentCreate(
            advisor_actor_id=advisor,
            client_id=client_a.id,
        )
        result = create_assignment(body=body, db=db, actor=_admin_ctx())
        assert result.advisor_actor_id == advisor
        assert result.status == "active"

    def test_client_cannot_create_assignment_guard(self):
        guard = require_admin_or_ops()
        with pytest.raises(HTTPException) as exc_info:
            guard(actor=_client_ctx("c1"))
        assert exc_info.value.status_code == 403

    def test_patch_status_works(self, db, client_a):
        advisor = str(uuid.uuid4())
        body = AdvisorClientAssignmentCreate(advisor_actor_id=advisor, client_id=client_a.id)
        created = create_assignment(body=body, db=db, actor=_admin_ctx())

        update_body = AdvisorClientAssignmentUpdate(status="suspended")
        updated = update_assignment(
            assignment_id=created.id, body=update_body, db=db, actor=_admin_ctx(),
        )
        assert updated.status == "suspended"

    def test_list_assignments_works(self, db, client_a, client_b):
        adv = str(uuid.uuid4())
        body1 = AdvisorClientAssignmentCreate(advisor_actor_id=adv, client_id=client_a.id)
        body2 = AdvisorClientAssignmentCreate(advisor_actor_id=adv, client_id=client_b.id)
        create_assignment(body=body1, db=db, actor=_admin_ctx())
        create_assignment(body=body2, db=db, actor=_admin_ctx())

        result = list_assignments(
            advisor_actor_id=adv, client_id=None, status_filter=None,
            skip=0, limit=50, db=db, actor=_admin_ctx(),
        )
        assert result.total >= 2


# ---------------------------------------------------------------------------
# 20  Portfolio list filtering
# ---------------------------------------------------------------------------

class TestPortfolioListFiltering:

    def test_client_sees_only_own_portfolios(
        self, db, client_a, client_b, portfolio_a, portfolio_b,
    ):
        svc = PortfolioService()
        authz = AuthorizationService()
        actor = _client_ctx(str(client_a.id))

        scoped_client_id = uuid.UUID(actor.actor_id) if actor.actor_id else None
        items, total = svc.list_portfolios(db, client_id=scoped_client_id, skip=0, limit=50)

        ids = [p.id for p in items]
        assert portfolio_a.id in ids
        assert portfolio_b.id not in ids

    def test_advisor_sees_only_assigned_portfolios(
        self, db, client_a, client_b, portfolio_a, portfolio_b,
        advisor_id, active_assignment,
    ):
        svc = PortfolioService()
        authz = AuthorizationService()
        assigned = authz.get_accessible_client_ids_for_advisor(db, advisor_id)

        items, total = svc.list_portfolios(db, client_ids=assigned, skip=0, limit=50)

        ids = [p.id for p in items]
        assert portfolio_a.id in ids
        assert portfolio_b.id not in ids

    def test_admin_sees_all_portfolios(
        self, db, client_a, client_b, portfolio_a, portfolio_b,
    ):
        svc = PortfolioService()
        items, total = svc.list_portfolios(db, skip=0, limit=50)

        ids = [p.id for p in items]
        assert portfolio_a.id in ids
        assert portfolio_b.id in ids
