"""
Pytest configuration and shared fixtures.

Test isolation strategy:
- Every test function gets its own DB transaction that is rolled back at the end.
- The FastAPI TestClient is wired to share this same transaction via a get_db override.
- This prevents tests from permanently polluting the real local database.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import event

from database import SessionLocal, Base, engine, get_db, Person
from services.portfolio_engine.clients.models import Client as _Client  # noqa: F401 — force mapper init
import services.presentations.models as _PresentationDeckModels  # noqa: F401 — presentation ORM
import services.test_clients.operation_statement_snapshot_model as _OperationStatementSnapshots  # noqa: F401 — PR5 ORM
import services.portfolio_engine.bundle_ledger.models as _BundleLedgerModels  # noqa: F401 — Phase 4A ORM
import services.cost_basis.models as _CostBasisModels  # noqa: F401 — Cost basis V2 ORM
import services.transaction_outbox.models as _TransactionOutboxModels  # noqa: F401 — Phase 2 S1 ORM
import services.portfolio_engine.financial_operations.models as _PortfolioFinancialOpsModels  # noqa: F401 — PR-4 ORM


@pytest.fixture(scope="session", autouse=True)
def _main_app_testing_mode_for_zero_trust():
    """``main.app`` (non ``create_app(testing=True)``) : active le mode testing pour les garde-fous ZT."""
    import main as _main_module

    _main_module.app.state.testing = True


@pytest.fixture(autouse=True)
def _disable_auth_security_events_isolated_writes(monkeypatch):
    """Évite la pollution DB : les événements « isolated » utilisent SessionLocal + commit."""
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "false")


@pytest.fixture(scope="function")
def test_app():
    """FastAPI app in testing mode (create_app(testing=True)). No heavy startup."""
    from main import create_app
    return create_app(testing=True)


@pytest.fixture(scope="function")
def db():
    """
    Database session fixture with transaction rollback.
    Each test runs in a transaction that is rolled back at the end.
    """
    connection = engine.connect()
    trans = connection.begin()
    session = SessionLocal(bind=connection)

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if connection.in_nested_transaction():
            connection.begin_nested()

    connection.begin_nested()

    from services.cost_basis.models import CostBasisExecution

    CostBasisExecution.__table__.create(bind=connection, checkfirst=True)

    try:
        yield session
    finally:
        if connection.in_nested_transaction():
            connection.rollback()
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(test_app, db):
    """TestClient that shares the transactional db session.

    All HTTP calls through this client use the same DB session (via get_db
    override), so every INSERT/UPDATE is rolled back when the test ends.
    This is the key fix that prevents test pollution of the real database.
    """
    def _override_get_db():
        yield db

    test_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(test_app) as c:
        yield c
    test_app.dependency_overrides.pop(get_db, None)


def make_linked_client(db: Session, **overrides):
    """Helper: create a Client with a properly linked Person (required since person_id is NOT NULL).

    Usage in test fixtures:
        client = make_linked_client(db, email="test@example.com", kyc_status="approved")
    """
    from services.portfolio_engine.clients.models import Client

    defaults = {
        "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "status": "active",
        "kyc_status": "approved",
    }
    defaults.update(overrides)

    person = Person(
        id=uuid.uuid4(),
        status="active",
        profile_json={
            "security": {"local_passcode_registered_at": "2020-01-01T00:00:00Z"},
        },
        kyc_status=defaults["kyc_status"],
    )
    db.add(person)
    db.flush()

    client_obj = Client(
        id=overrides.get("id", uuid.uuid4()),
        email=defaults["email"],
        status=defaults["status"],
        kyc_status=defaults["kyc_status"],
        person_id=person.id,
    )
    db.add(client_obj)
    db.flush()

    person.client_id = client_obj.id
    db.flush()

    return client_obj


def ensure_admin_for_linked_client(db: Session, pe_client, *, password: str = "test"):
    """Crée un ``AdminUser`` lié au ``pe_client`` s’il manque (JWT ``sub`` = ``au:<id>``)."""
    from auth import get_password_hash
    from database import AdminUser

    u = db.query(AdminUser).filter(AdminUser.person_id == pe_client.person_id).first()
    if u is not None:
        return u
    email = getattr(pe_client, "email", None) or f"au-{uuid.uuid4().hex[:8]}@example.com"
    u = AdminUser(
        email=email,
        hashed_password=get_password_hash(password),
        person_id=pe_client.person_id,
    )
    db.add(u)
    db.flush()
    return u


def make_admin_user_with_pe_client(db: Session, *, email: str, password: str):
    """``AdminUser`` lié à une Person + ``pe_clients`` — requis pour ``/auth/login`` et refresh JWT."""
    from auth import get_password_hash
    from database import AdminUser, Person

    pe = make_linked_client(db, email=email)
    person = db.query(Person).filter(Person.id == pe.person_id).first()
    if person is not None:
        pj = dict(person.profile_json or {})
        sec = dict(pj.get("security") or {})
        sec.setdefault("local_passcode_registered_at", "2020-01-01T00:00:00Z")
        pj["security"] = sec
        person.profile_json = pj
        db.add(person)
        db.flush()
    u = AdminUser(
        email=email,
        hashed_password=get_password_hash(password),
        person_id=pe.person_id,
    )
    db.add(u)
    db.flush()
    return u


def mobile_auth_headers(
    db: Session,
    pe_client,
    *,
    create_user_if_missing: bool = True,
) -> dict:
    """En-têtes Bearer pour les routes ``/api/app/*`` (JWT : ``sub`` = ``au:<admin_users.id>``).

    Par défaut, crée un ``AdminUser`` minimal si absent (confort de test).
    Passez ``create_user_if_missing=False`` pour échouer explicitement si aucun compte
    n’existe (détection de trous de fixture).
    """
    from auth import create_access_token, get_password_hash
    from database import AdminUser
    from services.auth.jwt_user_claims import build_user_jwt_access_base_claims

    u = db.query(AdminUser).filter(AdminUser.person_id == pe_client.person_id).first()
    if u is None:
        if not create_user_if_missing:
            raise AssertionError(
                "mobile_auth_headers: aucun AdminUser pour ce pe_client "
                "(create_user_if_missing=False). Créez-le (ex. make_admin_user_with_pe_client)."
            )
        u = AdminUser(
            email=pe_client.email,
            hashed_password=get_password_hash("test-mobile-auth-headers"),
            person_id=pe_client.person_id,
        )
        db.add(u)
        db.flush()
    token = create_access_token(build_user_jwt_access_base_claims(u))
    return {"Authorization": f"Bearer {token}"}


def make_admin_headers(db: Session) -> dict:
    """Create an admin user + JWT and return auth headers for API tests."""
    from database import AdminUser
    from auth import create_access_token, get_password_hash
    from services.auth.jwt_user_claims import build_user_jwt_access_base_claims

    email = "admin-test@example.com"
    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if user is None:
        user = AdminUser(email=email, hashed_password=get_password_hash("test"))
        db.add(user)
        db.flush()
    token = create_access_token(build_user_jwt_access_base_claims(user))
    return {"Authorization": f"Bearer {token}"}


def custody_admin_headers(db: Session) -> dict:
    """JWT admin + en-têtes X-Actor (requis pour certaines routes custody admin)."""
    return {
        "X-Actor-Type": "admin",
        "X-Actor-Id": "test-admin@example.com",
        "X-Actor-Roles": "admin",
        **make_admin_headers(db),
    }


@pytest.fixture(scope="function")
def chatbot_client(test_app, client, db):
    """Client with get_llm_client overridden to FakeLLMClient. Use for chatbot HTTP tests (no OpenAI)."""
    from services.chatbot_epargne.routes import get_llm_client
    from services.chatbot_epargne.ai.llm import FakeLLMClient
    test_app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()
    try:
        yield client
    finally:
        test_app.dependency_overrides.pop(get_llm_client, None)
