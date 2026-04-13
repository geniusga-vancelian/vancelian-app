"""
Authentication utilities.

Les sujets JWT sont résolus via ``AdminUser`` (table ``admin_users``) : magasin
technique des identifiants de connexion (voir docstring du modèle ``AdminUser``).
Ne pas confondre avec un rôle « administrateur produit » sans vérifier le contexte
(``zero_trust_role``, routes admin, etc.).
"""
# CRITICAL: Load environment variables FIRST
from dotenv import load_dotenv
from pathlib import Path

# Force load .env.local first, then .env (explicit order)
api_dir = Path(__file__).parent
def _safe_load_dotenv(path: Path) -> None:
    try:
        load_dotenv(path)
    except PermissionError:
        return

_safe_load_dotenv(api_dir / ".env.local")
_safe_load_dotenv(api_dir / ".env")

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import uuid
from jose import JWTError, jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db, AdminUser, AuthSession
from core.env import is_dev_mode
import logging
import os
import bcrypt

logger = logging.getLogger(__name__)


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "14"))

# Debug: Log which secret is being used (masked)
def mask_secret(secret: str) -> str:
    """Mask secret for logging"""
    if len(secret) > 8:
        return secret[:4] + "***" + secret[-4:]
    return "***"

print(f"[auth.py] JWT_SECRET_KEY loaded: {mask_secret(SECRET_KEY)} (length: {len(SECRET_KEY)})")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    *,
    device_trust: Optional[str] = None,
    step_up_otp_required: bool = False,
    auth_strength: Optional[str] = None,
    session_id: Optional[str] = None,
    session_trust_level: Optional[str] = None,
    last_step_up_at_ts: Optional[int] = None,
    relock_required: bool = False,
    biometric_hint: bool = False,
    security_incomplete: bool = False,
    account_state: Optional[str] = None,
    device_binding_hash: Optional[str] = None,
):
    """Create a JWT access token (claims optionnels confiance appareil / step-up / ZT / session intelligence)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    if security_incomplete:
        to_encode["sec_inc"] = True
    if account_state:
        to_encode["acct_st"] = str(account_state)[:16]
    if device_trust:
        to_encode["dtrust"] = device_trust
    if step_up_otp_required:
        to_encode["step_up_otp"] = True
    if auth_strength:
        to_encode["auth_str"] = auth_strength
    if session_id:
        to_encode["sid"] = session_id
    if session_trust_level:
        to_encode["strust"] = str(session_trust_level)[:32]
    if last_step_up_at_ts is not None:
        to_encode["lstup"] = int(last_step_up_at_ts)
    if relock_required:
        to_encode["relock"] = True
    if biometric_hint:
        to_encode["bio_req"] = True
    if device_binding_hash:
        to_encode["did_h"] = str(device_binding_hash)[:32]
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    sub: str,
    device_id: str,
    jti: Optional[str] = None,
    *,
    sub_typ: str = "user_id",
    session_id: Optional[str] = None,
    device_binding_hash: Optional[str] = None,
) -> Tuple[str, str]:
    """JWT refresh — ``sub``, ``typ``, ``jti``, ``device_id``, ``did`` (même valeur), ``sid``.

    Ne jamais logger le jeton.
    """
    if jti is None:
        jti = str(uuid.uuid4())
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode: Dict[str, Any] = {
        "sub": sub,
        "sub_typ": sub_typ,
        "exp": expire,
        "typ": "refresh",
        "jti": jti,
        "device_id": device_id,
        # PR B — claim stable pour binding (même valeur que device_id ; les clients peuvent préférer did)
        "did": device_id,
    }
    if session_id:
        to_encode["sid"] = str(session_id)
    if device_binding_hash:
        to_encode["did_h"] = str(device_binding_hash)[:32]
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM), jti


def try_decode_refresh_token(token: str) -> Optional[dict]:
    """Retourne le payload si JWT refresh valide, sinon None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("typ") != "refresh":
        return None
    return payload


def create_registration_otp_token(person_id) -> str:
    """Short-lived JWT so Flutter can call /api/2fa/verify during registration (person_id claim)."""
    from uuid import UUID

    pid = str(person_id) if isinstance(person_id, UUID) else person_id
    return create_access_token(
        {
            "sub": "registration:2fa",
            "person_id": pid,
        },
        expires_delta=timedelta(minutes=45),
    )


def decode_token_debug(token: str) -> dict:
    """
    Debug helper to decode JWT token and identify validation issues.
    Returns unverified header/claims and verification result.
    Does NOT log or return the token itself.
    """
    result = {
        "unverified_header": None,
        "unverified_claims": None,
        "verify_ok": False,
        "verify_error": None,
        "verify_error_type": None,
        "expected_algorithm": ALGORITHM,
        "secret_source": "JWT_SECRET_KEY",
        "secret_length": len(SECRET_KEY),
        "secret_masked": mask_secret(SECRET_KEY),
    }
    
    try:
        # Get unverified header (no signature check)
        # python-jose provides get_unverified_header()
        try:
            unverified_header = jwt.get_unverified_header(token)
            result["unverified_header"] = unverified_header
        except Exception as e:
            result["unverified_header_error"] = str(e)
        
        # Get unverified claims (no signature check)
        # python-jose provides get_unverified_claims()
        try:
            unverified_claims = jwt.get_unverified_claims(token)
            result["unverified_claims"] = unverified_claims
        except Exception as e:
            result["unverified_claims_error"] = str(e)
        
        # Now try verified decode (same as get_current_user)
        try:
            verified_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            result["verify_ok"] = True
            result["verified_claims"] = verified_payload
        except JWTError as e:
            result["verify_ok"] = False
            result["verify_error"] = str(e)
            result["verify_error_type"] = type(e).__name__
        except Exception as e:
            result["verify_ok"] = False
            result["verify_error"] = f"Unexpected error: {str(e)}"
            result["verify_error_type"] = type(e).__name__
    except Exception as e:
        result["verify_ok"] = False
        result["verify_error"] = f"Token decode failed: {str(e)}"
        result["verify_error_type"] = type(e).__name__
    
    return result


def _get_current_user_internal(token: str, db: Session) -> tuple[Optional[AdminUser], Optional[str], Optional[str], Optional[str]]:
    """
    Internal function to get current user with detailed error tracking.
    Returns: (user, error_reason, error_type, sub_typ) — ``sub_typ`` = ``user_id`` si résolu OK.
    """
    from services.auth.jwt_subject_resolution import NonUserJWTSubjectError, resolve_user_from_jwt_sub

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        return None, f"JWT decode failed: {str(e)}", type(e).__name__, None
    except Exception as e:
        return None, f"Unexpected JWT error: {str(e)}", type(e).__name__, None

    sub_raw = payload.get("sub")
    if sub_raw is None:
        available_keys = list(payload.keys())
        return (
            None,
            f"Missing 'sub' in token payload. Available keys: {available_keys}",
            "missing_claim",
            None,
        )

    try:
        user, sub_typ, kind = resolve_user_from_jwt_sub(db, str(sub_raw), record_metric=True)
    except NonUserJWTSubjectError as exc:
        return (
            None,
            str(exc),
            "non_user_subject",
            "registration_special",
        )

    if kind == "ok" and user is not None:
        return user, None, None, sub_typ

    if kind == "non_user":
        return (
            None,
            "JWT subject is not a user session token (e.g. registration flow)",
            "non_user_subject",
            sub_typ,
        )

    if kind == "invalid":
        return None, f"Invalid JWT subject format: {sub_raw!r}", "invalid_sub", sub_typ

    identity = str(sub_raw).strip()
    reason = f"User not found in DB: {identity}"
    return None, reason, "user_not_found", sub_typ


def authenticated_admin_core_sync(token: str, db: Session) -> AdminUser:
    """JWT valide + règles ``enforce_access_security`` (sans couche Zero Trust)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user, error_reason, error_type, _sub_typ = _get_current_user_internal(token, db)
    if user is None:
        if is_dev_mode():
            print(f"[auth.py] authenticated_admin_core_sync FAILED: {error_reason} (type: {error_type})")
        raise credentials_exception
    enforce_access_security(token, user, db)
    return user


def authenticated_admin_core(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    """Dependency FastAPI : auth de base admin (pour gardes ZT sans récursion)."""
    return authenticated_admin_core_sync(token, db)


def _apply_zero_trust_default_access(
    *,
    request: Request,
    user: AdminUser,
    token: str,
    db: Session,
    x_device_id: Optional[str],
) -> None:
    from services.security.zero_trust.decision_logging import persist_security_decision
    from services.security.zero_trust.request_security_context import build_request_security_context, is_zero_trust_enforced
    from services.security.zero_trust.security_policy_engine import evaluate_security_policy

    if getattr(request.app.state, "testing", False):
        return
    if not is_zero_trust_enforced():
        return
    ctx = build_request_security_context(
        db=db,
        request=request,
        user=user,
        access_token=token,
        device_header=x_device_id,
    )
    result = evaluate_security_policy(ctx, "session.api_access", "*")
    persist_security_decision(db, context=ctx, result=result, action="session.api_access", resource="*")
    try:
        db.flush()
    except Exception:
        pass
    if not result.get("allow"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "zero_trust.api_access_denied",
                "message": result.get("deny_reason") or "Accès API refusé (politique Zero Trust).",
                "policy_id": result.get("policy_id"),
                "require_step_up": result.get("require_step_up"),
            },
        )


def enforce_access_security(token: str, user: AdminUser, db: Session) -> None:
    """Verrouillage compte, step-up OTP (jeton / refresh), conformité session."""
    now = datetime.now(timezone.utc)
    locked_until = getattr(user, "security_account_locked_until", None)
    if locked_until is not None and locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "security.account_locked",
                "message": "Compte temporairement verrouillé pour raison de sécurité.",
            },
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    active_step_up = (
        db.query(AuthSession)
        .filter(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
            AuthSession.step_up_otp_required.is_(True),
        )
        .first()
    )
    if active_step_up is not None and not payload.get("step_up_otp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "security.step_up_refresh_required",
                "message": "Rafraîchir le jeton pour appliquer la vérification OTP requise.",
            },
        )
    if payload.get("step_up_otp"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "security.step_up_otp_required",
                "step_up": True,
                "otp_login_path": "/auth/login/email-otp/start",
                "message": "OTP requis avant d’accéder à cette ressource.",
            },
        )


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
) -> AdminUser:
    """
    Get current authenticated user from JWT token (``sub`` = ``au:<admin_users.id>``).
    Optionnellement applique ``session.api_access`` si ``ZERO_TRUST_ENFORCE_DEFAULT_ACCESS``.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    from services.auth.auth_resolution import resolve_auth_context_strict_db

    try:
        user, sub_typ = resolve_auth_context_strict_db(token, db)
    except HTTPException:
        if is_dev_mode():
            print("[auth.py] get_current_user FAILED: resolve_auth_context_strict_db rejected token")
        raise credentials_exception
    if sub_typ == "user_id":
        from services.auth.jwt_subject_resolution import classify_sub_format

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            sub_preview = str(payload.get("sub") or "")[:128]
        except JWTError:
            sub_preview = ""
        logger.debug(
            "jwt_subject_resolution",
            extra={
                "sub": sub_preview,
                "sub_typ": sub_typ,
                "sub_format": classify_sub_format(sub_preview),
                "resolved_user_id": user.id,
                "route": request.url.path,
            },
        )
    logger.debug(
        "auth_identity_resolution",
        extra={"auth_resolution_mode": "db", "route": request.url.path},
    )
    enforce_access_security(token, user, db)
    from services.auth.device_pr_d4_policy import enforce_jwt_device_binding_if_configured

    enforce_jwt_device_binding_if_configured(token=token, x_device_id=x_device_id)
    _apply_zero_trust_default_access(
        request=request,
        user=user,
        token=token,
        db=db,
        x_device_id=x_device_id,
    )
    return user


get_current_user_strict = get_current_user


def get_optional_user_for_registration(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[AdminUser]:
    """JWT optionnel pour ``POST /api/registration/sessions/start`` — lie la session à ``admin_users.person_id``."""
    from services.auth.jwt_subject_resolution import (
        NonUserJWTSubjectError,
        is_non_user_subject_token,
        resolve_user_from_jwt_sub,
    )

    if not authorization or not authorization.strip().lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    sub_raw = payload.get("sub")
    if sub_raw is None:
        return None
    s = str(sub_raw).strip()
    if not s or is_non_user_subject_token(s):
        return None
    try:
        user, _sub_typ, kind = resolve_user_from_jwt_sub(db, s, record_metric=False)
    except NonUserJWTSubjectError:
        return None
    if kind != "ok" or user is None:
        return None
    return user

