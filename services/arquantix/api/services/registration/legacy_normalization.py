"""Legacy registration component normalization — diagnostic, classification, safe auto-fix.

Uses governance.py as single source of truth for component type families.
Only mutates binding_slug and field_definition_id; never deletes rows.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from database import (
    FieldDefinition,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationScreenComponent,
    RegistrationStepScreen,
)

from .governance import (
    ALL_KNOWN_COMPONENT_TYPES,
    CONTENT_COMPONENT_TYPES,
    INPUT_COMPONENT_TYPES,
    check_flow_health,
)

logger = logging.getLogger(__name__)


def normalize_slug(value: Optional[str]) -> str:
    """Normalize for comparison: lowercase, hyphens → underscores, strip."""
    if not value or not str(value).strip():
        return ""
    s = str(value).strip().lower().replace("-", "_")
    return s


def are_field_slugs_equivalent(a: Optional[str], b: Optional[str]) -> bool:
    """True if two slug/binding values refer to the same logical field after normalization."""
    na, nb = normalize_slug(a), normalize_slug(b)
    if not na and not nb:
        return True
    return na == nb


class LegacyCategory(str, Enum):
    OK = "ok"
    AUTO_FIXABLE = "auto_fixable"
    AMBIGUOUS = "ambiguous"


class LegacyAction(str, Enum):
    NONE = "none"
    LINK_FIELD_BY_BINDING = "link_field_by_binding"
    CANONICAL_BINDING_FROM_FD = "canonical_binding_from_fd"
    CLEAR_CONTENT_BINDINGS = "clear_content_bindings"


@dataclass
class ComponentContext:
    component_id: UUID
    screen_id: UUID
    flow_id: Optional[UUID]
    flow_name: Optional[str]
    component_type: str
    binding_slug: Optional[str]
    field_definition_id: Optional[UUID]
    category: LegacyCategory
    action: LegacyAction
    reason_codes: List[str] = dc_field(default_factory=list)
    proposed_binding_slug: Optional[str] = None
    proposed_field_definition_id: Optional[UUID] = None


@dataclass
class NormalizationResult:
    dry_run: bool
    timestamp_utc: str
    totals: Dict[str, int]
    ok: List[Dict[str, Any]]
    auto_fixable: List[Dict[str, Any]]
    ambiguous: List[Dict[str, Any]]
    applied: List[Dict[str, Any]]
    health_before: Dict[str, Any]
    health_after: Optional[Dict[str, Any]]
    errors: List[str]


def load_field_definition_indexes(db: Session) -> Tuple[Dict[str, List[FieldDefinition]], Dict[UUID, FieldDefinition]]:
    fds = db.query(FieldDefinition).all()
    by_norm: Dict[str, List[FieldDefinition]] = {}
    by_id: Dict[UUID, FieldDefinition] = {}
    for f in fds:
        by_id[f.id] = f
        k = normalize_slug(f.slug)
        if k not in by_norm:
            by_norm[k] = []
        by_norm[k].append(f)
    return by_norm, by_id


def _flow_context_for_screen(db: Session, screen_id: UUID) -> Tuple[Optional[UUID], Optional[str]]:
    scr = (
        db.query(RegistrationStepScreen)
        .options(
            joinedload(RegistrationStepScreen.step).joinedload(RegistrationFlowStep.flow),
        )
        .filter(RegistrationStepScreen.id == screen_id)
        .first()
    )
    if not scr or not scr.step:
        return None, None
    fl = scr.step.flow
    if not fl:
        return None, None
    return fl.id, fl.name


def classify_component_legacy_state(
    component_type: str,
    binding_slug: Optional[str],
    field_definition_id: Optional[UUID],
    fd_by_norm: Dict[str, List[FieldDefinition]],
    fds_by_id: Dict[UUID, FieldDefinition],
) -> Tuple[LegacyCategory, LegacyAction, List[str], Optional[str], Optional[UUID]]:
    """Return (category, action, reason_codes, proposed_binding, proposed_fd_id)."""
    reasons: List[str] = []

    if component_type not in ALL_KNOWN_COMPONENT_TYPES:
        return LegacyCategory.AMBIGUOUS, LegacyAction.NONE, ["unknown_component_type"], None, None

    if component_type in CONTENT_COMPONENT_TYPES:
        if binding_slug or field_definition_id:
            return (
                LegacyCategory.AUTO_FIXABLE,
                LegacyAction.CLEAR_CONTENT_BINDINGS,
                ["content_has_binding_or_field_def"],
                None,
                None,
            )
        return LegacyCategory.OK, LegacyAction.NONE, [], None, None

    # Field-bound (INPUT_COMPONENT_TYPES)
    if field_definition_id:
        fd = fds_by_id.get(field_definition_id)
        if not fd:
            return LegacyCategory.AMBIGUOUS, LegacyAction.NONE, ["orphan_field_definition_id"], None, None
        if not are_field_slugs_equivalent(binding_slug, fd.slug):
            return (
                LegacyCategory.AUTO_FIXABLE,
                LegacyAction.CANONICAL_BINDING_FROM_FD,
                ["binding_mismatch_with_linked_field"],
                fd.slug,
                field_definition_id,
            )
        return LegacyCategory.OK, LegacyAction.NONE, [], None, None

    # No field_definition_id
    if not binding_slug or not str(binding_slug).strip():
        return LegacyCategory.AMBIGUOUS, LegacyAction.NONE, ["field_bound_missing_binding_and_fd"], None, None

    matches = fd_by_norm.get(normalize_slug(binding_slug), [])
    if len(matches) == 0:
        return LegacyCategory.AMBIGUOUS, LegacyAction.NONE, ["no_field_definition_for_binding"], None, None
    if len(matches) > 1:
        return (
            LegacyCategory.AMBIGUOUS,
            LegacyAction.NONE,
            ["multiple_field_definitions_for_binding"],
            None,
            None,
        )

    fd = matches[0]
    return (
        LegacyCategory.AUTO_FIXABLE,
        LegacyAction.LINK_FIELD_BY_BINDING,
        ["link_unique_field_by_binding"],
        fd.slug,
        fd.id,
    )


def build_component_context(
    comp: RegistrationScreenComponent,
    db: Session,
    fd_by_norm: Dict[str, List[FieldDefinition]],
    fds_by_id: Dict[UUID, FieldDefinition],
) -> ComponentContext:
    flow_id, flow_name = _flow_context_for_screen(db, comp.screen_id)
    cat, action, reasons, pb, pfd = classify_component_legacy_state(
        comp.component_type,
        comp.binding_slug,
        comp.field_definition_id,
        fd_by_norm,
        fds_by_id,
    )
    return ComponentContext(
        component_id=comp.id,
        screen_id=comp.screen_id,
        flow_id=flow_id,
        flow_name=flow_name,
        component_type=comp.component_type,
        binding_slug=comp.binding_slug,
        field_definition_id=comp.field_definition_id,
        category=cat,
        action=action,
        reason_codes=reasons,
        proposed_binding_slug=pb,
        proposed_field_definition_id=pfd,
    )


def diagnose_registration_components(db: Session) -> NormalizationResult:
    """Full diagnostic: no writes."""
    fd_by_norm, fds_by_id = load_field_definition_indexes(db)
    comps = (
        db.query(RegistrationScreenComponent)
        .order_by(RegistrationScreenComponent.screen_id, RegistrationScreenComponent.position)
        .all()
    )

    ok_l: List[Dict[str, Any]] = []
    auto_l: List[Dict[str, Any]] = []
    amb_l: List[Dict[str, Any]] = []

    for comp in comps:
        ctx = build_component_context(comp, db, fd_by_norm, fds_by_id)
        row = _ctx_to_dict(ctx, comp)
        if ctx.category == LegacyCategory.OK:
            ok_l.append(row)
        elif ctx.category == LegacyCategory.AUTO_FIXABLE:
            auto_l.append(row)
        else:
            amb_l.append(row)

    health_before = _summarize_all_flows_health(db)

    return NormalizationResult(
        dry_run=True,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        totals={
            "components_total": len(comps),
            "ok": len(ok_l),
            "auto_fixable": len(auto_l),
            "ambiguous": len(amb_l),
        },
        ok=ok_l,
        auto_fixable=auto_l,
        ambiguous=amb_l,
        applied=[],
        health_before=health_before,
        health_after=None,
        errors=[],
    )


def _ctx_to_dict(ctx: ComponentContext, comp: RegistrationScreenComponent) -> Dict[str, Any]:
    return {
        "component_id": str(ctx.component_id),
        "screen_id": str(ctx.screen_id),
        "flow_id": str(ctx.flow_id) if ctx.flow_id else None,
        "flow_name": ctx.flow_name,
        "component_type": ctx.component_type,
        "binding_slug": ctx.binding_slug,
        "field_definition_id": str(ctx.field_definition_id) if ctx.field_definition_id else None,
        "category": ctx.category.value,
        "action": ctx.action.value,
        "reason_codes": ctx.reason_codes,
        "proposed_binding_slug": ctx.proposed_binding_slug,
        "proposed_field_definition_id": str(ctx.proposed_field_definition_id)
        if ctx.proposed_field_definition_id
        else None,
        "component_key": comp.component_key,
    }


def _summarize_all_flows_health(db: Session) -> Dict[str, Any]:
    flows = db.query(RegistrationFlow).all()
    publishable = 0
    blocked = 0
    flow_summaries: List[Dict[str, Any]] = []
    for f in flows:
        r = check_flow_health(f.id, db)
        if r.can_publish:
            publishable += 1
        else:
            blocked += 1
        flow_summaries.append({
            "flow_id": str(f.id),
            "flow_name": f.name,
            "status": f.status,
            "can_publish": r.can_publish,
            "error_count": len(r.errors),
            "warning_count": len(r.warnings),
        })
    return {
        "flows_total": len(flows),
        "publishable": publishable,
        "blocked": blocked,
        "flows": flow_summaries,
    }


def apply_auto_fixes(
    db: Session,
    *,
    dry_run: bool = False,
) -> NormalizationResult:
    """Apply only AUTO_FIXABLE patches; rollback all on any error."""
    fd_by_norm, fds_by_id = load_field_definition_indexes(db)
    health_before = _summarize_all_flows_health(db)

    comps = (
        db.query(RegistrationScreenComponent)
        .order_by(RegistrationScreenComponent.id)
        .all()
    )

    ok_l: List[Dict[str, Any]] = []
    auto_l: List[Dict[str, Any]] = []
    amb_l: List[Dict[str, Any]] = []
    applied: List[Dict[str, Any]] = []

    for comp in comps:
        ctx = build_component_context(comp, db, fd_by_norm, fds_by_id)
        row = _ctx_to_dict(ctx, comp)
        if ctx.category == LegacyCategory.OK:
            ok_l.append(row)
        elif ctx.category == LegacyCategory.AUTO_FIXABLE:
            auto_l.append(row)
        else:
            amb_l.append(row)

    if dry_run:
        return NormalizationResult(
            dry_run=True,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            totals={
                "components_total": len(comps),
                "ok": len(ok_l),
                "auto_fixable": len(auto_l),
                "ambiguous": len(amb_l),
            },
            ok=ok_l,
            auto_fixable=auto_l,
            ambiguous=amb_l,
            applied=[],
            health_before=health_before,
            health_after=health_before,
            errors=[],
        )

    errors: List[str] = []
    try:
        for comp in comps:
            ctx = build_component_context(comp, db, fd_by_norm, fds_by_id)
            if ctx.category != LegacyCategory.AUTO_FIXABLE:
                continue

            old_bs = comp.binding_slug
            old_fd = comp.field_definition_id
            action = ctx.action
            ts = datetime.now(timezone.utc).isoformat()

            if action == LegacyAction.CLEAR_CONTENT_BINDINGS:
                comp.binding_slug = None
                comp.field_definition_id = None
                log_entry = {
                    "timestamp": ts,
                    "component_id": str(comp.id),
                    "screen_id": str(comp.screen_id),
                    "flow_id": str(ctx.flow_id) if ctx.flow_id else None,
                    "action": action.value,
                    "old_binding_slug": old_bs,
                    "new_binding_slug": None,
                    "old_field_definition_id": str(old_fd) if old_fd else None,
                    "new_field_definition_id": None,
                }
                applied.append(log_entry)
                logger.info("legacy_normalization %s", log_entry)

            elif action == LegacyAction.CANONICAL_BINDING_FROM_FD:
                fd = fds_by_id.get(old_fd) if old_fd else None
                if not fd:
                    continue
                comp.binding_slug = fd.slug
                log_entry = {
                    "timestamp": ts,
                    "component_id": str(comp.id),
                    "screen_id": str(comp.screen_id),
                    "flow_id": str(ctx.flow_id) if ctx.flow_id else None,
                    "action": action.value,
                    "old_binding_slug": old_bs,
                    "new_binding_slug": fd.slug,
                    "old_field_definition_id": str(old_fd) if old_fd else None,
                    "new_field_definition_id": str(old_fd) if old_fd else None,
                }
                applied.append(log_entry)
                logger.info("legacy_normalization %s", log_entry)

            elif action == LegacyAction.LINK_FIELD_BY_BINDING:
                comp.field_definition_id = ctx.proposed_field_definition_id
                comp.binding_slug = ctx.proposed_binding_slug
                log_entry = {
                    "timestamp": ts,
                    "component_id": str(comp.id),
                    "screen_id": str(comp.screen_id),
                    "flow_id": str(ctx.flow_id) if ctx.flow_id else None,
                    "action": action.value,
                    "old_binding_slug": old_bs,
                    "new_binding_slug": ctx.proposed_binding_slug,
                    "old_field_definition_id": str(old_fd) if old_fd else None,
                    "new_field_definition_id": str(ctx.proposed_field_definition_id)
                    if ctx.proposed_field_definition_id
                    else None,
                }
                applied.append(log_entry)
                logger.info("legacy_normalization %s", log_entry)

        db.commit()
    except Exception as e:
        db.rollback()
        errors.append(str(e))
        logger.exception("legacy_normalization rollback: %s", e)
        return NormalizationResult(
            dry_run=False,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            totals={
                "components_total": len(comps),
                "ok": len(ok_l),
                "auto_fixable": len(auto_l),
                "ambiguous": len(amb_l),
            },
            ok=ok_l,
            auto_fixable=auto_l,
            ambiguous=amb_l,
            applied=[],
            health_before=health_before,
            health_after=None,
            errors=errors,
        )

    # Refresh index if needed for health
    health_after = _summarize_all_flows_health(db)

    return NormalizationResult(
        dry_run=False,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        totals={
            "components_total": len(comps),
            "ok": len(ok_l),
            "auto_fixable": len(auto_l),
            "ambiguous": len(amb_l),
            "applied_count": len(applied),
        },
        ok=ok_l,
        auto_fixable=auto_l,
        ambiguous=amb_l,
        applied=applied,
        health_before=health_before,
        health_after=health_after,
        errors=[],
    )


def result_to_dict(r: NormalizationResult) -> Dict[str, Any]:
    return {
        "dry_run": r.dry_run,
        "timestamp_utc": r.timestamp_utc,
        "totals": r.totals,
        "ok": r.ok,
        "auto_fixable": r.auto_fixable,
        "ambiguous": r.ambiguous,
        "applied": r.applied,
        "health_before": r.health_before,
        "health_after": r.health_after,
        "errors": r.errors,
    }
