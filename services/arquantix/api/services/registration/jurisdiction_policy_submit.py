"""Submit-time validation against jurisdiction policies (explicit ``policy_scope``).

Phone, residence, and nationality checks are routed by ``resolve_policy_scope`` —
not by binding slug heuristics. Legacy flows must set ``policy_scope`` on components
(see Alembic 103) or on ``field_definitions.policy_scope``.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .execution_events import (
    RegistrationEventSource,
    RegistrationEventStatus,
    RegistrationEventType,
    safe_log_registration_event,
)
from .jurisdiction_policies import (
    is_nationality_country_allowed,
    is_residence_country_allowed,
    jurisdiction_has_nationality_policies,
    jurisdiction_has_phone_policies,
    jurisdiction_has_residence_policies,
)
from .masking import mask_phone
from .phone_validation import (
    phone_validation_debug_dict,
    phone_validation_debug_enabled,
    validate_mobile_phone_for_jurisdiction,
)
from .policy_scope import resolve_policy_scope
from .address_autocomplete import (
    resolved_address_step_binding_slugs,
    resolved_binding_slugs,
)

if TYPE_CHECKING:
    from database import RegistrationSession

logger = logging.getLogger(__name__)


def _emit_phone_validation_audit(
    db: Session,
    session: Optional["RegistrationSession"],
    *,
    jurisdiction_code: str,
    field_slug: str,
    raw_val: str,
    res: Any,
    step_id: Optional[UUID],
    screen_id: Optional[UUID],
) -> None:
    if session is None:
        return
    try:
        ntype_label = None
        if res.number_type is not None:
            import phonenumbers

            try:
                ntype_label = phonenumbers.PhoneNumberType.to_string(res.number_type)
            except Exception:
                ntype_label = str(res.number_type)
        payload = {
            "phone_validation_event": True,
            "field_slug": field_slug,
            "raw_input": mask_phone(raw_val),
            "normalized": mask_phone(res.normalized_e164),
            "region": res.region_code,
            "type": res.number_type,
            "type_label": ntype_label,
            "jurisdiction": jurisdiction_code.strip().upper(),
            "result": "accepted" if res.ok else "rejected",
            "error_code": res.error_code,
            "risk_signal": getattr(res, "risk_signal", None),
        }
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.PHONE_VALIDATED,
            event_source=RegistrationEventSource.RUNTIME,
            event_status=RegistrationEventStatus.SUCCESS
            if res.ok
            else RegistrationEventStatus.FAILURE,
            payload=payload,
            step_id=step_id,
            screen_id=screen_id,
        )
    except Exception:
        logger.warning(
            "phone_validation_audit_failed session_id=%s",
            getattr(session, "id", None),
            exc_info=True,
        )


def _validate_residence_for_address_composite_components(
    db: Session,
    jurisdiction_code: str,
    has_residence_policies: bool,
    components: list,
    answers: Dict[str, Any],
) -> None:
    """Apply residence allowlist to country values bound by address_step / address_autocomplete.

    Component rows use ``policy_scope: none`` for these composites; the country slug lives in
    ``props.binding_slugs`` instead of ``binding_slug``. Without this pass, residence policy
    would never run on submitted country values.
    """
    from .service import ValidationError

    if not has_residence_policies:
        return

    jc = jurisdiction_code.strip().upper()

    for comp in components:
        ct = getattr(comp, "component_type", None) or ""
        pj = getattr(comp, "props_json", None) or {}
        if not isinstance(pj, dict):
            pj = {}

        country_slug: Optional[str] = None
        if ct == "address_step":
            country_slug = resolved_address_step_binding_slugs(pj).get("country_of_residence")
        elif ct == "address_autocomplete":
            country_slug = resolved_binding_slugs(pj).get("country")

        if not country_slug or country_slug not in answers:
            continue

        val = answers[country_slug]
        if val is None or val == "":
            continue

        iso = str(val).strip().upper()
        if len(iso) != 2:
            # Format errors are handled by validate_screen_answers (ISO2); avoid duplicate messages here.
            continue

        if not is_residence_country_allowed(db, jc, iso):
            raise ValidationError(
                f"[RESIDENCE_COUNTRY_NOT_ALLOWED] Country {iso} is not allowed as residence for this jurisdiction."
            )


def validate_jurisdiction_policies_on_submit(
    db: Session,
    jurisdiction_code: str,
    components: list,
    answers: Dict[str, Any],
    *,
    session: Optional["RegistrationSession"] = None,
    step_id: Optional[UUID] = None,
    screen_id: Optional[UUID] = None,
) -> None:
    from .service import ValidationError

    if not jurisdiction_code:
        return
    jc = jurisdiction_code.strip().upper()
    has_phone = jurisdiction_has_phone_policies(db, jc)
    has_res = jurisdiction_has_residence_policies(db, jc)
    has_nat = jurisdiction_has_nationality_policies(db, jc)

    for comp in components:
        slug = comp.binding_slug
        if not slug:
            continue

        scope = resolve_policy_scope(comp)

        if scope == "phone":
            raw_key = f"{slug}_raw"
            raw_val_o = answers.get(raw_key)
            legacy_val_o = answers.get(slug)
            val = None
            if raw_val_o is not None and str(raw_val_o).strip() != "":
                val = str(raw_val_o).strip()
            elif legacy_val_o is not None and str(legacy_val_o).strip() != "":
                val = str(legacy_val_o).strip()
            else:
                continue

            iso2_key = f"{slug}_country_iso2"
            legacy_cc = f"{slug}_country_code"
            raw_sel = answers.get(iso2_key)
            if raw_sel is None:
                raw_sel = answers.get(legacy_cc)
            sel = str(raw_sel or "").strip().upper()
            if len(sel) != 2:
                sel = None

            res = validate_mobile_phone_for_jurisdiction(
                db,
                val,
                jc,
                selected_country_iso2=sel,
                enforce_jurisdiction_allowlist=has_phone,
            )
            _emit_phone_validation_audit(
                db,
                session,
                jurisdiction_code=jc,
                field_slug=slug,
                raw_val=val,
                res=res,
                step_id=step_id,
                screen_id=screen_id,
            )
            if not res.ok:
                dbg = (
                    phone_validation_debug_dict(res)
                    if phone_validation_debug_enabled()
                    else None
                )
                raise ValidationError(
                    res.user_message or "Invalid phone number",
                    code=res.error_code or "invalid_phone_number",
                    field_slug=slug,
                    message_hint=res.message_hint,
                    debug_extra=dbg,
                )
            if res.normalized_e164:
                answers[slug] = res.normalized_e164
            continue

        if scope == "nationality" and slug in answers:
            val = answers[slug]
            if val is None or val == "":
                continue
            iso = str(val).strip().upper()
            if has_nat and not is_nationality_country_allowed(db, jc, iso):
                raise ValidationError(
                    f"[NATIONALITY_COUNTRY_NOT_ALLOWED] Country {iso} is not allowed as nationality for this jurisdiction."
                )
            continue

        if scope == "residence" and slug in answers:
            val = answers[slug]
            if val is None or val == "":
                continue
            iso = str(val).strip().upper()
            if has_res and not is_residence_country_allowed(db, jc, iso):
                raise ValidationError(
                    f"[RESIDENCE_COUNTRY_NOT_ALLOWED] Country {iso} is not allowed as residence for this jurisdiction."
                )

    _validate_residence_for_address_composite_components(
        db, jc, has_res, components, answers,
    )
