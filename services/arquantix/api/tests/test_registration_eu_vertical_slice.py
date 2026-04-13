"""End-to-end vertical slice tests for the EU Registration Flow.

Tests the complete lifecycle: seed → start → navigate → submit → complete → projection,
using the EU_VS jurisdiction seeded by migration 087.
This suite also validates the admin preview endpoint and the Flutter contract endpoint.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import (
    Person,
    RegistrationJurisdiction,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationStepScreen,
    RegistrationScreenComponent,
    RegistrationSessionStep,
)
from services.registration.service import (
    RegistrationFlowService,
    RegistrationSessionService,
    SessionCompletedError,
    NoNextScreenError,
    StepBlockedError,
    get_person_collected_value,
)


def _seed_eu_vs(db: Session) -> dict:
    """Create the EU_VS vertical slice flow in the test DB."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code="EU_VS_TEST", name="EU Vertical Slice Test", is_active=True,
        entity_name="Vancelian Europe SAS",
    )
    db.add(j)
    db.flush()

    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name="EU Individual Registration v1", version=1,
        status="active", entrypoint_type="individual",
    )
    db.add(flow)
    db.flush()

    # Step 1: Personal Info (blocking)
    step1 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="personal_info", title="Personal Information", position=0,
        is_blocking=True,
    )
    # Step 2: Residency (blocking)
    step2 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="residency", title="Residency", position=1,
        is_blocking=True,
    )
    # Step 3: Consent (non-blocking)
    step3 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="consent", title="Consent", position=2,
        is_blocking=False,
    )
    db.add_all([step1, step2, step3])
    db.flush()

    # Screen 1
    screen1 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step1.id,
        screen_key="personal_info_form", title="Your Information", position=0,
    )
    # Screen 2
    screen2 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step2.id,
        screen_key="residency_form", title="Your Residency", position=0,
    )
    # Screen 3
    screen3 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step3.id,
        screen_key="consent_form", title="Terms & Conditions", position=0,
    )
    db.add_all([screen1, screen2, screen3])
    db.flush()

    # Components for Screen 1
    comps_s1 = [
        ("text_input", "first_name", "first_name", {"label": "First Name", "required": True}),
        ("text_input", "last_name", "last_name", {"label": "Last Name", "required": True}),
        ("text_input", "email", "email", {"label": "Email", "required": True}),
        ("phone_input", "phone_number", "phone_number", {"label": "Phone Number", "required": True}),
    ]
    for pos, (ctype, ckey, slug, props) in enumerate(comps_s1):
        db.add(RegistrationScreenComponent(
            id=uuid.uuid4(), screen_id=screen1.id,
            component_type=ctype, component_key=ckey, position=pos,
            binding_slug=slug, props_json=props,
        ))

    # Components for Screen 2
    comps_s2 = [
        ("country_picker", "country_of_residence", "country_of_residence", {"label": "Country", "required": True}),
        ("country_picker", "nationality", "nationality", {"label": "Nationality", "required": True}),
        ("date_picker", "date_of_birth", "date_of_birth", {"label": "DOB", "required": True}),
    ]
    for pos, (ctype, ckey, slug, props) in enumerate(comps_s2):
        db.add(RegistrationScreenComponent(
            id=uuid.uuid4(), screen_id=screen2.id,
            component_type=ctype, component_key=ckey, position=pos,
            binding_slug=slug, props_json=props,
        ))

    # Components for Screen 3
    db.add(RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen3.id,
        component_type="legal_content", component_key="terms_text", position=0,
        props_json={"text": "Please review and accept the terms"},
    ))
    db.add(RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen3.id,
        component_type="checkbox", component_key="terms_and_conditions", position=1,
        binding_slug="terms_and_conditions",
        props_json={"label": "I accept T&C", "required": True},
    ))
    db.add(RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen3.id,
        component_type="checkbox", component_key="privacy_policy", position=2,
        binding_slug="privacy_policy",
        props_json={"label": "I accept Privacy Policy", "required": True},
    ))
    db.flush()

    return {
        "jurisdiction": j, "flow": flow,
        "step1": step1, "step2": step2, "step3": step3,
        "screen1": screen1, "screen2": screen2, "screen3": screen3,
    }


class TestEUVerticalSliceFlowCreation:

    def test_flow_has_3_steps(self, db: Session):
        data = _seed_eu_vs(db)
        flow = RegistrationFlowService.get_active_flow(db, "EU_VS_TEST")
        assert len(flow.steps) == 3

    def test_personal_info_has_4_components(self, db: Session):
        data = _seed_eu_vs(db)
        flow = RegistrationFlowService.get_active_flow(db, "EU_VS_TEST")
        step = next(s for s in flow.steps if s.step_key == "personal_info")
        assert len(step.screens[0].components) == 4

    def test_consent_is_non_blocking(self, db: Session):
        data = _seed_eu_vs(db)
        flow = RegistrationFlowService.get_active_flow(db, "EU_VS_TEST")
        consent = next(s for s in flow.steps if s.step_key == "consent")
        assert consent.is_blocking is False

    def test_serialize_flow(self, db: Session):
        data = _seed_eu_vs(db)
        flow = RegistrationFlowService.get_active_flow(db, "EU_VS_TEST")
        serialized = RegistrationFlowService.serialize_flow(flow)

        assert serialized["name"] == "EU Individual Registration v1"
        assert len(serialized["steps"]) == 3
        assert serialized["steps"][0]["is_blocking"] is True
        assert serialized["steps"][2]["is_blocking"] is False


class TestEUVerticalSliceNavigation:

    def test_start_session(self, db: Session):
        _seed_eu_vs(db)
        svc = RegistrationSessionService()
        result = svc.start_session(db, "EU_VS_TEST")

        assert result["status"] == "in_progress"
        assert result["current_step"]["step_key"] == "personal_info"
        assert result["screen"]["screen_key"] == "personal_info_form"
        assert result["flow_version"] == 1

    def test_submit_step1_and_advance(self, db: Session):
        _seed_eu_vs(db)
        svc = RegistrationSessionService()
        start = svc.start_session(db, "EU_VS_TEST")
        sid = uuid.UUID(start["session_id"])

        result = svc.submit_screen(db, sid, {
            "first_name": "Gael",
            "last_name": "Itier",
            "email": "gael@vancelian.com",
            "phone_number": "+33612345678",
        })

        assert result["current_step"]["step_key"] == "residency"
        assert result["collected_data"]["first_name"] == "Gael"

    def test_submit_step2_and_advance_to_consent(self, db: Session):
        _seed_eu_vs(db)
        svc = RegistrationSessionService()
        start = svc.start_session(db, "EU_VS_TEST")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {
            "first_name": "A", "last_name": "B", "email": "a@b.com", "phone_number": "+1",
        })
        result = svc.submit_screen(db, sid, {
            "country_of_residence": "FR", "nationality": "FR", "date_of_birth": "1990-01-01",
        })

        assert result["current_step"]["step_key"] == "consent"

    def test_cannot_skip_blocking_step_without_data(self, db: Session):
        _seed_eu_vs(db)
        svc = RegistrationSessionService()
        start = svc.start_session(db, "EU_VS_TEST")
        sid = uuid.UUID(start["session_id"])

        with pytest.raises(StepBlockedError):
            svc.next_screen(db, sid)

    def test_consent_non_blocking_allows_skip(self, db: Session):
        _seed_eu_vs(db)
        svc = RegistrationSessionService()
        start = svc.start_session(db, "EU_VS_TEST")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {
            "first_name": "A", "last_name": "B", "email": "a@b.com", "phone_number": "+1",
        })
        svc.submit_screen(db, sid, {
            "country_of_residence": "FR", "nationality": "FR", "date_of_birth": "1990-01-01",
        })
        result = svc.submit_screen(db, sid, {})
        assert result["is_last_screen"] is True


class TestEUVerticalSliceProjection:

    def test_full_flow_and_projection(self, db: Session):
        _seed_eu_vs(db)
        svc = RegistrationSessionService()
        start = svc.start_session(db, "EU_VS_TEST")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {
            "first_name": "Gael", "last_name": "Itier",
            "email": "gael@vancelian.com", "phone_number": "+33600000000",
        })
        svc.submit_screen(db, sid, {
            "country_of_residence": "FR", "nationality": "FR",
            "date_of_birth": "1990-05-15",
        })
        svc.submit_screen(db, sid, {
            "terms_and_conditions": True, "privacy_policy": True,
        })
        result = svc.complete_session(db, sid)

        assert result["status"] == "completed"
        person_id = uuid.UUID(result["person_id"])
        person = db.query(Person).filter(Person.id == person_id).first()

        assert person is not None
        assert person.profile_json["collected"]["first_name"] == "Gael"
        assert person.profile_json["collected"]["email"] == "gael@vancelian.com"
        assert person.profile_json["collected"]["country_of_residence"] == "FR"
        assert person.profile_json["collected"]["terms_and_conditions"] is True

        assert get_person_collected_value(person, "first_name") == "Gael"

    def test_step_states_after_completion(self, db: Session):
        _seed_eu_vs(db)
        svc = RegistrationSessionService()
        start = svc.start_session(db, "EU_VS_TEST")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {
            "first_name": "A", "last_name": "B", "email": "a@b.com", "phone_number": "+1",
        })
        svc.submit_screen(db, sid, {
            "country_of_residence": "FR", "nationality": "FR", "date_of_birth": "1990-01-01",
        })
        svc.submit_screen(db, sid, {
            "terms_and_conditions": True, "privacy_policy": True,
        })
        svc.complete_session(db, sid)

        states = db.query(RegistrationSessionStep).filter(
            RegistrationSessionStep.session_id == sid
        ).all()
        status_map = {s.step.step_key: s.status for s in states}
        assert status_map["personal_info"] == "completed"
        assert status_map["residency"] == "completed"
        assert status_map["consent"] == "completed"


class TestEUVerticalSliceAPI:

    def test_start_session_via_api(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        resp = client.post("/api/registration/sessions/start", json={
            "jurisdiction": "EU_VS_TEST",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["current_step"]["step_key"] == "personal_info"
        assert len(data["screen"]["components"]) == 4

    def test_submit_and_navigate_via_api(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        start = client.post("/api/registration/sessions/start", json={
            "jurisdiction": "EU_VS_TEST",
        })
        sid = start.json()["session_id"]

        submit = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {
                "first_name": "Gael", "last_name": "Itier",
                "email": "g@v.com", "phone_number": "+33600000000",
            },
        })
        assert submit.status_code == 200
        assert submit.json()["current_step"]["step_key"] == "residency"

    def test_complete_via_api(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        start = client.post("/api/registration/sessions/start", json={
            "jurisdiction": "EU_VS_TEST",
        })
        sid = start.json()["session_id"]

        client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"first_name": "A", "last_name": "B", "email": "a@b.com", "phone_number": "+1"},
        })
        client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"country_of_residence": "FR", "nationality": "FR", "date_of_birth": "1990-01-01"},
        })
        client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"terms_and_conditions": True, "privacy_policy": True},
        })
        complete = client.post(f"/api/registration/sessions/{sid}/complete")
        assert complete.status_code == 200
        assert complete.json()["status"] == "completed"

    def test_admin_preview_endpoint(self, client: TestClient, db: Session):
        data = _seed_eu_vs(db)
        flow_id = str(data["flow"].id)
        resp = client.get(f"/api/admin/registration/flows/{flow_id}/preview")
        assert resp.status_code == 200
        body = resp.json()
        assert body["statistics"]["total_steps"] == 3
        assert body["statistics"]["total_screens"] == 3
        assert body["statistics"]["total_components"] == 10
        assert body["statistics"]["blocking_steps"] == 2

    def test_flutter_contract_endpoint(self, client: TestClient, db: Session):
        data = _seed_eu_vs(db)
        flow_id = str(data["flow"].id)
        resp = client.get(f"/api/registration/flows/{flow_id}/flutter-contract")
        assert resp.status_code == 200
        body = resp.json()
        assert body["contract_version"] == "1.0"
        assert "text_input" in body["flutter_metadata"]["component_types_used"]
        assert "checkbox" in body["flutter_metadata"]["component_types_used"]
        assert "first_name" in body["flutter_metadata"]["binding_slugs"]
        assert body["flutter_metadata"]["total_screens"] == 3
        assert body["flutter_metadata"]["total_components"] == 10
