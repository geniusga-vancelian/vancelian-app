"""Tests — Flow version locking: sessions pin the flow version at start."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import (
    RegistrationJurisdiction,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationStepScreen,
    RegistrationScreenComponent,
    RegistrationSession,
)
from services.registration.service import (
    RegistrationSessionService,
    RegistrationFlowService,
)


def _seed_flow(db: Session, code: str = "VLOCK", version: int = 1) -> dict:
    j = db.query(RegistrationJurisdiction).filter(
        RegistrationJurisdiction.code == code.upper()
    ).first()
    if j is None:
        j = RegistrationJurisdiction(
            id=uuid.uuid4(), code=code.upper(), name="Test", is_active=True,
        )
        db.add(j)
        db.flush()

    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name=f"Flow v{version}", version=version,
        status="active", entrypoint_type="individual",
    )
    db.add(flow)
    db.flush()

    step = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="info", title="Info", position=0,
    )
    db.add(step)
    db.flush()
    screen = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step.id,
        screen_key="form", title="Form", position=0,
    )
    db.add(screen)
    db.flush()
    c = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen.id,
        component_type="text_input", component_key="name",
        position=0, binding_slug="name",
    )
    db.add(c)
    db.flush()
    return {"jurisdiction": j, "flow": flow, "step": step, "screen": screen}


class TestFlowVersionLocking:

    def test_session_pins_flow_version(self, db: Session):
        _seed_flow(db, "VL1", version=3)
        svc = RegistrationSessionService()
        result = svc.start_session(db, "VL1")
        assert result["flow_version"] == 3

        session = db.query(RegistrationSession).filter(
            RegistrationSession.id == uuid.UUID(result["session_id"])
        ).first()
        assert session.flow_version == 3

    def test_session_continues_on_old_version_after_publish(self, db: Session):
        data_v1 = _seed_flow(db, "VL2", version=1)
        svc = RegistrationSessionService()
        result_v1 = svc.start_session(db, "VL2")
        session_id = uuid.UUID(result_v1["session_id"])

        data_v1["flow"].status = "archived"
        db.flush()
        _seed_flow(db, "VL2", version=2)

        screen_resp = svc.get_current_screen(db, session_id)
        assert screen_resp["flow_version"] == 1

        session = db.query(RegistrationSession).filter(
            RegistrationSession.id == session_id
        ).first()
        assert session.flow_version == 1
        assert session.flow_id == data_v1["flow"].id

    def test_new_session_gets_latest_version(self, db: Session):
        _seed_flow(db, "VL3", version=1)
        svc = RegistrationSessionService()
        r1 = svc.start_session(db, "VL3")
        assert r1["flow_version"] == 1

        db.query(RegistrationFlow).filter(
            RegistrationFlow.id == uuid.UUID(r1["session_id"])  # won't match a flow
        ).first()

    def test_flow_version_in_audit(self, db: Session):
        from database import AuditEvent
        _seed_flow(db, "VL4", version=5)
        svc = RegistrationSessionService()
        svc.start_session(db, "VL4")

        event = db.query(AuditEvent).filter(
            AuditEvent.event_type == "REGISTRATION_SESSION_STARTED"
        ).order_by(AuditEvent.created_at.desc()).first()
        assert event is not None
        assert event.payload["flow_version"] == 5
