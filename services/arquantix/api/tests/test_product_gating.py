"""Tests for product eligibility gating — exchange + lending blocked if not eligible."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from database import Person
from services.compliance.eligibility_service import EligibilityService
from services.portfolio_engine.provisioning.errors import ClientNotEligibleError
from tests.conftest import make_linked_client


class TestEligibilityGateExchange:
    """ExchangeService.buy/sell/swap/sell_all should reject non-eligible clients."""

    def test_buy_blocked_for_non_approved_kyc(self, db: Session, monkeypatch):
        monkeypatch.setenv("DISABLE_ELIGIBILITY_CHECKS", "false")
        linked = make_linked_client(db, kyc_status="in_progress")

        from services.exchange.service import ExchangeService
        from services.exchange.schemas import ExchangeBuyRequest
        from services.portfolio_engine.hardening.security.context import ActorContext

        svc = ExchangeService()
        payload = ExchangeBuyRequest(
            client_id=linked.id,
            asset="BTC",
            fiat_amount=Decimal("100"),
            currency="EUR",
            external_reference=f"test-buy-{uuid.uuid4().hex[:8]}",
        )
        actor = ActorContext(actor_type="admin", actor_id="1", roles=["admin"])

        with pytest.raises(ClientNotEligibleError):
            svc.buy(db, payload, actor)

    def test_buy_allowed_for_approved_kyc_with_bypass_off(self, db: Session, monkeypatch):
        """Approved client should NOT raise ClientNotEligibleError (may fail later for other reasons)."""
        monkeypatch.setenv("DISABLE_ELIGIBILITY_CHECKS", "false")
        linked = make_linked_client(db, kyc_status="approved")

        from services.exchange.service import ExchangeService
        from services.exchange.schemas import ExchangeBuyRequest
        from services.portfolio_engine.hardening.security.context import ActorContext

        svc = ExchangeService()
        payload = ExchangeBuyRequest(
            client_id=linked.id,
            asset="BTC",
            fiat_amount=Decimal("100"),
            currency="EUR",
            external_reference=f"test-buy-{uuid.uuid4().hex[:8]}",
        )
        actor = ActorContext(actor_type="admin", actor_id="1", roles=["admin"])

        try:
            svc.buy(db, payload, actor)
        except ClientNotEligibleError:
            pytest.fail("ClientNotEligibleError should NOT be raised for approved client")
        except Exception:
            pass  # Other errors (price, balance) are expected — eligibility passed

    def test_buy_passes_when_checks_disabled(self, db: Session, monkeypatch):
        monkeypatch.setenv("DISABLE_ELIGIBILITY_CHECKS", "true")
        linked = make_linked_client(db, kyc_status="in_progress")

        from services.exchange.service import ExchangeService
        from services.exchange.schemas import ExchangeBuyRequest
        from services.portfolio_engine.hardening.security.context import ActorContext

        svc = ExchangeService()
        payload = ExchangeBuyRequest(
            client_id=linked.id,
            asset="BTC",
            fiat_amount=Decimal("100"),
            currency="EUR",
            external_reference=f"test-buy-{uuid.uuid4().hex[:8]}",
        )
        actor = ActorContext(actor_type="admin", actor_id="1", roles=["admin"])

        try:
            svc.buy(db, payload, actor)
        except ClientNotEligibleError:
            pytest.fail("ClientNotEligibleError should NOT be raised when checks disabled")
        except Exception:
            pass  # Other errors expected

    def test_sell_blocked_for_non_approved_kyc(self, db: Session, monkeypatch):
        monkeypatch.setenv("DISABLE_ELIGIBILITY_CHECKS", "false")
        linked = make_linked_client(db, kyc_status="rejected")

        from services.exchange.service import ExchangeService
        from services.exchange.schemas import ExchangeSellRequest
        from services.portfolio_engine.hardening.security.context import ActorContext

        svc = ExchangeService()
        payload = ExchangeSellRequest(
            client_id=linked.id,
            asset="BTC",
            amount_crypto=Decimal("0.01"),
            currency="EUR",
            external_reference=f"test-sell-{uuid.uuid4().hex[:8]}",
        )
        actor = ActorContext(actor_type="admin", actor_id="1", roles=["admin"])

        with pytest.raises(ClientNotEligibleError):
            svc.sell(db, payload, actor)


class TestEligibilityGateLending:
    """LendingService + PoolLendingService should reject non-eligible clients."""

    def test_create_loan_blocked_for_non_approved(self, db: Session, monkeypatch):
        monkeypatch.setenv("DISABLE_ELIGIBILITY_CHECKS", "false")
        lender = make_linked_client(db, kyc_status="in_progress")
        borrower = make_linked_client(db, kyc_status="approved")

        from services.lending.service import LendingService

        svc = LendingService()
        with pytest.raises(ClientNotEligibleError):
            svc.create_loan(
                db,
                lender_client_id=lender.id,
                borrower_client_id=borrower.id,
                asset="USDC",
                principal=Decimal("1000"),
                interest_rate_bps=500,
                duration_days=30,
            )

    def test_supply_commitment_blocked_for_non_approved(self, db: Session, monkeypatch):
        monkeypatch.setenv("DISABLE_ELIGIBILITY_CHECKS", "false")
        linked = make_linked_client(db, kyc_status="not_started")

        from services.lending.pool_service import PoolLendingService

        svc = PoolLendingService()
        with pytest.raises(ClientNotEligibleError):
            svc.create_supply_commitment(
                db,
                client_id=linked.id,
                asset="USDC",
                amount=Decimal("500"),
            )

    def test_borrow_blocked_for_non_approved(self, db: Session, monkeypatch):
        monkeypatch.setenv("DISABLE_ELIGIBILITY_CHECKS", "false")
        linked = make_linked_client(db, kyc_status="pending_review")

        from services.lending.pool_service import PoolLendingService

        svc = PoolLendingService()
        with pytest.raises(ClientNotEligibleError):
            svc.borrow_from_pool(
                db,
                borrower_client_id=linked.id,
                asset="USDC",
                amount=Decimal("500"),
            )


class TestAuditOnBlock:
    """Verify audit event is created when a client is blocked."""

    def test_blocked_creates_audit_event(self, db: Session, monkeypatch):
        from database import AuditEvent
        monkeypatch.setenv("DISABLE_ELIGIBILITY_CHECKS", "false")
        linked = make_linked_client(db, kyc_status="in_progress")
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        before_count = db.query(AuditEvent).filter(
            AuditEvent.event_type == "CLIENT_BLOCKED_BY_ELIGIBILITY",
            AuditEvent.person_id == person.id,
        ).count()

        with pytest.raises(ClientNotEligibleError):
            EligibilityService.require_eligible_by_client_id(db, linked.id)

        after_count = db.query(AuditEvent).filter(
            AuditEvent.event_type == "CLIENT_BLOCKED_BY_ELIGIBILITY",
            AuditEvent.person_id == person.id,
        ).count()

        assert after_count == before_count + 1
