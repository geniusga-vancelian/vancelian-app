"""Tests for registration legacy component normalization."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import (
    FieldDefinition,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationJurisdiction,
    RegistrationScreenComponent,
    RegistrationStepScreen,
)
from services.registration.governance import check_flow_health
from services.registration.legacy_normalization import (
    apply_auto_fixes,
    are_field_slugs_equivalent,
    classify_component_legacy_state,
    diagnose_registration_components,
    normalize_slug,
    LegacyCategory,
    LegacyAction,
)


class TestNormalizeSlug:
    def test_kebab_to_snake_normalized(self):
        assert normalize_slug("date-of-birth") == "date_of_birth"

    def test_snake_stable(self):
        assert normalize_slug("date_of_birth") == "date_of_birth"

    def test_empty(self):
        assert normalize_slug("") == ""
        assert normalize_slug(None) == ""


class TestSlugEquivalence:
    def test_equivalent_kebab_snake(self):
        assert are_field_slugs_equivalent("date-of-birth", "date_of_birth")

    def test_exact(self):
        assert are_field_slugs_equivalent("email", "email")

    def test_mismatch(self):
        assert not are_field_slugs_equivalent("email", "phone_number")


def _fd(db: Session, slug: str) -> FieldDefinition:
    f = FieldDefinition(
        id=uuid.uuid4(),
        slug=slug,
        field_name_en=slug.replace("_", " ").title(),
        field_type="string",
        is_active=True,
    )
    db.add(f)
    db.flush()
    return f


def _index(db: Session):
    from services.registration.legacy_normalization import load_field_definition_indexes

    return load_field_definition_indexes(db)


class TestClassify:
    def test_content_ok(self, db: Session):
        by_n, by_i = _index(db)
        cat, act, *_ = classify_component_legacy_state("rich_text", None, None, by_n, by_i)
        assert cat == LegacyCategory.OK
        assert act == LegacyAction.NONE

    def test_content_auto_clear(self, db: Session):
        fd = _fd(db, "oops")
        by_n, by_i = _index(db)
        cat, act, reasons, pb, pfd = classify_component_legacy_state(
            "legal_content", "oops", fd.id, by_n, by_i
        )
        assert cat == LegacyCategory.AUTO_FIXABLE
        assert act == LegacyAction.CLEAR_CONTENT_BINDINGS

    def test_field_bound_link_unique(self, db: Session):
        u = uuid.uuid4().hex[:8]
        slug = f"uniq_link_{u}"
        _fd(db, slug)
        by_n, by_i = _index(db)
        cat, act, reasons, pb, pfd = classify_component_legacy_state(
            "text_input", slug.replace("_", "-"), None, by_n, by_i
        )
        assert cat == LegacyCategory.AUTO_FIXABLE
        assert act == LegacyAction.LINK_FIELD_BY_BINDING
        assert pb == slug
        assert pfd is not None

    def test_field_bound_canonical_binding(self, db: Session):
        fd = _fd(db, "canonical_slug")
        by_n, by_i = _index(db)
        cat, act, _, pb, pfd = classify_component_legacy_state(
            "text_input", "wrong_slug", fd.id, by_n, by_i
        )
        assert cat == LegacyCategory.AUTO_FIXABLE
        assert act == LegacyAction.CANONICAL_BINDING_FROM_FD
        assert pb == "canonical_slug"

    def test_ambiguous_no_binding_no_fd(self, db: Session):
        by_n, by_i = _index(db)
        cat, _, reasons, _, _ = classify_component_legacy_state("text_input", None, None, by_n, by_i)
        assert cat == LegacyCategory.AMBIGUOUS
        assert "field_bound_missing_binding_and_fd" in reasons

    def test_ambiguous_unknown_type(self, db: Session):
        by_n, by_i = _index(db)
        cat, _, reasons, _, _ = classify_component_legacy_state("weird_widget", "x", None, by_n, by_i)
        assert cat == LegacyCategory.AMBIGUOUS
        assert "unknown_component_type" in reasons

    def test_ambiguous_multiple_fd_same_norm(self, db: Session):
        u = uuid.uuid4().hex[:8]
        _fd(db, f"dup-{u}-a")
        _fd(db, f"dup_{u}_a")
        by_n, by_i = _index(db)
        cat, _, reasons, _, _ = classify_component_legacy_state(
            "text_input", f"dup-{u}-a", None, by_n, by_i
        )
        assert cat == LegacyCategory.AMBIGUOUS
        assert "multiple_field_definitions_for_binding" in reasons

    def test_ambiguous_no_fd_for_binding(self, db: Session):
        by_n, by_i = _index(db)
        cat, _, reasons, _, _ = classify_component_legacy_state(
            "text_input", "nonexistent_slug_xyz", None, by_n, by_i
        )
        assert cat == LegacyCategory.AMBIGUOUS
        assert "no_field_definition_for_binding" in reasons


def _minimal_flow(db: Session) -> tuple:
    j = RegistrationJurisdiction(
        id=uuid.uuid4(),
        code=f"LN{uuid.uuid4().hex[:6]}".upper(),
        name="Legacy Norm",
        is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(),
        jurisdiction_id=j.id,
        name="Flow",
        version=1,
        status="draft",
        entrypoint_type="individual",
    )
    db.add(flow)
    db.flush()
    step = RegistrationFlowStep(
        id=uuid.uuid4(),
        flow_id=flow.id,
        step_key="s1",
        title="Step",
        position=0,
        is_blocking=True,
    )
    db.add(step)
    db.flush()
    screen = RegistrationStepScreen(
        id=uuid.uuid4(),
        step_id=step.id,
        screen_key="sc1",
        title="Titled screen",
        position=0,
    )
    db.add(screen)
    db.flush()
    return flow, screen


class TestApplyAndHealth:
    def test_content_cleanup_apply(self, db: Session):
        _, screen = _minimal_flow(db)
        fd = _fd(db, "ghost")
        c = RegistrationScreenComponent(
            id=uuid.uuid4(),
            screen_id=screen.id,
            component_type="divider",
            component_key="d1",
            position=0,
            binding_slug="x",
            field_definition_id=fd.id,
        )
        db.add(c)
        db.flush()

        r = apply_auto_fixes(db, dry_run=False)
        assert not r.errors
        db.refresh(c)
        assert c.binding_slug is None
        assert c.field_definition_id is None
        assert any(a["action"] == LegacyAction.CLEAR_CONTENT_BINDINGS.value for a in r.applied)

    def test_link_and_canonical_then_publishable(self, db: Session):
        flow, screen = _minimal_flow(db)
        _fd(db, "legacy_field")
        comp = RegistrationScreenComponent(
            id=uuid.uuid4(),
            screen_id=screen.id,
            component_type="text_input",
            component_key="t1",
            position=0,
            binding_slug="legacy-field",
            field_definition_id=None,
            props_json={"label": "L"},
        )
        db.add(comp)
        db.flush()

        before = check_flow_health(flow.id, db)
        assert before.can_publish is False

        r = apply_auto_fixes(db, dry_run=False)
        assert not r.errors
        db.refresh(comp)
        assert comp.field_definition_id is not None
        assert comp.binding_slug == "legacy_field"

        after = check_flow_health(flow.id, db)
        assert after.can_publish is True

    def test_diagnose_counts(self, db: Session):
        _, screen = _minimal_flow(db)
        _fd(db, "only_one")
        db.add(
            RegistrationScreenComponent(
                id=uuid.uuid4(),
                screen_id=screen.id,
                component_type="text_input",
                component_key="a",
                position=0,
                binding_slug="only-one",
                props_json={},
            )
        )
        db.flush()
        d = diagnose_registration_components(db)
        assert d.totals["components_total"] >= 1
        assert d.totals["auto_fixable"] >= 1
