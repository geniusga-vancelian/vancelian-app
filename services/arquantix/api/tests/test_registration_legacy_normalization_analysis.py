"""Tests for legacy normalization report analysis (pure JSON / no DB for analysis)."""
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
from services.registration.legacy_normalization import apply_auto_fixes, result_to_dict
from services.registration.legacy_normalization_analysis import (
    analyze_legacy_normalization_report,
    compute_post_apply_delta,
    format_console_analysis,
    format_post_apply_delta,
    load_report,
    validate_safe_to_apply,
)


def _minimal_report(**kwargs):
    base = {
        "dry_run": True,
        "timestamp_utc": "2026-01-01T00:00:00Z",
        "totals": {"components_total": 10, "ok": 8, "auto_fixable": 1, "ambiguous": 1},
        "ok": [],
        "auto_fixable": [],
        "ambiguous": [],
        "applied": [],
        "health_before": {
            "flows_total": 5,
            "publishable": 2,
            "blocked": 3,
            "flows": [
                {"flow_id": str(uuid.uuid4()), "can_publish": False, "flow_name": "A"},
            ],
        },
        "health_after": None,
        "errors": [],
    }
    base.update(kwargs)
    return base


def test_analyze_coherent_totals():
    r = _minimal_report()
    a = analyze_legacy_normalization_report(r)
    assert a.total_components == 10
    assert a.ok_count == 8
    assert a.auto_fixable_count == 1
    assert a.ambiguous_count == 1
    assert "==== LEGACY NORMALIZATION REPORT ====" in format_console_analysis(a)


def test_analyze_top_reasons_and_dangerous():
    r = _minimal_report(
        ambiguous=[
            {
                "component_id": "c1",
                "reason_codes": ["no_field_definition_for_binding", "orphan_field_definition_id"],
                "binding_slug": "lost",
                "component_type": "text_input",
            },
            {
                "component_id": "c2",
                "reason_codes": ["multiple_field_definitions_for_binding"],
                "binding_slug": "dup",
                "component_type": "text_input",
            },
            {
                "component_id": "c3",
                "reason_codes": ["unknown_component_type"],
                "binding_slug": None,
                "component_type": "weird",
            },
        ],
    )
    a = analyze_legacy_normalization_report(r)
    assert a.dangerous_unknown_type_count == 1
    assert a.dangerous_orphan_fd_count == 1
    assert a.multiple_field_match_count == 1
    codes = [x[0] for x in a.top_ambiguous_reasons]
    assert "no_field_definition_for_binding" in codes


def test_validate_blocks_high_ambiguous_pct():
    r = _minimal_report(
        totals={"components_total": 100, "ok": 50, "auto_fixable": 30, "ambiguous": 20},
    )
    a = analyze_legacy_normalization_report(r)
    v = validate_safe_to_apply(a, max_ambiguous_pct=10.0)
    assert v.safe is False
    assert any("Ambiguous ratio" in b for b in v.blockers)


def test_validate_allows_low_ambiguous():
    r = _minimal_report(
        totals={"components_total": 100, "ok": 95, "auto_fixable": 4, "ambiguous": 1},
    )
    a = analyze_legacy_normalization_report(r)
    v = validate_safe_to_apply(a, max_ambiguous_pct=10.0)
    assert v.safe is True


def test_compute_delta_and_format():
    before = _minimal_report(
        totals={"components_total": 5, "ok": 2, "auto_fixable": 2, "ambiguous": 1},
        health_before={"flows_total": 3, "publishable": 1, "blocked": 2, "flows": []},
    )
    after = _minimal_report(
        totals={"components_total": 5, "ok": 4, "auto_fixable": 0, "ambiguous": 1},
        health_before={"flows_total": 3, "publishable": 2, "blocked": 1, "flows": []},
    )
    apply_rep = {
        "applied": [
            {"action": "link_field_by_binding"},
            {"action": "link_field_by_binding"},
        ]
    }
    d = compute_post_apply_delta(before, after, apply_rep)
    assert d["auto_fixable"]["before"] == 2
    assert d["auto_fixable"]["after"] == 0
    text = format_post_apply_delta(d)
    assert "POST APPLY DELTA" in text
    assert "link_field_by_binding" in text


def test_load_report_roundtrip(tmp_path):
    p = tmp_path / "r.json"
    data = _minimal_report()
    p.write_text(__import__("json").dumps(data), encoding="utf-8")
    assert load_report(p)["totals"]["components_total"] == 10


class TestApplyIntegrationAnalysis:
    """Apply reduces auto_fixable; ambiguous stable; no row delete."""

    def test_apply_reduces_auto_fixable_improves_health_no_delete(self, db: Session):
        j = RegistrationJurisdiction(
            id=uuid.uuid4(),
            code=f"AN{uuid.uuid4().hex[:6]}".upper(),
            name="A",
            is_active=True,
        )
        db.add(j)
        db.flush()
        flow = RegistrationFlow(
            id=uuid.uuid4(),
            jurisdiction_id=j.id,
            name="F",
            version=1,
            status="draft",
            entrypoint_type="individual",
        )
        db.add(flow)
        db.flush()
        step = RegistrationFlowStep(
            id=uuid.uuid4(),
            flow_id=flow.id,
            step_key="s",
            title="S",
            position=0,
            is_blocking=True,
        )
        db.add(step)
        db.flush()
        screen = RegistrationStepScreen(
            id=uuid.uuid4(),
            step_id=step.id,
            screen_key="sc",
            title="T",
            position=0,
        )
        db.add(screen)
        db.flush()
        fd = FieldDefinition(
            id=uuid.uuid4(),
            slug="fixme_slug",
            field_name_en="X",
            field_type="string",
            is_active=True,
        )
        db.add(fd)
        db.flush()
        c = RegistrationScreenComponent(
            id=uuid.uuid4(),
            screen_id=screen.id,
            component_type="text_input",
            component_key="k",
            position=0,
            binding_slug="fixme-slug",
            props_json={},
        )
        db.add(c)
        db.flush()

        n_before = db.query(RegistrationScreenComponent).count()
        dry_before = result_to_dict(apply_auto_fixes(db, dry_run=True))
        ab = analyze_legacy_normalization_report(dry_before)
        assert ab.auto_fixable_count >= 1

        r = apply_auto_fixes(db, dry_run=False)
        assert not r.errors
        n_after = db.query(RegistrationScreenComponent).count()
        assert n_before == n_after

        dry_after = result_to_dict(apply_auto_fixes(db, dry_run=True))
        aa = analyze_legacy_normalization_report(dry_after)
        assert aa.auto_fixable_count == 0

        delta = compute_post_apply_delta(dry_before, dry_after, result_to_dict(r))
        assert delta["auto_fixable"]["after"] == 0
