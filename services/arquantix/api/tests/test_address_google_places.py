"""Unit tests for Google Places parsing (no live API calls)."""
from __future__ import annotations

import pytest

from services.address.google_places_service import (
    _components_param,
    get_place_details,
    parse_address_components,
)
from services.registration.address_autocomplete import (
    allowed_countries_iso2_from_props,
    clamp_address_metadata_value,
)


def test_parse_address_components_singapore_style():
    components = [
        {"long_name": "18A", "short_name": "18A", "types": ["street_number"]},
        {"long_name": "Republic Avenue", "short_name": "Republic Ave", "types": ["route"]},
        {"long_name": "039953", "short_name": "039953", "types": ["postal_code"]},
        {"long_name": "Singapore", "short_name": "Singapore", "types": ["locality"]},
        {
            "long_name": "Singapore",
            "short_name": "SG",
            "types": ["country", "political"],
        },
    ]
    out = parse_address_components(components)
    assert out["address_line_1"] == "18A Republic Avenue"
    assert out["postal_code"] == "039953"
    assert out["locality"] == "Singapore"
    assert out["country_short"] == "SG"


def test_parse_address_components_minimal():
    assert parse_address_components([])["address_line_1"] == ""


def test_components_param_countries_over_region():
    c = _components_param(region="US", countries=["FR", "DE"])
    assert c == "country:FR|country:DE"


def test_components_param_region_only():
    c = _components_param(region="sg", countries=None)
    assert c == "country:SG"


def test_allowed_countries_iso2_from_props():
    props = {
        "allowed_countries": [
            {"iso2": "fr", "label_en": "France"},
            {"iso2": "DE", "label_en": "Germany"},
        ]
    }
    assert allowed_countries_iso2_from_props(props) == ["FR", "DE"]


def test_clamp_address_metadata_strips_raw_and_bounds():
    huge = {"raw": {"x": 1}, "formatted_address": "a" * 20000, "source": "google_places"}
    out = clamp_address_metadata_value(huge)
    assert "raw" not in out
    assert out.get("truncated") is True or len(str(out)) < 20000


def test_get_place_details_rejects_wrong_country(monkeypatch):
    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            class R:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {
                        "status": "OK",
                        "result": {
                            "place_id": "X",
                            "formatted_address": "Paris",
                            "partial_match": False,
                            "address_components": [
                                {
                                    "long_name": "France",
                                    "short_name": "FR",
                                    "types": ["country", "political"],
                                },
                            ],
                            "geometry": {"location": {"lat": 48.8, "lng": 2.3}},
                        },
                    }

            return R()

    monkeypatch.setattr(
        "services.address.google_places_service.httpx.Client",
        FakeClient,
    )
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    detail, err = get_place_details(
        "X",
        allowed_countries=["SG"],
        include_raw=False,
    )
    assert err == "country_not_allowed"
    assert detail == {}


def test_get_place_details_rejects_missing_country_when_allowlist(monkeypatch):
    """Google payload without country component → must not pass strict allowlist."""
    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            class R:
                def raise_for_status(self):
                    return None

                def json(self):
                    return {
                        "status": "OK",
                        "result": {
                            "place_id": "X",
                            "formatted_address": "Somewhere",
                            "partial_match": False,
                            "address_components": [
                                {
                                    "long_name": "Brussels",
                                    "short_name": "Brussels",
                                    "types": ["locality", "political"],
                                },
                            ],
                            "geometry": {"location": {"lat": 50.8, "lng": 4.3}},
                        },
                    }

            return R()

    monkeypatch.setattr(
        "services.address.google_places_service.httpx.Client",
        FakeClient,
    )
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    detail, err = get_place_details(
        "X",
        allowed_countries=["BE"],
        include_raw=False,
    )
    assert err == "country_not_allowed"
    assert detail == {}
