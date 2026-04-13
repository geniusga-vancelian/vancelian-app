"""API-level tests for Registration Flow Engine (runtime + admin)."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import (
    FieldDefinition,
    Person,
    RegistrationJurisdiction,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationSession,
    RegistrationSessionStep,
    RegistrationStepScreen,
    RegistrationScreenComponent,
)
from services.registration.execution_events import RegistrationEventType


def _seed_flow_for_api(db: Session) -> dict:
    """Seed a minimal flow that can be tested via HTTP."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code="API_TEST", name="API Test", is_active=True,
    )
    db.add(j)
    db.flush()

    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name="API Test Flow", version=1, status="active",
    )
    db.add(flow)
    db.flush()

    step = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="step1", title="Step 1", position=0,
    )
    db.add(step)
    db.flush()

    screen = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step.id,
        screen_key="screen1", title="Screen 1", position=0,
    )
    db.add(screen)
    db.flush()

    comp = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=screen.id,
        component_type="text_input", component_key="name",
        position=0, binding_slug="full_name",
        props_json={"label": "Full name"},
    )
    db.add(comp)
    db.flush()

    return {"jurisdiction": j, "flow": flow, "step": step, "screen": screen}


class TestRuntimeAPI:

    def test_get_active_flow(self, client: TestClient, db: Session):
        _seed_flow_for_api(db)
        resp = client.get("/api/registration/flows/active?jurisdiction=API_TEST")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "API Test Flow"
        assert len(data["steps"]) == 1

    def test_get_active_flow_not_found(self, client: TestClient):
        resp = client.get("/api/registration/flows/active?jurisdiction=NOPE")
        assert resp.status_code == 404

    def test_start_session(self, client: TestClient, db: Session):
        _seed_flow_for_api(db)
        resp = client.post("/api/registration/sessions/start", json={
            "jurisdiction": "API_TEST",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        assert data["screen"]["screen_key"] == "screen1"

    def test_start_session_resumes_in_progress_same_person(self, client: TestClient, db: Session):
        """Deux POST /sessions/start avec le même ``person_id`` → même session (reprise)."""
        _seed_flow_for_api(db)
        pid = uuid.uuid4()
        person = Person(
            id=pid,
            status="active",
            jurisdiction="API_TEST",
            profile_json={"collected": {}, "computed": {}, "compliance": {}},
        )
        db.add(person)
        db.flush()

        r1 = client.post(
            "/api/registration/sessions/start",
            json={"jurisdiction": "API_TEST", "person_id": str(pid)},
        )
        assert r1.status_code == 201, r1.text
        sid1 = r1.json()["session_id"]

        r2 = client.post(
            "/api/registration/sessions/start",
            json={"jurisdiction": "API_TEST", "person_id": str(pid)},
        )
        assert r2.status_code == 201, r2.text
        assert r2.json()["session_id"] == sid1

        row = db.query(RegistrationSession).filter(RegistrationSession.person_id == pid).all()
        assert len(row) == 1

    def test_start_session_rejects_when_registration_already_completed(
        self, client: TestClient, db: Session
    ):
        """Après une session ``completed``, un nouveau ``sessions/start`` → 409 (pas de 2ᵉ parcours)."""
        _seed_flow_for_api(db)
        pid = uuid.uuid4()
        person = Person(
            id=pid,
            status="active",
            jurisdiction="API_TEST",
            profile_json={"collected": {}, "computed": {}, "compliance": {}},
        )
        db.add(person)
        db.flush()

        r1 = client.post(
            "/api/registration/sessions/start",
            json={"jurisdiction": "API_TEST", "person_id": str(pid)},
        )
        assert r1.status_code == 201, r1.text
        session_id = r1.json()["session_id"]

        submit = client.post(
            f"/api/registration/sessions/{session_id}/submit",
            json={"answers": {"full_name": "Test User"}},
        )
        assert submit.status_code == 200, submit.text

        complete = client.post(f"/api/registration/sessions/{session_id}/complete")
        assert complete.status_code == 200, complete.text

        r2 = client.post(
            "/api/registration/sessions/start",
            json={"jurisdiction": "API_TEST", "person_id": str(pid)},
        )
        assert r2.status_code == 409, r2.text
        body = r2.json()
        assert body["detail"]["code"] == "registration_already_completed"
        assert "message" in body["detail"]

        rows = db.query(RegistrationSession).filter(RegistrationSession.person_id == pid).all()
        assert len(rows) == 1

    def test_submit_and_complete(self, client: TestClient, db: Session):
        _seed_flow_for_api(db)
        start = client.post("/api/registration/sessions/start", json={
            "jurisdiction": "API_TEST",
        })
        session_id = start.json()["session_id"]

        submit = client.post(f"/api/registration/sessions/{session_id}/submit", json={
            "answers": {"full_name": "Gael Itier"},
        })
        assert submit.status_code == 200

        complete = client.post(f"/api/registration/sessions/{session_id}/complete")
        assert complete.status_code == 200
        assert complete.json()["status"] == "completed"
        assert complete.json()["person_id"] is not None

    def test_execution_events_timeline(self, client: TestClient, db: Session):
        """Admin timeline + replay endpoints; payloads normalized (Phase A hardened)."""
        _seed_flow_for_api(db)
        start = client.post("/api/registration/sessions/start", json={
            "jurisdiction": "API_TEST",
        })
        session_id = start.json()["session_id"]
        client.post(f"/api/registration/sessions/{session_id}/submit", json={
            "answers": {"full_name": "Gael Itier"},
        })
        client.post(f"/api/registration/sessions/{session_id}/complete")

        ev = client.get(f"/api/admin/registration/sessions/{session_id}/execution-events")
        assert ev.status_code == 200
        body = ev.json()
        types = [e["event_type"] for e in body["events"]]
        assert RegistrationEventType.FLOW_VERSION_LOCKED in types
        assert RegistrationEventType.SESSION_STARTED in types
        assert RegistrationEventType.SCREEN_ENTERED in types
        assert RegistrationEventType.FIELDS_SUBMITTED in types
        assert RegistrationEventType.SCREEN_SUBMITTED in types
        assert RegistrationEventType.PROJECTION_COMPLETED in types
        assert RegistrationEventType.SESSION_COMPLETED in types
        completed = next(e for e in body["events"] if e["event_type"] == RegistrationEventType.SESSION_COMPLETED)
        assert completed["payload_json"].get("person_id")
        assert isinstance(completed["payload_json"].get("projected_fields"), list)
        assert body["event_count"] == len(body["events"])
        assert all("label_fr" in e for e in body["events"])

        times = [e["created_at"] for e in body["events"]]
        assert times == sorted(times)

        detail = client.get(f"/api/admin/registration/sessions/{session_id}")
        assert detail.status_code == 200
        assert detail.json()["summary"]["events_total"] == body["event_count"]

        replay = client.get(f"/api/admin/registration/sessions/{session_id}/replay")
        assert replay.status_code == 200
        rj = replay.json()
        assert len(rj["timeline"]) == body["event_count"]
        assert rj["summary"]["submits_count"] >= 1

        lst = client.get("/api/admin/registration/sessions?limit=10")
        assert lst.status_code == 200
        assert any(x["id"] == session_id for x in lst.json()["items"])

    def test_rule_evaluated_emitted_when_step_has_visibility_rule(self, client: TestClient, db: Session):
        meta = _seed_flow_for_api(db)
        meta["step"].visibility_rule_json = {"operator": "all_of", "rules": []}
        db.flush()
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "API_TEST"})
        assert start.status_code == 201
        session_id = start.json()["session_id"]
        ev = client.get(f"/api/admin/registration/sessions/{session_id}/execution-events")
        types = [e["event_type"] for e in ev.json()["events"]]
        assert RegistrationEventType.RULE_EVALUATED in types
        rule_ev = next(e for e in ev.json()["events"] if e["event_type"] == RegistrationEventType.RULE_EVALUATED)
        assert rule_ev["payload_json"].get("count", 0) >= 1

    def test_get_screen(self, client: TestClient, db: Session):
        _seed_flow_for_api(db)
        start = client.post("/api/registration/sessions/start", json={
            "jurisdiction": "API_TEST",
        })
        session_id = start.json()["session_id"]

        resp = client.get(f"/api/registration/sessions/{session_id}/screen")
        assert resp.status_code == 200
        assert resp.json()["screen"]["screen_key"] == "screen1"


class TestAdminAPI:

    def test_sessions_summary_stats(self, client: TestClient, db: Session):
        r = client.get("/api/admin/registration/sessions/summary-stats")
        assert r.status_code == 200
        data = r.json()
        assert "sessions_total" in data
        assert "completed_count" in data

    def test_create_and_list_jurisdictions(self, client: TestClient, db: Session):
        resp = client.post("/api/admin/registration/jurisdictions", json={
            "code": "ADMIN_TEST",
            "name": "Admin Test",
        })
        assert resp.status_code == 201
        j_id = resp.json()["id"]

        resp = client.get("/api/admin/registration/jurisdictions")
        assert resp.status_code == 200
        codes = [j["code"] for j in resp.json()]
        assert "ADMIN_TEST" in codes

    def test_create_flow_and_publish(self, client: TestClient, db: Session):
        j_resp = client.post("/api/admin/registration/jurisdictions", json={
            "code": "PUB_TEST", "name": "Pub Test",
        })
        j_id = j_resp.json()["id"]

        f_resp = client.post("/api/admin/registration/flows", json={
            "jurisdiction_id": j_id, "name": "Test Flow",
        })
        assert f_resp.status_code == 201
        f_id = f_resp.json()["id"]
        assert f_resp.json()["status"] == "draft"

        # Publish is gated by flow health: need at least one step and a screen with title (or components).
        st_resp = client.post(f"/api/admin/registration/flows/{f_id}/steps", json={
            "step_key": "s1", "title": "Step 1", "position": 0,
        })
        assert st_resp.status_code == 201
        step_id = st_resp.json()["id"]
        sc_resp = client.post(f"/api/admin/registration/steps/{step_id}/screens", json={
            "screen_key": "sc1", "title": "Welcome", "position": 0,
        })
        assert sc_resp.status_code == 201

        pub_resp = client.post(f"/api/admin/registration/flows/{f_id}/publish", json={
            "published_by": "admin@test.com",
        })
        assert pub_resp.status_code == 200
        assert pub_resp.json()["status"] == "active"

    def test_crud_steps(self, client: TestClient, db: Session):
        data = _seed_flow_for_api(db)
        flow_id = str(data["flow"].id)

        resp = client.post(f"/api/admin/registration/flows/{flow_id}/steps", json={
            "step_key": "new_step", "title": "New Step", "position": 99,
        })
        assert resp.status_code == 201
        step_id = resp.json()["id"]

        resp = client.get(f"/api/admin/registration/flows/{flow_id}/steps")
        assert resp.status_code == 200
        keys = [s["step_key"] for s in resp.json()]
        assert "new_step" in keys

        resp = client.patch(f"/api/admin/registration/steps/{step_id}", json={
            "title": "Updated Step",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Step"

        resp = client.delete(f"/api/admin/registration/steps/{step_id}")
        assert resp.status_code == 204

    def test_delete_step_with_session_references_returns_204(
        self, client: TestClient, db: Session
    ):
        """Régression : FK session sans ON DELETE provoquait 500 au Del step admin."""
        data = _seed_flow_for_api(db)
        step = data["step"]
        screen = data["screen"]
        flow = data["flow"]
        j = data["jurisdiction"]
        sess = RegistrationSession(
            id=uuid.uuid4(),
            jurisdiction_id=j.id,
            flow_id=flow.id,
            flow_version=1,
            status="in_progress",
            current_step_id=step.id,
            current_screen_id=screen.id,
        )
        db.add(sess)
        db.flush()
        db.add(
            RegistrationSessionStep(
                id=uuid.uuid4(),
                session_id=sess.id,
                step_id=step.id,
                status="in_progress",
                last_screen_id=screen.id,
            )
        )
        db.commit()

        resp = client.delete(f"/api/admin/registration/steps/{step.id}")
        assert resp.status_code == 204

    def _minimal_screen_id(self, client: TestClient) -> str:
        code = f"Z{uuid.uuid4().hex[:6]}".upper()
        j = client.post("/api/admin/registration/jurisdictions", json={"code": code, "name": "Comp Test"}).json()
        f = client.post(
            "/api/admin/registration/flows",
            json={"jurisdiction_id": j["id"], "name": "Comp Flow"},
        ).json()
        st = client.post(
            f"/api/admin/registration/flows/{f['id']}/steps",
            json={"step_key": "s1", "title": "Step"},
        ).json()
        sc = client.post(
            f"/api/admin/registration/steps/{st['id']}/screens",
            json={"screen_key": "sc1", "title": "Scr"},
        ).json()
        return sc["id"]

    def test_create_content_component_without_binding_ok(self, client: TestClient, db: Session):
        screen_id = self._minimal_screen_id(client)
        r = client.post(
            f"/api/admin/registration/screens/{screen_id}/components",
            json={
                "component_type": "rich_text",
                "component_key": "rt1",
                "position": 0,
                "props_json": {"label": "Intro"},
            },
        )
        assert r.status_code == 201
        assert r.json().get("binding_slug") in (None, "")

    def test_create_input_without_field_definition_rejected(self, client: TestClient, db: Session):
        screen_id = self._minimal_screen_id(client)
        r = client.post(
            f"/api/admin/registration/screens/{screen_id}/components",
            json={
                "component_type": "text_input",
                "component_key": "t1",
                "position": 0,
                "binding_slug": "orphan_slug",
                "props_json": {"label": "X"},
            },
        )
        assert r.status_code == 422

    def test_create_input_with_mismatched_binding_rejected(self, client: TestClient, db: Session):
        screen_id = self._minimal_screen_id(client)
        fd = FieldDefinition(
            id=uuid.uuid4(),
            slug="correct_slug",
            field_name_en="Correct",
            field_type="string",
            is_active=True,
        )
        db.add(fd)
        db.flush()
        r = client.post(
            f"/api/admin/registration/screens/{screen_id}/components",
            json={
                "component_type": "text_input",
                "component_key": "t1",
                "position": 0,
                "binding_slug": "wrong_slug",
                "field_definition_id": str(fd.id),
                "props_json": {"label": "X"},
            },
        )
        assert r.status_code == 422

    def test_create_content_with_binding_rejected(self, client: TestClient, db: Session):
        screen_id = self._minimal_screen_id(client)
        r = client.post(
            f"/api/admin/registration/screens/{screen_id}/components",
            json={
                "component_type": "legal_content",
                "component_key": "leg1",
                "position": 0,
                "binding_slug": "illegal",
                "props_json": {"label": "L"},
            },
        )
        assert r.status_code == 422

    def test_create_input_with_field_definition_ok(self, client: TestClient, db: Session):
        screen_id = self._minimal_screen_id(client)
        fd = FieldDefinition(
            id=uuid.uuid4(),
            slug="api_bound_field",
            field_name_en="Bound",
            field_type="string",
            is_active=True,
        )
        db.add(fd)
        db.flush()
        r = client.post(
            f"/api/admin/registration/screens/{screen_id}/components",
            json={
                "component_type": "text_input",
                "component_key": "tbound",
                "position": 0,
                "binding_slug": "api_bound_field",
                "field_definition_id": str(fd.id),
                "props_json": {"label": "L"},
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["field_definition_id"] == str(fd.id)
        assert body["binding_slug"] == "api_bound_field"

    def test_publish_blocked_when_flow_has_input_without_field_definition(self, client: TestClient, db: Session):
        screen_id = self._minimal_screen_id(client)
        scr = db.query(RegistrationStepScreen).filter(RegistrationStepScreen.id == uuid.UUID(screen_id)).one()
        db.add(
            RegistrationScreenComponent(
                id=uuid.uuid4(),
                screen_id=scr.id,
                component_type="text_input",
                component_key="orphan",
                position=0,
                binding_slug="solo",
                props_json={"label": "L"},
            )
        )
        db.flush()
        step = db.query(RegistrationFlowStep).filter(RegistrationFlowStep.id == scr.step_id).one()
        flow_id = str(step.flow_id)
        pub = client.post(
            f"/api/admin/registration/flows/{flow_id}/publish",
            json={"published_by": "admin@test.com"},
        )
        assert pub.status_code == 422
        detail = pub.json().get("detail", {})
        assert "errors" in detail or isinstance(detail, list)

    def test_legacy_normalization_report_ok(self, client: TestClient, db: Session):
        r = client.get("/api/admin/registration/legacy-normalization/report")
        assert r.status_code == 200
        body = r.json()
        assert "totals" in body
        assert "ok" in body["totals"]
        assert "health_before" in body

    def test_legacy_normalization_apply_requires_confirm(self, client: TestClient, db: Session):
        r = client.post("/api/admin/registration/legacy-normalization/apply", json={"confirm": False})
        assert r.status_code == 400

    def test_flows_health_summary(self, client: TestClient):
        r = client.get("/api/admin/registration/flows/health-summary")
        assert r.status_code == 200
        data = r.json()
        assert "flows_total" in data
        assert "publishable_count" in data
        assert "blocked_count" in data
        assert isinstance(data["flows"], list)
        for f in data["flows"]:
            assert "flow_id" in f
            assert "can_publish" in f
            assert isinstance(f["errors"], list)

    def test_list_flows_include_health(self, client: TestClient):
        r = client.get("/api/admin/registration/flows?include_health=true")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1
        assert "can_publish" in rows[0]
        assert "health_error_count" in rows[0]
        assert "health_warning_count" in rows[0]

    def test_component_validation_visibility_rules_roundtrip(self, client: TestClient, db: Session):
        screen_id = self._minimal_screen_id(client)
        fd = FieldDefinition(
            id=uuid.uuid4(),
            slug="opt-b-test-field",
            field_name_en="OptB",
            field_type="string",
            is_active=True,
        )
        db.add(fd)
        db.flush()
        r = client.post(
            f"/api/admin/registration/screens/{screen_id}/components",
            json={
                "component_type": "text_input",
                "component_key": "c1",
                "position": 0,
                "props_json": {"label": "Label"},
                "binding_slug": "opt_b_test_field",
                "field_definition_id": str(fd.id),
                "validation_rule_json": {"operator": "exists", "field": "email"},
                "visibility_rule_json": {"operator": "equals", "field": "country", "value": "FR"},
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["validation_rule_json"]["operator"] == "exists"
        assert body["visibility_rule_json"]["field"] == "country"
        lst = client.get(f"/api/admin/registration/screens/{screen_id}/components")
        assert lst.status_code == 200
        match = next(x for x in lst.json() if x["id"] == body["id"])
        assert match["validation_rule_json"]["field"] == "email"
