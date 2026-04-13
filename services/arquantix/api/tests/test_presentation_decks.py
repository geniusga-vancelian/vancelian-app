"""
Tests API présentations / templates / versions (deck persistence).
Requiert migration 095 appliquée sur la base utilisée par les tests.
"""
import uuid

import pytest


@pytest.fixture
def title_template_id(client):
    r = client.get("/api/presentation-templates")
    assert r.status_code == 200
    data = r.json()
    t = next((x for x in data if x.get("key") == "title"), None)
    if not t:
        pytest.skip("Seed template 'title' absent — exécuter alembic upgrade head")
    return uuid.UUID(t["id"])


def test_list_templates(client, title_template_id):
    r = client.get("/api/presentation-templates?search=title")
    assert r.status_code == 200
    assert any(x["key"] == "title" for x in r.json())


def test_create_template_and_duplicate_key(client):
    key = f"test_tpl_{uuid.uuid4().hex[:8]}"
    body = {
        "key": key,
        "name": "Test",
        "category": "test",
        "schema_json": {"type": "object", "properties": {"x": {"type": "string"}}},
        "default_content_json": {"x": "a"},
    }
    r = client.post("/api/presentation-templates", json=body)
    assert r.status_code == 200
    r2 = client.post("/api/presentation-templates", json=body)
    assert r2.status_code == 409


def test_create_presentation_has_v1_draft_current(client, title_template_id):
    slug = f"deck-{uuid.uuid4().hex[:10]}"
    r = client.post(
        "/api/presentations",
        json={"name": "Investor", "slug": slug, "deck_type": "investor", "create_initial_version": True},
    )
    assert r.status_code == 200
    deck = r.json()
    assert deck["current_version_id"]
    v = client.get(f"/api/presentation-versions/{deck['current_version_id']}")
    assert v.status_code == 200
    vd = v.json()
    assert vd["status"] == "draft"
    assert vd["is_current"] is True
    assert vd["version_number"] == 1


def test_slide_crud_validate_duplicate_archive_restore_set_current(client, title_template_id):
    slug = f"deck-{uuid.uuid4().hex[:10]}"
    dr = client.post(
        "/api/presentations",
        json={"name": "Flow", "slug": slug, "create_initial_version": True},
    )
    deck = dr.json()
    vid = uuid.UUID(deck["current_version_id"])

    sr = client.post(
        f"/api/presentation-versions/{vid}/slides",
        json={"slide_template_id": str(title_template_id), "content_json": {"title": "Hello", "subtitle": "World"}},
    )
    assert sr.status_code == 200
    slide_id = sr.json()["id"]

    val = client.post(f"/api/presentation-versions/{vid}/validate")
    assert val.status_code == 200
    assert val.json()["status"] == "validated"
    assert val.json()["snapshot_json"] is not None

    bad = client.put(
        f"/api/presentation-versions/{vid}/slides/{slide_id}",
        json={"content_json": {"title": "X"}},
    )
    assert bad.status_code == 400

    dup = client.post(f"/api/presentation-versions/{vid}/duplicate")
    assert dup.status_code == 200
    v2 = dup.json()
    assert v2["version_number"] == 2
    assert v2["status"] == "draft"

    arch = client.post(f"/api/presentation-versions/{v2['id']}/archive")
    assert arch.status_code == 200
    assert arch.json()["status"] == "archived"

    rest = client.post(f"/api/presentation-versions/{v2['id']}/restore")
    assert rest.status_code == 200
    assert rest.json()["status"] == "draft"

    cur = client.post(f"/api/presentation-versions/{v2['id']}/set-current")
    assert cur.status_code == 200
    assert cur.json()["is_current"] is True
    deck2 = client.get(f"/api/presentations/{deck['id']}")
    assert deck2.json()["current_version_id"] == v2["id"]


def test_validate_slide_content_invalid(client, title_template_id):
    r = client.post(
        "/api/presentation-templates/validate-content",
        params={"template_id": str(title_template_id)},
        json={"content_json": {"title": 123}},
    )
    assert r.status_code == 422


def test_save_draft_replaces_slides(client, title_template_id):
    slug = f"deck-{uuid.uuid4().hex[:10]}"
    dr = client.post("/api/presentations", json={"name": "Save", "slug": slug, "create_initial_version": True})
    vid = uuid.UUID(dr.json()["current_version_id"])
    client.post(
        f"/api/presentation-versions/{vid}/slides",
        json={"slide_template_id": str(title_template_id), "content_json": {"title": "A"}},
    )
    r = client.post(
        f"/api/presentation-versions/{vid}/save-draft",
        json={
            "slides": [
                {
                    "slide_template_id": str(title_template_id),
                    "sort_order": 0,
                    "content_json": {"title": "B", "subtitle": ""},
                }
            ]
        },
    )
    assert r.status_code == 200
    assert len(r.json()["slides"]) == 1
    assert r.json()["slides"][0]["content_json"]["title"] == "B"


def test_presentation_archive_restore(client):
    slug = f"deck-{uuid.uuid4().hex[:10]}"
    dr = client.post("/api/presentations", json={"name": "Arch", "slug": slug, "create_initial_version": False})
    did = dr.json()["id"]
    a = client.post(f"/api/presentations/{did}/archive")
    assert a.status_code == 200
    assert a.json()["archived_at"]
    x = client.post(f"/api/presentations/{did}/restore")
    assert x.status_code == 200
    assert x.json()["archived_at"] is None
