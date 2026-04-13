"""Tests for Registration Flow Engine — full session lifecycle + projection."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import (
    Person,
    RegistrationJurisdiction,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationStepScreen,
    RegistrationScreenComponent,
    RegistrationSession,
    RegistrationSessionData,
)
from services.registration.service import (
    RegistrationFlowService,
    RegistrationSessionService,
    FlowNotFoundError,
    SessionNotFoundError,
    SessionCompletedError,
    NoNextScreenError,
    NoPreviousScreenError,
)


def _seed_flow(db: Session, jurisdiction_code: str = "EU") -> dict:
    """Create a minimal flow with 2 steps, 1 screen each, 2 components each."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code=jurisdiction_code.upper(),
        name="Test Jurisdiction", is_active=True,
    )
    db.add(j)
    db.flush()

    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name=f"Test Flow {jurisdiction_code}", version=1,
        status="active", entrypoint_type="individual",
    )
    db.add(flow)
    db.flush()

    step1 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="basic_info", title="Basic Info", position=0,
    )
    step2 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="consent", title="Consent", position=1,
    )
    db.add_all([step1, step2])
    db.flush()

    screen1 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step1.id,
        screen_key="basic_form", title="Your Info", position=0,
    )
    screen2 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step2.id,
        screen_key="consent_form", title="Agree", position=0,
    )
    db.add_all([screen1, screen2])
    db.flush()

    c1 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen1.id,
        component_type="text_input", component_key="first_name", position=0,
        binding_slug="first_name",
        props_json={"label": "First name", "required": True},
    )
    c2 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen1.id,
        component_type="text_input", component_key="last_name", position=1,
        binding_slug="last_name",
        props_json={"label": "Last name", "required": True},
    )
    c3 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen2.id,
        component_type="checkbox", component_key="terms", position=0,
        binding_slug="terms_accepted",
        props_json={"label": "I accept", "required": True},
    )
    db.add_all([c1, c2, c3])
    db.flush()

    return {
        "jurisdiction": j, "flow": flow,
        "step1": step1, "step2": step2,
        "screen1": screen1, "screen2": screen2,
    }


def _seed_flow_one_step_two_screens(db: Session, jurisdiction_code: str = "EU") -> dict:
    """Un seul step avec deux écrans (pour tester prev sans changer de step)."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code=jurisdiction_code.upper(),
        name="Test Jurisdiction", is_active=True,
    )
    db.add(j)
    db.flush()

    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name=f"Test Flow {jurisdiction_code}", version=1,
        status="active", entrypoint_type="individual",
    )
    db.add(flow)
    db.flush()

    step1 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="basic_info", title="Basic Info", position=0,
    )
    db.add(step1)
    db.flush()

    screen1 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step1.id,
        screen_key="basic_form", title="Your Info", position=0,
    )
    screen2 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step1.id,
        screen_key="extra_form", title="Extra", position=1,
    )
    db.add_all([screen1, screen2])
    db.flush()

    c1 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen1.id,
        component_type="text_input", component_key="first_name", position=0,
        binding_slug="first_name",
        props_json={"label": "First name", "required": True},
    )
    c2 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen1.id,
        component_type="text_input", component_key="last_name", position=1,
        binding_slug="last_name",
        props_json={"label": "Last name", "required": True},
    )
    c3 = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen2.id,
        component_type="text_input", component_key="nickname", position=0,
        binding_slug="nickname",
        props_json={"label": "Nickname", "required": True},
    )
    db.add_all([c1, c2, c3])
    db.flush()

    return {
        "jurisdiction": j, "flow": flow,
        "step1": step1,
        "screen1": screen1, "screen2": screen2,
    }


class TestGetActiveFlow:

    def test_returns_active_flow(self, db: Session):
        data = _seed_flow(db, "TEST_FLOW")
        flow = RegistrationFlowService.get_active_flow(db, "TEST_FLOW")
        assert flow.id == data["flow"].id

    def test_raises_if_no_active(self, db: Session):
        with pytest.raises(FlowNotFoundError):
            RegistrationFlowService.get_active_flow(db, "NONEXISTENT")

    def test_serialize_flow(self, db: Session):
        data = _seed_flow(db, "SER")
        flow = RegistrationFlowService.get_active_flow(db, "SER")
        result = RegistrationFlowService.serialize_flow(flow)

        assert result["name"] == flow.name
        assert len(result["steps"]) == 2
        assert result["steps"][0]["step_key"] == "basic_info"
        assert len(result["steps"][0]["screens"]) == 1
        assert len(result["steps"][0]["screens"][0]["components"]) == 2


class TestSessionLifecycle:

    def test_start_session(self, db: Session):
        _seed_flow(db, "START")
        svc = RegistrationSessionService()

        result = svc.start_session(db, "START")

        assert "session_id" in result
        assert result["status"] == "in_progress"
        assert result["screen"] is not None
        assert result["current_step"]["step_key"] == "basic_info"
        assert result["flow_version"] == 1
        assert isinstance(result["step_states"], list)
        assert len(result["step_states"]) >= 1

    def test_submit_and_next(self, db: Session):
        _seed_flow(db, "SUBMIT")
        svc = RegistrationSessionService()

        start = svc.start_session(db, "SUBMIT")
        session_id = uuid.UUID(start["session_id"])

        result = svc.submit_screen(db, session_id, {
            "first_name": "Gael",
            "last_name": "Itier",
        })

        assert result["current_step"]["step_key"] == "consent"
        assert result["collected_data"]["first_name"] == "Gael"
        assert result["collected_data"]["last_name"] == "Itier"

    def test_prev_screen_within_same_step(self, db: Session):
        """Le retour ne traverse plus les steps : il faut 2 écrans dans le même step."""
        _seed_flow_one_step_two_screens(db, "PREV")
        svc = RegistrationSessionService()

        start = svc.start_session(db, "PREV")
        session_id = uuid.UUID(start["session_id"])

        svc.submit_screen(db, session_id, {"first_name": "A", "last_name": "B"})
        result = svc.prev_screen(db, session_id)

        assert result["current_step"]["step_key"] == "basic_info"
        assert result["screen"]["screen_key"] == "basic_form"

    def test_prev_cannot_reopen_finished_step(self, db: Session):
        """Depuis le 1er écran d'un nouveau step, pas de retour vers le step précédent."""
        _seed_flow(db, "PREV_XSTEP")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "PREV_XSTEP")
        session_id = uuid.UUID(start["session_id"])
        svc.submit_screen(db, session_id, {"first_name": "A", "last_name": "B"})
        with pytest.raises(NoPreviousScreenError):
            svc.prev_screen(db, session_id)

    def test_prev_at_first_raises(self, db: Session):
        _seed_flow(db, "PREV_FIRST")
        svc = RegistrationSessionService()

        start = svc.start_session(db, "PREV_FIRST")
        session_id = uuid.UUID(start["session_id"])

        with pytest.raises(NoPreviousScreenError):
            svc.prev_screen(db, session_id)

    def test_complete_session(self, db: Session):
        _seed_flow(db, "COMPLETE")
        svc = RegistrationSessionService()

        start = svc.start_session(db, "COMPLETE")
        session_id = uuid.UUID(start["session_id"])

        svc.submit_screen(db, session_id, {"first_name": "Gael", "last_name": "Itier"})
        svc.submit_screen(db, session_id, {"terms_accepted": True})

        result = svc.complete_session(db, session_id)

        assert result["status"] == "completed"
        assert result["person_id"] is not None
        assert result["projection"]["projected_fields"] == 3

    def test_double_complete_raises(self, db: Session):
        _seed_flow(db, "DBL_COMPLETE")
        svc = RegistrationSessionService()

        start = svc.start_session(db, "DBL_COMPLETE")
        session_id = uuid.UUID(start["session_id"])
        svc.complete_session(db, session_id)

        with pytest.raises(SessionCompletedError):
            svc.complete_session(db, session_id)

    def test_session_not_found(self, db: Session):
        svc = RegistrationSessionService()
        with pytest.raises(SessionNotFoundError):
            svc.get_current_screen(db, uuid.uuid4())


class TestProjection:

    def test_data_projected_to_profile_json_collected(self, db: Session):
        _seed_flow(db, "PROJ")
        svc = RegistrationSessionService()

        start = svc.start_session(db, "PROJ")
        session_id = uuid.UUID(start["session_id"])

        svc.submit_screen(db, session_id, {"first_name": "Alice", "last_name": "Smith"})
        svc.submit_screen(db, session_id, {"terms_accepted": True})
        result = svc.complete_session(db, session_id)

        person_id = uuid.UUID(result["person_id"])
        person = db.query(Person).filter(Person.id == person_id).first()
        assert person is not None
        assert person.profile_json["collected"]["first_name"] == "Alice"
        assert person.profile_json["collected"]["last_name"] == "Smith"
        assert person.profile_json["collected"]["terms_accepted"] is True
        assert "computed" in person.profile_json
        assert "compliance" in person.profile_json

    def test_existing_person_updated(self, db: Session):
        person = Person(
            id=uuid.uuid4(), status="active",
            profile_json={"existing_field": "keep_me"},
            kyc_status="not_started",
        )
        db.add(person)
        db.flush()

        _seed_flow(db, "PROJ_EXIST")
        svc = RegistrationSessionService()

        start = svc.start_session(db, "PROJ_EXIST", person_id=person.id)
        session_id = uuid.UUID(start["session_id"])

        svc.submit_screen(
            db, session_id, {"first_name": "Bob", "last_name": "Builder"}
        )
        svc.submit_screen(db, session_id, {"terms_accepted": True})
        result = svc.complete_session(db, session_id)

        db.refresh(person)
        assert person.profile_json["collected"]["first_name"] == "Bob"
        assert person.profile_json["collected"]["last_name"] == "Builder"
        assert person.profile_json["existing_field"] == "keep_me"


class TestVisibilityRules:

    def test_component_hidden_by_rule(self, db: Session):
        j = RegistrationJurisdiction(
            id=uuid.uuid4(), code="VIS_TEST", name="Vis Test", is_active=True,
        )
        db.add(j)
        db.flush()

        flow = RegistrationFlow(
            id=uuid.uuid4(), jurisdiction_id=j.id,
            name="Vis Flow", version=1, status="active",
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
            screen_key="info_form", title="Info", position=0,
        )
        db.add(screen)
        db.flush()

        c_always = RegistrationScreenComponent(
            id=uuid.uuid4(), screen_id=screen.id,
            component_type="select", component_key="status", position=0,
            binding_slug="employment_status",
        )
        c_conditional = RegistrationScreenComponent(
            id=uuid.uuid4(), screen_id=screen.id,
            component_type="text_input", component_key="employer", position=1,
            binding_slug="employer_name",
            visibility_rule_json={"field": "employment_status", "operator": "equals", "value": "employed"},
        )
        db.add_all([c_always, c_conditional])
        db.flush()

        svc = RegistrationSessionService()
        start = svc.start_session(db, "VIS_TEST")
        session_id = uuid.UUID(start["session_id"])

        screen_data = start["screen"]
        component_keys = [c["component_key"] for c in screen_data["components"]]
        assert "status" in component_keys
        assert "employer" not in component_keys

        # Après submit, next_screen échoue (un seul écran) → réponse is_last avec contexte à jour
        after_submit = svc.submit_screen(
            db, session_id, {"employment_status": "employed"}
        )
        refreshed_keys = [
            c["component_key"] for c in after_submit["screen"]["components"]
        ]
        assert "employer" in refreshed_keys
