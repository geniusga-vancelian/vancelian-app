"""Phase 5A — couche UX auth continue (messages, priorité raisons)."""
from __future__ import annotations

import pytest

from services.security.continuous_auth_ux import (
    build_continuous_auth_ux_fields,
    _pick_primary_reason,
)


def test_priority_reauth_over_device_and_recent():
    codes = ["recent_auth_required", "device_not_trusted", "reauth_required", "step_up_required"]
    assert _pick_primary_reason(codes) == "reauth_required"


def test_priority_device_over_recent():
    assert (
        _pick_primary_reason(["recent_auth_required", "device_not_trusted", "step_up_required"])
        == "device_not_trusted"
    )


def test_priority_recent_over_step_up_alone():
    assert _pick_primary_reason(["step_up_required", "recent_auth_required"]) == "recent_auth_required"


def test_ux_message_withdrawal_recent_auth():
    u = build_continuous_auth_ux_fields(
        reason_codes=["recent_auth_required"],
        action_key="wallet_transfer",
    )
    assert u["ux_context"] == "withdrawal"
    assert "transfert" in u["ux_message"].lower() or "sécurité" in u["ux_message"].lower()
    assert u["ux_tone"] == "soft"


def test_ux_message_view_sensitive_data_access():
    u = build_continuous_auth_ux_fields(
        reason_codes=["recent_auth_required"],
        action_key="view_sensitive_data",
    )
    assert u["ux_context"] == "data_access"
    assert "identité" in u["ux_message"].lower() or "informations" in u["ux_message"].lower()


def test_ux_message_device_not_trusted():
    u = build_continuous_auth_ux_fields(
        reason_codes=["device_not_trusted", "step_up_required"],
        action_key="view_sensitive_data",
    )
    assert "appareil" in u["ux_message"].lower() or "vérifions" in u["ux_message"].lower()
    assert u["ux_tone"] == "warning"


def test_fallback_unknown_reason():
    u = build_continuous_auth_ux_fields(
        reason_codes=["totally_unknown_code_xyz"],
        action_key="view_sensitive_data",
    )
    assert u["ux_message"]
    assert u["ux_tone"] in ("soft", "warning", "critical")
    assert u["ux_action_label"]
    assert u["ux_context"] == "data_access"


def test_security_change_context():
    u = build_continuous_auth_ux_fields(
        reason_codes=["recent_auth_required"],
        action_key="security_settings_change",
    )
    assert u["ux_context"] == "security_change"
    assert "paramètre" in u["ux_message"].lower() or "sensible" in u["ux_message"].lower()
