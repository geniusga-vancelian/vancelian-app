"""PR F.5 — API admin règles dynamiques."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from auth import get_current_user


@pytest.fixture
def admin_user(db):
    from tests.conftest import make_admin_user_with_pe_client

    return make_admin_user_with_pe_client(db, email="risk-admin@test.local", password="test")


@pytest.fixture
def client_as_admin(client, test_app, admin_user):
    test_app.dependency_overrides[get_current_user] = lambda: admin_user
    yield client
    test_app.dependency_overrides.pop(get_current_user, None)


def test_validate_dsl_ok(client_as_admin):
    r = client_as_admin.post(
        "/admin/risk/rules/validate",
        json={"conditions": {"all": ["new_device"]}},
    )
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_validate_dsl_bad(client_as_admin):
    r = client_as_admin.post(
        "/admin/risk/rules/validate",
        json={"conditions": {"oops": 1}},
    )
    assert r.status_code == 200
    assert r.json()["valid"] is False


def test_simulate_inline_without_persisted_rule(client_as_admin, admin_user):
    """Simulate avec conditions brouillon uniquement (sans table auth_risk_rules)."""
    r = client_as_admin.post(
        "/admin/risk/rules/simulate",
        json={
            "conditions": {"all": ["new_device"]},
            "user_id": admin_user.id,
            "device_id": "dev-sim-1",
            "action_type": "wallet_transfer",
            "country": "FR",
        },
    )
    assert r.status_code == 200
    assert r.json().get("would_trigger")
    assert r.json().get("simulate_mode") == "runtime"
    assert r.json().get("used_runtime_state") is True
    assert r.json().get("used_cache") is False


def test_simulate_isolated_no_profile_db_call(client_as_admin, admin_user):
    """Mode isolated : pas de résolution profil device (pas de lecture DB profil)."""
    with patch(
        "services.auth.risk_rules_admin_routes.resolve_user_device_profile",
    ) as m_prof:
        r = client_as_admin.post(
            "/admin/risk/rules/simulate",
            json={
                "simulate_mode": "isolated",
                "conditions": {"all": ["new_device"]},
                "user_id": admin_user.id,
                "device_id": "dev-iso-1",
                "action_type": "wallet_transfer",
                "country": "FR",
            },
        )
    assert r.status_code == 200
    m_prof.assert_not_called()
    body = r.json()
    assert body.get("simulate_mode") == "isolated"
    assert body.get("used_cache") is False
    assert body.get("used_runtime_state") is False
    assert body.get("used_baseline") is False
    assert "risk_score" in body
    assert "decision" in body


def test_simulate_isolated_no_redis_risk_cache(client_as_admin, admin_user):
    """Isolated n’utilise pas le cache risk Redis."""
    with patch("services.auth.risk_cache.get_risk_cache_payload") as m_cache:
        r = client_as_admin.post(
            "/admin/risk/rules/simulate",
            json={
                "simulate_mode": "isolated",
                "conditions": {"all": ["new_device"]},
                "user_id": admin_user.id,
                "device_id": "x",
                "action_type": "wallet_transfer",
            },
        )
    assert r.status_code == 200
    m_cache.assert_not_called()


def test_simulate_isolated_baseline_override_used(client_as_admin, admin_user):
    r = client_as_admin.post(
        "/admin/risk/rules/simulate",
        json={
            "simulate_mode": "isolated",
            "conditions": {"all": ["new_device"]},
            "user_id": admin_user.id,
            "device_id": "x",
            "action_type": "wallet_transfer",
            "current_hour_utc": 3,
            "weekday_utc": 1,
            "baseline_override": {
                "baseline_sample_count": 50,
                "avg_hour_of_day": 14.0,
                "std_hour_of_day": 1.5,
                "avg_weekday": 1.0,
                "std_weekday": 1.0,
                "last_10_actions_types": ["login"],
            },
        },
    )
    assert r.status_code == 200
    assert r.json().get("used_baseline") is True


def test_simulate_runtime_unchanged_explicit(client_as_admin, admin_user):
    r = client_as_admin.post(
        "/admin/risk/rules/simulate",
        json={
            "simulate_mode": "runtime",
            "conditions": {"all": ["new_device"]},
            "user_id": admin_user.id,
            "device_id": "dev-sim-rt",
            "action_type": "wallet_transfer",
            "country": "FR",
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("simulate_mode") == "runtime"
    assert j.get("would_trigger")
    assert j.get("used_runtime_state") is True


def test_simulate_isolated_known_device_new_device_signal_false(client_as_admin, admin_user):
    """F.5.2 — device connu : signal new_device faux (DSL new_device ne matche pas)."""
    r = client_as_admin.post(
        "/admin/risk/rules/simulate",
        json={
            "simulate_mode": "isolated",
            "conditions": {"all": ["new_device"]},
            "user_id": admin_user.id,
            "device_id": "known-1",
            "action_type": "wallet_transfer",
            "country": "FR",
            "profile_override": {
                "is_known_device": True,
                "last_country": "FR",
                "last_ip": "10.0.0.1",
                "device_count_24h": 0,
            },
            "current_ip": "10.0.0.1",
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("used_profile_override") is True
    assert j.get("explain", {}).get("matched") is False
    assert "rule_conditions_not_matched" in j.get("risk_reason", [])


def test_simulate_isolated_stable_country_no_combination_block(client_as_admin, admin_user, monkeypatch):
    """Device connu, même pays / IP : pas de blocage new_device+country."""
    monkeypatch.setenv("DEVICE_RISK_ENABLE_COMBINATION_RULES", "true")
    r = client_as_admin.post(
        "/admin/risk/rules/simulate",
        json={
            "simulate_mode": "isolated",
            "conditions": {"all": ["new_device"]},
            "user_id": admin_user.id,
            "device_id": "k2",
            "action_type": "wallet_transfer",
            "country": "FR",
            "profile_override": {
                "is_known_device": True,
                "last_country": "FR",
                "last_ip": "10.0.0.2",
                "device_count_24h": 0,
            },
            "current_ip": "10.0.0.2",
            "velocity_count": 0,
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert "rule_new_device_and_country_change" not in j.get("risk_reason", [])


def test_simulate_isolated_churn_velocity_combination(client_as_admin, admin_user, monkeypatch):
    """Churn + vélocité issus du profil injecté → règle combinée PR F.2."""
    monkeypatch.setenv("DEVICE_RISK_ENABLE_COMBINATION_RULES", "true")
    r = client_as_admin.post(
        "/admin/risk/rules/simulate",
        json={
            "simulate_mode": "isolated",
            "conditions": {"all": ["new_device"]},
            "user_id": admin_user.id,
            "device_id": "k3",
            "action_type": "wallet_transfer",
            "country": "FR",
            "profile_override": {
                "is_known_device": True,
                "last_country": "FR",
                "last_ip": "10.0.0.3",
                "device_count_24h": 2,
            },
            "current_ip": "10.0.0.3",
            "velocity_count": 1,
        },
    )
    assert r.status_code == 200
    j = r.json()
    assert j.get("decision") == "block"
    assert "rule_device_churn_and_velocity" in j.get("risk_reason", [])


def test_simulate_isolated_now_utc_deterministic(client_as_admin, admin_user):
    """Même now_utc → même score (reproductibilité)."""
    base = {
        "simulate_mode": "isolated",
        "conditions": {"all": ["new_device"]},
        "user_id": admin_user.id,
        "device_id": "t",
        "action_type": "wallet_transfer",
        "now_utc": "2026-06-15T14:30:00Z",
        "deterministic": True,
    }
    a = client_as_admin.post("/admin/risk/rules/simulate", json=base).json()
    b = client_as_admin.post("/admin/risk/rules/simulate", json=base).json()
    assert a.get("risk_score") == b.get("risk_score")


def test_simulate_isolated_vs_runtime_both_ok(client_as_admin, admin_user):
    """Smoke : runtime et isolé répondent pour le même brouillon."""
    body = {
        "conditions": {"all": ["new_device"]},
        "user_id": admin_user.id,
        "device_id": "cmp",
        "action_type": "wallet_transfer",
        "country": "FR",
    }
    r1 = client_as_admin.post(
        "/admin/risk/rules/simulate",
        json={**body, "simulate_mode": "runtime"},
    )
    r2 = client_as_admin.post(
        "/admin/risk/rules/simulate",
        json={**body, "simulate_mode": "isolated"},
    )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json().get("would_trigger") and r2.json().get("decision")
