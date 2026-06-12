"""Tests du pilote serveur de rééquilibrage (gating + start/resume dispatch).

Tests **purs** (sans DB) : on isole le routage du worker. L'exécution réelle
(executor trigger=server) est couverte par test_rebalance_executor_server_trigger.py
et test_bundle_rebalance_executor.py.
"""
from __future__ import annotations

import uuid

import pytest

from services.portfolio_engine.bundles import server_rebalance_worker as srw


def test_skips_when_client_has_no_person(monkeypatch):
    monkeypatch.setattr(srw, "_resolve_person_id", lambda _db, _cid: None)
    out = srw.run_server_side_rebalance_for_portfolio(
        object(), client_id=uuid.uuid4(), portfolio_id=uuid.uuid4(),
    )
    assert out["skipped"] is True
    assert out["reason"] == "client_has_no_person_id"


def test_skips_when_not_allowlisted(monkeypatch):
    monkeypatch.setattr(srw, "_resolve_person_id", lambda _db, _cid: uuid.uuid4())
    monkeypatch.setattr(
        "services.lifi.orchestrator_allowlist.lifi_rebalance_worker_enabled_for_person",
        lambda _db, _pid: False,
    )
    out = srw.run_server_side_rebalance_for_portfolio(
        object(), client_id=uuid.uuid4(), portfolio_id=uuid.uuid4(),
    )
    assert out["skipped"] is True
    assert out["reason"] == "rebalance_worker_not_enabled_for_person"


def test_starts_when_enabled_and_required(monkeypatch):
    pid = uuid.uuid4()
    monkeypatch.setattr(srw, "_resolve_person_id", lambda _db, _cid: pid)
    monkeypatch.setattr(
        "services.lifi.orchestrator_allowlist.lifi_rebalance_worker_enabled_for_person",
        lambda _db, _pid: True,
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.rebalance_executor.find_running_v3_rebalance_execution",
        lambda _db, *, portfolio_id: None,
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.rebalancing_portfolio.should_use_portfolio_rebalancing",
        lambda _db, *, client_id, portfolio_id: True,
    )
    called = {}

    def _fake_start(_db, *, client_id, portfolio_id, trigger):
        called["trigger"] = trigger
        return {"v3_status": "RUNNING", "trigger": trigger}

    monkeypatch.setattr(
        "services.portfolio_engine.bundles.rebalancing_portfolio.rebalancing_portfolio",
        _fake_start,
    )
    out = srw.run_server_side_rebalance_for_portfolio(
        object(), client_id=uuid.uuid4(), portfolio_id=uuid.uuid4(),
    )
    assert called["trigger"] == "server"
    assert out["v3_status"] == "RUNNING"


def test_resumes_when_running(monkeypatch):
    monkeypatch.setattr(srw, "_resolve_person_id", lambda _db, _cid: uuid.uuid4())
    monkeypatch.setattr(
        "services.lifi.orchestrator_allowlist.lifi_rebalance_worker_enabled_for_person",
        lambda _db, _pid: True,
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.rebalance_executor.find_running_v3_rebalance_execution",
        lambda _db, *, portfolio_id: {"rebalance_execution_id": "x", "v3_status": "RUNNING"},
    )
    called = {}

    def _fake_resume(_db, *, client_id, portfolio_id, trigger):
        called["trigger"] = trigger
        return {"v3_status": "COMPLETED", "trigger": trigger}

    monkeypatch.setattr(
        "services.portfolio_engine.bundles.rebalancing_portfolio.resume_rebalancing_portfolio",
        _fake_resume,
    )
    out = srw.run_server_side_rebalance_for_portfolio(
        object(), client_id=uuid.uuid4(), portfolio_id=uuid.uuid4(),
    )
    assert called["trigger"] == "server"
    assert out["v3_status"] == "COMPLETED"


def test_flag_default_off(monkeypatch):
    from services.lifi.config import lifi_rebalance_worker_enabled

    monkeypatch.delenv("LIFI_REBALANCE_WORKER_ENABLED", raising=False)
    assert lifi_rebalance_worker_enabled() is False
    monkeypatch.setenv("LIFI_REBALANCE_WORKER_ENABLED", "true")
    assert lifi_rebalance_worker_enabled() is True


def test_allowlist_fail_closed_when_flag_off_or_empty(monkeypatch):
    from services.lifi.orchestrator_allowlist import (
        lifi_rebalance_worker_enabled_for_person,
    )

    # Flag OFF → jamais éligible (aucun accès DB requis).
    monkeypatch.delenv("LIFI_REBALANCE_WORKER_ENABLED", raising=False)
    assert lifi_rebalance_worker_enabled_for_person(object(), uuid.uuid4()) is False

    # Flag ON mais allowlist vide → fail-closed (aucun accès DB requis).
    monkeypatch.setenv("LIFI_REBALANCE_WORKER_ENABLED", "true")
    monkeypatch.delenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", raising=False)
    assert lifi_rebalance_worker_enabled_for_person(object(), uuid.uuid4()) is False

    # Personne nulle → jamais éligible.
    monkeypatch.setenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", "x@example.com")
    assert lifi_rebalance_worker_enabled_for_person(object(), None) is False


def test_deposit_rebalance_trigger_selection(monkeypatch):
    """bundle.v3_rebalance_requested : trigger 'server' si allowlisté, sinon 'deposit'."""
    from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
        _resolve_deposit_rebalance_trigger,
    )

    # Pas de person → deposit (fail-closed).
    assert _resolve_deposit_rebalance_trigger(object(), None) == "deposit"

    # person_id invalide → deposit (jamais d'exception).
    assert _resolve_deposit_rebalance_trigger(object(), "not-a-uuid") == "deposit"

    # Non allowlisté → deposit.
    monkeypatch.setattr(
        "services.lifi.orchestrator_allowlist.lifi_rebalance_worker_enabled_for_person",
        lambda _db, _pid: False,
    )
    assert _resolve_deposit_rebalance_trigger(object(), str(uuid.uuid4())) == "deposit"

    # Allowlisté → server.
    monkeypatch.setattr(
        "services.lifi.orchestrator_allowlist.lifi_rebalance_worker_enabled_for_person",
        lambda _db, _pid: True,
    )
    assert _resolve_deposit_rebalance_trigger(object(), str(uuid.uuid4())) == "server"


def test_server_trigger_skips_plan_drift_terminalize():
    """server reprend le plan figé (comme deposit) plutôt que terminaliser sur drift."""
    from services.portfolio_engine.bundles.rebalance_executor import (
        _skip_plan_drift_terminalize,
    )

    assert _skip_plan_drift_terminalize("server") is True
    assert _skip_plan_drift_terminalize("deposit") is True
    assert _skip_plan_drift_terminalize("manual") is False
    assert _skip_plan_drift_terminalize("cron") is False


def test_skips_when_not_required(monkeypatch):
    monkeypatch.setattr(srw, "_resolve_person_id", lambda _db, _cid: uuid.uuid4())
    monkeypatch.setattr(
        "services.lifi.orchestrator_allowlist.lifi_rebalance_worker_enabled_for_person",
        lambda _db, _pid: True,
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.rebalance_executor.find_running_v3_rebalance_execution",
        lambda _db, *, portfolio_id: None,
    )
    monkeypatch.setattr(
        "services.portfolio_engine.bundles.rebalancing_portfolio.should_use_portfolio_rebalancing",
        lambda _db, *, client_id, portfolio_id: False,
    )
    out = srw.run_server_side_rebalance_for_portfolio(
        object(), client_id=uuid.uuid4(), portfolio_id=uuid.uuid4(),
    )
    assert out["skipped"] is True
    assert out["reason"] == "no_rebalance_required"
