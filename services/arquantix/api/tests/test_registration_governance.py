"""Tests for the Registration Governance service — health checks, consistency, i18n, rules."""
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import (
    FieldDefinition,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationJurisdiction,
    RegistrationScreenComponent,
    RegistrationStepScreen,
)
from services.registration.governance import (
    HealthReport,
    check_flow_health,
    summarize_rule,
    get_component_support_registry,
    validate_component_family,
    VALID_RULE_OPERATORS,
    ALL_KNOWN_COMPONENT_TYPES,
    INPUT_COMPONENT_TYPES,
    CONTENT_COMPONENT_TYPES,
)


# ---------------------------------------------------------------------------
# Rule Summary
# ---------------------------------------------------------------------------

class TestSummarizeRule:
    def test_none(self):
        assert summarize_rule(None) is None

    def test_empty(self):
        assert summarize_rule({}) is None

    def test_equals(self):
        result = summarize_rule({"field": "country", "operator": "equals", "value": "FR"})
        assert result == "country = FR"

    def test_not_equals(self):
        result = summarize_rule({"field": "x", "operator": "not_equals", "value": "a"})
        assert result == "x != a"

    def test_in(self):
        result = summarize_rule({"field": "c", "operator": "in", "values": ["FR", "BE"]})
        assert "c in" in result
        assert "FR" in result

    def test_exists(self):
        result = summarize_rule({"field": "email", "operator": "exists"})
        assert result == "email exists"

    def test_not_exists(self):
        result = summarize_rule({"field": "x", "operator": "not_exists"})
        assert result == "x does not exist"

    def test_all_of(self):
        rule = {
            "operator": "all_of",
            "rules": [
                {"field": "a", "operator": "equals", "value": "1"},
                {"field": "b", "operator": "exists"},
            ],
        }
        result = summarize_rule(rule)
        assert "AND" in result
        assert "a = 1" in result
        assert "b exists" in result

    def test_any_of(self):
        rule = {
            "operator": "any_of",
            "rules": [
                {"field": "x", "operator": "equals", "value": "y"},
            ],
        }
        result = summarize_rule(rule)
        assert "x = y" in result


# ---------------------------------------------------------------------------
# Component Support Registry
# ---------------------------------------------------------------------------

class TestComponentSupportRegistry:
    def test_returns_list(self):
        registry = get_component_support_registry()
        assert isinstance(registry, list)
        assert len(registry) > 0

    def test_each_entry_has_required_keys(self):
        registry = get_component_support_registry()
        for entry in registry:
            assert "component_type" in entry
            assert "family" in entry
            assert entry["family"] in ("content", "field_bound")
            assert "is_input" in entry
            assert "admin_builder" in entry
            assert "flutter" in entry

    def test_text_input_is_input(self):
        registry = get_component_support_registry()
        text_input = next(e for e in registry if e["component_type"] == "text_input")
        assert text_input["is_input"] is True
        assert text_input["flutter"] is True

    def test_divider_is_not_input(self):
        registry = get_component_support_registry()
        divider = next(e for e in registry if e["component_type"] == "divider")
        assert divider["is_input"] is False


# ---------------------------------------------------------------------------
# HealthReport dataclass
# ---------------------------------------------------------------------------

class TestHealthReport:
    def test_default_can_publish(self):
        r = HealthReport()
        assert r.can_publish is True
        assert r.errors == []
        assert r.warnings == []

    def test_add_error_blocks_publish(self):
        r = HealthReport()
        r.add_error(category="test", message="fail")
        assert r.can_publish is False
        assert len(r.errors) == 1

    def test_add_warning_keeps_publish(self):
        r = HealthReport()
        r.add_warning(category="test", message="warn")
        assert r.can_publish is True
        assert len(r.warnings) == 1

    def test_to_dict(self):
        r = HealthReport()
        r.add_error(category="a", message="e")
        r.add_warning(category="b", message="w")
        d = r.to_dict()
        assert d["can_publish"] is False
        assert d["error_count"] == 1
        assert d["warning_count"] == 1
        assert len(d["errors"]) == 1
        assert len(d["warnings"]) == 1

    def test_issue_to_dict_optional_fields(self):
        r = HealthReport()
        r.add_error(category="c", message="m", step_id="s1", screen_id="sc1", component_id="co1")
        d = r.errors[0].to_dict()
        assert d["step_id"] == "s1"
        assert d["screen_id"] == "sc1"
        assert d["component_id"] == "co1"


# ---------------------------------------------------------------------------
# Constants integrity
# ---------------------------------------------------------------------------

class TestConstants:
    def test_input_and_content_disjoint(self):
        assert INPUT_COMPONENT_TYPES.isdisjoint(CONTENT_COMPONENT_TYPES)

    def test_all_known_is_union(self):
        assert ALL_KNOWN_COMPONENT_TYPES == INPUT_COMPONENT_TYPES | CONTENT_COMPONENT_TYPES

    def test_valid_operators(self):
        expected = {"equals", "not_equals", "in", "not_in", "exists", "not_exists", "all_of", "any_of"}
        assert VALID_RULE_OPERATORS == expected


# ---------------------------------------------------------------------------
# Field-bound enforcement (API helper)
# ---------------------------------------------------------------------------

class TestValidateComponentFamily:
    def _mock_db_with_fd(self, slug: str):
        fd = MagicMock()
        fd.slug = slug
        chain = MagicMock()
        chain.filter.return_value.first.return_value = fd
        db = MagicMock()
        db.query.return_value = chain
        return db

    def test_content_component_ok_without_binding(self):
        db = MagicMock()
        validate_component_family("rich_text", None, None, db)

    def test_content_rejects_binding_slug(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as ei:
            validate_component_family("section_title", None, "oops", db)
        assert ei.value.status_code == 422

    def test_content_rejects_field_definition_id(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as ei:
            validate_component_family("divider", uuid.uuid4(), None, db)
        assert ei.value.status_code == 422

    def test_input_requires_field_definition_id(self):
        db = MagicMock()
        with pytest.raises(HTTPException) as ei:
            validate_component_family("text_input", None, "first_name", db)
        assert ei.value.status_code == 422

    def test_input_requires_binding_slug(self):
        db = self._mock_db_with_fd("first_name")
        with pytest.raises(HTTPException) as ei:
            validate_component_family("text_input", uuid.uuid4(), None, db)
        assert ei.value.status_code == 422

    def test_input_rejects_binding_mismatch(self):
        db = self._mock_db_with_fd("first_name")
        with pytest.raises(HTTPException) as ei:
            validate_component_family("text_input", uuid.uuid4(), "last_name", db)
        assert ei.value.status_code == 422

    def test_input_accepts_matching_binding(self):
        fd_id = uuid.uuid4()
        db = self._mock_db_with_fd("first_name")
        validate_component_family("text_input", fd_id, "first_name", db)


# ---------------------------------------------------------------------------
# Health: field binding as blocking errors
# ---------------------------------------------------------------------------

def _minimal_flow_with_component(db: Session, **comp_kwargs):
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code=f"HB{uuid.uuid4().hex[:6]}".upper(), name="Health Test", is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id, name="H Flow", version=1, status="draft", entrypoint_type="individual",
    )
    db.add(flow)
    db.flush()
    step = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id, step_key="s1", title="S1", position=0, is_blocking=True,
    )
    db.add(step)
    db.flush()
    screen = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step.id, screen_key="sc1", title="Screen", position=0,
    )
    db.add(screen)
    db.flush()
    comp = RegistrationScreenComponent(
        id=uuid.uuid4(),
        screen_id=screen.id,
        position=0,
        **comp_kwargs,
    )
    db.add(comp)
    db.flush()
    return flow


class TestCheckFlowHealthFieldBinding:
    def test_input_without_field_definition_blocks_publish(self, db: Session):
        flow = _minimal_flow_with_component(
            db,
            component_type="text_input",
            component_key="t1",
            binding_slug="full_name",
            field_definition_id=None,
            props_json={"label": "Name"},
        )
        report = check_flow_health(flow.id, db)
        assert report.can_publish is False
        assert any(e.category == "field_binding" for e in report.errors)

    def test_content_with_binding_blocks_publish(self, db: Session):
        flow = _minimal_flow_with_component(
            db,
            component_type="rich_text",
            component_key="c1",
            binding_slug="should_not_exist",
            field_definition_id=None,
            props_json={"label": "Hi"},
        )
        report = check_flow_health(flow.id, db)
        assert report.can_publish is False
        msgs = " ".join(e.message for e in report.errors)
        assert "binding_slug" in msgs

    def test_valid_field_bound_passes_field_checks(self, db: Session):
        fd = FieldDefinition(
            id=uuid.uuid4(),
            slug="full_name",
            field_name_en="Full name",
            field_type="string",
            category="identity",
            is_active=True,
        )
        db.add(fd)
        db.flush()
        flow = _minimal_flow_with_component(
            db,
            component_type="text_input",
            component_key="t1",
            binding_slug="full_name",
            field_definition_id=fd.id,
            props_json={"label": "Name"},
        )
        report = check_flow_health(flow.id, db)
        assert all(e.category != "field_binding" for e in report.errors)
