"""Tests — Blocking vs non-blocking step behavior."""
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
)


def _seed_mixed_flow(db: Session, code: str = "BLK") -> dict:
    """Three steps: blocking, non-blocking, blocking."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code=code.upper(), name="Test", is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name="Blocking Flow", version=1, status="active",
    )
    db.add(flow)
    db.flush()

    step1 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="identity", title="Identity", position=0,
        is_blocking=True,
    )
    step2 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="preferences", title="Preferences", position=1,
        is_blocking=False,
    )
    step3 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="legal", title="Legal", position=2,
        is_blocking=True,
    )
    db.add_all([step1, step2, step3])
    db.flush()

    screen1 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step1.id,
        screen_key="id_form", title="ID Form", position=0,
    )
    screen2 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step2.id,
        screen_key="pref_form", title="Pref Form", position=0,
    )
    screen3 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step3.id,
        screen_key="legal_form", title="Legal Form", position=0,
    )
    db.add_all([screen1, screen2, screen3])
    db.flush()

    c1 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen1.id,
        component_type="text_input", component_key="name", position=0,
        binding_slug="full_name",
        props_json={"label": "Name", "required": True},
    )
    c2 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen2.id,
        component_type="select", component_key="theme", position=0,
        binding_slug="theme",
        props_json={"label": "Theme"},
    )
    c3 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen3.id,
        component_type="checkbox", component_key="terms", position=0,
        binding_slug="terms_accepted",
        props_json={"label": "Accept terms", "required": True},
    )
    db.add_all([c1, c2, c3])
    db.flush()

    return {"flow": flow, "step1": step1, "step2": step2, "step3": step3}


class TestBlockingSteps:

    def test_blocking_step_blocks_without_required(self, db: Session):
        _seed_mixed_flow(db, "BLK1")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "BLK1")
        sid = uuid.UUID(start["session_id"])

        with pytest.raises(StepBlockedError):
            svc.next_screen(db, sid)

    def test_blocking_step_passes_with_required(self, db: Session):
        _seed_mixed_flow(db, "BLK2")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "BLK2")
        sid = uuid.UUID(start["session_id"])

        result = svc.submit_screen(db, sid, {"full_name": "Test User"})
        assert result["current_step"]["step_key"] == "preferences"

    def test_non_blocking_step_advances_freely(self, db: Session):
        _seed_mixed_flow(db, "BLK3")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "BLK3")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {"full_name": "Test User"})
        result = svc.submit_screen(db, sid, {})
        assert result["current_step"]["step_key"] == "legal"

    def test_non_blocking_step_can_be_skipped(self, db: Session):
        _seed_mixed_flow(db, "BLK4")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "BLK4")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {"full_name": "Test"})
        result = svc.next_screen(db, sid)
        assert result["current_step"]["step_key"] == "legal"

    def test_is_blocking_exposed_in_step_data(self, db: Session):
        _seed_mixed_flow(db, "BLK5")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "BLK5")

        assert start["current_step"]["is_blocking"] is True

    def test_is_blocking_in_serialized_flow(self, db: Session):
        from services.registration.service import RegistrationFlowService
        _seed_mixed_flow(db, "BLK6")
        flow = RegistrationFlowService.get_active_flow(db, "BLK6")
        serialized = RegistrationFlowService.serialize_flow(flow)

        steps = serialized["steps"]
        assert steps[0]["is_blocking"] is True
        assert steps[1]["is_blocking"] is False
        assert steps[2]["is_blocking"] is True

    def test_full_flow_with_mixed_blocking(self, db: Session):
        _seed_mixed_flow(db, "BLK7")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "BLK7")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {"full_name": "User"})
        svc.submit_screen(db, sid, {"theme": "dark"})
        svc.submit_screen(db, sid, {"terms_accepted": True})
        result = svc.complete_session(db, sid)

        assert result["status"] == "completed"
