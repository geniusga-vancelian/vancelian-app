"""
Configuration WebAuthn centralisée (RP ID, origines, gabarits AASA / asset links).

Validation stricte en environnement prod-like (staging/production) au démarrage.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from services.security.security_env import (
    current_environment_label,
    is_admin_email_otp_enabled,
    is_mobile_otp_login_enabled,
    is_passkeys_enabled,
    is_webauthn_strict_environment,
)

logger = logging.getLogger("arquantix.auth.webauthn_config")


@dataclass
class WebAuthnSettings:
    rp_id: str
    rp_name: str
    origins: List[str]
    warnings: List[str] = field(default_factory=list)


_settings_cache: Optional[WebAuthnSettings] = None


def _default_origins_dev() -> str:
    return os.getenv("WEBAUTHN_ORIGINS") or "http://localhost:8011,http://127.0.0.1:8011"


def load_webauthn_settings_from_env(*, compute_warnings: bool = True) -> WebAuthnSettings:
    rp_id = (os.getenv("WEBAUTHN_RP_ID") or "localhost").strip()
    rp_name = (os.getenv("WEBAUTHN_RP_NAME") or "Arquantix").strip()
    origins_raw = os.getenv("WEBAUTHN_ORIGINS")
    if not origins_raw or not origins_raw.strip():
        origins_raw = _default_origins_dev()
    origins = [o.strip() for o in origins_raw.split(",") if o.strip()]
    warnings: List[str] = []
    if compute_warnings:
        warnings = collect_webauthn_warnings(WebAuthnSettings(rp_id=rp_id, rp_name=rp_name, origins=origins))
    return WebAuthnSettings(rp_id=rp_id, rp_name=rp_name, origins=origins, warnings=warnings)


def origin_host(origin: str) -> Optional[str]:
    try:
        p = urlparse(origin)
        if not p.scheme or not p.netloc:
            return None
        host = p.hostname
        return host.lower() if host else None
    except Exception:  # noqa: BLE001
        return None


def host_matches_rp_id(host: str, rp_id: str) -> bool:
    """True si l'hôte d'origine est autorisé pour ce rpId (égalité ou sous-domaine)."""
    h = host.lower().strip(".")
    r = rp_id.lower().strip(".")
    if not h or not r:
        return False
    if h == r:
        return True
    return h.endswith("." + r)


def collect_webauthn_warnings(settings: WebAuthnSettings) -> List[str]:
    w: List[str] = []
    if not settings.rp_id:
        w.append("WEBAUTHN_RP_ID is empty.")
    for o in settings.origins:
        if not o.startswith(("http://", "https://")):
            w.append(f"Origin is not a valid absolute URL: {o!r}")
            continue
        host = origin_host(o)
        if not host:
            w.append(f"Cannot parse host from origin: {o!r}")
            continue
        if not host_matches_rp_id(host, settings.rp_id):
            w.append(
                f"Origin host {host!r} is not equal to nor a subdomain of WEBAUTHN_RP_ID {settings.rp_id!r}."
            )
    if is_webauthn_strict_environment():
        if not settings.origins:
            w.append("WEBAUTHN_ORIGINS is empty (required in prod-like environment).")
        for o in settings.origins:
            if o.startswith("http://") and "localhost" not in o and "127.0.0.1" not in o:
                w.append(f"Non-local origin uses http:// (use https in production): {o!r}")
    return w


def validate_webauthn_strict(settings: WebAuthnSettings) -> None:
    """Lève RuntimeError si la configuration est invalide pour un déploiement réel."""
    errs: List[str] = []
    if not settings.rp_id:
        errs.append("WEBAUTHN_RP_ID must be non-empty in prod-like / strict WebAuthn mode.")
    if not settings.origins:
        errs.append("WEBAUTHN_ORIGINS must be non-empty (comma-separated) in prod-like / strict WebAuthn mode.")
    for o in settings.origins:
        if not o.startswith("https://"):
            if o.startswith("http://") and ("localhost" in o or "127.0.0.1" in o):
                continue
            errs.append(
                f"Every WEBAUTHN_ORIGINS entry must use https:// in prod-like mode (except localhost). Got: {o!r}"
            )
        host = origin_host(o)
        if host and settings.rp_id and not host_matches_rp_id(host, settings.rp_id):
            errs.append(
                f"Origin {o!r} host does not match WEBAUTHN_RP_ID {settings.rp_id!r} "
                "(must be equal or subdomain)."
            )
    if errs:
        raise RuntimeError(
            "WebAuthn configuration is invalid for this environment:\n"
            + "\n".join(f"  - {e}" for e in errs)
            + "\nSet WEBAUTHN_RP_ID, WEBAUTHN_ORIGINS (https only) and ensure each origin's host matches the RP ID."
        )


def validate_webauthn_at_startup(*, testing: bool) -> None:
    if testing:
        return
    if not is_passkeys_enabled():
        return
    if not is_webauthn_strict_environment():
        return
    s = load_webauthn_settings_from_env(compute_warnings=False)
    validate_webauthn_strict(s)
    logger.info("WebAuthn strict validation passed (rp_id=%s, origins=%s)", s.rp_id, len(s.origins))


def get_webauthn_settings() -> WebAuthnSettings:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = load_webauthn_settings_from_env(compute_warnings=True)
    return _settings_cache


def reset_webauthn_settings_cache() -> None:
    global _settings_cache
    _settings_cache = None


def webauthn_challenge_ttl_sec() -> int:
    return max(30, min(600, int(os.getenv("WEBAUTHN_CHALLENGE_TTL_SEC", "120"))))


# ——— Gabarits mobile (AASA / asset links) — lecteurs seulement depuis l’env ———


def webcredentials_app_ids_from_env() -> List[str]:
    raw = (os.getenv("WEBAUTHN_AASA_APP_IDS") or "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    team = (os.getenv("APPLE_TEAM_ID") or "").strip()
    bundle = (os.getenv("IOS_BUNDLE_ID") or "").strip()
    if team and bundle:
        return [f"{team}.{bundle}"]
    return []


def build_apple_app_site_association() -> Dict[str, Any]:
    apps = webcredentials_app_ids_from_env()
    return {
        "applinks": {"apps": [], "details": []},
        "webcredentials": {"apps": apps},
        "appclips": {"apps": []},
    }


def android_assetlinks_targets_from_env() -> List[Dict[str, Any]]:
    pkg = (os.getenv("ANDROID_PACKAGE_NAME") or "").strip()
    fps_raw = (os.getenv("ANDROID_SHA256_CERT_FINGERPRINTS") or "").strip()
    if not pkg or not fps_raw:
        return []
    fps = [re.sub(r"\s+", "", x.strip().upper()) for x in fps_raw.split(",") if x.strip()]
    return [
        {
            "relation": [
                "delegate_permission/common.get_login_creds",
                "delegate_permission/common.handle_all_urls",
            ],
            "target": {
                "namespace": "android_app",
                "package_name": pkg,
                "sha256_cert_fingerprints": fps,
            },
        }
    ]


def public_base_url_for_well_known() -> str:
    """Base publique du RP (ex. https://auth.example.com) — pour sondes diagnostics."""
    return (os.getenv("WEBAUTHN_PUBLIC_BASE_URL") or "").rstrip("/")


def probe_well_known_endpoints(
    base: str, timeout_sec: float = 5.0
) -> Dict[str, Any]:
    """Sonde les URLs .well-known (best-effort, ne lève pas)."""
    out: Dict[str, Any] = {"base": base, "results": {}}
    if not base.startswith("https://"):
        out["error"] = "WEBAUTHN_PUBLIC_BASE_URL must be https:// for meaningful probe"
        return out
    paths = (
        "/.well-known/apple-app-site-association",
        "/apple-app-site-association",
        "/.well-known/assetlinks.json",
    )
    for path in paths:
        url = base + path
        try:
            req = UrlRequest(url, headers={"User-Agent": "Arquantix-WebAuthn-Probe/1.0"}, method="GET")
            with urlopen(req, timeout=timeout_sec) as resp:  # noqa: S310 — intentional admin probe
                status = resp.getcode()
                ct = resp.headers.get("Content-Type", "")
                body = resp.read(8192)
                snippet = body.decode("utf-8", errors="replace")[:200]
                ok_json = False
                if status == 200:
                    try:
                        json.loads(body.decode("utf-8"))
                        ok_json = True
                    except json.JSONDecodeError:
                        pass
                out["results"][path] = {
                    "status": status,
                    "content_type": ct,
                    "json_ok": ok_json,
                    "body_preview": snippet,
                }
        except Exception as exc:  # noqa: BLE001
            out["results"][path] = {"error": str(exc)[:200]}
    return out


def build_passkeys_admin_config_dict(*, probe: bool = False) -> Dict[str, Any]:
    s = load_webauthn_settings_from_env(compute_warnings=True)
    strict = is_webauthn_strict_environment()
    w = list(s.warnings)
    apps = webcredentials_app_ids_from_env()
    if strict and is_passkeys_enabled() and not apps:
        w.append(
            "No WEBAUTHN_AASA_APP_IDS (or APPLE_TEAM_ID+IOS_BUNDLE_ID): "
            "Associated Domains / AASA will be incomplete for iOS passkeys."
        )
    al = android_assetlinks_targets_from_env()
    if strict and is_passkeys_enabled() and not al:
        w.append(
            "ANDROID_PACKAGE_NAME or ANDROID_SHA256_CERT_FINGERPRINTS missing: "
            "assetlinks.json will be empty for Android passkeys."
        )
    domains_expected = [f"webcredentials:{s.rp_id}"] if s.rp_id else []
    result: Dict[str, Any] = {
        "rp_id": s.rp_id,
        "rp_name": s.rp_name,
        "origins": s.origins,
        "passkeys_enabled": is_passkeys_enabled(),
        "admin_email_otp_enabled": is_admin_email_otp_enabled(),
        "environment": current_environment_label(),
        "strict_webauthn_validation": strict,
        "associated_domains_expected": domains_expected,
        "webcredentials_apps_template": apps,
        "assetlinks_expected": al if al else None,
        "warnings": w,
    }
    if probe:
        base = public_base_url_for_well_known()
        if base:
            result["well_known_probe"] = probe_well_known_endpoints(base)
        else:
            result["well_known_probe"] = {
                "skipped": True,
                "reason": "Set WEBAUTHN_PUBLIC_BASE_URL (https://…) to enable remote probe.",
            }
    return result


def validate_admin_email_otp_at_startup(*, testing: bool) -> None:
    if testing or not is_admin_email_otp_enabled():
        return
    if not is_webauthn_strict_environment():
        return
    from services.security.providers.email_provider import get_email_provider

    prov = get_email_provider()
    if prov.is_noop:
        raise RuntimeError(
            "AUTH_ADMIN_EMAIL_OTP_ENABLED is true but no outbound email provider is configured "
            "(set SES_FROM_EMAIL / AWS SES for production-like environments)."
        )
