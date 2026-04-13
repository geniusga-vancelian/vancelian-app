"""Tests — Navigation hardening: next/prev controls and blocking enforcement."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import (
    RegistrationJurisdiction,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationStepScreen,
    RegistrationScreenComponent,
)
from services.registration.service import (
    RegistrationSessionService,
    StepBlockedError,
    ValidationError,
    NoPreviousScreenError,
    NoNextScreenError,
)


def _seed_blocking_flow(db: Session, code: str = "NAV") -> dict:
    """Two steps: step1 blocking (required field), step2 non-blocking."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code=code.upper(), name="Test", is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name="Nav Flow", version=1, status="active",
    )
    db.add(flow)
    db.flush()

    step1 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="required_step", title="Required", position=0,
        is_blocking=True,
    )
    step2 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="optional_step", title="Optional", position=1,
        is_blocking=False,
    )
    db.add_all([step1, step2])
    db.flush()

    screen1 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step1.id,
        screen_key="req_form", title="Required Form", position=0,
    )
    screen2 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step2.id,
        screen_key="opt_form", title="Optional Form", position=0,
    )
    db.add_all([screen1, screen2])
    db.flush()

    c1 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen1.id,
        component_type="text_input", component_key="email", position=0,
        binding_slug="email",
        props_json={"label": "Email", "required": True},
    )
    c2 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen2.id,
        component_type="text_input", component_key="nickname", position=0,
        binding_slug="nickname",
        props_json={"label": "Nickname"},
    )
    db.add_all([c1, c2])
    db.flush()
    return {
        "flow": flow, "step1": step1, "step2": step2,
        "screen1": screen1, "screen2": screen2,
    }


class TestNavigationGuards:

    def test_cannot_next_past_blocking_step_without_required_fields(self, db: Session):
        _seed_blocking_flow(db, "NG1")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "NG1")
        sid = uuid.UUID(start["session_id"])

        with pytest.raises(StepBlockedError):
            svc.next_screen(db, sid)

    def test_can_next_past_blocking_step_with_required_fields(self, db: Session):
        _seed_blocking_flow(db, "NG2")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "NG2")
        sid = uuid.UUID(start["session_id"])

        result = svc.submit_screen(db, sid, {"email": "test@example.com"})
        assert result["current_step"]["step_key"] == "optional_step"

    def test_submit_validates_required_fields(self, db: Session):
        _seed_blocking_flow(db, "NG3")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "NG3")
        sid = uuid.UUID(start["session_id"])

        with pytest.raises(ValidationError, match="email"):
            svc.submit_screen(db, sid, {})

    def test_submit_accepts_empty_value_as_missing(self, db: Session):
        _seed_blocking_flow(db, "NG4")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "NG4")
        sid = uuid.UUID(start["session_id"])

        with pytest.raises(ValidationError, match="email"):
            svc.submit_screen(db, sid, {"email": ""})

    def test_prev_at_first_screen_raises(self, db: Session):
        _seed_blocking_flow(db, "NG5")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "NG5")
        sid = uuid.UUID(start["session_id"])

        with pytest.raises(NoPreviousScreenError):
            svc.prev_screen(db, sid)

    def test_prev_after_advance_to_new_step_raises(self, db: Session):
        """Au 1er écran d'un nouveau step, pas de retour vers le step bouclé précédent."""
        _seed_blocking_flow(db, "NG6")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "NG6")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {"email": "a@b.com"})
        with pytest.raises(NoPreviousScreenError):
            svc.prev_screen(db, sid)

    def test_backend_decides_next_screen(self, db: Session):
        """The client doesn't choose a target screen — backend decides."""
        _seed_blocking_flow(db, "NG7")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "NG7")
        sid = uuid.UUID(start["session_id"])

        result = svc.submit_screen(db, sid, {"email": "x@y.com"})
        assert result["screen"]["screen_key"] == "opt_form"

    def test_no_next_at_last_screen(self, db: Session):
        _seed_blocking_flow(db, "NG8")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "NG8")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {"email": "x@y.com"})

        result = svc.submit_screen(db, sid, {"nickname": "test"})
        assert result["is_last_screen"] is True
