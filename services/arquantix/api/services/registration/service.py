"""Registration Flow Engine — Service Layer (Phase 2A + 2B Hardening).

Two stateless service classes:
  - RegistrationFlowService   : flow resolution, serialisation
  - RegistrationSessionService: session lifecycle, navigation, projection

Phase 2B hardening:
  1. Data layering — projection writes to profile_json["collected"] after each successful
     screen submit (and after SMS interaction complete), not only on session completion.
  2. Flow version locking — session pins flow_version at start
  3. Session step state tracking — per-step status via registration_session_steps
  4. Navigation hardening — next requires completed blocking steps
  5. Blocking vs non-blocking steps — is_blocking respected in navigation
"""
from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.orm.attributes import flag_modified

from database import (
    AuditEvent,
    Person,
    RegistrationJurisdiction,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationStepScreen,
    RegistrationScreenComponent,
    RegistrationSession,
    RegistrationSessionData,
    RegistrationSessionStep,
    TwoFactorChallenge,
)
from auth import create_registration_otp_token
from services.security.two_factor_env import (
    is_two_factor_relaxed,
    two_factor_dev_code_for_api_exposure,
)
from services.security.two_factor_rate_limits import RESEND_SECONDS
from services.security.two_factor_service import (
    TwoFactorException,
    TwoFactorRequestContext,
    get_two_factor_service,
    latest_sms_challenge_for_target,
    supersede_pending_sms_challenges_for_target,
)
from services.security.masking import mask_phone_e164
from .i18n import resolve_localized, resolve_localized_props
from .interaction_helpers import (
    INTERACTION_PHONE_SMS,
    build_phone_sms_read_payload,
    default_phone_region_from_session,
    effective_screen_type,
    ensure_session_person,
    find_reusable_sms_challenge,
    parse_phone_verification_config,
    session_slug_to_compliance,
    validate_phone_verification_prerequisites,
)
from .address_autocomplete import (
    REG_ADDRESS_OVERRIDE_KEY,
    REG_ADDRESS_SOURCES_KEY,
    clamp_address_metadata_value,
    metadata_slug_from_props,
    normalize_sources_map,
    resolved_address_step_binding_slugs,
    resolved_binding_slugs,
    VALID_ADDRESS_SOURCES,
)
from services.address.observability import registration_address_submit_payload
from .permission_prompt import parse_permission_prompt_config
from .rules import evaluate_rule, filter_visible_items
from .validators import validate_screen_answers
from .jurisdiction_policies import enrich_registration_component_props
from .jurisdiction_policy_submit import validate_jurisdiction_policies_on_submit
from .execution_events import (
    safe_log_registration_event,
    RegistrationEventType,
    RegistrationEventStatus,
)
from .masking import mask_answers_for_audit
from .rule_audit import build_visibility_evaluation_batch
from services.registration_progress_derived import (
    CANONICAL_KEY_TO_SCREEN_KEY,
    compute_next_registration_step_from_collected,
    compute_registration_progress_from_collected,
)

logger = logging.getLogger(__name__)

# Session-only: not exposed in collected_data, not projected to person profile.
_REG_INTERNAL_SMS_LAST_RESEND_AT = "__reg_internal_sms_last_resend_at"


def _public_registration_context(context: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in context.items() if not str(k).startswith("__reg_internal_")}


def _parse_iso_utc_maybe(raw: Any) -> Optional[datetime]:
    if raw is None or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RegistrationError(Exception):
    pass

class FlowNotFoundError(RegistrationError):
    pass

class SessionNotFoundError(RegistrationError):
    pass

class SessionCompletedError(RegistrationError):
    pass


class RegistrationAlreadyCompletedError(RegistrationError):
    """``start_session`` alors qu'une session ``completed`` existe déjà pour cette personne."""

    def __init__(
        self,
        message: str = "L'inscription est déjà terminée pour ce compte.",
    ) -> None:
        super().__init__(message)


class NoNextScreenError(RegistrationError):
    pass

class NoPreviousScreenError(RegistrationError):
    pass

class JurisdictionNotFoundError(RegistrationError):
    pass

class ValidationError(RegistrationError):
    """422 validation; optional ``code`` / ``field_slug`` for structured API + Flutter."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        field_slug: Optional[str] = None,
        message_hint: Optional[str] = None,
        debug_extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.field_slug = field_slug
        self.message_hint = message_hint
        self.debug_extra = debug_extra


def _require_phone_verification_prerequisites(
    screen: RegistrationStepScreen,
    context: Dict[str, Any],
    *,
    default_region: Optional[str] = None,
) -> Tuple[str, str, str]:
    return validate_phone_verification_prerequisites(
        screen,
        context,
        default_region=default_region,
    )


class StepBlockedError(RegistrationError):
    """Raised when navigation is blocked by an incomplete blocking step."""
    pass


# ---------------------------------------------------------------------------
# Profile helpers
# ---------------------------------------------------------------------------

def get_person_collected_value(person: Person, slug: str, default: Any = None) -> Any:
    """Read a collected registration value from the layered profile_json.

    Looks in profile_json["collected"][slug] first, then falls back to
    profile_json[slug] for backward compatibility with pre-layered data.
    """
    pj = person.profile_json or {}
    collected = pj.get("collected")
    if isinstance(collected, dict) and slug in collected:
        return collected[slug]
    return pj.get(slug, default)


# ---------------------------------------------------------------------------
# Flow Service
# ---------------------------------------------------------------------------

class RegistrationFlowService:
    """Read-only operations on flows, steps, screens, components."""

    @staticmethod
    def get_active_flow(
        db: Session,
        jurisdiction_code: str,
        entrypoint_type: str = "individual",
    ) -> RegistrationFlow:
        """Return the single active flow for a jurisdiction + entrypoint."""
        flow = (
            db.query(RegistrationFlow)
            .join(RegistrationJurisdiction)
            .filter(
                RegistrationJurisdiction.code == jurisdiction_code.upper(),
                RegistrationJurisdiction.is_active == True,
                RegistrationFlow.entrypoint_type == entrypoint_type,
                RegistrationFlow.status == "active",
            )
            .options(
                joinedload(RegistrationFlow.steps)
                .joinedload(RegistrationFlowStep.screens)
                .joinedload(RegistrationStepScreen.components),
                joinedload(RegistrationFlow.jurisdiction),
            )
            .first()
        )
        if flow is None:
            raise FlowNotFoundError(
                f"No active flow for jurisdiction={jurisdiction_code}, entrypoint={entrypoint_type}"
            )
        return flow

    @staticmethod
    def get_flow_by_id(db: Session, flow_id: UUID) -> RegistrationFlow:
        """Load a specific flow by ID with full tree (version-locked lookup)."""
        flow = (
            db.query(RegistrationFlow)
            .options(
                joinedload(RegistrationFlow.steps)
                .joinedload(RegistrationFlowStep.screens)
                .joinedload(RegistrationStepScreen.components),
                joinedload(RegistrationFlow.jurisdiction),
            )
            .filter(RegistrationFlow.id == flow_id)
            .first()
        )
        if flow is None:
            raise FlowNotFoundError(f"Flow {flow_id} not found")
        return flow

    @staticmethod
    def serialize_flow(
        flow: RegistrationFlow,
        context: Optional[Dict[str, Any]] = None,
        lang: Optional[str] = None,
    ) -> dict:
        """Serialize a flow to JSON-friendly dict, applying visibility rules.

        If *lang* is provided, title/subtitle/props are resolved to that language
        with fallback to the jurisdiction default_language then "en".
        """
        ctx = context or {}
        default_lang = "en"
        if flow.jurisdiction:
            default_lang = flow.jurisdiction.default_language or "en"
        effective_lang = lang or default_lang
        visible_steps = filter_visible_items(flow.steps, ctx)

        return {
            "id": str(flow.id),
            "name": flow.name,
            "version": flow.version,
            "status": flow.status,
            "entrypoint_type": flow.entrypoint_type,
            "jurisdiction": {
                "code": flow.jurisdiction.code,
                "name": flow.jurisdiction.name,
                "entity_name": flow.jurisdiction.entity_name,
            },
            "steps": [
                RegistrationFlowService._serialize_step(step, ctx, effective_lang, default_lang)
                for step in visible_steps
            ],
        }

    @staticmethod
    def _serialize_step(
        step: RegistrationFlowStep,
        context: Dict[str, Any],
        lang: str = "en",
        default_lang: str = "en",
    ) -> dict:
        visible_screens = filter_visible_items(step.screens, context)
        title = resolve_localized(step.title_i18n, lang, default_lang) if step.title_i18n else step.title
        description = resolve_localized(step.description_i18n, lang, default_lang) if step.description_i18n else step.description
        return {
            "id": str(step.id),
            "step_key": step.step_key,
            "title": title,
            "description": description,
            "position": step.position,
            "is_optional": step.is_optional,
            "is_blocking": step.is_blocking,
            "screens": [
                RegistrationFlowService._serialize_screen(screen, context, lang, default_lang)
                for screen in visible_screens
            ],
        }

    @staticmethod
    def _serialize_screen(
        screen: RegistrationStepScreen,
        context: Dict[str, Any],
        lang: str = "en",
        default_lang: str = "en",
    ) -> dict:
        visible_components = filter_visible_items(screen.components, context)
        title = resolve_localized(screen.title_i18n, lang, default_lang) if screen.title_i18n else screen.title
        subtitle = resolve_localized(screen.subtitle_i18n, lang, default_lang) if screen.subtitle_i18n else screen.subtitle
        button_label = resolve_localized(screen.button_label_i18n, lang, default_lang) if screen.button_label_i18n else screen.button_label
        st = effective_screen_type(screen)
        out = {
            "id": str(screen.id),
            "screen_key": screen.screen_key,
            "title": title,
            "subtitle": subtitle,
            "button_label": button_label,
            "position": screen.position,
            "layout_type": screen.layout_type,
            "screen_type": st,
            "config": screen.config_json,
            "components": [
                RegistrationFlowService._serialize_component(c, lang, default_lang)
                for c in visible_components
            ],
        }
        if st == "interaction":
            out["interaction_type"] = screen.interaction_type
            out["interaction_config"] = screen.interaction_config_json
        if st == "permission_prompt":
            out["permission_kind"] = (screen.config_json or {}).get("permission_kind")
        return out

    @staticmethod
    def _serialize_component(
        comp: RegistrationScreenComponent,
        lang: str = "en",
        default_lang: str = "en",
    ) -> dict:
        raw_props = comp.props_json or {}
        resolved_props = resolve_localized_props(raw_props, lang, default_lang)
        return {
            "id": str(comp.id),
            "component_type": comp.component_type,
            "component_key": comp.component_key,
            "position": comp.position,
            "props": resolved_props,
            "binding_slug": comp.binding_slug,
            "validation": comp.validation_rule_json,
        }


# ---------------------------------------------------------------------------
# Session Service
# ---------------------------------------------------------------------------

class RegistrationSessionService:
    """Manages session lifecycle: start, navigate, submit, complete."""

    _flow_svc = RegistrationFlowService()

    def _emit_rule_evaluation_batch(
        self,
        db: Session,
        session: RegistrationSession,
        context: Dict[str, Any],
        batch_source: str,
    ) -> None:
        try:
            try:
                flow = self._flow_svc.get_flow_by_id(db, session.flow_id)
            except FlowNotFoundError:
                return
            evaluations = build_visibility_evaluation_batch(flow, context, batch_source=batch_source)
            if not evaluations:
                return
            safe_log_registration_event(
                db,
                session,
                event_type=RegistrationEventType.RULE_EVALUATED,
                event_status=RegistrationEventStatus.INFO,
                payload={
                    "batch_source": batch_source,
                    "count": len(evaluations),
                    "evaluations": evaluations,
                },
            )
        except Exception:
            logger.warning(
                "registration_rule_audit_batch_failed session_id=%s source=%s",
                session.id,
                batch_source,
                exc_info=True,
            )

    def _labels_for_step_screen(
        self,
        session: RegistrationSession,
        step: Optional[RegistrationFlowStep],
        screen: Optional[RegistrationStepScreen],
    ) -> Dict[str, Optional[str]]:
        default_lang = "en"
        if session.jurisdiction:
            default_lang = session.jurisdiction.default_language or "en"
        lang = default_lang
        out: Dict[str, Optional[str]] = {
            "step_key": step.step_key if step else None,
            "step_title": None,
            "screen_key": screen.screen_key if screen else None,
            "screen_title": None,
        }
        if step:
            out["step_title"] = (
                resolve_localized(step.title_i18n, lang, default_lang) if step.title_i18n else step.title
            )
        if screen:
            out["screen_title"] = (
                resolve_localized(screen.title_i18n, lang, default_lang) if screen.title_i18n else screen.title
            )
        return out

    def _resolve_screen_for_canonical_key(
        self,
        db: Session,
        flow_id: UUID,
        canonical_key: str,
    ) -> Optional[Tuple[UUID, UUID]]:
        """Retourne ``(step_id, screen_id)`` pour un jalon canonique (v4 via screen_key, v3 via step_key)."""
        screen_key = CANONICAL_KEY_TO_SCREEN_KEY.get(canonical_key)
        if screen_key:
            row = (
                db.query(RegistrationStepScreen, RegistrationFlowStep)
                .join(RegistrationFlowStep, RegistrationStepScreen.step_id == RegistrationFlowStep.id)
                .filter(
                    RegistrationFlowStep.flow_id == flow_id,
                    RegistrationStepScreen.screen_key == screen_key,
                )
                .first()
            )
            if row:
                screen, step = row
                return (step.id, screen.id)
        row = (
            db.query(RegistrationStepScreen, RegistrationFlowStep)
            .join(RegistrationFlowStep, RegistrationStepScreen.step_id == RegistrationFlowStep.id)
            .filter(
                RegistrationFlowStep.flow_id == flow_id,
                RegistrationFlowStep.step_key == canonical_key,
            )
            .order_by(RegistrationStepScreen.position)
            .first()
        )
        if row:
            screen, step = row
            return (step.id, screen.id)
        return None

    def _realign_session_cursor_from_collected(self, db: Session, session: RegistrationSession) -> None:
        """Recale le curseur sur le step courant à finaliser et le 1er écran incomplet dans ce step.

        Les steps déjà validés ne sont pas revisités : on reste dans le step indiqué par le prochain
        jalon canonique incomplet, avec un curseur d'écran cohérent avec les données collectées.
        """
        if session.person_id is None:
            return
        person = db.query(Person).filter(Person.id == session.person_id).first()
        if person is None:
            return
        pj = person.profile_json or {}
        collected = pj.get("collected")
        if not isinstance(collected, dict):
            collected = {}
        nxt = compute_next_registration_step_from_collected(collected)
        _ratio, pct, _done, _total = compute_registration_progress_from_collected(collected)
        if nxt is None:
            if session.progress_percent != pct:
                session.progress_percent = pct
                db.flush()
            db.expire(session)
            return
        canonical_key, _label = nxt
        target = self._resolve_screen_for_canonical_key(db, session.flow_id, canonical_key)
        if target is None:
            logger.warning(
                "registration_realign: no screen for canonical_key=%s flow_id=%s",
                canonical_key,
                session.flow_id,
            )
            if session.progress_percent != pct:
                session.progress_percent = pct
                db.flush()
            db.expire(session)
            return
        step_id, screen_id = target
        step = (
            db.query(RegistrationFlowStep)
            .filter(RegistrationFlowStep.id == step_id)
            .first()
        )
        if step is None:
            if session.progress_percent != pct:
                session.progress_percent = pct
                db.flush()
            db.expire(session)
            return

        ctx_session = self._get_session_context(db, session.id)
        merged_context = {**collected, **ctx_session}

        resume_screen = self._first_incomplete_visible_screen_in_step(step, merged_context)
        resume_screen_id = resume_screen.id if resume_screen is not None else screen_id

        if session.current_step_id == step_id and session.current_screen_id == resume_screen_id:
            if session.progress_percent != pct:
                session.progress_percent = pct
                db.flush()
            db.expire(session)
            return

        session.current_step_id = step_id
        session.current_screen_id = resume_screen_id

        flow = self._flow_svc.get_flow_by_id(db, session.flow_id)
        flat_screens = self._flatten_visible_screens(flow, merged_context)
        idx = self._find_screen_index(flat_screens, resume_screen_id)
        if idx is not None and flat_screens:
            session.progress_percent = self._compute_progress(idx, len(flat_screens))
        else:
            session.progress_percent = pct
        db.flush()
        db.expire(session)

    def _screen_entered_event_payload(
        self,
        session: RegistrationSession,
        step: Optional[RegistrationFlowStep],
        screen: Optional[RegistrationStepScreen],
    ) -> Dict[str, Any]:
        labels = self._labels_for_step_screen(session, step, screen)
        if screen:
            st = effective_screen_type(screen)
            labels["screen_type"] = st
            if st == "interaction":
                labels["interaction_type"] = screen.interaction_type
        return labels

    # ── Start ──────────────────────────────────────────────────────

    def start_session(
        self,
        db: Session,
        jurisdiction_code: str,
        entrypoint_type: str = "individual",
        person_id: Optional[UUID] = None,
    ) -> dict:
        """Create a new session and return the first screen, or resume an existing one.

        Si ``person_id`` est fourni et qu'une session ``in_progress`` existe déjà pour
        cette personne et cette juridiction, renvoie l'écran courant de cette session.

        Sinon, crée une session et épingle ``flow_version`` (immunisé aux publishes ultérieurs).
        """
        flow = self._flow_svc.get_active_flow(db, jurisdiction_code, entrypoint_type)
        jurisdiction = flow.jurisdiction

        # Reprise : une session ``in_progress`` pour la même personne + juridiction évite
        # de repartir de zéro (données déjà dans registration_session_data + profile_json).
        if person_id is not None:
            existing = (
                db.query(RegistrationSession)
                .filter(
                    RegistrationSession.person_id == person_id,
                    RegistrationSession.status == "in_progress",
                    RegistrationSession.jurisdiction_id == jurisdiction.id,
                )
                .order_by(RegistrationSession.updated_at.desc())
                .first()
            )
            if existing is not None:
                self._realign_session_cursor_from_collected(db, existing)
                return self._build_screen_response(db, existing)

            # Pas de nouvelle session si l'inscription est déjà finalisée (même personne,
            # même juridiction, même type d'entrée) — évite de repasser tout le flux.
            completed_exists = (
                db.query(RegistrationSession)
                .join(RegistrationFlow, RegistrationSession.flow_id == RegistrationFlow.id)
                .filter(
                    RegistrationSession.person_id == person_id,
                    RegistrationSession.status == "completed",
                    RegistrationSession.jurisdiction_id == jurisdiction.id,
                    RegistrationFlow.entrypoint_type == entrypoint_type,
                )
                .first()
            )
            if completed_exists is not None:
                raise RegistrationAlreadyCompletedError()

        visible_steps = filter_visible_items(flow.steps, {})
        if not visible_steps:
            raise RegistrationError("Flow has no visible steps")

        first_step = visible_steps[0]
        visible_screens = filter_visible_items(first_step.screens, {})
        first_screen = visible_screens[0] if visible_screens else None

        session = RegistrationSession(
            id=uuid_mod.uuid4(),
            jurisdiction_id=jurisdiction.id,
            flow_id=flow.id,
            flow_version=flow.version,
            person_id=person_id,
            status="in_progress",
            current_step_id=first_step.id,
            current_screen_id=first_screen.id if first_screen else None,
            progress_percent=0,
        )
        db.add(session)
        db.flush()

        self._ensure_step_state(db, session, first_step, "in_progress")

        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.FLOW_VERSION_LOCKED,
            event_status=RegistrationEventStatus.SUCCESS,
            payload={
                "flow_id": str(flow.id),
                "flow_version": flow.version,
                "flow_name": flow.name,
                "jurisdiction": jurisdiction.code,
            },
        )
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.SESSION_STARTED,
            event_status=RegistrationEventStatus.SUCCESS,
            payload={
                "jurisdiction": jurisdiction.code,
                "entrypoint_type": entrypoint_type,
                "flow_name": flow.name,
                "flow_version": flow.version,
            },
        )
        if first_screen:
            safe_log_registration_event(
                db,
                session,
                event_type=RegistrationEventType.SCREEN_ENTERED,
                event_status=RegistrationEventStatus.SUCCESS,
                step_id=first_step.id,
                screen_id=first_screen.id,
                payload=self._screen_entered_event_payload(session, first_step, first_screen),
            )

        self._emit_rule_evaluation_batch(
            db, session, self._get_session_context(db, session.id), "session_start",
        )

        self._log_audit(db, session, "REGISTRATION_SESSION_STARTED")

        if person_id is not None:
            self._realign_session_cursor_from_collected(db, session)

        return self._build_screen_response(db, session)

    # ── Get current screen ─────────────────────────────────────────

    def get_current_screen(self, db: Session, session_id: UUID) -> dict:
        """Return the current screen for a session."""
        session = self._get_session(db, session_id)
        self._realign_session_cursor_from_collected(db, session)
        return self._build_screen_response(db, session)

    # ── Submit answers ─────────────────────────────────────────────

    def submit_screen(
        self,
        db: Session,
        session_id: UUID,
        answers: Dict[str, Any],
    ) -> dict:
        """Save answers for current screen, validate required fields, then advance."""
        session = self._get_session(db, session_id)
        if session.status == "completed":
            raise SessionCompletedError("Session already completed")

        if session.current_screen and effective_screen_type(session.current_screen) == "interaction":
            raise ValidationError(
                "This screen is an interaction step (e.g. SMS verification). "
                "Use POST .../interaction/prepare and .../interaction/complete instead of submit."
            )

        context = self._get_session_context(db, session.id)
        visible_components: List = []
        if session.current_screen:
            visible_components = filter_visible_items(session.current_screen.components, context)

        work = dict(answers)
        had_override = bool(work.get(REG_ADDRESS_OVERRIDE_KEY))
        trace_map = normalize_sources_map(work.pop(REG_ADDRESS_SOURCES_KEY, None))
        work.pop(REG_ADDRESS_OVERRIDE_KEY, None)

        metadata_slugs: set[str] = set()
        if session.current_screen:
            vis = filter_visible_items(session.current_screen.components, context)
            for comp in vis:
                if comp.component_type in ("address_autocomplete", "address_step"):
                    ms = metadata_slug_from_props(comp.props_json)
                    if ms:
                        metadata_slugs.add(ms)

        if session.current_screen:
            self._validate_required_fields(db, session, session.current_screen, work, context)

        jcode = session.jurisdiction.code if session.jurisdiction else ""
        validate_jurisdiction_policies_on_submit(
            db,
            jcode,
            visible_components,
            work,
            session=session,
            step_id=session.current_step_id,
            screen_id=session.current_screen_id,
        )

        for slug, value in work.items():
            if slug in metadata_slugs:
                value = clamp_address_metadata_value(value)
            src = trace_map.get(slug) if trace_map else None
            if not src or src not in VALID_ADDRESS_SOURCES:
                src = "user_input"
            existing = (
                db.query(RegistrationSessionData)
                .filter(
                    RegistrationSessionData.session_id == session.id,
                    RegistrationSessionData.field_slug == slug,
                )
                .first()
            )
            if existing:
                existing.value_json = value
                existing.source = src
                existing.updated_at = datetime.now(timezone.utc)
            else:
                db.add(RegistrationSessionData(
                    id=uuid_mod.uuid4(),
                    session_id=session.id,
                    field_slug=slug,
                    value_json=value,
                    source=src,
                ))
        db.flush()

        screen_key = session.current_screen.screen_key if session.current_screen else None
        masked = mask_answers_for_audit(work)
        fields_payload: Dict[str, Any] = {
            "field_slugs": list(work.keys()),
            "masked_values": masked,
            "screen_key": screen_key,
        }
        if trace_map or had_override:
            fields_payload.update(registration_address_submit_payload(trace_map, had_override))
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.FIELDS_SUBMITTED,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=session.current_step_id,
            screen_id=session.current_screen_id,
            payload=fields_payload,
        )
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.SCREEN_SUBMITTED,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=session.current_step_id,
            screen_id=session.current_screen_id,
            payload={
                "screen_key": screen_key,
                "field_slugs_count": len(work),
            },
        )

        self._log_audit(db, session, "REGISTRATION_SCREEN_SUBMITTED", {
            "screen_id": str(session.current_screen_id),
            "fields": list(work.keys()),
        })

        if session.current_screen:
            post_context = self._get_session_context(db, session.id)
            visible_components = filter_visible_items(
                session.current_screen.components, post_context,
            )
            validation_errors = validate_screen_answers(visible_components, work)
            if validation_errors:
                safe_log_registration_event(
                    db,
                    session,
                    event_type=RegistrationEventType.VALIDATION_FAILED,
                    event_status=RegistrationEventStatus.FAILURE,
                    step_id=session.current_step_id,
                    screen_id=session.current_screen_id,
                    payload={
                        "screen_key": screen_key,
                        "reason": "field_format_or_constraint",
                        "errors": [{"slug": e.slug, "message": e.message} for e in validation_errors],
                    },
                )
                raise ValidationError(
                    "Validation failed: "
                    + "; ".join(f"{e.slug}: {e.message}" for e in validation_errors)
                )

            self._emit_rule_evaluation_batch(db, session, post_context, "after_submit")

        # Projection incrémentale : chaque « Continuer » valide persiste dans
        # ``persons.profile_json`` (collected / compliance), pas seulement à la fin du parcours.
        self._project_to_person(db, session)

        try:
            return self.next_screen(db, session_id)
        except NoNextScreenError:
            return self._build_screen_response(db, session, is_last=True)

    # ── Navigation ─────────────────────────────────────────────────

    def next_screen(self, db: Session, session_id: UUID) -> dict:
        """Advance to the next visible screen, respecting blocking steps."""
        session = self._get_session(db, session_id)
        if session.status == "completed":
            raise SessionCompletedError("Session already completed")

        context = self._get_session_context(db, session.id)
        if session.current_screen:
            self._ensure_interaction_advance_allowed(db, session, session.current_screen, context)

        flow = self._flow_svc.get_flow_by_id(db, session.flow_id)

        flat_screens = self._flatten_visible_screens(flow, context)
        current_idx = self._find_screen_index(flat_screens, session.current_screen_id)

        if current_idx is None or current_idx >= len(flat_screens) - 1:
            raise NoNextScreenError("Already at last screen")

        current_screen = flat_screens[current_idx]
        next_screen = flat_screens[current_idx + 1]
        from_screen_id = session.current_screen_id
        from_step_id = session.current_step_id
        current_step = current_screen.step
        next_step = next_screen.step

        if next_step.id != current_step.id:
            self._enforce_blocking_gate(db, session, current_step, flow, context)
            self._mark_step_completed(db, session, current_step)

        self._ensure_step_state(db, session, next_step, "in_progress")

        session.current_screen_id = next_screen.id
        session.current_step_id = next_step.id
        session.progress_percent = self._compute_progress(current_idx + 1, len(flat_screens))
        db.flush()
        db.expire(session)

        from_labels = self._labels_for_step_screen(session, current_step, current_screen)
        to_labels = self._labels_for_step_screen(session, next_step, next_screen)
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.NAVIGATION_NEXT,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=next_step.id,
            screen_id=next_screen.id,
            payload={
                "from_screen_id": str(from_screen_id) if from_screen_id else None,
                "to_screen_id": str(next_screen.id),
                "from_step_id": str(from_step_id) if from_step_id else None,
                "to_step_id": str(next_step.id),
                "from_screen_key": from_labels.get("screen_key"),
                "to_screen_key": to_labels.get("screen_key"),
                "from_step_key": from_labels.get("step_key"),
                "to_step_key": to_labels.get("step_key"),
                "via": "next",
            },
        )
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.SCREEN_ENTERED,
            event_status=RegistrationEventStatus.INFO,
            step_id=next_step.id,
            screen_id=next_screen.id,
            payload={**self._screen_entered_event_payload(session, next_step, next_screen), "via": "next"},
        )

        return self._build_screen_response(db, session)

    def prev_screen(self, db: Session, session_id: UUID) -> dict:
        """Go back to the previous visible screen (bounded by session flow)."""
        session = self._get_session(db, session_id)
        context = self._get_session_context(db, session.id)
        flow = self._flow_svc.get_flow_by_id(db, session.flow_id)

        flat_screens = self._flatten_visible_screens(flow, context)
        current_idx = self._find_screen_index(flat_screens, session.current_screen_id)

        if current_idx is None or current_idx <= 0:
            raise NoPreviousScreenError("Already at first screen")

        prev_screen = flat_screens[current_idx - 1]
        from_screen_id = session.current_screen_id
        from_step_id = session.current_step_id
        cur = flat_screens[current_idx]

        # Un step validé est « bouclé » : pas de retour vers les écrans des steps précédents.
        if prev_screen.step.id != cur.step.id:
            raise NoPreviousScreenError("Already at first screen of step")

        session.current_screen_id = prev_screen.id
        session.current_step_id = prev_screen.step.id
        session.progress_percent = self._compute_progress(current_idx - 1, len(flat_screens))
        db.flush()
        db.expire(session)

        from_labels = self._labels_for_step_screen(session, cur.step, cur)
        to_labels = self._labels_for_step_screen(session, prev_screen.step, prev_screen)
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.NAVIGATION_PREV,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=prev_screen.step.id,
            screen_id=prev_screen.id,
            payload={
                "from_screen_id": str(from_screen_id) if from_screen_id else None,
                "to_screen_id": str(prev_screen.id),
                "from_step_id": str(from_step_id) if from_step_id else None,
                "to_step_id": str(prev_screen.step.id),
                "from_screen_key": from_labels.get("screen_key"),
                "to_screen_key": to_labels.get("screen_key"),
                "via": "prev",
            },
        )
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.SCREEN_ENTERED,
            event_status=RegistrationEventStatus.INFO,
            step_id=prev_screen.step.id,
            screen_id=prev_screen.id,
            payload={**self._screen_entered_event_payload(session, prev_screen.step, prev_screen), "via": "prev"},
        )

        return self._build_screen_response(db, session)

    # ── Interaction screens (SMS phone verification) ──────────────

    def prepare_interaction(
        self,
        db: Session,
        session_id: UUID,
        *,
        app_testing: bool = False,
        client_ip: Optional[str] = None,
    ) -> dict:
        """Create or reuse an SMS challenge and return a short-lived JWT for /api/2fa/verify."""
        session = self._get_session(db, session_id)
        if session.status == "completed":
            raise SessionCompletedError("Session already completed")
        screen = session.current_screen
        if screen is None or effective_screen_type(screen) != "interaction":
            raise RegistrationError("Current screen is not an interaction screen")
        if screen.interaction_type != INTERACTION_PHONE_SMS:
            raise RegistrationError("Unsupported interaction_type for prepare")

        context = self._get_session_context(db, session.id)
        phone, purpose, vflag = _require_phone_verification_prerequisites(
            screen,
            context,
            default_region=default_phone_region_from_session(session),
        )
        person = ensure_session_person(db, session)
        relaxed = is_two_factor_relaxed(app_testing=app_testing)
        svc = get_two_factor_service()
        tf_ctx = TwoFactorRequestContext(relaxed=relaxed, client_ip=client_ip)
        reused = False
        existing = find_reusable_sms_challenge(
            db, person_id=person.id, purpose=purpose, target_e164=phone,
        )
        if existing:
            ch = existing
            masked = mask_phone_e164(ch.target)
            reused = True
        else:
            try:
                ch, meta = svc.create_challenge(
                    db, person.id, "sms", purpose, phone, tf_ctx,
                )
                svc.send_code(db, ch, meta)
            except TwoFactorException as exc:
                raise ValidationError(exc.message) from exc
            masked = meta.get("masked_target")
            self._delete_session_field(db, session, _REG_INTERNAL_SMS_LAST_RESEND_AT)
        token = create_registration_otp_token(person.id)
        cfg = parse_phone_verification_config(screen)
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.INTERACTION_PREPARED,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=session.current_step_id,
            screen_id=screen.id,
            payload={
                "interaction_type": INTERACTION_PHONE_SMS,
                "challenge_id": str(ch.id),
                "reused": reused,
                "sent": not reused,
                "purpose": purpose,
                "screen_key": screen.screen_key,
            },
        )
        out = {
            "otp_token": token,
            "challenge_id": str(ch.id),
            "target_masked": masked,
            "purpose": purpose,
            "source_field_slug": cfg["source_field_slug"],
            "verified_flag_slug": vflag,
            "reused": reused,
            "sent": not reused,
            "resend_after_seconds": RESEND_SECONDS,
        }
        dev_code = two_factor_dev_code_for_api_exposure()
        if dev_code:
            out["dev_code"] = dev_code
        return out

    def resend_interaction(
        self,
        db: Session,
        session_id: UUID,
        *,
        screen_id: UUID,
        interaction_type: str,
        app_testing: bool = False,
        client_ip: Optional[str] = None,
    ) -> dict:
        """Explicit SMS resend: supersede pending OTPs, create a new challenge, send SMS."""
        session = self._get_session(db, session_id)
        if session.status == "completed":
            raise SessionCompletedError("Session already completed")
        if session.current_screen_id != screen_id:
            raise ValidationError("screen_id does not match the current registration screen")
        screen = session.current_screen
        if screen is None or effective_screen_type(screen) != "interaction":
            raise RegistrationError("Current screen is not an interaction screen")
        if screen.interaction_type != interaction_type:
            raise ValidationError("interaction_type does not match the current screen")
        if interaction_type != INTERACTION_PHONE_SMS:
            raise RegistrationError("Unsupported interaction_type for resend")

        context = self._get_session_context(db, session.id)
        phone, purpose, vflag = _require_phone_verification_prerequisites(
            screen,
            context,
            default_region=default_phone_region_from_session(session),
        )
        last_dt = _parse_iso_utc_maybe(context.get(_REG_INTERNAL_SMS_LAST_RESEND_AT))
        if last_dt is not None:
            now = datetime.now(timezone.utc)
            if (now - last_dt).total_seconds() < RESEND_SECONDS:
                raise ValidationError(
                    f"Wait {RESEND_SECONDS}s before requesting a new code",
                )
        person = ensure_session_person(db, session)

        latest = latest_sms_challenge_for_target(
            db, person_id=person.id, purpose=purpose, target_e164=phone,
        )
        if latest is not None and latest.status == "verified":
            raise ValidationError(
                "This phone number was already verified; continue registration instead of resending."
            )

        relaxed = is_two_factor_relaxed(app_testing=app_testing)
        svc = get_two_factor_service()
        tf_ctx = TwoFactorRequestContext(relaxed=relaxed, client_ip=client_ip)
        superseded_n = supersede_pending_sms_challenges_for_target(
            db, person_id=person.id, purpose=purpose, target_e164=phone,
        )
        try:
            ch, meta = svc.create_challenge(
                db, person.id, "sms", purpose, phone, tf_ctx,
            )
            svc.send_code(db, ch, meta)
        except TwoFactorException as exc:
            raise ValidationError(exc.message) from exc
        masked = meta.get("masked_target")
        token = create_registration_otp_token(person.id)
        cfg = parse_phone_verification_config(screen)
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.INTERACTION_RESEND_REQUESTED,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=session.current_step_id,
            screen_id=screen.id,
            payload={
                "interaction_type": INTERACTION_PHONE_SMS,
                "challenge_id": str(ch.id),
                "purpose": purpose,
                "screen_key": screen.screen_key,
                "superseded_count": superseded_n,
                "sent": True,
            },
        )
        self._upsert_session_field(
            db,
            session,
            _REG_INTERNAL_SMS_LAST_RESEND_AT,
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        out = {
            "otp_token": token,
            "challenge_id": str(ch.id),
            "target_masked": masked,
            "purpose": purpose,
            "source_field_slug": cfg["source_field_slug"],
            "verified_flag_slug": vflag,
            "sent": True,
            "resend_after_seconds": RESEND_SECONDS,
            "superseded_count": superseded_n,
        }
        dev_code = two_factor_dev_code_for_api_exposure()
        if dev_code:
            out["dev_code"] = dev_code
        return out

    def complete_interaction(
        self,
        db: Session,
        session_id: UUID,
        *,
        screen_id: UUID,
        interaction_type: str,
        challenge_id: UUID,
        verified: bool,
    ) -> dict:
        if not verified:
            raise ValidationError("verified must be true after successful SMS verification")
        session = self._get_session(db, session_id)
        if session.status == "completed":
            raise SessionCompletedError("Session already completed")
        if session.current_screen_id != screen_id:
            raise ValidationError("screen_id does not match the current registration screen")
        screen = session.current_screen
        if screen is None or effective_screen_type(screen) != "interaction":
            raise RegistrationError("Current screen is not an interaction screen")
        if screen.interaction_type != interaction_type:
            raise ValidationError("interaction_type does not match the current screen")
        if interaction_type != INTERACTION_PHONE_SMS:
            raise RegistrationError("Unsupported interaction_type for complete")

        context = self._get_session_context(db, session.id)
        phone, purpose, vflag = _require_phone_verification_prerequisites(
            screen,
            context,
            default_region=default_phone_region_from_session(session),
        )
        if session.person_id is None:
            raise ValidationError("Session has no person record")

        ch = (
            db.query(TwoFactorChallenge)
            .filter(
                TwoFactorChallenge.id == challenge_id,
                TwoFactorChallenge.person_id == session.person_id,
            )
            .first()
        )
        if ch is None:
            raise ValidationError("Challenge not found for this session")
        if ch.status != "verified":
            raise ValidationError("Challenge is not verified; complete SMS verification first")
        if ch.purpose != purpose:
            raise ValidationError("Challenge purpose does not match this screen configuration")
        if (ch.target or "").strip() != phone:
            raise ValidationError("Verified challenge does not match the phone number on file")

        now_iso = datetime.now(timezone.utc).isoformat()
        self._upsert_session_field(db, session, vflag, True)
        self._upsert_session_field(db, session, "phone_verified_at", now_iso)
        self._upsert_session_field(db, session, "phone_verification_channel", "sms")
        self._delete_session_field(db, session, _REG_INTERNAL_SMS_LAST_RESEND_AT)
        db.flush()

        self._project_to_person(db, session)

        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.INTERACTION_COMPLETED,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=session.current_step_id,
            screen_id=screen.id,
            payload={
                "interaction_type": interaction_type,
                "challenge_id": str(challenge_id),
                "verified_flag_slug": vflag,
                "screen_key": screen.screen_key,
            },
        )
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.FIELDS_SUBMITTED,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=session.current_step_id,
            screen_id=screen.id,
            payload={
                "field_slugs": [vflag, "phone_verified_at", "phone_verification_channel"],
                "masked_values": {},
                "screen_key": screen.screen_key,
                "via": "interaction_complete",
            },
        )
        return {
            "status": "ok",
            "session_id": str(session.id),
            "verified_flag_slug": vflag,
        }

    def _upsert_session_field(
        self,
        db: Session,
        session: RegistrationSession,
        field_slug: str,
        value: Any,
    ) -> None:
        existing = (
            db.query(RegistrationSessionData)
            .filter(
                RegistrationSessionData.session_id == session.id,
                RegistrationSessionData.field_slug == field_slug,
            )
            .first()
        )
        if existing:
            existing.value_json = value
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.add(
                RegistrationSessionData(
                    id=uuid_mod.uuid4(),
                    session_id=session.id,
                    field_slug=field_slug,
                    value_json=value,
                    source="interaction",
                )
            )

    def _delete_session_field(
        self,
        db: Session,
        session: RegistrationSession,
        field_slug: str,
    ) -> None:
        (
            db.query(RegistrationSessionData)
            .filter(
                RegistrationSessionData.session_id == session.id,
                RegistrationSessionData.field_slug == field_slug,
            )
            .delete()
        )

    def _ensure_interaction_advance_allowed(
        self,
        db: Session,
        session: RegistrationSession,
        screen: RegistrationStepScreen,
        context: Dict[str, Any],
    ) -> None:
        if effective_screen_type(screen) != "interaction":
            return
        if screen.interaction_type == INTERACTION_PHONE_SMS:
            cfg = parse_phone_verification_config(screen)
            flag = cfg.get("verified_flag_slug") or ""
            if not flag:
                raise StepBlockedError("Interaction screen is misconfigured (verified_flag_slug)")
            val = context.get(flag)
            if val is None or val is False or val == "":
                sk = screen.screen_key
                safe_log_registration_event(
                    db,
                    session,
                    event_type=RegistrationEventType.STEP_BLOCKED,
                    event_status=RegistrationEventStatus.BLOCKED,
                    step_id=session.current_step_id,
                    screen_id=screen.id,
                    payload={
                        "step_key": (
                            session.current_step.step_key if session.current_step else None
                        ),
                        "reason": "interaction_incomplete",
                        "screen_key": sk,
                    },
                )
                raise StepBlockedError(
                    "Complete SMS verification on this screen before continuing."
                )

    # ── Complete ───────────────────────────────────────────────────

    def complete_session(self, db: Session, session_id: UUID) -> dict:
        """Mark session complete and project data to persons.profile_json["collected"]."""
        session = self._get_session(db, session_id)
        if session.status == "completed":
            raise SessionCompletedError("Session already completed")

        if session.current_step:
            self._mark_step_completed(db, session, session.current_step)

        session.status = "completed"
        session.progress_percent = 100
        db.flush()

        projection_result = self._project_to_person(db, session)
        db.flush()

        projected_slugs = projection_result.get("projected_field_slugs") or []
        person_s = projection_result.get("person_id") or (
            str(session.person_id) if session.person_id else None
        )
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.PROJECTION_COMPLETED,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=session.current_step_id,
            screen_id=session.current_screen_id,
            payload={
                "person_id": person_s,
                "projected_fields": projected_slugs,
            },
        )
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.SESSION_COMPLETED,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=session.current_step_id,
            screen_id=session.current_screen_id,
            payload={
                "status": "completed",
                "projected_fields": projected_slugs,
                "person_id": person_s,
            },
        )

        self._log_audit(db, session, "REGISTRATION_SESSION_COMPLETED", {
            "projected_fields": projection_result.get("projected_fields", 0),
        })

        return {
            "session_id": str(session.id),
            "status": "completed",
            "person_id": str(session.person_id) if session.person_id else None,
            "projection": projection_result,
        }

    # ── Projection (layered) ───────────────────────────────────────

    def _project_to_person(self, db: Session, session: RegistrationSession) -> dict:
        """Sync session_data → persons.profile_json["collected"].

        Writes registration answers into a dedicated "collected" namespace
        inside profile_json to avoid collisions with computed/compliance data.
        """
        if session.person_id is None:
            person = Person(
                id=uuid_mod.uuid4(),
                status="active",
                jurisdiction=session.jurisdiction.code if session.jurisdiction else None,
                profile_json={"collected": {}, "computed": {}, "compliance": {}},
                kyc_status="not_started",
            )
            db.add(person)
            db.flush()
            session.person_id = person.id
            db.flush()
        else:
            person = db.query(Person).filter(Person.id == session.person_id).first()
            if person is None:
                logger.error("Person %s not found for session %s", session.person_id, session.id)
                return {"projected_fields": 0, "error": "person_not_found"}

        entries = (
            db.query(RegistrationSessionData)
            .filter(RegistrationSessionData.session_id == session.id)
            .all()
        )

        profile = dict(person.profile_json) if person.profile_json else {}
        if "collected" not in profile or not isinstance(profile.get("collected"), dict):
            profile["collected"] = {}
        if "computed" not in profile:
            profile["computed"] = {}
        if "compliance" not in profile:
            profile["compliance"] = {}

        count = 0
        slugs: List[str] = []
        for entry in entries:
            slug = entry.field_slug
            if str(slug).startswith("__reg_internal_"):
                continue
            if session_slug_to_compliance(slug):
                profile["compliance"][slug] = entry.value_json
            else:
                profile["collected"][slug] = entry.value_json
            count += 1
            slugs.append(slug)

        person.profile_json = profile
        flag_modified(person, "profile_json")
        db.flush()

        return {
            "person_id": str(person.id),
            "projected_fields": count,
            "projected_field_slugs": slugs,
        }

    # ── Step state tracking ────────────────────────────────────────

    def _ensure_step_state(
        self,
        db: Session,
        session: RegistrationSession,
        step: RegistrationFlowStep,
        target_status: str,
    ) -> RegistrationSessionStep:
        """Get or create a RegistrationSessionStep record and update its status."""
        ss = (
            db.query(RegistrationSessionStep)
            .filter(
                RegistrationSessionStep.session_id == session.id,
                RegistrationSessionStep.step_id == step.id,
            )
            .first()
        )
        now = datetime.now(timezone.utc)
        if ss is None:
            ss = RegistrationSessionStep(
                id=uuid_mod.uuid4(),
                session_id=session.id,
                step_id=step.id,
                status=target_status,
                started_at=now if target_status == "in_progress" else None,
            )
            db.add(ss)
            db.flush()
        else:
            if target_status == "in_progress" and ss.status == "not_started":
                ss.status = "in_progress"
                ss.started_at = now
            elif target_status != ss.status:
                ss.status = target_status
            db.flush()
        return ss

    def _mark_step_completed(
        self,
        db: Session,
        session: RegistrationSession,
        step: RegistrationFlowStep,
    ) -> None:
        ss = self._ensure_step_state(db, session, step, "completed")
        ss.completed_at = datetime.now(timezone.utc)
        ss.last_screen_id = session.current_screen_id
        db.flush()
        labels = self._labels_for_step_screen(session, step, None)
        safe_log_registration_event(
            db,
            session,
            event_type=RegistrationEventType.STEP_COMPLETED,
            event_status=RegistrationEventStatus.SUCCESS,
            step_id=step.id,
            screen_id=session.current_screen_id,
            payload={
                "step_key": labels.get("step_key"),
                "step_title": labels.get("step_title"),
            },
        )

    def _get_step_status(
        self,
        db: Session,
        session: RegistrationSession,
        step: RegistrationFlowStep,
    ) -> str:
        ss = (
            db.query(RegistrationSessionStep)
            .filter(
                RegistrationSessionStep.session_id == session.id,
                RegistrationSessionStep.step_id == step.id,
            )
            .first()
        )
        return ss.status if ss else "not_started"

    # ── Navigation guards ──────────────────────────────────────────

    def _enforce_blocking_gate(
        self,
        db: Session,
        session: RegistrationSession,
        current_step: RegistrationFlowStep,
        flow: RegistrationFlow,
        context: Dict[str, Any],
    ) -> None:
        """Prevent advancing past an incomplete blocking step.

        Checks all blocking steps up to and including current_step.
        If any required fields are missing on a blocking step, raises StepBlockedError.
        """
        if not current_step.is_blocking:
            return

        visible_steps = filter_visible_items(flow.steps, context)
        for step in visible_steps:
            if step.position > current_step.position:
                break
            if not step.is_blocking:
                continue
            status = self._get_step_status(db, session, step)
            if status in ("completed", "skipped"):
                continue
            if step.id == current_step.id:
                if not self._are_step_required_fields_present(step, context):
                    sk = session.current_screen.screen_key if session.current_screen else None
                    safe_log_registration_event(
                        db,
                        session,
                        event_type=RegistrationEventType.STEP_BLOCKED,
                        event_status=RegistrationEventStatus.BLOCKED,
                        step_id=step.id,
                        screen_id=session.current_screen_id,
                        payload={
                            "step_key": step.step_key,
                            "blocking_step_key": step.step_key,
                            "screen_key": sk,
                            "reason": "blocking_step_incomplete",
                        },
                    )
                    raise StepBlockedError(
                        f"Step '{step.step_key}' is blocking and has missing required fields"
                    )

    def _are_step_required_fields_present(
        self,
        step: RegistrationFlowStep,
        context: Dict[str, Any],
    ) -> bool:
        """Check that all required visible fields in a step have values in context."""
        for screen in filter_visible_items(step.screens, context):
            if effective_screen_type(screen) == "permission_prompt":
                cfg = parse_permission_prompt_config(screen)
                slug = (cfg.get("decision_slug") or "").strip()
                if not slug:
                    return False
                if slug not in context:
                    return False
                continue
            if effective_screen_type(screen) == "interaction":
                if screen.interaction_type == INTERACTION_PHONE_SMS:
                    cfg = parse_phone_verification_config(screen)
                    flag = (cfg.get("verified_flag_slug") or "").strip()
                    if not flag:
                        return False
                    val = context.get(flag)
                    if val is None or val is False or val == "":
                        return False
                continue
            visible_components = filter_visible_items(screen.components, context)
            for comp in visible_components:
                if not comp.binding_slug:
                    continue
                props = comp.props_json or {}
                if not props.get("required", False):
                    continue
                if comp.component_type == "address_autocomplete":
                    for sub_slug in resolved_binding_slugs(props).values():
                        sv = context.get(sub_slug)
                        if sv is None or sv == "" or sv == []:
                            return False
                    continue
                if comp.component_type == "address_step":
                    opts = resolved_address_step_binding_slugs(props)
                    line2_opt = props.get("address_line_2_optional", True)
                    for key, sub_slug in opts.items():
                        if key == "address_line_2" and line2_opt:
                            continue
                        sv = context.get(sub_slug)
                        if sv is None or sv == "" or sv == []:
                            return False
                    continue
                val = context.get(comp.binding_slug)
                if val is None or val == "" or val == []:
                    return False
        return True

    def _screen_resume_complete(
        self,
        screen: RegistrationStepScreen,
        merged: Dict[str, Any],
    ) -> bool:
        """True si les champs requis visibles de l'écran sont satisfaits (reprise curseur, sans audit)."""
        st = effective_screen_type(screen)
        if st == "permission_prompt":
            cfg = parse_permission_prompt_config(screen)
            slug = (cfg.get("decision_slug") or "").strip()
            if not slug:
                return False
            v = merged.get(slug)
            return isinstance(v, bool)
        if st == "interaction":
            if screen.interaction_type == INTERACTION_PHONE_SMS:
                cfg = parse_phone_verification_config(screen)
                flag = (cfg.get("verified_flag_slug") or "").strip()
                if not flag:
                    return False
                val = merged.get(flag)
                return not (val is None or val is False or val == "")
            return True
        visible_components = filter_visible_items(screen.components, merged)
        for comp in visible_components:
            if not comp.binding_slug:
                continue
            props = comp.props_json or {}
            if not props.get("required", False):
                continue
            slug = comp.binding_slug
            val = merged.get(slug)
            if comp.component_type == "phone_input":
                raw_key = f"{slug}_raw"
                raw_side = merged.get(raw_key)
                has_phone = (val is not None and val != "" and val != []) or (
                    raw_side is not None and str(raw_side).strip() != ""
                )
                if not has_phone:
                    return False
                continue
            if comp.component_type == "address_autocomplete":
                for sub_slug in resolved_binding_slugs(props).values():
                    sv = merged.get(sub_slug)
                    if sv is None or sv == "" or sv == []:
                        return False
                continue
            if comp.component_type == "address_step":
                opts = resolved_address_step_binding_slugs(props)
                line2_opt = props.get("address_line_2_optional", True)
                for key, sub_slug in opts.items():
                    if key == "address_line_2" and line2_opt:
                        continue
                    sv = merged.get(sub_slug)
                    if sv is None or sv == "" or sv == []:
                        return False
                continue
            if val is None or val == "" or val == []:
                return False
        return True

    def _first_incomplete_visible_screen_in_step(
        self,
        step: RegistrationFlowStep,
        merged: Dict[str, Any],
    ) -> Optional[RegistrationStepScreen]:
        """Premier écran du step (par position) dont les exigences ne sont pas encore remplies."""
        vis = [s for s in filter_visible_items(step.screens, merged)]
        vis.sort(key=lambda s: s.position)
        for screen in vis:
            if not self._screen_resume_complete(screen, merged):
                return screen
        return None

    def _validate_required_fields(
        self,
        db: Session,
        session: RegistrationSession,
        screen: RegistrationStepScreen,
        answers: Dict[str, Any],
        context: Dict[str, Any],
    ) -> None:
        """Check that required visible components have values in answers or context."""
        merged = {**context, **answers}
        if effective_screen_type(screen) == "permission_prompt":
            cfg = parse_permission_prompt_config(screen)
            slug = (cfg.get("decision_slug") or "").strip()
            if not slug:
                raise ValidationError("Permission screen is missing decision_slug in config")
            val = merged.get(slug)
            if val is None:
                raise ValidationError(f"Missing required field: {slug}")
            if not isinstance(val, bool):
                raise ValidationError(f"Field {slug} must be true or false")
            return
        visible_components = filter_visible_items(screen.components, merged)
        missing = []
        for comp in visible_components:
            if not comp.binding_slug:
                continue
            props = comp.props_json or {}
            if not props.get("required", False):
                continue
            slug = comp.binding_slug
            val = merged.get(slug)
            if comp.component_type == "phone_input":
                raw_key = f"{slug}_raw"
                raw_side = merged.get(raw_key)
                has_phone = (val is not None and val != "" and val != []) or (
                    raw_side is not None
                    and str(raw_side).strip() != ""
                )
                if not has_phone:
                    missing.append(slug)
                continue
            if comp.component_type == "address_autocomplete":
                for sub_slug in resolved_binding_slugs(props).values():
                    sv = merged.get(sub_slug)
                    if sv is None or sv == "" or sv == []:
                        missing.append(sub_slug)
                continue
            if comp.component_type == "address_step":
                opts = resolved_address_step_binding_slugs(props)
                line2_opt = props.get("address_line_2_optional", True)
                for key, sub_slug in opts.items():
                    if key == "address_line_2" and line2_opt:
                        continue
                    sv = merged.get(sub_slug)
                    if sv is None or sv == "" or sv == []:
                        missing.append(sub_slug)
                continue
            if val is None or val == "" or val == []:
                missing.append(slug)

        if missing:
            safe_log_registration_event(
                db,
                session,
                event_type=RegistrationEventType.VALIDATION_FAILED,
                event_status=RegistrationEventStatus.FAILURE,
                step_id=screen.step_id,
                screen_id=screen.id,
                payload={
                    "screen_key": screen.screen_key,
                    "reason": "missing_required",
                    "errors": [{"slug": s, "message": "required"} for s in missing],
                    "fields": missing,
                },
            )
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")

    # ── Helpers ─────────────────────────────────────────────────────

    def _get_session(self, db: Session, session_id: UUID) -> RegistrationSession:
        session = (
            db.query(RegistrationSession)
            .options(
                joinedload(RegistrationSession.jurisdiction),
                joinedload(RegistrationSession.current_step),
                joinedload(RegistrationSession.current_screen)
                .selectinload(RegistrationStepScreen.components)
                .joinedload(RegistrationScreenComponent.field_definition),
            )
            .filter(RegistrationSession.id == session_id)
            .first()
        )
        if session is None:
            raise SessionNotFoundError(f"Session {session_id} not found")
        return session

    def _get_session_context(self, db: Session, session_id: UUID) -> Dict[str, Any]:
        """Build a flat dict of all collected data for rule evaluation."""
        entries = (
            db.query(RegistrationSessionData)
            .filter(RegistrationSessionData.session_id == session_id)
            .all()
        )
        return {e.field_slug: e.value_json for e in entries}

    def _flatten_visible_screens(
        self,
        flow: RegistrationFlow,
        context: Dict[str, Any],
    ) -> List[RegistrationStepScreen]:
        """Return all visible screens in order across all visible steps."""
        result = []
        for step in filter_visible_items(flow.steps, context):
            for screen in filter_visible_items(step.screens, context):
                result.append(screen)
        return result

    @staticmethod
    def _find_screen_index(flat_screens: list, screen_id: Optional[UUID]) -> Optional[int]:
        if screen_id is None:
            return None
        for i, s in enumerate(flat_screens):
            if s.id == screen_id:
                return i
        return None

    @staticmethod
    def _compute_progress(current_idx: int, total: int) -> int:
        if total <= 1:
            return 100
        return min(100, int((current_idx / (total - 1)) * 100))

    def _build_screen_response(
        self,
        db: Session,
        session: RegistrationSession,
        is_last: bool = False,
        lang: Optional[str] = None,
    ) -> dict:
        """Build the full response for the current screen."""
        context = self._get_session_context(db, session.id)

        default_lang = "en"
        if session.jurisdiction:
            default_lang = session.jurisdiction.default_language or "en"
        effective_lang = lang or default_lang

        screen_data = None
        if session.current_screen:
            screen = session.current_screen
            visible_components = filter_visible_items(screen.components, context)
            title = resolve_localized(screen.title_i18n, effective_lang, default_lang) if screen.title_i18n else screen.title
            subtitle = resolve_localized(screen.subtitle_i18n, effective_lang, default_lang) if screen.subtitle_i18n else screen.subtitle
            button_label = resolve_localized(screen.button_label_i18n, effective_lang, default_lang) if screen.button_label_i18n else screen.button_label
            st = effective_screen_type(screen)
            jcode = session.jurisdiction.code if session.jurisdiction else None
            enriched_components: List[dict] = []
            for c in visible_components:
                comp_dict = RegistrationFlowService._serialize_component(c, effective_lang, default_lang)
                comp_dict["props"] = enrich_registration_component_props(
                    db,
                    jcode,
                    c.component_type,
                    comp_dict["props"],
                    effective_lang,
                    default_lang,
                    c.binding_slug,
                )
                enriched_components.append(comp_dict)

            screen_data = {
                "id": str(screen.id),
                "screen_key": screen.screen_key,
                "title": title,
                "subtitle": subtitle,
                "button_label": button_label,
                "layout_type": screen.layout_type,
                "screen_type": st,
                "config": screen.config_json,
                "components": enriched_components,
                "interaction_type": screen.interaction_type if st == "interaction" else None,
                "interaction_config": screen.interaction_config_json if st == "interaction" else None,
                "interaction_payload": (
                    build_phone_sms_read_payload(db, session, screen, context)
                    if st == "interaction" and screen.interaction_type == INTERACTION_PHONE_SMS
                    else None
                ),
            }

        step_data = None
        current_step_status = None
        if session.current_step:
            step = session.current_step
            current_step_status = self._get_step_status(db, session, step)
            title = resolve_localized(step.title_i18n, effective_lang, default_lang) if step.title_i18n else step.title
            description = resolve_localized(step.description_i18n, effective_lang, default_lang) if step.description_i18n else step.description
            step_data = {
                "id": str(step.id),
                "step_key": step.step_key,
                "title": title,
                "description": description,
                "is_blocking": step.is_blocking,
                "status": current_step_status,
            }

        step_states = self._get_all_step_states(db, session)

        step_context = None
        if session.current_step and session.current_screen:
            vis = [s for s in filter_visible_items(session.current_step.screens, context)]
            vis.sort(key=lambda s: s.position)
            idx = next(
                (i for i, s in enumerate(vis) if s.id == session.current_screen.id),
                0,
            )
            step_context = {
                "step_key": session.current_step.step_key,
                "step_position": session.current_step.position,
                "screen_index_in_step": idx,
                "screens_in_step": len(vis),
            }

        # Premier écran *du step courant* (pas du flux entier) : croix / pas de retour arrière step.
        is_first_screen = False
        if step_context is not None:
            is_first_screen = step_context["screen_index_in_step"] == 0
        else:
            is_first_screen = session.progress_percent == 0

        return {
            "session_id": str(session.id),
            "status": session.status,
            "flow_version": session.flow_version,
            "progress_percent": session.progress_percent,
            "is_first_screen": is_first_screen,
            "is_last_screen": is_last,
            "current_step": step_data,
            "current_step_status": current_step_status,
            "screen": screen_data,
            "collected_data": _public_registration_context(context),
            "step_states": step_states,
            "step_context": step_context,
        }

    def _get_all_step_states(self, db: Session, session: RegistrationSession) -> List[dict]:
        rows = (
            db.query(RegistrationSessionStep)
            .filter(RegistrationSessionStep.session_id == session.id)
            .order_by(RegistrationSessionStep.started_at)
            .all()
        )
        return [
            {
                "step_id": str(r.step_id),
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in rows
        ]

    def _log_audit(
        self,
        db: Session,
        session: RegistrationSession,
        event_type: str,
        extra: Optional[dict] = None,
    ) -> None:
        if session.person_id is None:
            logger.debug("Skipping audit %s: no person_id yet", event_type)
            return
        try:
            payload = {
                "session_id": str(session.id),
                "flow_id": str(session.flow_id),
                "flow_version": session.flow_version,
                "jurisdiction_id": str(session.jurisdiction_id),
                "status": session.status,
                "progress_percent": session.progress_percent,
            }
            if extra:
                payload.update(extra)

            nested = db.begin_nested()
            try:
                event = AuditEvent(
                    id=uuid_mod.uuid4(),
                    person_id=session.person_id,
                    event_type=event_type,
                    actor_type="system",
                    actor_id=None,
                    correlation_id=uuid_mod.uuid4(),
                    payload=payload,
                    schema_version=1,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(event)
                db.flush()
                nested.commit()
            except Exception:
                nested.rollback()
                raise
        except Exception:
            logger.warning("Failed to write registration audit event: %s", event_type, exc_info=True)
