"""Centralized Eligibility Engine.

Single source of truth for determining whether a client is authorized
to access products (trading, lending, exclusive offers).

V1 checks:
  - kyc_ok    : person.kyc_status == "approved"
  - aml_ok    : derived from aml_status (non-blocking until ENABLE_AML_BLOCKING=True)
  - risk_ok   : person risk_tier != "high"
  - aml_status: explicit state — "not_checked" | "pending" | "verified" | "failed"
"""
import logging
import uuid as uuid_mod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import AuditEvent, Person

logger = logging.getLogger(__name__)

from services.portfolio_engine.provisioning.errors import ClientNotEligibleError

AML_STATUS_NOT_CHECKED = "not_checked"
AML_STATUS_PENDING = "pending"
AML_STATUS_VERIFIED = "verified"
AML_STATUS_FAILED = "failed"


@dataclass
class EligibilityResult:
    eligible: bool
    reasons: List[str] = field(default_factory=list)
    kyc_ok: bool = False
    aml_ok: bool = False
    aml_status: str = AML_STATUS_NOT_CHECKED
    risk_ok: bool = True


class EligibilityService:
    """Stateless service — call evaluate_client_eligibility()."""

    @staticmethod
    def evaluate_client_eligibility(
        db: Session,
        person: Person,
        client: Any = None,
    ) -> EligibilityResult:
        """Evaluate all eligibility criteria for a client.

        Args:
            db: Database session (used for audit logging).
            person: The Person record (source of truth for KYC/compliance).
            client: The pe_client record (optional, for future per-product rules).

        Returns:
            EligibilityResult with detailed pass/fail per criterion.
        """
        from core.env import enable_aml_blocking

        reasons: List[str] = []

        kyc_ok = person.kyc_status == "approved"
        if not kyc_ok:
            reasons.append(f"kyc_status is '{person.kyc_status}', expected 'approved'")

        # AML — explicit status, non-blocking until ENABLE_AML_BLOCKING
        aml_status = AML_STATUS_NOT_CHECKED
        aml_ok = (aml_status == AML_STATUS_VERIFIED)

        aml_blocks = False
        if enable_aml_blocking() and not aml_ok:
            aml_blocks = True
            reasons.append(f"aml_status is '{aml_status}', expected 'verified'")

        # Risk tier from profile_json derived fields
        risk_ok = True
        risk_tier_data = (person.profile_json or {}).get("risk-tier-current")
        if isinstance(risk_tier_data, dict):
            risk_tier = risk_tier_data.get("value")
        else:
            risk_tier = risk_tier_data

        if risk_tier == "high":
            risk_ok = False
            reasons.append("risk_tier is 'high'")

        eligible = kyc_ok and risk_ok and (not aml_blocks)

        result = EligibilityResult(
            eligible=eligible,
            reasons=reasons,
            kyc_ok=kyc_ok,
            aml_ok=aml_ok,
            aml_status=aml_status,
            risk_ok=risk_ok,
        )

        EligibilityService._log_audit(
            db,
            person_id=person.id,
            result=result,
        )

        return result

    @staticmethod
    def require_eligible_by_client_id(
        db: Session,
        client_id: UUID,
    ) -> EligibilityResult:
        """Gate: resolve person from client_id, evaluate, raise if blocked.

        Respects DISABLE_ELIGIBILITY_CHECKS flag for emergency bypass.
        Logs CLIENT_BLOCKED_BY_ELIGIBILITY audit event on rejection.
        """
        from core.env import disable_eligibility_checks

        if disable_eligibility_checks():
            logger.warning("eligibility_check_bypassed client_id=%s (DISABLE_ELIGIBILITY_CHECKS=true)", client_id)
            return EligibilityResult(eligible=True, kyc_ok=True, aml_ok=True, aml_status=AML_STATUS_NOT_CHECKED, risk_ok=True)

        def _get_client_model():
            from services.portfolio_engine.clients.models import Client
            return Client
        Client = _get_client_model()

        client = db.query(Client).filter(Client.id == client_id).first()
        if client is None:
            result = EligibilityResult(eligible=False, reasons=["client_not_found"], kyc_ok=False, aml_ok=False, aml_status=AML_STATUS_NOT_CHECKED, risk_ok=False)
            raise ClientNotEligibleError(client_id, "; ".join(result.reasons))

        if client.person_id is None:
            result = EligibilityResult(eligible=False, reasons=["no_linked_person"], kyc_ok=False, aml_ok=False, aml_status=AML_STATUS_NOT_CHECKED, risk_ok=False)
            raise ClientNotEligibleError(client_id, "; ".join(result.reasons))

        person = db.query(Person).filter(Person.id == client.person_id).first()
        if person is None:
            result = EligibilityResult(eligible=False, reasons=["person_not_found"], kyc_ok=False, aml_ok=False, aml_status=AML_STATUS_NOT_CHECKED, risk_ok=False)
            raise ClientNotEligibleError(client_id, "; ".join(result.reasons))

        result = EligibilityService.evaluate_client_eligibility(db, person, client)
        if not result.eligible:
            EligibilityService._log_blocked_audit(db, person_id=person.id, client_id=client_id, result=result)
            raise ClientNotEligibleError(client_id, "; ".join(result.reasons))

        return result

    @staticmethod
    def evaluate_by_person_id(
        db: Session,
        person_id: UUID,
    ) -> EligibilityResult:
        """Convenience wrapper that fetches the Person first."""
        person = db.query(Person).filter(Person.id == person_id).first()
        if person is None:
            return EligibilityResult(
                eligible=False,
                reasons=["person_not_found"],
                kyc_ok=False,
                aml_ok=False,
                risk_ok=False,
            )
        return EligibilityService.evaluate_client_eligibility(db, person)

    @staticmethod
    def _log_audit(
        db: Session,
        *,
        person_id: UUID,
        result: EligibilityResult,
    ) -> None:
        try:
            event = AuditEvent(
                id=uuid_mod.uuid4(),
                person_id=person_id,
                event_type="CLIENT_ELIGIBILITY_EVALUATED",
                actor_type="system",
                actor_id=None,
                correlation_id=uuid_mod.uuid4(),
                payload={
                    "person_id": str(person_id),
                    "eligible": result.eligible,
                    "kyc_ok": result.kyc_ok,
                    "aml_ok": result.aml_ok,
                    "aml_status": result.aml_status,
                    "risk_ok": result.risk_ok,
                    "reasons": result.reasons,
                },
                schema_version=1,
                created_at=datetime.now(timezone.utc),
            )
            db.add(event)
            db.flush()
        except Exception:
            logger.warning("Failed to write eligibility audit event for person %s", person_id, exc_info=True)

    @staticmethod
    def _log_blocked_audit(
        db: Session,
        *,
        person_id: UUID,
        client_id: UUID,
        result: "EligibilityResult",
    ) -> None:
        try:
            event = AuditEvent(
                id=uuid_mod.uuid4(),
                person_id=person_id,
                event_type="CLIENT_BLOCKED_BY_ELIGIBILITY",
                actor_type="system",
                actor_id=None,
                correlation_id=uuid_mod.uuid4(),
                payload={
                    "person_id": str(person_id),
                    "client_id": str(client_id),
                    "eligible": result.eligible,
                    "kyc_ok": result.kyc_ok,
                    "aml_ok": result.aml_ok,
                    "aml_status": result.aml_status,
                    "risk_ok": result.risk_ok,
                    "reasons": result.reasons,
                },
                schema_version=1,
                created_at=datetime.now(timezone.utc),
            )
            db.add(event)
            db.flush()
        except Exception:
            logger.warning("Failed to write blocked audit event for person %s", person_id, exc_info=True)
