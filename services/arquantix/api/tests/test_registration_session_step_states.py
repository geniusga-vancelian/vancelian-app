"""Tests — Session step state tracking via registration_session_steps."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import (
    RegistrationJurisdiction,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationStepScreen,
    RegistrationScreenComponent,
    RegistrationSessionStep,
)
from services.registration.service import (
    RegistrationSessionService,
    NoNextScreenError,
)


def _seed_flow(db: Session, code: str = "SS_TEST") -> dict:
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code=code.upper(), name="Test", is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name="StepState Flow", version=1, status="active",
    )
    db.add(flow)
    db.flush()

    step1 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="step_a", title="Step A", position=0,
        is_blocking=True,
    )
    step2 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="step_b", title="Step B", position=1,
        is_blocking=True,
    )
    db.add_all([step1, step2])
    db.flush()

    screen1 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step1.id,
        screen_key="form_a", title="Form A", position=0,
    )
    screen2 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step2.id,
        screen_key="form_b", title="Form B", position=0,
    )
    db.add_all([screen1, screen2])
    db.flush()

    c1 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen1.id,
        component_type="text_input", component_key="field_a", position=0,
        binding_slug="field_a",
        props_json={"label": "A", "required": True},
    )
    c2 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen2.id,
        component_type="text_input", component_key="field_b", position=0,
        binding_slug="field_b",
        props_json={"label": "B", "required": True},
    )
    db.add_all([c1, c2])
    db.flush()

    return {"flow": flow, "step1": step1, "step2": step2, "screen1": screen1, "screen2": screen2}


class TestSessionStepStates:

    def test_first_step_in_progress_on_start(self, db: Session):
        _seed_flow(db, "SS1")
        svc = RegistrationSessionService()
        result = svc.start_session(db, "SS1")

        states = result["step_states"]
        assert len(states) == 1
        assert states[0]["status"] == "in_progress"
        assert states[0]["started_at"] is not None

    def test_step_completed_after_advancing(self, db: Session):
        data = _seed_flow(db, "SS2")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "SS2")
        sid = uuid.UUID(start["session_id"])

        result = svc.submit_screen(db, sid, {"field_a": "val"})
        states = result["step_states"]

        step_a = next((s for s in states if s["step_id"] == str(data["step1"].id)), None)
        assert step_a is not None
        assert step_a["status"] == "completed"
        assert step_a["completed_at"] is not None

        step_b = next((s for s in states if s["step_id"] == str(data["step2"].id)), None)
        assert step_b is not None
        assert step_b["status"] == "in_progress"

    def test_step_state_from_response(self, db: Session):
        _seed_flow(db, "SS3")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "SS3")
        sid = uuid.UUID(start["session_id"])

        assert start["current_step_status"] == "in_progress"

        result = svc.submit_screen(db, sid, {"field_a": "val"})
        assert result["current_step_status"] == "in_progress"

    def test_complete_marks_last_step_completed(self, db: Session):
        data = _seed_flow(db, "SS4")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "SS4")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {"field_a": "val"})
        svc.submit_screen(db, sid, {"field_b": "val2"})
        svc.complete_session(db, sid)

        ss = db.query(RegistrationSessionStep).filter(
            RegistrationSessionStep.step_id == data["step2"].id,
        ).first()
        assert ss.status == "completed"
        assert ss.completed_at is not None

    def test_step_state_persisted_in_db(self, db: Session):
        data = _seed_flow(db, "SS5")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "SS5")
        sid = uuid.UUID(start["session_id"])

        rows = db.query(RegistrationSessionStep).filter(
            RegistrationSessionStep.session_id == sid,
        ).all()
        assert len(rows) == 1
        assert rows[0].step_id == data["step1"].id
        assert rows[0].status == "in_progress"
