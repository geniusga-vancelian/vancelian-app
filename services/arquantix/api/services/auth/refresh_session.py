"""
Phase 2 — sessions serveur, rotation refresh, device binding, denylist jti.
Phase 3.1 — empreinte appareil, persistance événements sécurité (observabilité).

Ne jamais logger les jetons en clair ; device_id / jti partiellement masqués dans les logs.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    try_decode_refresh_token,
    verify_password,
)
from database import (
    AdminUser,
    AuthDeviceCredential,
    AuthRefreshToken,
    AuthSession,
    AuthSpentRefreshJti,
    Person,
)
from services.auth.account_policy import has_portfolio_customer_for_person, is_web_only_mobile_app_user
from services.auth.security_setup_state import (
    derive_account_state,
    persist_person_account_state_column,
    should_issue_partial_session_for_mobile_app,
)
from services.auth.device_attestation_service import (
    DEVICE_TRUST_UNKNOWN,
    AttestationResult,
    evaluate_header_for_auth,
    fail_blocks_login,
    finalize_successful_attestation,
    is_device_attestation_enabled,
    parse_x_device_attestation_header,
)
from services.auth.device_fingerprint import is_device_fingerprint_enabled, parse_device_fingerprint_header
from services.auth.security_events_service import is_security_events_enabled, persist_auth_security_event
from services.auth.jwt_subject_resolution import NonUserJWTSubjectError, classify_sub_format, resolve_user_from_jwt_sub

logger = logging.getLogger("arquantix.auth.security")

LEGACY_UNKNOWN_DEVICE = "legacy-unknown"
MAX_DEVICE_ID_LEN = 128


def normalize_device_id(header_val: Optional[str]) -> str:
    """Sans en-tête : `legacy-unknown` (rétrocompat Phase 1 / clients sans binding)."""
    if header_val is None or not str(header_val).strip():
        return LEGACY_UNKNOWN_DEVICE
    s = str(header_val).strip()
    if len(s) > MAX_DEVICE_ID_LEN:
        s = s[:MAX_DEVICE_ID_LEN]
    return s


def _jwt_refresh_device_claims_consistent(payload: Dict[str, Any]) -> bool:
    """``did`` et ``device_id`` ne peuvent pas diverger s’ils sont tous deux présents."""
    d_raw = payload.get("did")
    c_raw = payload.get("device_id")
    if d_raw is None or c_raw is None:
        return True
    return normalize_device_id(str(d_raw)) == normalize_device_id(str(c_raw))


def _is_server_tmp_device_id(did: str) -> bool:
    """Identifiant bootstrap émis au login sans ``X-Device-ID`` (``srvtmp-<uuid>``)."""
    if not did or not str(did).strip():
        return False
    return str(did).strip().startswith("srvtmp-")


def _is_srvtmp_to_client_promotion(jwt_device: str, header_device: str) -> bool:
    """JWT encore en ``srvtmp-*``, en-tête = premier ID client stable — pas un conflit malveillant."""
    if not _is_server_tmp_device_id(jwt_device):
        return False
    if header_device == LEGACY_UNKNOWN_DEVICE or _is_server_tmp_device_id(header_device):
        return False
    return True


def _session_matches_effective_for_revoke(
    session: AuthSession,
    effective_device: str,
    payload: Dict[str, Any],
) -> bool:
    """Aligne session et appareil effectif, y compris avant promotion ``srvtmp`` (session/jwt encore bootstrap)."""
    if session.device_id == effective_device:
        return True
    if _is_server_tmp_device_id(session.device_id) and not _is_server_tmp_device_id(
        effective_device
    ) and effective_device != LEGACY_UNKNOWN_DEVICE:
        jw_raw = payload.get("did") or payload.get("device_id")
        if jw_raw is None:
            return False
        return normalize_device_id(str(jw_raw)) == session.device_id
    return False


def _effective_device_for_refresh(header_device: str, payload: Dict[str, Any]) -> str:
    """En-tête prioritaire ; si ``legacy-unknown``, utiliser ``did`` / ``device_id`` du JWT si présents."""
    if header_device != LEGACY_UNKNOWN_DEVICE:
        return header_device
    for key in ("did", "device_id"):
        raw = payload.get(key)
        if raw is not None and str(raw).strip():
            return normalize_device_id(str(raw))
    return LEGACY_UNKNOWN_DEVICE


def _jwt_has_device_binding_claims(payload: Dict[str, Any]) -> bool:
    return payload.get("did") is not None or payload.get("device_id") is not None


def _apply_pr_b_device_binding(
    db: Session,
    request: Request,
    *,
    session: AuthSession,
    effective_device: str,
    jti: str,
    route: Optional[str],
) -> Literal["ok", "migrated", "revoked"]:
    """PR B — migration ``legacy-unknown`` / promotion unique ``srvtmp-*`` → client, ou révocation."""
    expected = session.device_id
    received = effective_device

    if expected == LEGACY_UNKNOWN_DEVICE and received != LEGACY_UNKNOWN_DEVICE:
        session.device_id = received
        logger.info(
            "device_binding_migrated",
            extra={
                "event": "device_binding_migrated",
                "admin_user_id": session.user_id,
                "session_id": str(session.id),
                "expected_device_id": _mask_device(expected),
                "received_device_id": _mask_device(received),
                "route": route or "",
                "kind": "legacy_unknown_to_client",
            },
        )
        return "migrated"

    # Une seule promotion : bootstrap serveur → premier ID client stable (voir PR_B_DEVICE_BINDING.md).
    if _is_server_tmp_device_id(expected) and received != expected:
        if (
            received != LEGACY_UNKNOWN_DEVICE
            and not _is_server_tmp_device_id(received)
        ):
            session.device_id = received
            logger.info(
                "device_binding_migrated",
                extra={
                    "event": "device_binding_migrated",
                    "admin_user_id": session.user_id,
                    "session_id": str(session.id),
                    "expected_device_id": _mask_device(expected),
                    "received_device_id": _mask_device(received),
                    "route": route or "",
                    "kind": "srvtmp_promoted_to_client",
                },
            )
            return "migrated"

    if expected != received:
        logger.error(
            "device_mismatch_detected",
            extra={
                "event": "device_mismatch_detected",
                "admin_user_id": session.user_id,
                "session_id": str(session.id),
                "expected_device_id": _mask_device(expected),
                "received_device_id": _mask_device(received),
                "route": route or "",
            },
        )
        _revoke_session_for_refresh_reuse(
            db,
            request,
            session=session,
            reason="device_binding_mismatch",
            jti=str(jti),
            route=route,
        )
        db.commit()
        _note_failed_refresh(request)
        return "revoked"

    return "ok"


def _mask_device(did: str) -> str:
    if len(did) <= 8:
        return "***"
    return f"{did[:4]}***{did[-4:]}"


def _mask_jti(jti: str) -> str:
    return f"{jti[:8]}…" if jti else ""


def _mask_ip(ip: str) -> str:
    if not ip or len(ip) <= 8:
        return "***"
    return f"{ip[:4]}***{ip[-2:]}"


def _note_failed_refresh(request: Request) -> None:
    from services.auth.auth_rate_limit import client_ip_for_rl
    from services.auth.auth_security_signals import note_refresh_reject

    note_refresh_reject(client_ip_for_rl(request))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _client_email_for_pe_provision(user: AdminUser) -> Optional[str]:
    """E-mail métier pour pe_clients si présent ; sinon None (PR4, plus de placeholder SMS)."""
    raw = getattr(user, "email", None)
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def _ensure_pe_client_for_login_user_best_effort(db: Session, user: AdminUser) -> None:
    """Garantit une ligne ``pe_clients`` pour les routes ``/api/app/*`` (profil mobile).

    Voir ``API_PROFILE_404_ROOT_CAUSE_REPORT.md``. Ne bloque pas l’auth si collision rare.
    """
    if getattr(user, "person_id", None) is None:
        return
    try:
        from services.client_identity.service import ClientIdentityService

        ClientIdentityService.ensure_pe_client_for_login_user(
            db,
            person_id=user.person_id,
            client_email=_client_email_for_pe_provision(user),
            actor_type="auth.session",
            actor_id=str(user.id),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ensure_pe_client_for_login_user skipped user=%s: %s",
            user.id,
            exc,
        )


def _assert_user_not_security_locked(user: AdminUser) -> None:
    now = _utcnow()
    lu = getattr(user, "security_account_locked_until", None)
    if lu is not None and lu > now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "security.account_locked",
                "message": "Compte temporairement verrouillé pour raison de sécurité.",
            },
        )


MOBILE_APP_NOT_ALLOWED_DETAIL: Dict[str, str] = {
    "code": "MOBILE_APP_NOT_ALLOWED",
    "message": (
        "Ce compte est réservé à l’administration web et ne peut pas être utilisé "
        "sur l’application mobile."
    ),
}

APP_JWT_REQUIRES_CUSTOMER_DETAIL: Dict[str, str] = {
    "code": "APP_JWT_REQUIRES_CUSTOMER",
    "message": (
        "Les jetons de session sont réservés aux clients (identité Person avec "
        "portefeuille enregistré). Connexion administrateur non autorisée."
    ),
}


def _assert_portfolio_customer_for_app_jwt(db: Session, user: AdminUser) -> None:
    """Toute session JWT (login / refresh) exige une ligne ``pe_clients`` pour la Person liée."""
    if has_portfolio_customer_for_person(db, user):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=APP_JWT_REQUIRES_CUSTOMER_DETAIL,
    )


def _assert_mobile_app_session_allowed(user: AdminUser) -> None:
    """Refuse toute session JWT (app mobile) pour les comptes réservés au back-office web."""
    if not is_web_only_mobile_app_user(user):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=MOBILE_APP_NOT_ALLOWED_DETAIL,
    )


LOGIN_FROZEN_DETAIL: Dict[str, str] = {
    "code": "auth.login_frozen",
    "message": "Ce compte est suspendu. Contactez le support.",
}


def _assert_person_login_not_frozen(db: Session, user: AdminUser) -> None:
    """Gel administratif sur ``persons.login_frozen`` (Customer 360)."""
    pid = getattr(user, "person_id", None)
    if pid is None:
        return
    p = db.get(Person, pid)
    if p is None:
        return
    if getattr(p, "login_frozen", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=LOGIN_FROZEN_DETAIL,
        )


def _assert_refresh_allowed(db: Session, user: AdminUser) -> None:
    _assert_user_not_security_locked(user)
    _assert_person_login_not_frozen(db, user)
    if getattr(user, "security_refresh_blocked", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "security.refresh_blocked", "message": "Renouvellement de session suspendu."},
        )


def _client_meta(request: Request) -> tuple[Optional[str], Optional[str]]:
    ip = None
    if request.client:
        ip = request.client.host
    ua = request.headers.get("user-agent")
    if ua and len(ua) > 512:
        ua = ua[:512]
    return ip, ua


def _fingerprint_from_request(request: Request) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    raw = request.headers.get("x-device-fingerprint")
    return parse_device_fingerprint_header(raw)


def _auth_audit(
    event_type: str,
    *,
    db: Optional[Session] = None,
    request: Optional[Request] = None,
    user_id: Optional[int] = None,
    device_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    isolated: bool = False,
) -> None:
    safe = {k: v for k, v in (metadata or {}).items() if v is not None}
    logger.info("%s %s", event_type, safe)
    if not is_security_events_enabled():
        return
    ip, ua = (None, None)
    if request is not None:
        ip, ua = _client_meta(request)
    persist_auth_security_event(
        user_id=user_id,
        device_id=device_id or "",
        event_type=event_type,
        ip_address=ip,
        user_agent=ua,
        metadata=safe,
        db=None if isolated else db,
    )


def claim_refresh_jti(db: Session, jti: str) -> bool:
    """True si le jti vient d'être réservé ; False si déjà consommé (réutilisation)."""
    stmt = (
        insert(AuthSpentRefreshJti)
        .values(jti=jti)
        .on_conflict_do_nothing(index_elements=["jti"])
    )
    res = db.execute(stmt)
    return res.rowcount == 1


def _spend_jti_safe(db: Session, jti: str) -> None:
    """Marque un jti comme dépensé sans échouer si déjà présent."""
    stmt = (
        insert(AuthSpentRefreshJti)
        .values(jti=jti)
        .on_conflict_do_nothing(index_elements=["jti"])
    )
    db.execute(stmt)


def _register_auth_refresh_token_row(db: Session, *, session_id: uuid.UUID, jti: str) -> None:
    """Enregistre le jti courant pour une session (login / upgrade legacy)."""
    db.add(
        AuthRefreshToken(
            id=uuid.uuid4(),
            session_id=session_id,
            jti=str(jti)[:64],
            issued_at=_utcnow(),
        )
    )


def _rotate_auth_refresh_token_chain(
    db: Session, *, session: AuthSession, old_jti: str, new_jti: str
) -> None:
    """Marque l’ancien jti comme rotaté et enregistre le nouveau (même ``session_id``)."""
    prev = db.query(AuthRefreshToken).filter(AuthRefreshToken.jti == str(old_jti)[:64]).one_or_none()
    now = _utcnow()
    if prev is not None:
        prev.rotated_at = now
        prev.replaced_by_jti = str(new_jti)[:64]
    db.add(
        AuthRefreshToken(
            id=uuid.uuid4(),
            session_id=session.id,
            jti=str(new_jti)[:64],
            issued_at=now,
        )
    )


def _revoke_session_for_refresh_reuse(
    db: Session,
    request: Request,
    *,
    session: AuthSession,
    reason: str,
    jti: str,
    route: Optional[str],
) -> None:
    """Révoque la session après reuse : ``revoked_at``, ``revoke_reason`` (tronqué 255), jti en spent.

    Ne modifie pas les lignes ``auth_refresh_tokens`` (historique conservé). Les access tokens déjà
    émis restent valides jusqu’à ``exp``.
    """
    session.revoked_at = _utcnow()
    session.revoke_reason = reason[:255]
    _spend_jti_safe(db, str(jti)[:64])
    logger.error(
        "refresh_token_reuse_detected",
        extra={
            "event": "refresh_token_reuse_detected",
            "admin_user_id": session.user_id,
            "session_id": str(session.id),
            "jti": _mask_jti(str(jti)),
            "route": route or "",
            "device_id": session.device_id,
            "reason": reason,
        },
    )
    _auth_audit(
        "auth.refresh.reuse_revokes_session",
        db=db,
        request=request,
        user_id=session.user_id,
        device_id=session.device_id,
        metadata={"reason": reason, "jti": _mask_jti(str(jti))},
        isolated=False,
    )


def _try_revoke_session_for_stale_rotated_jti(
    db: Session,
    request: Request,
    *,
    jti: str,
    header_device: str,
) -> bool:
    """Si le jti correspond à un refresh déjà rotaté, révoque la session et retourne True."""
    tok = (
        db.query(AuthRefreshToken)
        .filter(
            AuthRefreshToken.jti == str(jti)[:64],
            AuthRefreshToken.rotated_at.isnot(None),
        )
        .first()
    )
    if tok is None:
        return False
    sess = db.get(AuthSession, tok.session_id)
    if sess is not None and sess.revoked_at is None:
        sess.revoked_at = _utcnow()
        sess.revoke_reason = "refresh_token_reuse_detected"
        _spend_jti_safe(db, str(jti)[:64])
        logger.error(
            "refresh_token_reuse_detected",
            extra={
                "event": "refresh_token_reuse_detected",
                "admin_user_id": sess.user_id,
                "session_id": str(sess.id),
                "jti": _mask_jti(str(jti)),
                "route": request.url.path if request else "",
                "device_id": header_device,
                "reason": "stale_rotated_jti",
            },
        )
        _auth_audit(
            "auth.refresh.stale_jti_revokes_session",
            db=db,
            request=request,
            user_id=sess.user_id,
            device_id=sess.device_id,
            metadata={"jti": _mask_jti(str(jti))},
            isolated=False,
        )
        db.commit()
    else:
        db.commit()
    _note_failed_refresh(request)
    return True


def _try_revoke_session_for_sid_jti_mismatch(
    db: Session,
    request: Request,
    *,
    payload: Dict[str, Any],
    jti: str,
    sub_claim: Any,
    header_device: str,
) -> bool:
    """Si le JWT porte ``sid`` et que le ``jti`` ne correspond pas au ``refresh_jti`` courant
    de cette session (mais ``sub`` résolu = ``session.user_id``), traiter comme reuse stale /
    chaîne incomplète (ex. pas de ligne ``auth_refresh_tokens`` pour un ancien jti) et révoquer.

    Ne révoque pas si ``sub`` ne correspond pas à la session (JWT incohérent côté métier) :
    on laisse la branche ``unknown_jti`` / legacy.
    """
    sid_raw = payload.get("sid")
    if not sid_raw:
        return False
    try:
        sid = uuid.UUID(str(sid_raw))
    except (ValueError, TypeError, AttributeError):
        return False

    sess = db.get(AuthSession, sid)
    if sess is None or sess.revoked_at is not None:
        return False

    if str(sess.refresh_jti) == str(jti):
        return False

    try:
        user_res, _sub_typ, sub_kind = resolve_user_from_jwt_sub(
            db, str(sub_claim), record_metric=False
        )
    except NonUserJWTSubjectError:
        return False
    if user_res is None or sub_kind != "ok" or sess.user_id != user_res.id:
        return False

    _revoke_session_for_refresh_reuse(
        db,
        request,
        session=sess,
        reason="refresh_sid_jti_mismatch_or_stale",
        jti=str(jti),
        route=request.url.path if request else None,
    )
    db.commit()
    _note_failed_refresh(request)
    return True


def _issue_pair_for_session_row(
    *,
    user: AdminUser,
    device_id: str,
    refresh_jti: str,
    device_trust: Optional[str] = None,
    step_up_otp_required: bool = False,
    auth_strength: str = "password",
    session_uuid: Optional[uuid.UUID] = None,
    session_intel: Optional[Any] = None,
    security_incomplete: bool = False,
    account_state: Optional[str] = None,
    emit_context: str = "session",
    emit_route: Optional[str] = None,
) -> Dict[str, str]:
    from services.auth.jwt_user_claims import (
        build_user_jwt_access_base_claims,
        format_user_jwt_sub,
        log_jwt_subject_emitted,
    )

    lstup: Optional[int] = None
    strust: Optional[str] = None
    relock = False
    bio_hint = False
    if session_intel is not None:
        strust = getattr(session_intel, "session_trust_level", None)
        lu = getattr(session_intel, "last_step_up_at", None)
        if lu is not None:
            try:
                lstup = int(lu.timestamp())
            except Exception:  # noqa: BLE001
                lstup = None
        relock = bool(getattr(session_intel, "relock_required", False))
        auth_s = str(getattr(session_intel, "auth_strength", "") or "").lower()
        bio_hint = bool(getattr(session_intel, "relock_required", False)) and "passkey" not in auth_s

    token_data: Dict[str, Any] = build_user_jwt_access_base_claims(user)

    from services.auth.device_pr_d4_policy import (
        compute_device_binding_hash,
        device_access_jwt_binding_enabled,
    )

    did_h: Optional[str] = None
    if device_access_jwt_binding_enabled():
        did_h = compute_device_binding_hash(normalize_device_id(device_id))

    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        device_trust=device_trust or DEVICE_TRUST_UNKNOWN,
        step_up_otp_required=step_up_otp_required,
        auth_strength=auth_strength,
        session_id=str(session_uuid) if session_uuid else None,
        session_trust_level=strust,
        last_step_up_at_ts=lstup,
        relock_required=relock,
        biometric_hint=bio_hint,
        security_incomplete=security_incomplete,
        account_state=account_state,
        device_binding_hash=did_h,
    )
    refresh_token, _ = create_refresh_token(
        format_user_jwt_sub(user.id),
        device_id,
        jti=refresh_jti,
        sub_typ="user_id",
        session_id=str(session_uuid) if session_uuid else None,
        device_binding_hash=did_h,
    )
    log_jwt_subject_emitted(user=user, context=emit_context, route=emit_route)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "device_id": device_id,
    }


def issue_fresh_auth_session(
    *,
    db: Session,
    request: Request,
    user: AdminUser,
    device_header: Optional[str],
    success_event_type: str,
    success_metadata: Optional[Dict[str, Any]] = None,
    device_trust_level: str = DEVICE_TRUST_UNKNOWN,
    step_up_otp_required: bool = False,
    auth_strength: str = "password",
    attestation_parsed: Optional[Dict[str, Any]] = None,
    attestation_result: Optional[AttestationResult] = None,
) -> Dict[str, str]:
    """
    Crée une ligne ``auth_sessions`` + jetons access/refresh (Phase 2/3.1).
    Utilisé par login mot de passe, passkeys, ou tout facteur fort validé.
    """
    _assert_mobile_app_session_allowed(user)
    _assert_person_login_not_frozen(db, user)
    from services.security.device_reputation.device_reputation_service import (
        evaluate_auth_impact,
        is_device_reputation_enabled,
        record_device_usage,
        resolve_device_hash_from_request,
    )
    from services.security.login_auth_strategy_service import (
        enforce_login_strategy_or_raise,
        is_login_auth_strategy_enabled,
        merge_device_trust_for_session,
        merge_step_up_flags,
    )
    from services.security.login_device_trust_service import (
        is_login_device_trust_enabled,
        update_user_device_profile_on_login,
    )

    fp_meta, fp_hash = _fingerprint_from_request(request)
    if device_header and str(device_header).strip():
        device_id = normalize_device_id(device_header)
    else:
        device_id = f"srvtmp-{uuid.uuid4()}"
        logger.info(
            "auth.session.server_issued_device_id %s",
            {"user_id": user.id, "device_id": _mask_device(device_id)},
        )

    ip, ua = _client_meta(request)
    rep_meta: Dict[str, Any] = {}
    device_hash_ctx: Optional[str] = None
    if (
        is_device_reputation_enabled()
        or is_login_device_trust_enabled()
        or is_login_auth_strategy_enabled()
    ):
        device_hash_ctx = resolve_device_hash_from_request(request, device_id, fp_hash)

    if is_device_reputation_enabled() and device_hash_ctx:
        blocked, su_rep, rep_meta = evaluate_auth_impact(db, device_hash_ctx, user_id=user.id)
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "DEVICE_REPUTATION_BLOCKED",
                    "message": "Appareil exclu par la politique de réputation.",
                },
            )
        step_up_otp_required = bool(step_up_otp_required) or su_rep

    effective_trust_level = device_trust_level
    strat: Optional[Any] = None
    if is_login_auth_strategy_enabled():
        att_ok = bool(attestation_result and attestation_result.is_valid)
        strat = enforce_login_strategy_or_raise(
            db,
            request,
            user,
            device_header=device_header,
            attestation_trusted=att_ok,
            persist_action="auth.session.issue_strategy",
            login_channel="session_refresh",
            login_identifier=(
                {"kind": "email", "value": str(user.email).strip().lower()}
                if getattr(user, "email", None)
                else None
            ),
        )
        step_up_otp_required = merge_step_up_flags(step_up_otp_required, strat.step_up_required)
        effective_trust_level = merge_device_trust_for_session(device_trust_level, strat.session_trust_flag)

    fraud_meta_extra: Dict[str, Any] = {}
    try:
        from services.security.device_reputation.device_reputation_service import (
            resolve_device_hash_from_request,
        )
        from services.security.ml.login_fraud_evaluator import (
            evaluate_login_fraud_risk,
            is_login_fraud_evaluation_enabled,
            merge_step_up_from_login_fraud,
            metadata_for_security_event,
        )

        if is_login_fraud_evaluation_enabled():
            dh_fraud = device_hash_ctx or resolve_device_hash_from_request(request, device_id, fp_hash)
            if dh_fraud:
                fraud_eval = evaluate_login_fraud_risk(
                    db,
                    user.id,
                    device_hash=dh_fraud,
                    ip=ip,
                    session_id=None,
                )
                step_up_otp_required = merge_step_up_from_login_fraud(
                    bool(step_up_otp_required),
                    fraud_eval,
                )
                fraud_meta_extra = metadata_for_security_event(fraud_eval)
    except Exception as exc:  # noqa: BLE001 — ne pas bloquer l’émission de session
        logger.warning("login_fraud evaluation skipped user=%s: %s", user.id, exc)

    jti = str(uuid.uuid4())
    expires_at = _utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    row_kw: Dict[str, Any] = dict(
        user_id=user.id,
        device_id=device_id,
        refresh_jti=jti,
        expires_at=expires_at,
        ip_address=ip,
        user_agent=ua,
    )
    if is_device_fingerprint_enabled() and fp_hash:
        row_kw["fingerprint_hash"] = fp_hash
        row_kw["fingerprint_metadata"] = fp_meta
    row_kw["device_trust_level"] = effective_trust_level
    row_kw["step_up_otp_required"] = step_up_otp_required
    row_kw["auth_strength"] = auth_strength
    if attestation_result and attestation_result.is_valid:
        row_kw["attestation_type"] = attestation_result.attestation_type
        row_kw["attestation_verified_at"] = _utcnow()
        row_kw["attestation_metadata"] = attestation_result.metadata
    cred_bound = (
        db.query(AuthDeviceCredential)
        .filter(
            AuthDeviceCredential.user_id == user.id,
            AuthDeviceCredential.device_id == device_id,
            AuthDeviceCredential.revoked_at.is_(None),
            AuthDeviceCredential.attestation_bound_at.isnot(None),
        )
        .first()
    ) is not None
    from services.auth.device_attestation_trust import compute_attestation_trust_level

    row_kw["device_attestation_tier"] = compute_attestation_trust_level(
        attestation_verified_at=row_kw.get("attestation_verified_at"),
        attestation_type=row_kw.get("attestation_type"),
        attestation_metadata=row_kw.get("attestation_metadata") or {},
        credential_has_attestation_bound=cred_bound,
        attestation_result=attestation_result,
    )
    row = AuthSession(**row_kw)
    db.add(row)
    db.flush()
    _register_auth_refresh_token_row(db, session_id=row.id, jti=jti)
    if attestation_result and attestation_result.is_valid and attestation_parsed:
        finalize_successful_attestation(db, attestation_parsed)
    if device_hash_ctx:
        record_device_usage(
            db,
            device_hash=device_hash_ctx,
            user_id=user.id,
            event_type="auth.session.opened",
            ip_address=ip,
            session_id=row.id,
        )
    meta = dict(success_metadata or {})
    meta.update(rep_meta)
    meta.update(fraud_meta_extra)
    try:
        ad = (strat.context or {}).get("adaptive_decision") if strat else None
        if isinstance(ad, dict):
            meta["orchestrator_ui_variant"] = ad.get("ui_variant")
            meta["orchestrator_local_biometric_recommended"] = ad.get("local_biometric_recommended")
            meta["orchestrator_auth_strength_target"] = ad.get("auth_strength_target")
            meta["orchestrator_session_trust_target"] = ad.get("session_trust_target")
    except Exception:  # noqa: BLE001
        pass
    meta.setdefault("fingerprint_present", bool(fp_hash))
    meta.setdefault("device_trust_level", effective_trust_level)
    meta.setdefault("step_up_otp_required", step_up_otp_required)

    def _country_hdr() -> Optional[str]:
        for h in ("cf-ipcountry", "CF-IPCountry", "x-geo-country", "X-Geo-Country"):
            v = request.headers.get(h)
            if v and str(v).strip():
                return str(v).strip()[:8]
        return None

    if is_login_device_trust_enabled() and device_hash_ctx:
        update_user_device_profile_on_login(
            db,
            user=user,
            device_hash=device_hash_ctx,
            device_id_normalized=device_id,
            fingerprint_hash=fp_hash,
            ip_address=ip,
            country_code=_country_hdr(),
            success=True,
            auth_strength=auth_strength,
            attestation_level=(attestation_result.trust_level if attestation_result else None),
            attestation_trusted=bool(attestation_result and attestation_result.is_valid),
        )

    intel_row: Optional[Any] = None
    try:
        from services.security.session_intelligence_service import (
            initialize_session_intelligence,
            is_session_intelligence_enabled,
        )

        if is_session_intelligence_enabled():
            orch: Dict[str, Any] = {}
            try:
                if strat is not None:
                    ctx = getattr(strat, "context", None) or {}
                    ad = ctx.get("adaptive_decision") if isinstance(ctx, dict) else None
                    if isinstance(ad, dict):
                        orch = ad
            except Exception:  # noqa: BLE001
                orch = {}
            intel_row = initialize_session_intelligence(db, row, orchestrator_decision=orch or None)
    except Exception as exc:  # noqa: BLE001
        logger.warning("session intelligence init skipped: %s", exc)

    # PeClient pour toute Person (bootstrap + profil mobile, y compris session PARTIAL / sec_inc).
    if getattr(user, "person_id", None) is not None:
        _ensure_pe_client_for_login_user_best_effort(db, user)

    partial = should_issue_partial_session_for_mobile_app(db, user)
    acct_st = derive_account_state(db, user)
    persist_person_account_state_column(db, user, acct_st)
    if partial:
        meta["security_incomplete"] = True
    else:
        _assert_portfolio_customer_for_app_jwt(db, user)

    _auth_audit(
        success_event_type,
        db=db,
        request=request,
        user_id=user.id,
        device_id=device_id,
        metadata=meta,
        isolated=False,
    )
    db.commit()
    db.refresh(row)
    return _issue_pair_for_session_row(
        user=user,
        device_id=device_id,
        refresh_jti=jti,
        device_trust=effective_trust_level,
        step_up_otp_required=step_up_otp_required,
        auth_strength=auth_strength,
        session_uuid=row.id,
        session_intel=intel_row,
        security_incomplete=partial,
        account_state=acct_st,
        emit_context="issue_fresh_auth_session",
        emit_route=request.url.path if request else None,
    )


def perform_login(
    *,
    db: Session,
    request: Request,
    email: str,
    password: str,
    device_header: Optional[str],
    attest_header: Optional[str] = None,
) -> Dict[str, str]:
    device_id = normalize_device_id(device_header)
    parsed = parse_x_device_attestation_header(attest_header) if attest_header else None
    att_res: Optional[AttestationResult] = None
    trust_level = DEVICE_TRUST_UNKNOWN
    step_up = False
    from services.auth.device_attestation_pr_e_policy import device_attestation_required_login

    login_requires_attest = bool(
        device_attestation_required_login() and device_id != LEGACY_UNKNOWN_DEVICE
    )
    if login_requires_attest and (not attest_header or not str(attest_header).strip()):
        logger.info(
            "device_attestation_required",
            extra={
                "event": "device_attestation_required",
                "context": "login",
                "device_prefix": device_id[:12],
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "device_attestation_required",
                "message": "X-Device-Attestation required for login (policy).",
            },
        )

    if is_device_attestation_enabled() or login_requires_attest:
        att_res, trust_level, step_up = evaluate_header_for_auth(
            db=db,
            request_device_id=device_id,
            attestation_header_raw=attest_header,
            legacy_unknown_label=LEGACY_UNKNOWN_DEVICE,
        )
        if login_requires_attest and (att_res is None or not att_res.is_valid):
            logger.info(
                "device_attestation_required",
                extra={
                    "event": "device_attestation_required",
                    "context": "login_invalid",
                    "device_prefix": device_id[:12],
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "device_attestation_required",
                    "message": "Valid device attestation required for login.",
                },
            )
        if att_res is not None and not att_res.is_valid:
            _auth_audit(
                "auth.device.attestation_failed",
                db=None,
                request=request,
                user_id=None,
                device_id=device_id,
                metadata={
                    "risk_flags": att_res.risk_flags,
                    "trust_level": att_res.trust_level,
                },
                isolated=True,
            )
            if fail_blocks_login():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "DEVICE_ATTESTATION_FAILED",
                        "step_up": True,
                        "otp_login_path": "/auth/login/email-otp/start",
                    },
                )

    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        _auth_audit(
            "auth.login.failed",
            db=None,
            request=request,
            user_id=None,
            device_id=device_id,
            metadata={"email_domain": email.split("@")[-1] if "@" in email else None},
            isolated=True,
        )
        from services.security.device_reputation.device_reputation_service import (
            is_device_reputation_enabled,
            record_device_usage,
            resolve_device_hash_from_request,
        )

        if is_device_reputation_enabled():
            fp_meta_fail, fp_hash_fail = _fingerprint_from_request(request)
            dh_fail = resolve_device_hash_from_request(request, device_id, fp_hash_fail)
            lip, _ = _client_meta(request)
            record_device_usage(
                None,
                device_hash=dh_fail,
                user_id=None,
                event_type="auth.login.failed",
                ip_address=lip,
                session_id=None,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _assert_user_not_security_locked(user)

    auth_strength = "password+attestation" if (att_res is not None and att_res.is_valid) else "password"
    return issue_fresh_auth_session(
        db=db,
        request=request,
        user=user,
        device_header=device_header,
        success_event_type="auth.login.succeeded",
        success_metadata={"attestation_valid": att_res.is_valid if att_res else None},
        device_trust_level=trust_level,
        step_up_otp_required=step_up,
        auth_strength=auth_strength,
        attestation_parsed=parsed,
        attestation_result=att_res,
    )


def _reject_refresh(
    db: Session,
    request: Request,
    reason: str,
    *,
    user_id: Optional[int] = None,
    device_id: Optional[str] = None,
    **ctx: Any,
) -> None:
    _auth_audit(
        "auth.refresh.rejected",
        db=None,
        request=request,
        user_id=user_id,
        device_id=device_id or "",
        metadata={"reason": reason, **ctx},
        isolated=True,
    )


def perform_refresh(
    *,
    db: Session,
    request: Request,
    refresh_token: str,
    device_header: Optional[str],
    attest_header: Optional[str] = None,
) -> Dict[str, str]:
    """Émet une nouvelle paire access/refresh si le jeton de renouvellement est valide.

    **Branche principale** (session résolue par ``AuthSession.refresh_jti == claim jti``,
    ``revoked_at`` vide) — ordre garantissant l’absence de fenêtre « claim après rotation » :

    1. Décoder le JWT refresh (signature, ``exp``, claims obligatoires).
    2. Charger ``AuthSession`` par ``refresh_jti`` + non révoquée ; contrôles device, expiration,
       utilisateur, politiques, attestation, réputation, etc.
    3. ``claim_refresh_jti`` : INSERT atomique dans ``auth_spent_refresh_jti`` ; échec =
       reuse parallèle → ``_revoke_session_for_refresh_reuse`` (raison
       ``refresh_token_reuse_parallel``) puis commit.
    4. Rotation : ``_rotate_auth_refresh_token_chain``, ``session.refresh_jti`` ← nouveau jti,
       métadonnées session.
    5. ``db.commit`` — la persistance n’a lieu qu’après un claim réussi.

    Concurrence : deux refresh avec le **même** jti aboutissent à un seul ``claim_refresh_jti``
    réussi ; l’autre voit le jti déjà en ``auth_spent_refresh_jti`` → reuse parallèle.

    **Sans ligne session pour ce jti** : d’abord reuse « stale » via ``auth_refresh_tokens``
    (jti déjà rotaté), puis si le JWT contient ``sid`` et ``sub`` cohérents avec la session mais
    ``jti != session.refresh_jti`` → ``_try_revoke_session_for_sid_jti_mismatch`` (chaîne incomplète
    ou ancien jeton rejoué). Un refresh **sans** claim ``sid`` (émissions pré-chaîne) ne peut pas
    emprunter ce durcissement : on retombe sur legacy Phase 1 ou 401 ``unknown_jti``.

    **Sémantique « session révoquée »** : ``auth_sessions.revoked_at`` non NULL et
    ``auth_sessions.revoke_reason`` renseigné (pas de colonne ``status`` dédiée). Tout refresh
    ultérieur pour cette session est refusé. Les access tokens déjà émis restent utilisables jusqu’à
    leur ``exp`` (TTL court).

    **PR B — device binding** : appareil effectif = en-tête ``X-Device-ID`` s’il n’est pas
    ``legacy-unknown``, sinon ``did`` / ``device_id`` du JWT. Migrations : ``legacy-unknown`` ou
    ``srvtmp-*`` (bootstrap) → premier ID client réel (une fois) ; matrice détaillée dans
    ``docs/PR_B_DEVICE_BINDING.md``. Conflit jwt/header (hors promotion srvtmp) ou mismatch
    session/effectif : ``device_mismatch_detected``, révocation, 401.
    """
    fp_meta, fp_hash = _fingerprint_from_request(request)
    payload = try_decode_refresh_token(refresh_token)
    if not payload:
        _reject_refresh(db, request, "invalid_token")
        _note_failed_refresh(request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if not _jwt_refresh_device_claims_consistent(payload):
        _reject_refresh(
            db,
            request,
            "jwt_device_claims_conflict",
            jti=_mask_jti(str(payload.get("jti") or "")),
        )
        _note_failed_refresh(request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    sub_claim = payload.get("sub")
    jti = payload.get("jti")
    if sub_claim is None or str(sub_claim).strip() == "" or not jti:
        _reject_refresh(db, request, "missing_claims")
        _note_failed_refresh(request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    header_device = normalize_device_id(device_header)
    effective_device = _effective_device_for_refresh(header_device, payload)

    from services.auth.device_pr_d4_policy import enforce_device_binding_hash_if_present

    try:
        enforce_device_binding_hash_if_present(payload=payload, device_id_for_binding=effective_device)
    except HTTPException as exc:
        _note_failed_refresh(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=getattr(exc, "detail", "device binding failed"),
        ) from exc

    ip, ua = _client_meta(request)

    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.refresh_jti == str(jti),
            AuthSession.revoked_at.is_(None),
        )
        .first()
    )

    if session:
        if session.expires_at < _utcnow():
            _reject_refresh(db, request, "session_expired", user_id=session.user_id, device_id=session.device_id)
            _note_failed_refresh(request)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

        # Conflit en-tête vs JWT (deux identités non-placeholder différentes) — sauf promotion srvtmp → client.
        if header_device != LEGACY_UNKNOWN_DEVICE:
            jw_raw = payload.get("did") or payload.get("device_id")
            if jw_raw is not None:
                jw_n = normalize_device_id(str(jw_raw))
                if (
                    jw_n != LEGACY_UNKNOWN_DEVICE
                    and jw_n != header_device
                    and not _is_srvtmp_to_client_promotion(jw_n, header_device)
                ):
                    logger.error(
                        "device_mismatch_detected",
                        extra={
                            "event": "device_mismatch_detected",
                            "admin_user_id": session.user_id,
                            "session_id": str(session.id),
                            "expected_device_id": _mask_device(jw_n),
                            "received_device_id": _mask_device(header_device),
                            "route": request.url.path if request else "",
                            "reason": "jwt_vs_header_conflict",
                        },
                    )
                    _revoke_session_for_refresh_reuse(
                        db,
                        request,
                        session=session,
                        reason="device_jwt_header_conflict",
                        jti=str(jti),
                        route=request.url.path if request else None,
                    )
                    db.commit()
                    _note_failed_refresh(request)
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device mismatch")

        bind_out = _apply_pr_b_device_binding(
            db,
            request,
            session=session,
            effective_device=effective_device,
            jti=str(jti),
            route=request.url.path if request else None,
        )
        if bind_out == "revoked":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device mismatch")

        # PR D2 — fraîcheur attestation (optionnel) + signature ECDSA refresh si credential enregistré.
        from services.auth.device_security_pr_d2 import (
            check_attestation_freshness_or_raise,
            enforce_refresh_device_signature_if_configured,
        )

        try:
            check_attestation_freshness_or_raise(session=session)
        except HTTPException:
            _note_failed_refresh(request)
            raise
        try:
            enforce_refresh_device_signature_if_configured(
                db=db,
                request=request,
                session=session,
                refresh_token=refresh_token,
                normalized_session_device_id=normalize_device_id(session.device_id),
            )
        except HTTPException:
            _note_failed_refresh(request)
            raise

        from services.auth.device_attestation_pr_e_policy import (
            device_attestation_required_refresh,
            enforce_refresh_attestation_on_level_3,
            refresh_attestation_max_age_sec,
        )
        from services.auth.device_attestation_trust import is_attestation_stale

        refresh_need_attest = device_attestation_required_refresh() or (
            enforce_refresh_attestation_on_level_3()
            and is_attestation_stale(
                attestation_verified_at=session.attestation_verified_at,
                max_age_sec=refresh_attestation_max_age_sec(),
            )
        )
        if refresh_need_attest:
            if not attest_header or not str(attest_header).strip():
                logger.info(
                    "device_attestation_required",
                    extra={
                        "event": "device_attestation_required",
                        "context": "refresh",
                        "user_id": session.user_id,
                    },
                )
                _note_failed_refresh(request)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "device_attestation_required",
                        "message": "Fresh X-Device-Attestation required for refresh.",
                    },
                )
            parsed_ra = parse_x_device_attestation_header(attest_header)
            if not parsed_ra:
                _note_failed_refresh(request)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "device_attestation_required",
                        "message": "Invalid attestation payload on refresh.",
                    },
                )
            att_res_ra, _, _ = evaluate_header_for_auth(
                db=db,
                request_device_id=header_device,
                attestation_header_raw=attest_header,
                legacy_unknown_label=LEGACY_UNKNOWN_DEVICE,
            )
            if att_res_ra is None or not att_res_ra.is_valid:
                _note_failed_refresh(request)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "device_attestation_required",
                        "message": "Attestation verification failed on refresh.",
                    },
                )

        prev_ip = session.ip_address
        prev_fp = session.fingerprint_hash

        if ip and session.ip_address and session.ip_address != ip:
            _auth_audit(
                "auth.session.ip_changed",
                db=db,
                request=request,
                user_id=session.user_id,
                device_id=session.device_id,
                metadata={"old_ip": _mask_ip(session.ip_address), "new_ip": _mask_ip(ip)},
                isolated=False,
            )

        if (
            is_device_fingerprint_enabled()
            and fp_hash
            and session.fingerprint_hash
            and fp_hash != session.fingerprint_hash
        ):
            logger.info(
                "auth.device.fingerprint_changed %s",
                {
                    "user_id": session.user_id,
                    "device": _mask_device(session.device_id),
                },
            )
            _auth_audit(
                "auth.device.fingerprint_changed",
                db=db,
                request=request,
                user_id=session.user_id,
                device_id=session.device_id,
                metadata={"old_fp_prefix": session.fingerprint_hash[:12], "new_fp_prefix": fp_hash[:12]},
                isolated=False,
            )

        _lu = session.last_used_at
        if _lu is not None:
            delta = (_utcnow() - _lu).total_seconds()
            if 0 <= delta < 2.0:
                _auth_audit(
                    "auth.refresh.rapid_burst",
                    db=db,
                    request=request,
                    user_id=session.user_id,
                    device_id=session.device_id,
                    metadata={"delta_sec": round(delta, 3)},
                    isolated=False,
                )

        if (is_device_attestation_enabled() or refresh_need_attest) and attest_header:
            parsed = parse_x_device_attestation_header(attest_header)
            if parsed:
                att_res, trust, step_up = evaluate_header_for_auth(
                    db=db,
                    request_device_id=header_device,
                    attestation_header_raw=attest_header,
                    legacy_unknown_label=LEGACY_UNKNOWN_DEVICE,
                )
                if att_res is not None and not att_res.is_valid:
                    _auth_audit(
                        "auth.device.attestation_failed",
                        db=db,
                        request=request,
                        user_id=session.user_id,
                        device_id=session.device_id,
                        metadata={"context": "refresh", "risk_flags": att_res.risk_flags},
                        isolated=False,
                    )
                    if fail_blocks_login():
                        _reject_refresh(
                            db,
                            request,
                            "attestation_failed",
                            user_id=session.user_id,
                            device_id=session.device_id,
                        )
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail={
                                "code": "DEVICE_ATTESTATION_FAILED",
                                "step_up": True,
                                "otp_login_path": "/auth/login/email-otp/start",
                            },
                        )
                session.device_trust_level = trust
                session.step_up_otp_required = bool(step_up)
                if att_res and att_res.is_valid:
                    session.attestation_type = att_res.attestation_type
                    session.attestation_verified_at = _utcnow()
                    session.attestation_metadata = att_res.metadata
                    finalize_successful_attestation(db, parsed)
                    cred_b = (
                        db.query(AuthDeviceCredential)
                        .filter(
                            AuthDeviceCredential.user_id == session.user_id,
                            AuthDeviceCredential.device_id == session.device_id,
                            AuthDeviceCredential.revoked_at.is_(None),
                            AuthDeviceCredential.attestation_bound_at.isnot(None),
                        )
                        .first()
                    ) is not None
                    from services.auth.device_attestation_trust import compute_attestation_trust_level as _tier_login

                    session.device_attestation_tier = _tier_login(
                        attestation_verified_at=session.attestation_verified_at,
                        attestation_type=session.attestation_type,
                        attestation_metadata=dict(session.attestation_metadata or {}),
                        credential_has_attestation_bound=cred_b,
                        attestation_result=att_res,
                    )

        user = db.get(AdminUser, session.user_id)
        if user is None:
            _reject_refresh(db, request, "user_missing", user_id=session.user_id, device_id=session.device_id)
            _note_failed_refresh(request)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer valid")
        try:
            _assert_mobile_app_session_allowed(user)
        except HTTPException:
            _reject_refresh(db, request, "mobile_app_not_allowed", user_id=user.id, device_id=session.device_id)
            _note_failed_refresh(request)
            raise
        try:
            _assert_refresh_allowed(db, user)
        except HTTPException:
            _reject_refresh(db, request, "security_refresh_blocked", user_id=user.id, device_id=session.device_id)
            raise

        if getattr(user, "person_id", None) is not None:
            _ensure_pe_client_for_login_user_best_effort(db, user)

        partial = should_issue_partial_session_for_mobile_app(db, user)
        acct_rf = derive_account_state(db, user)
        if not partial:
            try:
                _assert_portfolio_customer_for_app_jwt(db, user)
            except HTTPException:
                _reject_refresh(
                    db,
                    request,
                    "portfolio_customer_required",
                    user_id=user.id,
                    device_id=session.device_id,
                )
                _note_failed_refresh(request)
                raise

        from services.security.device_reputation.device_reputation_service import (
            evaluate_auth_impact,
            is_device_reputation_enabled,
            record_device_usage,
            resolve_device_hash_from_request,
        )

        rep_meta_refresh: Dict[str, Any] = {}
        dh_refresh: Optional[str] = None
        if is_device_reputation_enabled():
            dh_refresh = resolve_device_hash_from_request(request, header_device, fp_hash)
            blocked_r, su_rep_r, rep_meta_refresh = evaluate_auth_impact(db, dh_refresh, user_id=user.id)
            if blocked_r:
                session.revoked_at = _utcnow()
                session.revoke_reason = "device_reputation_blocked"
                _spend_jti_safe(db, str(jti))
                _auth_audit(
                    "auth.refresh.rejected",
                    db=db,
                    request=request,
                    user_id=user.id,
                    device_id=session.device_id,
                    metadata={"reason": "device_reputation_blocked", **rep_meta_refresh},
                    isolated=False,
                )
                db.commit()
                _note_failed_refresh(request)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "DEVICE_REPUTATION_BLOCKED",
                        "message": "Appareil exclu par la politique de réputation.",
                    },
                )
            session.step_up_otp_required = bool(session.step_up_otp_required) or su_rep_r

        if not claim_refresh_jti(db, str(jti)):
            _reject_refresh(
                db,
                request,
                "refresh_token_reuse",
                user_id=session.user_id,
                device_id=session.device_id,
                jti=_mask_jti(str(jti)),
            )
            _revoke_session_for_refresh_reuse(
                db,
                request,
                session=session,
                reason="refresh_token_reuse_parallel",
                jti=str(jti),
                route=request.url.path if request else None,
            )
            db.commit()
            _note_failed_refresh(request)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected")

        from services.security.zero_trust.continuous_auth import maybe_require_step_up_after_refresh_signals

        ip_changed = bool(ip and prev_ip and prev_ip != ip)
        fp_changed = bool(
            is_device_fingerprint_enabled()
            and fp_hash
            and prev_fp
            and fp_hash != prev_fp
        )
        maybe_require_step_up_after_refresh_signals(
            session=session,
            ip_changed=ip_changed,
            fingerprint_changed=fp_changed,
        )

        new_jti = str(uuid.uuid4())
        _rotate_auth_refresh_token_chain(db, session=session, old_jti=str(jti), new_jti=new_jti)
        session.refresh_jti = new_jti
        session.last_used_at = _utcnow()
        session.expires_at = _utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        session.ip_address = ip or session.ip_address
        session.user_agent = ua or session.user_agent
        if is_device_fingerprint_enabled() and fp_hash:
            session.fingerprint_hash = fp_hash
            session.fingerprint_metadata = fp_meta

        if dh_refresh:
            record_device_usage(
                db,
                device_hash=dh_refresh,
                user_id=user.id,
                event_type="auth.refresh.succeeded",
                ip_address=ip,
                session_id=session.id,
            )

        refresh_fraud_meta: Dict[str, Any] = {}
        try:
            from services.security.ml.login_fraud_evaluator import (
                evaluate_refresh_fraud_risk,
                is_login_fraud_evaluation_enabled,
                merge_step_up_from_login_fraud,
                metadata_for_security_event,
            )

            if is_login_fraud_evaluation_enabled() and dh_refresh:
                rev_eval = evaluate_refresh_fraud_risk(
                    db,
                    user.id,
                    device_hash=dh_refresh,
                    ip=ip,
                    session_id=session.id,
                )
                session.step_up_otp_required = merge_step_up_from_login_fraud(
                    bool(getattr(session, "step_up_otp_required", False)),
                    rev_eval,
                )
                refresh_fraud_meta = metadata_for_security_event(rev_eval)
        except Exception as exc:  # noqa: BLE001
            logger.warning("refresh fraud eval skipped user=%s: %s", user.id, exc)

        _auth_audit(
            "auth.refresh.succeeded",
            db=db,
            request=request,
            user_id=user.id,
            device_id=session.device_id,
            metadata={"jti": _mask_jti(new_jti), **rep_meta_refresh, **refresh_fraud_meta},
            isolated=False,
        )
        from services.security.zero_trust.continuous_auth import reevaluate_security_on_critical_action

        reevaluate_security_on_critical_action(user_id=user.id, action="auth.refresh")

        intel_refresh: Optional[Any] = None
        try:
            from services.security.session_intelligence_service import (
                is_session_intelligence_enabled,
                sync_session_row_from_intelligence,
                update_session_intelligence_on_request,
            )

            if is_session_intelligence_enabled():
                intel_refresh = update_session_intelligence_on_request(
                    db,
                    session,
                    request,
                    fingerprint_changed=fp_changed,
                    ip_changed=ip_changed,
                )
                sync_session_row_from_intelligence(session, intel_refresh)
        except Exception as exc:  # noqa: BLE001
            logger.warning("session intelligence on refresh: %s", exc)

        db.commit()

        logger.debug(
            "refresh_token_rotated",
            extra={
                "event": "refresh_token_rotated",
                "admin_user_id": user.id,
                "session_id": str(session.id),
                "jti": _mask_jti(new_jti),
                "route": request.url.path if request else "",
                "device_id": session.device_id,
            },
        )

        return _issue_pair_for_session_row(
            user=user,
            device_id=session.device_id,
            refresh_jti=new_jti,
            device_trust=getattr(session, "device_trust_level", None) or DEVICE_TRUST_UNKNOWN,
            step_up_otp_required=bool(getattr(session, "step_up_otp_required", False)),
            auth_strength=getattr(session, "auth_strength", None) or "password",
            session_uuid=session.id,
            session_intel=intel_refresh,
            security_incomplete=partial,
            account_state=acct_rf,
            emit_context="perform_refresh_session",
            emit_route=request.url.path if request else None,
        )

    if _try_revoke_session_for_stale_rotated_jti(
        db, request, jti=str(jti), header_device=header_device
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected",
        )

    if _try_revoke_session_for_sid_jti_mismatch(
        db,
        request,
        payload=payload,
        jti=str(jti),
        sub_claim=sub_claim,
        header_device=header_device,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected",
        )

    # Pas de ligne session : jeton Phase 1 (sans did/device_id) ou jti inconnu
    if _jwt_has_device_binding_claims(payload):
        _reject_refresh(db, request, "unknown_jti", device_id=header_device, jti=_mask_jti(str(jti)))
        _note_failed_refresh(request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    try:
        user, _sub_typ, sub_kind = resolve_user_from_jwt_sub(db, str(sub_claim), record_metric=True)
    except NonUserJWTSubjectError:
        _reject_refresh(
            db,
            request,
            "legacy_refresh_non_user_sub",
            email=str(sub_claim)[:128],
            device_id=header_device,
        )
        _note_failed_refresh(request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer valid") from None

    if user is None or sub_kind != "ok":
        _reject_refresh(
            db,
            request,
            "legacy_user_missing",
            email=str(sub_claim)[:128],
            device_id=header_device,
        )
        _note_failed_refresh(request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer valid")

    sc = str(sub_claim)[:128]
    logger.debug(
        "jwt_subject_resolution",
        extra={
            "sub": sc,
            "sub_typ": _sub_typ,
            "sub_format": classify_sub_format(sc),
            "resolved_user_id": user.id,
            "route": request.url.path,
            "context": "refresh_legacy_phase1",
        },
    )

    try:
        _assert_mobile_app_session_allowed(user)
    except HTTPException:
        _reject_refresh(db, request, "mobile_app_not_allowed", user_id=user.id, device_id=header_device)
        _note_failed_refresh(request)
        raise
    try:
        _assert_refresh_allowed(db, user)
    except HTTPException:
        _reject_refresh(db, request, "security_refresh_blocked", user_id=user.id, device_id=header_device)
        raise

    if getattr(user, "person_id", None) is not None:
        _ensure_pe_client_for_login_user_best_effort(db, user)

    partial_leg = should_issue_partial_session_for_mobile_app(db, user)
    acct_leg = derive_account_state(db, user)
    if not partial_leg:
        try:
            _assert_portfolio_customer_for_app_jwt(db, user)
        except HTTPException:
            _reject_refresh(
                db,
                request,
                "portfolio_customer_required",
                user_id=user.id,
                device_id=header_device,
            )
            _note_failed_refresh(request)
            raise

    from services.security.device_reputation.device_reputation_service import (
        evaluate_auth_impact,
        is_device_reputation_enabled,
        record_device_usage,
        resolve_device_hash_from_request,
    )

    rep_meta_leg: Dict[str, Any] = {}
    dh_leg: Optional[str] = None
    su_rep_l = False
    if is_device_reputation_enabled():
        dh_leg = resolve_device_hash_from_request(request, effective_device, fp_hash)
        blocked_l, su_rep_l, rep_meta_leg = evaluate_auth_impact(db, dh_leg, user_id=user.id)
        if blocked_l:
            _reject_refresh(
                db,
                request,
                "device_reputation_blocked",
                user_id=user.id,
                device_id=effective_device,
                **rep_meta_leg,
            )
            _note_failed_refresh(request)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "DEVICE_REPUTATION_BLOCKED",
                    "message": "Appareil exclu par la politique de réputation.",
                },
            )

    if not claim_refresh_jti(db, str(jti)):
        _reject_refresh(
            db,
            request,
            "legacy_refresh_reuse",
            device_id=effective_device,
            jti=_mask_jti(str(jti)),
        )
        db.rollback()
        _note_failed_refresh(request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected")

    new_jti = str(uuid.uuid4())
    expires_at = _utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    leg_kw: Dict[str, Any] = dict(
        user_id=user.id,
        device_id=effective_device,
        refresh_jti=new_jti,
        expires_at=expires_at,
        ip_address=ip,
        user_agent=ua,
        device_trust_level=DEVICE_TRUST_UNKNOWN,
        step_up_otp_required=bool(su_rep_l),
        auth_strength="password",
    )
    if is_device_fingerprint_enabled() and fp_hash:
        leg_kw["fingerprint_hash"] = fp_hash
        leg_kw["fingerprint_metadata"] = fp_meta
    row = AuthSession(**leg_kw)
    db.add(row)
    db.flush()
    _register_auth_refresh_token_row(db, session_id=row.id, jti=new_jti)
    if dh_leg:
        record_device_usage(
            db,
            device_hash=dh_leg,
            user_id=user.id,
            event_type="auth.refresh.succeeded",
            ip_address=ip,
            session_id=row.id,
        )
    _auth_audit(
        "auth.refresh.succeeded",
        db=db,
        request=request,
        user_id=user.id,
        device_id=effective_device,
        metadata={"legacy_upgrade": True, "jti": _mask_jti(new_jti), **rep_meta_leg},
        isolated=False,
    )

    db.commit()

    logger.debug(
        "refresh_token_rotated",
        extra={
            "event": "refresh_token_rotated",
            "admin_user_id": user.id,
            "session_id": str(row.id),
            "jti": _mask_jti(new_jti),
            "route": request.url.path if request else "",
            "device_id": effective_device,
            "legacy_upgrade": True,
        },
    )
    logger.info(
        "auth.refresh.legacy_upgrade %s",
        {"user_id": user.id, "device": _mask_device(effective_device)},
    )
    return _issue_pair_for_session_row(
        user=user,
        device_id=effective_device,
        refresh_jti=new_jti,
        device_trust=DEVICE_TRUST_UNKNOWN,
        step_up_otp_required=bool(su_rep_l),
        auth_strength="password",
        session_uuid=row.id,
        security_incomplete=partial_leg,
        account_state=acct_leg,
        emit_context="perform_refresh_legacy_phase1",
        emit_route=request.url.path if request else None,
    )


def perform_revoke(
    *,
    db: Session,
    request: Optional[Request],
    refresh_token: str,
    device_header: Optional[str],
) -> None:
    """Révoque la session — même règle d’« appareil effectif » que le refresh (JWT ``did`` si en-tête absent)."""
    payload = try_decode_refresh_token(refresh_token)
    if not payload:
        return
    jti = payload.get("jti")
    if not jti:
        return
    if not _jwt_refresh_device_claims_consistent(payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    normalized_header = normalize_device_id(device_header)
    if normalized_header != LEGACY_UNKNOWN_DEVICE:
        for _k in ("did", "device_id"):
            raw = payload.get(_k)
            if raw is None:
                continue
            jw_n = normalize_device_id(str(raw))
            if jw_n == normalized_header:
                continue
            if _is_srvtmp_to_client_promotion(jw_n, normalized_header):
                continue
            _auth_audit(
                "auth.device.mismatch",
                db=None,
                request=request,
                user_id=None,
                device_id=normalized_header,
                metadata={
                    "context": "revoke_claim_vs_header",
                    "claim_key": _k,
                    "claim_device": _mask_device(str(raw)),
                    "jti": _mask_jti(str(jti)),
                },
                isolated=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Device mismatch",
            )

    effective_device = _effective_device_for_refresh(normalized_header, payload)
    if effective_device == LEGACY_UNKNOWN_DEVICE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Device-ID or refresh device claims required",
        )

    session = (
        db.query(AuthSession)
        .filter(AuthSession.refresh_jti == str(jti))
        .first()
    )
    now = _utcnow()
    if session and session.revoked_at is None:
        if not _session_matches_effective_for_revoke(session, effective_device, payload):
            _auth_audit(
                "auth.device.mismatch",
                db=None,
                request=request,
                user_id=session.user_id,
                device_id=effective_device,
                metadata={
                    "context": "revoke",
                    "session_device": _mask_device(session.device_id),
                    "effective_device": _mask_device(effective_device),
                    "jti": _mask_jti(str(jti)),
                },
                isolated=True,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Device mismatch",
            )
        session.revoked_at = now
        session.revoke_reason = "client_logout"
        _spend_jti_safe(db, str(jti))
        _auth_audit(
            "auth.revoke",
            db=db,
            request=request,
            user_id=session.user_id,
            device_id=effective_device,
            metadata={"jti": _mask_jti(str(jti))},
            isolated=False,
        )
        db.commit()
    else:
        _spend_jti_safe(db, str(jti))
        db.commit()


def perform_revoke_all(*, db: Session, request: Optional[Request], user: AdminUser) -> int:
    now = _utcnow()
    sessions = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .all()
    )
    n = 0
    for s in sessions:
        s.revoked_at = now
        s.revoke_reason = "revoke_all"
        _spend_jti_safe(db, s.refresh_jti)
        n += 1
    _auth_audit(
        "auth.revoke_all",
        db=db,
        request=request,
        user_id=user.id,
        device_id="",
        metadata={"count": n},
        isolated=False,
    )
    db.commit()
    logger.info("auth.session.revoked_all %s", {"user_id": user.id, "count": n})
    return n


def list_active_sessions(*, db: Session, user: AdminUser) -> List[AuthSession]:
    now = _utcnow()
    return (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .order_by(AuthSession.last_used_at.desc())
        .all()
    )
