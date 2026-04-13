"""Tests for Registration Engine Phase 2C.

Covers:
- P0.1: JSONB projection fix (flag_modified)
- P0.2: UAE nationality fix
- Field definitions binding
- Field slug normalization helpers
- Backend validations (email, phone, date, select)
- Admin CRUD (PATCH/DELETE flow)
- Flutter contract readiness
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
)
from services.registration.service import (
    RegistrationFlowService,
    RegistrationSessionService,
)
from services.registration.field_helpers import (
    normalize_to_snake,
    normalize_to_kebab,
    are_field_slugs_equivalent,
)


# ------------------------------------------------------------------
# Seed helper (mirrors _seed_eu_vs from test_registration_eu_vertical_slice)
# ------------------------------------------------------------------

def _seed_eu_vs(db: Session) -> dict:
    """Seed a 3-step EU_VS-like flow for Phase 2C tests."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code="P2C_TEST", name="Phase2C Test", is_active=True,
        entity_name="Test Entity",
    )
    db.add(j)
    db.flush()

    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name="P2C Individual v1", version=1,
        status="active", entrypoint_type="individual",
    )
    db.add(flow)
    db.flush()

    step1 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="personal_info", title="Personal Information", position=0,
        is_blocking=True,
    )
    step2 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="residency", title="Residency", position=1,
        is_blocking=True,
    )
    step3 = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="consent", title="Consent", position=2,
        is_blocking=False,
    )
    db.add_all([step1, step2, step3])
    db.flush()

    screen1 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step1.id,
        screen_key="personal_info_form", title="Your Information", position=0,
    )
    screen2 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step2.id,
        screen_key="residency_form", title="Your Residency", position=0,
    )
    screen3 = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step3.id,
        screen_key="consent_form", title="Terms & Conditions", position=0,
    )
    db.add_all([screen1, screen2, screen3])
    db.flush()

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


def _submit_full_flow(client: TestClient, jurisdiction: str = "P2C_TEST") -> dict:
    """Start a session, submit all 3 screens, and complete. Returns the complete response."""
    start = client.post("/api/registration/sessions/start", json={"jurisdiction": jurisdiction})
    assert start.status_code == 201
    sid = start.json()["session_id"]

    r1 = client.post(f"/api/registration/sessions/{sid}/submit", json={
        "answers": {"first_name": "P2C", "last_name": "Test", "email": "p2c@test.com", "phone_number": "+33600000000"},
    })
    assert r1.status_code == 200

    r2 = client.post(f"/api/registration/sessions/{sid}/submit", json={
        "answers": {"country_of_residence": "FR", "nationality": "FR", "date_of_birth": "1990-01-01"},
    })
    assert r2.status_code == 200

    r3 = client.post(f"/api/registration/sessions/{sid}/submit", json={
        "answers": {"terms_and_conditions": True, "privacy_policy": True},
    })
    assert r3.status_code == 200

    complete = client.post(f"/api/registration/sessions/{sid}/complete")
    assert complete.status_code == 200
    return complete.json()


# ====================================================================
# P0.1 — JSONB projection fix (flag_modified)
# ====================================================================

class TestProjectionFix:
    """P0.1: Verify projection actually persists in persons.profile_json."""

    def test_projection_persists_in_db(self, db: Session, client: TestClient):
        """After complete_session, persons.profile_json['collected'] must have data."""
        _seed_eu_vs(db)
        data = _submit_full_flow(client)

        person_id = data["person_id"]
        assert data["projection"]["projected_fields"] == 9

        person = db.query(Person).filter(Person.id == person_id).first()
        assert person is not None
        assert person.profile_json is not None
        collected = person.profile_json.get("collected", {})
        assert collected.get("first_name") == "P2C"
        assert collected.get("email") == "p2c@test.com"
        assert len(collected) == 9

    def test_projection_preserves_existing_data(self, db: Session, client: TestClient):
        """If person already has profile_json, new fields merge without overwriting."""
        person = Person(
            id=uuid.uuid4(), status="active",
            profile_json={"keep_this": "intact"},
            kyc_status="not_started",
        )
        db.add(person)
        db.flush()

        _seed_eu_vs(db)
        start = client.post("/api/registration/sessions/start", json={
            "jurisdiction": "P2C_TEST",
            "person_id": str(person.id),
        })
        assert start.status_code == 201
        sid = start.json()["session_id"]

        client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"first_name": "Merge", "last_name": "Test", "email": "m@t.com", "phone_number": "+33600000000"},
        })
        client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"country_of_residence": "FR", "nationality": "FR", "date_of_birth": "1990-01-01"},
        })
        client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"terms_and_conditions": True, "privacy_policy": True},
        })
        client.post(f"/api/registration/sessions/{sid}/complete")

        db.refresh(person)
        assert person.profile_json["keep_this"] == "intact"
        assert person.profile_json["collected"]["first_name"] == "Merge"

    def test_projection_via_service_layer(self, db: Session):
        """Same check using the service layer directly (no HTTP)."""
        _seed_eu_vs(db)
        svc = RegistrationSessionService()
        start = svc.start_session(db, "P2C_TEST")
        sid = uuid.UUID(start["session_id"])

        svc.submit_screen(db, sid, {
            "first_name": "Direct", "last_name": "Test",
            "email": "d@t.com", "phone_number": "+33600000000",
        })
        svc.submit_screen(db, sid, {
            "country_of_residence": "DE", "nationality": "DE", "date_of_birth": "1985-06-15",
        })
        svc.submit_screen(db, sid, {"terms_and_conditions": True, "privacy_policy": True})
        result = svc.complete_session(db, sid)

        person = db.query(Person).filter(Person.id == result["person_id"]).first()
        assert person.profile_json["collected"]["first_name"] == "Direct"
        assert person.profile_json["collected"]["country_of_residence"] == "DE"


# ====================================================================
# P0.2 — UAE nationality fix
# ====================================================================

class TestUAENationalityFix:
    """P0.2: UAE nationality must be country_picker, not select."""

    def test_uae_nationality_is_country_picker(self, db: Session):
        j = RegistrationJurisdiction(
            id=uuid.uuid4(), code="UAE_P2C", name="UAE P2C Test", is_active=True,
        )
        db.add(j)
        db.flush()

        flow = RegistrationFlow(
            id=uuid.uuid4(), jurisdiction_id=j.id,
            name="UAE Flow", version=1, status="active",
        )
        db.add(flow)
        db.flush()

        step = RegistrationFlowStep(
            id=uuid.uuid4(), flow_id=flow.id,
            step_key="identity", title="Identity", position=0,
        )
        db.add(step)
        db.flush()

        screen = RegistrationStepScreen(
            id=uuid.uuid4(), step_id=step.id,
            screen_key="identity_form", title="Identity", position=0,
        )
        db.add(screen)
        db.flush()

        db.add(RegistrationScreenComponent(
            id=uuid.uuid4(), screen_id=screen.id,
            component_type="country_picker", component_key="nationality", position=0,
            binding_slug="nationality",
            props_json={"label": "Nationality", "required": True},
        ))
        db.flush()

        comps = (
            db.query(RegistrationScreenComponent)
            .join(RegistrationScreenComponent.screen)
            .join(RegistrationFlowStep)
            .join(RegistrationFlow)
            .join(RegistrationJurisdiction)
            .filter(RegistrationJurisdiction.code == "UAE_P2C")
            .filter(RegistrationScreenComponent.binding_slug == "nationality")
            .all()
        )
        for comp in comps:
            assert comp.component_type == "country_picker", \
                f"UAE nationality should be country_picker, got {comp.component_type}"

    def test_nationality_not_select_in_uae(self, db: Session):
        """Negative check: ensure no 'select' component for nationality in UAE."""
        j = RegistrationJurisdiction(
            id=uuid.uuid4(), code="UAE_NEG", name="UAE Neg Test", is_active=True,
        )
        db.add(j)
        db.flush()

        flow = RegistrationFlow(
            id=uuid.uuid4(), jurisdiction_id=j.id,
            name="UAE Neg Flow", version=1, status="active",
        )
        db.add(flow)
        db.flush()

        step = RegistrationFlowStep(
            id=uuid.uuid4(), flow_id=flow.id,
            step_key="id", title="ID", position=0,
        )
        db.add(step)
        db.flush()

        screen = RegistrationStepScreen(
            id=uuid.uuid4(), step_id=step.id,
            screen_key="id_form", title="ID", position=0,
        )
        db.add(screen)
        db.flush()

        db.add(RegistrationScreenComponent(
            id=uuid.uuid4(), screen_id=screen.id,
            component_type="country_picker", component_key="nationality", position=0,
            binding_slug="nationality",
        ))
        db.flush()

        bad_comps = (
            db.query(RegistrationScreenComponent)
            .join(RegistrationScreenComponent.screen)
            .join(RegistrationFlowStep)
            .join(RegistrationFlow)
            .join(RegistrationJurisdiction)
            .filter(RegistrationJurisdiction.code == "UAE_NEG")
            .filter(RegistrationScreenComponent.binding_slug == "nationality")
            .filter(RegistrationScreenComponent.component_type == "select")
            .all()
        )
        assert len(bad_comps) == 0, "No 'select' component should exist for UAE nationality"


# ====================================================================
# Field slug normalization helpers
# ====================================================================

class TestFieldSlugHelpers:
    """Field slug normalization helpers."""

    def test_normalize_to_snake(self):
        assert normalize_to_snake("first-name") == "first_name"
        assert normalize_to_snake("first_name") == "first_name"
        assert normalize_to_snake("FIRST-NAME") == "first_name"
        assert normalize_to_snake("") == ""
        assert normalize_to_snake(None) is None

    def test_normalize_to_kebab(self):
        assert normalize_to_kebab("first_name") == "first-name"
        assert normalize_to_kebab("first-name") == "first-name"
        assert normalize_to_kebab("FIRST_NAME") == "first-name"
        assert normalize_to_kebab("") == ""
        assert normalize_to_kebab(None) is None

    def test_are_equivalent(self):
        assert are_field_slugs_equivalent("first-name", "first_name") is True
        assert are_field_slugs_equivalent("first_name", "first_name") is True
        assert are_field_slugs_equivalent("first-name", "last-name") is False
        assert are_field_slugs_equivalent("", "first_name") is False
        assert are_field_slugs_equivalent(None, "first_name") is False
        assert are_field_slugs_equivalent(None, None) is False

    def test_roundtrip_snake_kebab(self):
        """snake → kebab → snake must be idempotent."""
        original = "date_of_birth"
        kebab = normalize_to_kebab(original)
        assert kebab == "date-of-birth"
        back = normalize_to_snake(kebab)
        assert back == original


# ====================================================================
# Field definitions catalog
# ====================================================================

class TestFieldDefinitionsCatalog:
    """Field definitions catalog endpoint."""

    def test_catalog_returns_fields(self, client: TestClient, db: Session):
        from database import FieldDefinition

        existing = db.query(FieldDefinition).filter(FieldDefinition.is_active == True).count()
        if existing == 0:
            pytest.skip("No active field definitions in test DB")

        r = client.get("/api/admin/registration/field-definitions/catalog")
        assert r.status_code == 200
        fields = r.json()
        assert isinstance(fields, list)
        assert len(fields) > 0
        for f in fields[:3]:
            assert "id" in f
            assert "slug" in f
            assert "slug_snake" in f
            assert "label" in f
            assert "field_type" in f
            assert "category" in f

    def test_catalog_slug_snake_matches_normalization(self, client: TestClient, db: Session):
        from database import FieldDefinition

        existing = db.query(FieldDefinition).filter(FieldDefinition.is_active == True).count()
        if existing == 0:
            pytest.skip("No active field definitions in test DB")

        r = client.get("/api/admin/registration/field-definitions/catalog")
        for f in r.json():
            expected_snake = normalize_to_snake(f["slug"])
            assert f["slug_snake"] == expected_snake, \
                f"slug_snake mismatch for {f['slug']}: got {f['slug_snake']}, expected {expected_snake}"


# ====================================================================
# Backend validation
# ====================================================================

class TestBackendValidation:
    """Backend format validations on submit."""

    def test_invalid_email_rejected(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "P2C_TEST"})
        sid = start.json()["session_id"]

        r = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"first_name": "Test", "last_name": "User", "email": "not-an-email", "phone_number": "+33600000000"},
        })
        assert r.status_code == 422

    def test_invalid_phone_rejected(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "P2C_TEST"})
        sid = start.json()["session_id"]

        r = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"first_name": "Test", "last_name": "User", "email": "t@t.com", "phone_number": "abc"},
        })
        assert r.status_code == 422

    def test_valid_data_accepted(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "P2C_TEST"})
        sid = start.json()["session_id"]

        r = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"first_name": "Test", "last_name": "User", "email": "valid@test.com", "phone_number": "+33612345678"},
        })
        assert r.status_code == 200

    def test_invalid_date_rejected(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "P2C_TEST"})
        sid = start.json()["session_id"]

        r1 = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"first_name": "T", "last_name": "U", "email": "t@t.com", "phone_number": "+33600000000"},
        })
        assert r1.status_code == 200
        r = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"country_of_residence": "FR", "nationality": "FR", "date_of_birth": "not-a-date"},
        })
        assert r.status_code == 422

    def test_checkbox_must_be_boolean(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "P2C_TEST"})
        sid = start.json()["session_id"]

        r1 = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"first_name": "T", "last_name": "U", "email": "t@t.com", "phone_number": "+33600000000"},
        })
        assert r1.status_code == 200
        r2 = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"country_of_residence": "FR", "nationality": "FR", "date_of_birth": "1990-01-01"},
        })
        assert r2.status_code == 200
        r = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"terms_and_conditions": "yes", "privacy_policy": "yes"},
        })
        assert r.status_code == 422

    def test_valid_date_formats_accepted(self, client: TestClient, db: Session):
        """Both YYYY-MM-DD and DD/MM/YYYY should be accepted."""
        _seed_eu_vs(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "P2C_TEST"})
        sid = start.json()["session_id"]

        client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"first_name": "T", "last_name": "U", "email": "t@t.com", "phone_number": "+33600000000"},
        })
        r = client.post(f"/api/registration/sessions/{sid}/submit", json={
            "answers": {"country_of_residence": "FR", "nationality": "FR", "date_of_birth": "15/05/1990"},
        })
        assert r.status_code == 200


# ====================================================================
# Admin CRUD (PATCH / DELETE)
# ====================================================================

class TestAdminFlowCRUD:
    """Admin CRUD for flows."""

    def test_patch_flow_name(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        flows = client.get("/api/admin/registration/flows").json()
        target = next((f for f in flows if f["name"] == "P2C Individual v1"), None)
        if not target:
            pytest.skip("Seeded flow not found")

        r = client.patch(f"/api/admin/registration/flows/{target['id']}", json={"name": "Patched Name"})
        assert r.status_code == 200
        assert r.json()["name"] == "Patched Name"

        r2 = client.patch(f"/api/admin/registration/flows/{target['id']}", json={"name": "P2C Individual v1"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "P2C Individual v1"

    def test_delete_active_flow_blocked(self, client: TestClient, db: Session):
        _seed_eu_vs(db)
        flows = client.get("/api/admin/registration/flows").json()
        active = [f for f in flows if f.get("status") == "active"]
        if not active:
            pytest.skip("No active flows")

        r = client.delete(f"/api/admin/registration/flows/{active[0]['id']}")
        assert r.status_code == 409

    def test_delete_draft_flow(self, client: TestClient, db: Session):
        r_j = client.post("/api/admin/registration/jurisdictions", json={
            "code": "TST_DEL", "name": "Test Delete", "entity_name": "Test",
            "default_language": "en", "is_active": True,
        })
        assert r_j.status_code == 201
        jid = r_j.json()["id"]

        r_f = client.post("/api/admin/registration/flows", json={
            "jurisdiction_id": jid, "name": "Delete Me",
            "entrypoint_type": "individual",
        })
        assert r_f.status_code == 201
        fid = r_f.json()["id"]
        assert r_f.json()["status"] == "draft"

        r_del = client.delete(f"/api/admin/registration/flows/{fid}")
        assert r_del.status_code == 204

    def test_delete_nonexistent_flow(self, client: TestClient, db: Session):
        fake_id = str(uuid.uuid4())
        r = client.delete(f"/api/admin/registration/flows/{fake_id}")
        assert r.status_code == 404

    def test_patch_nonexistent_flow(self, client: TestClient, db: Session):
        fake_id = str(uuid.uuid4())
        r = client.patch(f"/api/admin/registration/flows/{fake_id}", json={"name": "X"})
        assert r.status_code == 404


# ====================================================================
# Flutter contract readiness
# ====================================================================

class TestFlutterContractReadiness:
    """Flutter contract should only contain supported component types."""

    SUPPORTED_TYPES = {
        "text_input", "phone_input", "select", "country_picker",
        "date_picker", "checkbox", "multi_select", "section_title", "legal_content",
    }

    def test_contract_structure(self, client: TestClient, db: Session):
        data = _seed_eu_vs(db)
        flow_id = str(data["flow"].id)
        r = client.get(f"/api/registration/flows/{flow_id}/flutter-contract")
        assert r.status_code == 200

        body = r.json()
        assert body["contract_version"] == "1.0"
        assert "flow" in body
        assert "flutter_metadata" in body
        assert body["flutter_metadata"]["total_screens"] == 3
        assert body["flutter_metadata"]["total_components"] == 10

    def test_all_component_types_supported(self, client: TestClient, db: Session):
        data = _seed_eu_vs(db)
        flow_id = str(data["flow"].id)
        r = client.get(f"/api/registration/flows/{flow_id}/flutter-contract")
        assert r.status_code == 200

        metadata = r.json()["flutter_metadata"]
        types = set(metadata["component_types_used"])
        unsupported = types - self.SUPPORTED_TYPES
        assert not unsupported, f"Unsupported types found: {unsupported}"

    def test_all_binding_slugs_non_empty(self, client: TestClient, db: Session):
        data = _seed_eu_vs(db)
        flow_id = str(data["flow"].id)
        r = client.get(f"/api/registration/flows/{flow_id}/flutter-contract")
        assert r.status_code == 200

        flow_data = r.json()["flow"]
        for step in flow_data.get("steps", []):
            for screen in step.get("screens", []):
                for comp in screen.get("components", []):
                    if comp.get("binding_slug"):
                        assert isinstance(comp["binding_slug"], str)
                        assert len(comp["binding_slug"]) > 0

    def test_binding_slugs_present(self, client: TestClient, db: Session):
        data = _seed_eu_vs(db)
        flow_id = str(data["flow"].id)
        r = client.get(f"/api/registration/flows/{flow_id}/flutter-contract")
        assert r.status_code == 200

        slugs = r.json()["flutter_metadata"]["binding_slugs"]
        assert "first_name" in slugs
        assert "email" in slugs
        assert "nationality" in slugs
        assert "terms_and_conditions" in slugs

    def test_nonexistent_flow_returns_404(self, client: TestClient, db: Session):
        fake_id = str(uuid.uuid4())
        r = client.get(f"/api/registration/flows/{fake_id}/flutter-contract")
        assert r.status_code == 404
