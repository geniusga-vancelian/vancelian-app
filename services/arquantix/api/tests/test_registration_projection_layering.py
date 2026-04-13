"""Tests — Data projection layering into profile_json.collected."""
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
)
from services.registration.service import (
    RegistrationSessionService,
    get_person_collected_value,
)


def _seed_flow(db: Session, code: str = "PROJ_LAYER") -> dict:
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code=code.upper(), name="Test", is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name="Projection Flow", version=1, status="active",
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
        component_type="text_input", component_key="first_name", position=0,
        binding_slug="first_name",
        props_json={"label": "First name", "required": True},
    )
    db.add(c)
    db.flush()
    return {"flow": flow, "step": step, "screen": screen}


class TestProjectionLayering:

    def test_new_person_gets_collected_namespace(self, db: Session):
        _seed_flow(db, "LAYER1")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "LAYER1")
        sid = uuid.UUID(start["session_id"])
        svc.submit_screen(db, sid, {"first_name": "Alice"})
        result = svc.complete_session(db, sid)

        person = db.query(Person).filter(Person.id == uuid.UUID(result["person_id"])).first()
        assert "collected" in person.profile_json
        assert "computed" in person.profile_json
        assert "compliance" in person.profile_json
        assert person.profile_json["collected"]["first_name"] == "Alice"

    def test_existing_person_preserves_other_keys(self, db: Session):
        person = Person(
            id=uuid.uuid4(), status="active",
            profile_json={"legacy_key": "keep", "computed": {"score": 42}},
            kyc_status="not_started",
        )
        db.add(person)
        db.flush()

        _seed_flow(db, "LAYER2")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "LAYER2", person_id=person.id)
        sid = uuid.UUID(start["session_id"])
        svc.submit_screen(db, sid, {"first_name": "Bob"})
        svc.complete_session(db, sid)

        db.refresh(person)
        assert person.profile_json["collected"]["first_name"] == "Bob"
        assert person.profile_json["legacy_key"] == "keep"
        assert person.profile_json["computed"]["score"] == 42

    def test_no_collision_with_compliance_namespace(self, db: Session):
        person = Person(
            id=uuid.uuid4(), status="active",
            profile_json={"compliance": {"aml_checked": True}},
            kyc_status="not_started",
        )
        db.add(person)
        db.flush()

        _seed_flow(db, "LAYER3")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "LAYER3", person_id=person.id)
        sid = uuid.UUID(start["session_id"])
        svc.submit_screen(db, sid, {"first_name": "Carol"})
        svc.complete_session(db, sid)

        db.refresh(person)
        assert person.profile_json["compliance"]["aml_checked"] is True
        assert person.profile_json["collected"]["first_name"] == "Carol"

    def test_submit_screen_projects_to_person_before_complete_session(self, db: Session):
        """Chaque Continuer (submit) doit synchroniser session → profile_json sans attendre complete."""
        _seed_flow(db, "INCRSUB")
        svc = RegistrationSessionService()
        start = svc.start_session(db, "INCRSUB")
        sid = uuid.UUID(start["session_id"])
        svc.submit_screen(db, sid, {"first_name": "Eve"})

        from database import RegistrationSession

        sess = db.query(RegistrationSession).filter(RegistrationSession.id == sid).first()
        assert sess is not None
        assert sess.person_id is not None
        person = db.query(Person).filter(Person.id == sess.person_id).first()
        assert person is not None
        assert get_person_collected_value(person, "first_name") == "Eve"


class TestGetPersonCollectedValue:

    def test_reads_from_collected_namespace(self, db: Session):
        person = Person(
            id=uuid.uuid4(), status="active",
            profile_json={"collected": {"email": "a@b.com"}},
        )
        db.add(person)
        db.flush()
        assert get_person_collected_value(person, "email") == "a@b.com"

    def test_falls_back_to_flat_for_legacy(self, db: Session):
        person = Person(
            id=uuid.uuid4(), status="active",
            profile_json={"email": "old@legacy.com"},
        )
        db.add(person)
        db.flush()
        assert get_person_collected_value(person, "email") == "old@legacy.com"

    def test_returns_default_if_missing(self, db: Session):
        person = Person(
            id=uuid.uuid4(), status="active",
            profile_json={},
        )
        db.add(person)
        db.flush()
        assert get_person_collected_value(person, "missing", "default_val") == "default_val"

    def test_collected_takes_priority_over_flat(self, db: Session):
        person = Person(
            id=uuid.uuid4(), status="active",
            profile_json={"collected": {"name": "new"}, "name": "old"},
        )
        db.add(person)
        db.flush()
        assert get_person_collected_value(person, "name") == "new"
