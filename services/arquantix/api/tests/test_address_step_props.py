"""address_step props normalization and validation."""
import pytest
from fastapi import HTTPException

from services.registration.address_step_props import (
    normalize_address_step_props,
    validate_address_step_props_json,
)


def test_normalize_merges_legacy_strings_into_i18n():
    raw = {
        "title": "Legacy title",
        "search_label": "Search",
        "field_labels_i18n": {"postal_code": "PC"},
    }
    out = normalize_address_step_props(raw)
    assert out["title_i18n"]["en"] == "Legacy title"
    assert out["title_i18n"]["fr"] == "Legacy title"
    assert out["search_label_i18n"]["en"] == "Search"
    assert out["field_labels_i18n"]["postal_code"] == {"en": "PC", "fr": "PC"}
    assert out["title"] == "Legacy title"


def test_validate_rejects_bad_field_key():
    with pytest.raises(HTTPException) as exc:
        validate_address_step_props_json({"field_labels_i18n": {"unknown": {"en": "x"}}})
    assert exc.value.status_code == 422


def test_validate_accepts_optional_i18n_absent():
    validate_address_step_props_json({})
