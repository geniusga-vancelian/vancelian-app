"""Field catalog slugs used by registration seeds align with legacy normalization."""
from __future__ import annotations

import uuid
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from database import FieldDefinition, RegistrationScreenComponent
from services.registration.legacy_normalization import (
    LegacyAction,
    LegacyCategory,
    classify_component_legacy_state,
    load_field_definition_indexes,
    normalize_slug,
)


def _fd(
    db: Session,
    *,
    slug: str,
    field_type: str = "string",
    component_type_default: Optional[str] = "text_input",
) -> FieldDefinition:
    existing = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
    if existing:
        return existing
    f = FieldDefinition(
        id=uuid.uuid4(),
        slug=slug,
        field_name_en=slug.replace("-", " ").title(),
        field_type=field_type,
        is_active=True,
        component_type_default=component_type_default,
    )
    db.add(f)
    db.flush()
    return f


@pytest.mark.parametrize(
    "binding_slug,fd_slug,component_type,exp_category,exp_action",
    [
        ("country_of_residence", "country-of-residence", "country_picker", LegacyCategory.AUTO_FIXABLE, LegacyAction.LINK_FIELD_BY_BINDING),
        ("annual_income_range", "annual-income-range", "select", LegacyCategory.AUTO_FIXABLE, LegacyAction.LINK_FIELD_BY_BINDING),
        ("known_asset_classes", "known-asset-classes", "multi_select", LegacyCategory.AUTO_FIXABLE, LegacyAction.LINK_FIELD_BY_BINDING),
        ("terms_accepted", "terms-accepted", "checkbox", LegacyCategory.AUTO_FIXABLE, LegacyAction.LINK_FIELD_BY_BINDING),
        ("terms_and_conditions", "terms-and-conditions", "checkbox", LegacyCategory.AUTO_FIXABLE, LegacyAction.LINK_FIELD_BY_BINDING),
        ("privacy_policy", "privacy-policy", "checkbox", LegacyCategory.AUTO_FIXABLE, LegacyAction.LINK_FIELD_BY_BINDING),
    ],
)
def test_seed_bindings_resolve_to_unique_field_definition(
    db: Session,
    binding_slug: str,
    fd_slug: str,
    component_type: str,
    exp_category: LegacyCategory,
    exp_action: LegacyAction,
):
    _fd(
        db,
        slug=fd_slug,
        field_type="boolean" if component_type == "checkbox" else "string",
        component_type_default=component_type,
    )
    by_n, by_i = load_field_definition_indexes(db)
    cat, act, reasons, pb, pfd = classify_component_legacy_state(
        component_type,
        binding_slug,
        None,
        by_n,
        by_i,
    )
    assert cat == exp_category
    assert act == exp_action
    assert "no_field_definition_for_binding" not in reasons
    assert pb == fd_slug
    assert pfd is not None


def test_kebab_slug_normalization_matches_snake_binding(db: Session):
    """Catalog uses kebab-case slugs; bindings in seeds use snake_case."""
    assert normalize_slug("country-of-residence") == normalize_slug("country_of_residence")
    assert normalize_slug("annual-income-range") == normalize_slug("annual_income_range")


def test_orphan_input_resolves_after_inferred_binding(db: Session):
    """Simulate post-migration state: component_key maps to binding + FD."""
    _fd(db, slug="first-name", component_type_default="text_input")
    by_n, by_i = load_field_definition_indexes(db)
    cat0, _, reasons0, _, _ = classify_component_legacy_state(
        "text_input", None, None, by_n, by_i
    )
    assert cat0 == LegacyCategory.AMBIGUOUS
    assert "field_bound_missing_binding_and_fd" in reasons0

    cat1, act1, reasons1, pb, pfd = classify_component_legacy_state(
        "text_input",
        "first_name",
        None,
        by_n,
        by_i,
    )
    assert cat1 == LegacyCategory.AUTO_FIXABLE
    assert act1 == LegacyAction.LINK_FIELD_BY_BINDING
    assert pb == "first-name"
    assert "no_field_definition_for_binding" not in reasons1


def test_autokey_component_resolves_when_binding_assigned(db: Session):
    """After DB repair (093-style), auto-generated keys + canonical binding are OK."""
    fd = _fd(db, slug="phone-number", field_type="string", component_type_default="phone_input")
    by_n, by_i = load_field_definition_indexes(db)
    cat, act, reasons, _, _ = classify_component_legacy_state(
        "phone_input",
        "phone_number",
        fd.id,
        by_n,
        by_i,
    )
    assert cat == LegacyCategory.OK
    assert act == LegacyAction.NONE
    assert "field_bound_missing_binding_and_fd" not in reasons


def test_no_duplicate_normalized_slug_in_catalog_slice(db: Session):
    """Guard: two distinct slugs must not collapse to the same normalize_slug in one test DB."""
    u = uuid.uuid4().hex[:8]
    s1, s2 = f"catalog-dup-a-{u}", f"catalog-dup-b-{u}"
    _fd(db, slug=s1)
    _fd(db, slug=s2)
    by_n, _ = load_field_definition_indexes(db)
    assert normalize_slug(s1) != normalize_slug(s2)
    assert len(by_n.get(normalize_slug(s1), [])) == 1
    assert len(by_n.get(normalize_slug(s2), [])) == 1
