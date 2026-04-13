"""Modèle V1 des préférences sécurité (biométrie, notifications) dans ``profile_json.security``.

Règles :
- Source de vérité : objets structurés ``biometric`` / ``push_notifications`` si ``security_model_version >= 1``.
- Champs legacy plats = projection dérivée (jamais lus comme vérité une fois V1 actif).
- Biométrie : si ``onboarding_outcome == unavailable`` et ``device_capability_last_known == available``,
  rejet explicite (422) — incohérence client ; voir ``validate_biometric_consistency``.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Optional

# --- Defaults (stockage JSON : datetimes en ISO 8601 UTC avec suffixe Z) ---


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_biometric() -> dict[str, Any]:
    return {
        "preference_enabled": None,
        "preference_updated_at": None,
        "onboarding_status": "not_started",
        "onboarding_outcome": "unknown",
        "onboarding_completed_at": None,
        "last_client_reported_at": None,
        "onboarding_source": "unknown",
        "device_capability_last_known": "unknown",
    }


def _default_push() -> dict[str, Any]:
    return {
        "preference_enabled": None,
        "preference_updated_at": None,
        "onboarding_status": "not_started",
        "onboarding_outcome": "unknown",
        "onboarding_completed_at": None,
        "last_client_reported_at": None,
        "onboarding_source": "unknown",
        "os_permission_last_known": "unknown",
    }


BIOMETRIC_FINAL_OUTCOMES = frozenset({"enabled", "skipped", "unavailable"})
PUSH_FINAL_OUTCOMES = frozenset({"enabled", "skipped"})

# Clés gérées par le module V1 ; le reste (ex. local_passcode_registered_at) est préservé.
_V1_MANAGED_KEYS = frozenset(
    {
        "security_model_version",
        "biometric",
        "push_notifications",
        "biometric_unlock_enabled",
        "biometric_login_onboarding_completed",
        "push_notifications_enabled",
        "push_notifications_onboarding_completed",
    }
)


def _merge_ancillary_security_fields(sec_raw: dict[str, Any], out: dict[str, Any]) -> None:
    """Conserve les clés hors modèle V1 (ACK passcode, futurs champs)."""
    for k, v in sec_raw.items():
        if k not in _V1_MANAGED_KEYS:
            out[k] = v


def derive_legacy_flat(biometric: dict[str, Any], push: dict[str, Any]) -> dict[str, bool]:
    """Projection stricte (decision memo)."""
    return {
        "biometric_unlock_enabled": biometric.get("preference_enabled") is True,
        "biometric_login_onboarding_completed": biometric.get("onboarding_status") == "completed",
        "push_notifications_enabled": push.get("preference_enabled") is True,
        "push_notifications_onboarding_completed": push.get("onboarding_status") == "completed",
    }


def migrate_legacy_to_v1(sec: dict[str, Any]) -> dict[str, Any]:
    """Normalise ``sec`` vers V1 en mémoire (idempotent si déjà V1 cohérent)."""
    if sec.get("security_model_version", 0) >= 1 and isinstance(sec.get("biometric"), dict) and isinstance(
        sec.get("push_notifications"), dict
    ):
        bio = {**_default_biometric(), **sec["biometric"]}
        push = {**_default_push(), **sec["push_notifications"]}
        out = {
            "security_model_version": 1,
            "biometric": bio,
            "push_notifications": push,
        }
        out.update(derive_legacy_flat(bio, push))
        _merge_ancillary_security_fields(sec, out)
        return out

    # Legacy : uniquement booléens plats
    bio_completed = sec.get("biometric_login_onboarding_completed") is True
    bio_enabled = sec.get("biometric_unlock_enabled") is True
    push_completed = sec.get("push_notifications_onboarding_completed") is True
    push_enabled = sec.get("push_notifications_enabled") is True

    if bio_completed:
        biometric = _default_biometric()
        biometric["preference_enabled"] = bio_enabled
        biometric["onboarding_status"] = "completed"
        biometric["onboarding_outcome"] = "enabled" if bio_enabled else "skipped"
    else:
        biometric = _default_biometric()

    if push_completed:
        push = _default_push()
        push["preference_enabled"] = push_enabled
        push["onboarding_status"] = "completed"
        push["onboarding_outcome"] = "enabled" if push_enabled else "skipped"
    else:
        push = _default_push()

    out = {
        "security_model_version": 1,
        "biometric": biometric,
        "push_notifications": push,
    }
    out.update(derive_legacy_flat(biometric, push))
    _merge_ancillary_security_fields(sec, out)
    return out


def validate_biometric_consistency(biometric: dict[str, Any]) -> None:
    """Lève ValueError si incohérence outcome / capability (politique : rejet API)."""
    if (
        biometric.get("onboarding_outcome") == "unavailable"
        and biometric.get("device_capability_last_known") == "available"
    ):
        raise ValueError(
            "security.biometric: onboarding_outcome 'unavailable' is incompatible with "
            "device_capability_last_known 'available'."
        )


def validate_domain_invariants(
    biometric: dict[str, Any],
    push: dict[str, Any],
    *,
    label: str = "",
) -> None:
    """Règles validation decision memo."""
    validate_biometric_consistency(biometric)

    for name, block in (("biometric", biometric), ("push_notifications", push)):
        st = block.get("onboarding_status")
        oc = block.get("onboarding_outcome")
        if st == "not_started" and oc != "unknown":
            raise ValueError(
                f"security.{name}: onboarding_status 'not_started' requires onboarding_outcome 'unknown'."
            )
        if st == "completed" and oc == "unknown":
            raise ValueError(
                f"security.{name}: onboarding_status 'completed' forbids onboarding_outcome 'unknown'."
            )


def _derive_onboarding_status_from_outcome(
    outcome: str,
    *,
    is_push: bool,
) -> str:
    if is_push:
        final = outcome in PUSH_FINAL_OUTCOMES
    else:
        final = outcome in BIOMETRIC_FINAL_OUTCOMES
    return "completed" if final else "not_started"


def apply_server_rules_after_merge(
    block: dict[str, Any],
    prev_block: dict[str, Any],
    *,
    is_push: bool,
    now_iso: str,
) -> None:
    """Met à jour onboarding_status, onboarding_completed_at (première fois), preference_updated_at."""
    outcome = block.get("onboarding_outcome", "unknown")
    block["onboarding_status"] = _derive_onboarding_status_from_outcome(outcome, is_push=is_push)

    prev_completed = prev_block.get("onboarding_status") == "completed"
    new_completed = block["onboarding_status"] == "completed"
    if new_completed:
        if not prev_completed:
            if block.get("onboarding_completed_at") is None:
                block["onboarding_completed_at"] = now_iso
        else:
            block["onboarding_completed_at"] = prev_block.get("onboarding_completed_at")
    else:
        block["onboarding_completed_at"] = None

    prev_pref = prev_block.get("preference_enabled")
    new_pref = block.get("preference_enabled")
    if prev_pref != new_pref:
        block["preference_updated_at"] = now_iso


def merge_patch_into_security(
    sec_raw: dict[str, Any],
    biometric_patch: Optional[dict[str, Any]],
    push_patch: Optional[dict[str, Any]],
    *,
    now_iso: Optional[str] = None,
) -> dict[str, Any]:
    """Fusionne un PATCH partiel dans l’état sécurité et applique les règles serveur."""
    now_iso = now_iso or _utc_now_iso()
    sec = migrate_legacy_to_v1(sec_raw if isinstance(sec_raw, dict) else {})
    prev_bio = copy.deepcopy(sec["biometric"])
    prev_push = copy.deepcopy(sec["push_notifications"])

    bio = {**prev_bio}
    if biometric_patch:
        for k, v in biometric_patch.items():
            if v is not None:
                bio[k] = v
    push = {**prev_push}
    if push_patch:
        for k, v in push_patch.items():
            if v is not None:
                push[k] = v

    apply_server_rules_after_merge(bio, prev_bio, is_push=False, now_iso=now_iso)
    apply_server_rules_after_merge(push, prev_push, is_push=True, now_iso=now_iso)

    validate_domain_invariants(bio, push)

    out = {
        "security_model_version": 1,
        "biometric": bio,
        "push_notifications": push,
    }
    out.update(derive_legacy_flat(bio, push))
    _merge_ancillary_security_fields(sec_raw if isinstance(sec_raw, dict) else {}, out)
    return out


def build_security_preferences_read_dict(sec: dict[str, Any]) -> dict[str, Any]:
    """Dict prêt pour JSON / Pydantic (GET profil, réponse PATCH)."""
    m = migrate_legacy_to_v1(sec if isinstance(sec, dict) else {})
    return {
        "security_model_version": m["security_model_version"],
        "biometric": m["biometric"],
        "push_notifications": m["push_notifications"],
        "biometric_unlock_enabled": m["biometric_unlock_enabled"],
        "biometric_login_onboarding_completed": m["biometric_login_onboarding_completed"],
        "push_notifications_enabled": m["push_notifications_enabled"],
        "push_notifications_onboarding_completed": m["push_notifications_onboarding_completed"],
    }


def security_blob_from_person(profile_json: Optional[dict[str, Any]]) -> dict[str, Any]:
    pj = profile_json or {}
    sec = pj.get("security")
    return dict(sec) if isinstance(sec, dict) else {}
