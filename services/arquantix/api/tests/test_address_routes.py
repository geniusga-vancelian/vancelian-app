"""Address proxy routes — rate limit, allowed_countries, country mismatch (mocked Google)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def addr_app():
    from main import create_app

    return create_app(testing=True)


@pytest.fixture
def addr_client(addr_app, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    monkeypatch.setenv("ADDRESS_RL_BACKEND", "memory")
    monkeypatch.setenv("ADDRESS_RL_AUTOCOMPLETE_MAX", "3")
    monkeypatch.setenv("ADDRESS_RL_DETAILS_MAX", "10")
    from services.address.rate_limiter import reset_address_rate_limiter_for_tests

    reset_address_rate_limiter_for_tests()
    with TestClient(addr_app) as c:
        yield c
    reset_address_rate_limiter_for_tests()


def test_autocomplete_ok(addr_client, monkeypatch):
    monkeypatch.setattr(
        "services.address.routes.autocomplete",
        lambda q, region=None, countries=None, **_: (
            [{"description": "1 Main St", "place_id": "ChIJx"}],
            None,
        ),
    )
    r = addr_client.get("/api/address/autocomplete?q=main&allowed_countries=FR,DE")
    assert r.status_code == 200
    assert r.json()["predictions"][0]["place_id"] == "ChIJx"


def test_autocomplete_invalid_allowed_countries(addr_client):
    r = addr_client.get("/api/address/autocomplete?q=test&allowed_countries=FRANCE")
    assert r.status_code == 422


def test_autocomplete_rate_limit(addr_client, monkeypatch):
    monkeypatch.setattr(
        "services.address.routes.autocomplete",
        lambda q, region=None, countries=None, **_: (
            [{"description": "x", "place_id": "p"}],
            None,
        ),
    )
    for _ in range(3):
        r = addr_client.get("/api/address/autocomplete?q=aa")
        assert r.status_code == 200
    r4 = addr_client.get("/api/address/autocomplete?q=bb")
    assert r4.status_code == 429
    body = r4.json()
    assert body["detail"]["error"]["code"] == "rate_limited"
    assert "retry_after" in body["detail"]["error"]


def test_details_country_mismatch(addr_client, monkeypatch):
    monkeypatch.setattr(
        "services.address.routes.get_place_details",
        lambda place_id, allowed_countries=None, include_raw=False: (
            {},
            "country_not_allowed",
        ),
    )
    r = addr_client.get(
        "/api/address/details?place_id=abc&allowed_countries=SG",
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "address_country_mismatch"


def test_details_ok_partial(addr_client, monkeypatch):
    monkeypatch.setattr(
        "services.address.routes.get_place_details",
        lambda place_id, allowed_countries=None, include_raw=False: (
            {
                "address_line_1": "18A Republic Ave",
                "postal_code": "",
                "city": "",
                "country": "SG",
                "google_place_id": "abc",
                "formatted_address": "…",
                "confidence_score": 0.72,
                "lat": 1.0,
                "lng": 103.0,
                "partial_match": True,
                "field_warnings": ["missing_postal_code", "missing_city"],
                "incomplete": True,
            },
            None,
        ),
    )
    r = addr_client.get("/api/address/details?place_id=abc")
    assert r.status_code == 200
    data = r.json()
    assert data["incomplete"] is True
    assert "missing_postal_code" in data["field_warnings"]


def test_autocomplete_country_be_passed_to_service(addr_client, monkeypatch):
    captured: dict = {}

    def fake_autocomplete(q, region=None, countries=None, **kwargs):
        captured["countries"] = countries
        return ([{"description": "Brussels", "place_id": "ChIJ1"}], None)

    monkeypatch.setattr("services.address.routes.autocomplete", fake_autocomplete)
    r = addr_client.get("/api/address/autocomplete?q=brux&country=be")
    assert r.status_code == 200
    assert captured.get("countries") == ["BE"]


def test_autocomplete_country_invalid_iso2(addr_client):
    """2 chars but non-letters → our validator (length ok for Query)."""
    r = addr_client.get("/api/address/autocomplete?q=test&country=12")
    assert r.status_code == 422
    body = r.json()
    assert body["detail"]["code"] == "invalid_country"


def test_autocomplete_country_too_long_rejected_by_fastapi(addr_client):
    r = addr_client.get("/api/address/autocomplete?q=test&country=BEL")
    assert r.status_code == 422


def test_details_country_param_be_merges_allowlist(addr_client, monkeypatch):
    captured: dict = {}

    def fake_details(place_id, allowed_countries=None, include_raw=False):
        captured["allowed_countries"] = allowed_countries
        return (
            {
                "address_line_1": "1 Rue",
                "postal_code": "1000",
                "city": "Brussels",
                "country": "BE",
                "google_place_id": "p",
                "formatted_address": "x",
                "confidence_score": 0.95,
                "lat": 1.0,
                "lng": 2.0,
                "partial_match": False,
                "field_warnings": [],
                "incomplete": False,
            },
            None,
        )

    monkeypatch.setattr("services.address.routes.get_place_details", fake_details)
    r = addr_client.get("/api/address/details?place_id=p&country=be")
    assert r.status_code == 200
    assert captured.get("allowed_countries") == ["BE"]


def test_details_country_param_overrides_disjoint_allowed_list(
    addr_client, monkeypatch
):
    """Résidence (`country`) prime : allowlist disjointe ne doit plus renvoyer 422."""
    monkeypatch.setattr(
        "services.address.routes.get_place_details",
        lambda place_id, allowed_countries=None, include_raw=False: (
            {
                "address_line_1": "1 Rue",
                "postal_code": "1000",
                "city": "Brussels",
                "country": "BE",
                "google_place_id": "x",
                "formatted_address": "x",
                "confidence_score": 0.95,
                "lat": 1.0,
                "lng": 2.0,
                "partial_match": False,
                "field_warnings": [],
                "incomplete": False,
            },
            None,
        ),
    )
    r = addr_client.get(
        "/api/address/details?place_id=x&country=BE&allowed_countries=FR",
    )
    assert r.status_code == 200
    assert r.json()["country"] == "BE"


def test_autocomplete_country_param_overrides_disjoint_allowed_list(
    addr_client, monkeypatch
):
    monkeypatch.setattr(
        "services.address.routes.autocomplete",
        lambda q, region=None, countries=None, **_: (
            [{"description": "x", "place_id": "p"}],
            None,
        ),
    )
    r = addr_client.get(
        "/api/address/autocomplete?q=x&country=BE&allowed_countries=FR,DE",
    )
    assert r.status_code == 200
    assert r.json()["predictions"][0]["place_id"] == "p"


def test_autocomplete_country_in_long_allowed_list_not_truncated_at_parse(
    addr_client, monkeypatch
):
    """Ancien bug : parse limitait à 5 codes — FR absent des 5 premiers → faux 422."""
    captured: dict = {}

    def fake_autocomplete(q, region=None, countries=None, **kwargs):
        captured["countries"] = countries
        return ([{"description": "Paris", "place_id": "ChIJ"}] if q else [], None)

    monkeypatch.setattr("services.address.routes.autocomplete", fake_autocomplete)
    long_list = "AT,BE,BG,HR,CY,CZ,DK,EE,FI,FR"
    r = addr_client.get(
        f"/api/address/autocomplete?q=pa&country=FR&allowed_countries={long_list}",
    )
    assert r.status_code == 200
    assert captured.get("countries") == ["FR"]
