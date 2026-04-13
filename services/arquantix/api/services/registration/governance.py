"""Registration Flow Governance — Health checks, consistency, i18n completeness.

Centralised service layer for:
  - Flow health / publish-readiness checks
  - Content vs field-bound component classification (INPUT_COMPONENT_TYPES / CONTENT_COMPONENT_TYPES)
  - Field binding enforcement (health + validate_component_family for API)
  - i18n completeness analysis
  - Rule JSON validation
  - Component support registry
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from database import (
    FieldDefinition,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationStepScreen,
    RegistrationScreenComponent,
    RegistrationJurisdiction,
)
from .interaction_helpers import effective_screen_type

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ["en", "fr"]

INPUT_COMPONENT_TYPES = {
    "text_input", "phone_input", "select", "country_picker",
    "date_picker", "checkbox", "multi_select",
    "address_autocomplete",
    "address_step",
}

CONTENT_COMPONENT_TYPES = {
    "section_title", "rich_text", "info_box", "legal_content",
    "divider", "spacer", "bullet_list", "link_text",
}

ALL_KNOWN_COMPONENT_TYPES = INPUT_COMPONENT_TYPES | CONTENT_COMPONENT_TYPES

FLUTTER_SUPPORTED_TYPES = ALL_KNOWN_COMPONENT_TYPES - {"link_text"}

VALID_RULE_OPERATORS = {
    "equals", "not_equals", "in", "not_in",
    "exists", "not_exists", "all_of", "any_of",
}


@dataclass
class HealthIssue:
    level: str  # "error" or "warning"
    category: str
    message: str
    step_id: Optional[str] = None
    screen_id: Optional[str] = None
    component_id: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"level": self.level, "category": self.category, "message": self.message}
        if self.step_id:
            d["step_id"] = self.step_id
        if self.screen_id:
            d["screen_id"] = self.screen_id
        if self.component_id:
            d["component_id"] = self.component_id
        return d


@dataclass
class HealthReport:
    can_publish: bool = True
    errors: List[HealthIssue] = field(default_factory=list)
    warnings: List[HealthIssue] = field(default_factory=list)

    def add_error(self, **kwargs: Any) -> None:
        self.errors.append(HealthIssue(level="error", **kwargs))
        self.can_publish = False

    def add_warning(self, **kwargs: Any) -> None:
        self.warnings.append(HealthIssue(level="warning", **kwargs))

    def to_dict(self) -> dict:
        return {
            "can_publish": self.can_publish,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


# ---------------------------------------------------------------------------
# Flow Health Check
# ---------------------------------------------------------------------------

def check_flow_health(flow_id: UUID, db: Session) -> HealthReport:
    """Run all health checks on a flow and return a publish-readiness report."""
    report = HealthReport()

    flow = (
        db.query(RegistrationFlow)
        .options(
            joinedload(RegistrationFlow.steps)
            .joinedload(RegistrationFlowStep.screens)
            .joinedload(RegistrationStepScreen.components)
            .joinedload(RegistrationScreenComponent.field_definition),
        )
        .options(joinedload(RegistrationFlow.jurisdiction))
        .filter(RegistrationFlow.id == flow_id)
        .first()
    )

    if not flow:
        report.add_error(category="flow", message="Flow not found")
        return report

    _check_flow_structure(flow, report)
    _check_jurisdiction(flow, report)
    _check_components(flow, report)
    _check_i18n(flow, report)
    _check_rules(flow, report)
    _check_field_consistency(flow, report)

    return report


def _check_flow_structure(flow: RegistrationFlow, report: HealthReport) -> None:
    if not flow.steps:
        report.add_error(category="structure", message="Flow has no steps")
        return

    for step in flow.steps:
        sid = str(step.id)
        if not step.screens:
            report.add_error(
                category="structure",
                message=f"Step '{step.title}' has no screens",
                step_id=sid,
            )
            continue

        for screen in step.screens:
            scid = str(screen.id)
            has_content = bool(screen.title) or bool(screen.subtitle)
            has_components = bool(screen.components)
            st = effective_screen_type(screen)
            skip_empty = st in ("interaction", "permission_prompt")
            if not has_content and not has_components and not skip_empty:
                report.add_error(
                    category="structure",
                    message=f"Screen '{screen.screen_key}' has no title/subtitle and no components",
                    step_id=sid,
                    screen_id=scid,
                )


def _check_jurisdiction(flow: RegistrationFlow, report: HealthReport) -> None:
    if not flow.jurisdiction:
        report.add_error(category="jurisdiction", message="Flow has no jurisdiction")
    elif not flow.jurisdiction.is_active:
        report.add_error(
            category="jurisdiction",
            message=f"Jurisdiction '{flow.jurisdiction.code}' is inactive",
        )


def _check_components(flow: RegistrationFlow, report: HealthReport) -> None:
    for step in flow.steps:
        sid = str(step.id)
        for screen in step.screens:
            scid = str(screen.id)
            binding_slugs_on_screen: List[str] = []

            for comp in screen.components:
                cid = str(comp.id)
                ct = comp.component_type

                if ct not in ALL_KNOWN_COMPONENT_TYPES:
                    report.add_error(
                        category="component",
                        message=f"Unknown component_type '{ct}'",
                        step_id=sid, screen_id=scid, component_id=cid,
                    )

                # ── Field-bound components (inputs) ──
                if ct in INPUT_COMPONENT_TYPES:
                    if not comp.field_definition_id:
                        report.add_error(
                            category="field_binding",
                            message=f"Client field component '{ct}' must be linked to a field definition",
                            step_id=sid, screen_id=scid, component_id=cid,
                        )

                    if not comp.binding_slug:
                        report.add_error(
                            category="field_binding",
                            message=f"Client field component '{ct}' must have a binding_slug",
                            step_id=sid, screen_id=scid, component_id=cid,
                        )

                    if comp.field_definition_id and comp.binding_slug:
                        fd = comp.field_definition
                        if fd and fd.slug.replace("-", "_") != comp.binding_slug.replace("-", "_"):
                            report.add_error(
                                category="field_binding",
                                message=f"binding_slug '{comp.binding_slug}' doesn't match field definition slug '{fd.slug}'",
                                step_id=sid, screen_id=scid, component_id=cid,
                            )

                    if ct == "address_autocomplete":
                        from .address_autocomplete import resolved_binding_slugs

                        pj = comp.props_json or {}
                        bs = pj.get("binding_slugs")
                        if not isinstance(bs, dict):
                            report.add_error(
                                category="component",
                                message="address_autocomplete requires props.binding_slugs",
                                step_id=sid, screen_id=scid, component_id=cid,
                            )
                        for s in resolved_binding_slugs(pj).values():
                            binding_slugs_on_screen.append(s)
                    elif ct == "address_step":
                        from .address_autocomplete import resolved_address_step_binding_slugs

                        pj = comp.props_json or {}
                        bs = pj.get("binding_slugs")
                        if bs is not None and not isinstance(bs, dict):
                            report.add_error(
                                category="component",
                                message="address_step props.binding_slugs must be an object",
                                step_id=sid, screen_id=scid, component_id=cid,
                            )
                        for s in resolved_address_step_binding_slugs(pj).values():
                            binding_slugs_on_screen.append(s)
                    elif comp.binding_slug:
                        binding_slugs_on_screen.append(comp.binding_slug)

                # ── Content components ──
                if ct in CONTENT_COMPONENT_TYPES:
                    if comp.binding_slug:
                        report.add_error(
                            category="field_binding",
                            message=f"Content component '{ct}' must not have a binding_slug (found '{comp.binding_slug}')",
                            step_id=sid, screen_id=scid, component_id=cid,
                        )
                    if comp.field_definition_id:
                        report.add_error(
                            category="field_binding",
                            message=f"Content component '{ct}' must not be linked to a field definition",
                            step_id=sid, screen_id=scid, component_id=cid,
                        )

                if ct in ("select", "multi_select"):
                    props = comp.props_json or {}
                    options = props.get("options")
                    if not options or not isinstance(options, list) or len(options) == 0:
                        report.add_error(
                            category="component",
                            message=f"'{ct}' component has no or invalid options",
                            step_id=sid, screen_id=scid, component_id=cid,
                        )

                if ct not in FLUTTER_SUPPORTED_TYPES:
                    report.add_warning(
                        category="flutter",
                        message=f"Component type '{ct}' may not be supported in Flutter",
                        step_id=sid, screen_id=scid, component_id=cid,
                    )

            dupes = [s for s in set(binding_slugs_on_screen)
                     if binding_slugs_on_screen.count(s) > 1]
            for dup in dupes:
                report.add_warning(
                    category="consistency",
                    message=f"Duplicate binding_slug '{dup}' on screen",
                    step_id=sid, screen_id=scid,
                )

            if effective_screen_type(screen) == "form":
                addr_only = [
                    c
                    for c in screen.components
                    if getattr(c, "component_type", None) == "address_step"
                ]
                if len(addr_only) == 1 and len(screen.components) == 1:
                    cfg = screen.config_json
                    if not isinstance(cfg, dict):
                        cfg = {}
                    preset = cfg.get("builder_preset")
                    if preset != "address_step":
                        report.add_warning(
                            category="builder_preset",
                            message=(
                                "Form screen contains only an address_step component but "
                                "config_json.builder_preset is not 'address_step'. "
                                "Use + Address in the registration builder so tooling recognizes the preset."
                            ),
                            step_id=sid,
                            screen_id=scid,
                        )


def _check_i18n(flow: RegistrationFlow, report: HealthReport) -> None:
    langs = SUPPORTED_LANGUAGES

    for step in flow.steps:
        sid = str(step.id)
        i18n = step.title_i18n or {}
        for lang in langs:
            if not i18n.get(lang):
                report.add_warning(
                    category="i18n",
                    message=f"Step '{step.title}': missing '{lang}' translation for title",
                    step_id=sid,
                )

        for screen in step.screens:
            scid = str(screen.id)
            si18n = screen.title_i18n or {}
            for lang in langs:
                if not si18n.get(lang):
                    report.add_warning(
                        category="i18n",
                        message=f"Screen '{screen.title or screen.screen_key}': missing '{lang}' translation for title",
                        step_id=sid, screen_id=scid,
                    )

            for comp in screen.components:
                cid = str(comp.id)
                if comp.component_type not in INPUT_COMPONENT_TYPES:
                    continue
                props = comp.props_json or {}
                label_i18n = props.get("label_i18n") or {}
                label = props.get("label", "")
                if label:
                    for lang in langs:
                        if not label_i18n.get(lang):
                            report.add_warning(
                                category="i18n",
                                message=f"Component '{label}': missing '{lang}' translation",
                                step_id=sid, screen_id=scid, component_id=cid,
                            )


def _check_rules(flow: RegistrationFlow, report: HealthReport) -> None:
    for step in flow.steps:
        sid = str(step.id)
        _validate_rule_json(step.visibility_rule_json, "visibility", sid, None, None, report)
        _validate_rule_json(step.completion_rule_json, "completion", sid, None, None, report)

        for screen in step.screens:
            for comp in screen.components:
                cid = str(comp.id)
                _validate_rule_json(
                    comp.visibility_rule_json, "visibility",
                    sid, str(screen.id), cid, report,
                )
                _validate_rule_json(
                    comp.validation_rule_json, "validation",
                    sid, str(screen.id), cid, report,
                )


def _validate_rule_json(
    rule: Optional[Dict[str, Any]],
    rule_type: str,
    step_id: str,
    screen_id: Optional[str],
    component_id: Optional[str],
    report: HealthReport,
) -> None:
    if not rule:
        return

    if not isinstance(rule, dict):
        report.add_warning(
            category="rules",
            message=f"'{rule_type}' rule: expected a JSON object",
            step_id=step_id, screen_id=screen_id, component_id=component_id,
        )
        return

    # Legacy / Flutter shorthand (e.g. {"type": "required"}) — not the rule-engine shape
    if "operator" not in rule and "rules" not in rule:
        return

    op = rule.get("operator", "equals")
    if op in ("all_of", "any_of"):
        sub_rules = rule.get("rules")
        if not isinstance(sub_rules, list):
            report.add_warning(
                category="rules",
                message=f"'{rule_type}' rule: '{op}' requires a 'rules' array",
                step_id=step_id, screen_id=screen_id, component_id=component_id,
            )
            return
        for sub in sub_rules:
            _validate_rule_json(sub, rule_type, step_id, screen_id, component_id, report)
        return

    if op not in VALID_RULE_OPERATORS:
        report.add_warning(
            category="rules",
            message=f"'{rule_type}' rule: unknown operator '{op}'",
            step_id=step_id, screen_id=screen_id, component_id=component_id,
        )
        return

    if not rule.get("field"):
        report.add_warning(
            category="rules",
            message=f"'{rule_type}' rule: missing 'field' for operator '{op}'",
            step_id=step_id, screen_id=screen_id, component_id=component_id,
        )


def _check_field_consistency(flow: RegistrationFlow, report: HealthReport) -> None:
    """Legacy field consistency — slug-level checks now live in _check_components.

    This function remains as an extension point for additional cross-component
    consistency analysis (e.g. detecting the same field used in multiple flows).
    """
    pass


def _validate_address_optional_metadata_slug(pj: Dict[str, Any], component_label: str) -> None:
    """Raise HTTPException(422) if metadata_slug is present but invalid."""
    from fastapi import HTTPException

    ms = pj.get("metadata_slug")
    if ms is None:
        return
    if not isinstance(ms, str) or not ms.strip():
        raise HTTPException(
            status_code=422,
            detail=f"{component_label} metadata_slug must be a non-empty string",
        )
    mst = ms.strip()
    if not mst.replace("_", "").isalnum() or not mst[0].isalpha():
        raise HTTPException(
            status_code=422,
            detail=f"{component_label} metadata_slug must be a simple snake_case slug",
        )


def _validate_address_allowed_countries(ac: Any, component_label: str) -> None:
    """Raise HTTPException(422) if allowed_countries is present but invalid."""
    from fastapi import HTTPException

    if ac is None:
        return
    if not isinstance(ac, list):
        raise HTTPException(
            status_code=422,
            detail=f"{component_label} allowed_countries must be a JSON array",
        )
    if len(ac) > 60:
        raise HTTPException(
            status_code=422,
            detail=f"{component_label} allowed_countries list is too long (max 60)",
        )
    for item in ac:
        if isinstance(item, str):
            s = item.strip()
            if len(s) != 2 or not s.isalpha():
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"{component_label} allowed_countries string entries must be "
                        "ISO 3166-1 alpha-2"
                    ),
                )
        elif isinstance(item, dict):
            iso = item.get("iso2") or item.get("value")
            if not isinstance(iso, str) or len(iso.strip()) != 2 or not iso.strip().isalpha():
                raise HTTPException(
                    status_code=422,
                    detail=f"{component_label} allowed_countries objects need iso2 (2-letter)",
                )
        else:
            raise HTTPException(
                status_code=422,
                detail=f"{component_label} allowed_countries entries must be string or object",
            )


# ---------------------------------------------------------------------------
# API-level enforcement helpers
# ---------------------------------------------------------------------------

def validate_component_family(
    component_type: str,
    field_definition_id: Optional[UUID],
    binding_slug: Optional[str],
    db: Session,
    props_json: Optional[Dict[str, Any]] = None,
) -> None:
    """Raise HTTPException(422) if the component violates content/field-bound rules.

    Called from create_component and update_component endpoints.
    """
    from fastapi import HTTPException

    if component_type in INPUT_COMPONENT_TYPES:
        if not field_definition_id:
            raise HTTPException(
                status_code=422,
                detail=f"Client field component '{component_type}' must be linked to a field definition (field_definition_id required)",
            )
        if not binding_slug:
            raise HTTPException(
                status_code=422,
                detail=f"Client field component '{component_type}' must have a binding_slug",
            )
        fd = db.query(FieldDefinition).filter(FieldDefinition.id == field_definition_id).first()
        if not fd:
            raise HTTPException(
                status_code=422,
                detail=f"Field definition '{field_definition_id}' not found",
            )
        if fd.slug.replace("-", "_") != binding_slug.replace("-", "_"):
            raise HTTPException(
                status_code=422,
                detail=f"binding_slug '{binding_slug}' doesn't match field definition slug '{fd.slug}'",
            )
        if component_type == "address_autocomplete":
            pj = props_json if isinstance(props_json, dict) else {}
            bs = pj.get("binding_slugs")
            if not isinstance(bs, dict):
                raise HTTPException(
                    status_code=422,
                    detail="address_autocomplete requires props_json.binding_slugs object",
                )
            for key in ("street", "postal", "city", "country"):
                v = bs.get(key)
                if not isinstance(v, str) or not v.strip():
                    raise HTTPException(
                        status_code=422,
                        detail=f"address_autocomplete binding_slugs.{key} must be a non-empty string",
                    )
            street_slug = bs.get("street", "").strip()
            if street_slug.replace("-", "_") != binding_slug.replace("-", "_"):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "address_autocomplete binding_slug must match binding_slugs.street "
                        f"(expected street slug '{street_slug}', got binding_slug '{binding_slug}')"
                    ),
                )
            _validate_address_optional_metadata_slug(pj, "address_autocomplete")
            _validate_address_allowed_countries(pj.get("allowed_countries"), "address_autocomplete")

        elif component_type == "address_step":
            from .address_autocomplete import resolved_address_step_binding_slugs

            pj = props_json if isinstance(props_json, dict) else {}
            bs = pj.get("binding_slugs")
            if bs is not None and not isinstance(bs, dict):
                raise HTTPException(
                    status_code=422,
                    detail="address_step binding_slugs must be an object when provided",
                )
            resolved = resolved_address_step_binding_slugs(pj)
            primary = resolved["address_line_1"].strip()
            if primary.replace("-", "_") != binding_slug.replace("-", "_"):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "address_step binding_slug must match binding_slugs.address_line_1 "
                        f"(expected '{primary}', got binding_slug '{binding_slug}')"
                    ),
                )
            for key, slug in resolved.items():
                if not isinstance(slug, str) or not slug.strip():
                    raise HTTPException(
                        status_code=422,
                        detail=f"address_step binding_slugs.{key} must be a non-empty string",
                    )
            se = pj.get("search_enabled")
            if se is not None and not isinstance(se, bool):
                raise HTTPException(
                    status_code=422,
                    detail="address_step search_enabled must be a boolean",
                )
            smc = pj.get("search_min_chars")
            if smc is not None:
                if not isinstance(smc, int) or smc < 1 or smc > 20:
                    raise HTTPException(
                        status_code=422,
                        detail="address_step search_min_chars must be an integer from 1 to 20",
                    )
            sdm = pj.get("search_debounce_ms")
            if sdm is not None:
                if not isinstance(sdm, int) or sdm < 50 or sdm > 5000:
                    raise HTTPException(
                        status_code=422,
                        detail="address_step search_debounce_ms must be an integer from 50 to 5000",
                    )
            spi = pj.get("store_place_id")
            if spi is not None and not isinstance(spi, bool):
                raise HTTPException(
                    status_code=422,
                    detail="address_step store_place_id must be a boolean",
                )
            lo = pj.get("address_line_2_optional")
            if lo is not None and not isinstance(lo, bool):
                raise HTTPException(
                    status_code=422,
                    detail="address_step address_line_2_optional must be a boolean",
                )
            from .address_step_props import validate_address_step_props_json

            validate_address_step_props_json(pj)
            _validate_address_optional_metadata_slug(pj, "address_step")
            _validate_address_allowed_countries(pj.get("allowed_countries"), "address_step")

    if component_type in CONTENT_COMPONENT_TYPES:
        if field_definition_id:
            raise HTTPException(
                status_code=422,
                detail=f"Content component '{component_type}' must not be linked to a field definition",
            )
        if binding_slug:
            raise HTTPException(
                status_code=422,
                detail=f"Content component '{component_type}' must not have a binding_slug",
            )


# ---------------------------------------------------------------------------
# Rule Summary — human-readable description
# ---------------------------------------------------------------------------

def summarize_rule(rule: Optional[Dict[str, Any]]) -> Optional[str]:
    """Return a human-readable summary of a rule JSON, or None if empty."""
    if not rule:
        return None

    op = rule.get("operator", "equals")

    if op == "all_of":
        subs = [summarize_rule(r) for r in rule.get("rules", [])]
        parts = [s for s in subs if s]
        return " AND ".join(parts) if parts else None

    if op == "any_of":
        subs = [summarize_rule(r) for r in rule.get("rules", [])]
        parts = [s for s in subs if s]
        return " OR ".join(parts) if parts else None

    fld = rule.get("field", "?")
    val = rule.get("value")
    vals = rule.get("values", val)

    if op == "equals":
        return f"{fld} = {val}"
    if op == "not_equals":
        return f"{fld} != {val}"
    if op == "in":
        return f"{fld} in {vals}"
    if op == "not_in":
        return f"{fld} not in {vals}"
    if op == "exists":
        return f"{fld} exists"
    if op == "not_exists":
        return f"{fld} does not exist"

    return f"{fld} {op} {val}"


# ---------------------------------------------------------------------------
# Field Definition Usage
# ---------------------------------------------------------------------------

def get_field_usage(field_id: UUID, db: Session) -> List[dict]:
    """Return a list of components using a given field definition."""
    comps = (
        db.query(RegistrationScreenComponent)
        .options(
            joinedload(RegistrationScreenComponent.screen)
            .joinedload(RegistrationStepScreen.step)
            .joinedload(RegistrationFlowStep.flow),
        )
        .filter(RegistrationScreenComponent.field_definition_id == field_id)
        .all()
    )
    usages = []
    for c in comps:
        flow = c.screen.step.flow if c.screen and c.screen.step else None
        usages.append({
            "component_id": str(c.id),
            "component_type": c.component_type,
            "binding_slug": c.binding_slug,
            "screen_title": c.screen.title if c.screen else None,
            "step_title": c.screen.step.title if c.screen and c.screen.step else None,
            "flow_name": flow.name if flow else None,
            "flow_id": str(flow.id) if flow else None,
            "flow_status": flow.status if flow else None,
        })
    return usages


def get_field_usage_count(db: Session) -> Dict[str, int]:
    """Return a dict of field_definition_id → usage count."""
    from sqlalchemy import func
    rows = (
        db.query(
            RegistrationScreenComponent.field_definition_id,
            func.count(RegistrationScreenComponent.id),
        )
        .filter(RegistrationScreenComponent.field_definition_id.isnot(None))
        .group_by(RegistrationScreenComponent.field_definition_id)
        .all()
    )
    return {str(fid): cnt for fid, cnt in rows}


# ---------------------------------------------------------------------------
# Component Support Registry
# ---------------------------------------------------------------------------

def get_component_support_registry() -> List[dict]:
    """Return a registry of all known component types and their support status."""
    registry = []
    for ct in sorted(ALL_KNOWN_COMPONENT_TYPES):
        registry.append({
            "component_type": ct,
            "family": "field_bound" if ct in INPUT_COMPONENT_TYPES else "content",
            "is_input": ct in INPUT_COMPONENT_TYPES,
            "admin_builder": True,
            "admin_preview": ct != "link_text",
            "flutter": ct in FLUTTER_SUPPORTED_TYPES,
        })
    return registry


def get_content_component_types() -> List[str]:
    """Return sorted list of content component types for UI selection."""
    return sorted(CONTENT_COMPONENT_TYPES)


def get_field_bound_component_types() -> List[str]:
    """Return sorted list of field-bound component types for UI selection."""
    return sorted(INPUT_COMPONENT_TYPES)
