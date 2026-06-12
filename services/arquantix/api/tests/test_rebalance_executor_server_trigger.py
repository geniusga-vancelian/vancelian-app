"""Tests du trigger ``server`` de BundleRebalanceExecutor (signature serveur par leg).

Tests **purs** (sans DB) : on isole la branche signature serveur greffée sur
l'executor existant. L'orchestration (sell→buy, idempotence, terminal status)
est déjà couverte par test_bundle_rebalance_executor.py.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from services.portfolio_engine.bundles import rebalance_executor as rex
from services.portfolio_engine.bundles.rebalance_executor import (
    CLIENT_SIGNATURE_TRIGGERS,
    PAUSE_ON_PENDING_TRIGGERS,
    SERVER_SIGNATURE_TRIGGERS,
    WORKER_RESUME_TRIGGERS,
    BundleRebalanceExecutor,
    V3LegExecutionResult,
    _uses_client_signature,
    _uses_server_signature,
)
from services.trade_core.server_execution import ServerSwapExecutionResult


def test_server_trigger_membership_and_helpers():
    """``server`` : signature serveur, pause sur pending, resync au resume — jamais client."""
    assert SERVER_SIGNATURE_TRIGGERS == frozenset({"server"})
    assert _uses_server_signature("server") is True
    assert _uses_client_signature("server") is False
    # Pause + resume worker comme deposit (poll d'un SUBMITTED au cycle suivant).
    assert "server" in PAUSE_ON_PENDING_TRIGGERS
    assert "server" in WORKER_RESUME_TRIGGERS
    # N'altère pas les triggers client historiques.
    assert CLIENT_SIGNATURE_TRIGGERS == frozenset({"manual", "deposit"})
    assert "server" not in CLIENT_SIGNATURE_TRIGGERS


def _leg(swap_id: str | None = "11111111-1111-1111-1111-111111111111") -> V3LegExecutionResult:
    return V3LegExecutionResult(
        asset="ETH",
        instrument_id=str(uuid.uuid4()),
        action="buy",
        amount_usdc="10",
        status="pending",
        attempts=1,
        swap_id=swap_id,
    )


def _call_sign(monkeypatch, *, exec_result=None, exec_exc=None, person_id=uuid.uuid4()):
    """Appelle _sign_leg_server_side avec ses dépendances mockées."""
    monkeypatch.setattr(
        rex, "_resolve_person_id_for_client", lambda _db, _cid: person_id
    )

    def _fake_exec(_db, *, person_id, swap_id):  # noqa: ARG001
        if exec_exc is not None:
            raise exec_exc
        return exec_result

    monkeypatch.setattr(
        "services.trade_core.server_execution.execute_prepared_swap_server_side",
        _fake_exec,
    )
    leg = _leg()
    # _sign_leg_server_side n'utilise pas self → MagicMock suffit.
    return BundleRebalanceExecutor._sign_leg_server_side(
        MagicMock(),
        MagicMock(),
        leg_result=leg,
        client_id=uuid.uuid4(),
    )


def _result(phase: str, **kw) -> ServerSwapExecutionResult:
    return ServerSwapExecutionResult(
        phase=phase,
        swap_id=uuid.uuid4(),
        signed_server_side=kw.get("signed_server_side", True),
        tx_hash=kw.get("tx_hash"),
        settled=kw.get("settled", False),
        fallback_reason=kw.get("fallback_reason"),
    )


def test_sign_leg_confirmed_maps_completed(monkeypatch):
    status, error = _call_sign(
        monkeypatch, exec_result=_result("confirmed", tx_hash="0xabc", settled=True),
    )
    assert status == "completed"
    assert error == ""


def test_sign_leg_submitted_maps_pending(monkeypatch):
    status, error = _call_sign(monkeypatch, exec_result=_result("submitted", tx_hash="0xdef"))
    assert status == "pending"
    assert error == "awaiting_confirmation"


def test_sign_leg_failed_maps_failed_with_reason(monkeypatch):
    status, error = _call_sign(
        monkeypatch, exec_result=_result("failed", fallback_reason="sign_failed:rate_limited"),
    )
    assert status == "failed"
    assert error == "sign_failed:rate_limited"


def test_sign_leg_expired_maps_expired(monkeypatch):
    status, error = _call_sign(monkeypatch, exec_result=_result("expired"))
    assert status == "expired"
    assert error == "expired"


def test_sign_leg_awaiting_signature_fallback_maps_expired(monkeypatch):
    """Délégation indisponible → awaiting_signature → leg expirée (fallback non signé)."""
    status, error = _call_sign(
        monkeypatch,
        exec_result=_result(
            "awaiting_signature", signed_server_side=False, fallback_reason="wallet_not_delegated",
        ),
    )
    assert status == "expired"
    assert error == "server_sign_unavailable:wallet_not_delegated"


def test_sign_leg_exception_maps_failed(monkeypatch):
    status, error = _call_sign(monkeypatch, exec_exc=RuntimeError("boom"))
    assert status == "failed"
    assert error.startswith("server_sign_error:")


def test_sign_leg_no_person_maps_failed(monkeypatch):
    status, error = _call_sign(
        monkeypatch, exec_result=_result("confirmed"), person_id=None,
    )
    assert status == "failed"
    assert error == "server_sign_no_person"


def test_sign_leg_no_swap_id_maps_expired(monkeypatch):
    monkeypatch.setattr(rex, "_resolve_person_id_for_client", lambda _db, _cid: uuid.uuid4())
    leg = _leg(swap_id=None)
    status, error = BundleRebalanceExecutor._sign_leg_server_side(
        MagicMock(), MagicMock(), leg_result=leg, client_id=uuid.uuid4(),
    )
    assert status == "expired"
    assert error == "server_sign_no_swap"


def test_sign_leg_invalid_swap_id_maps_expired(monkeypatch):
    monkeypatch.setattr(rex, "_resolve_person_id_for_client", lambda _db, _cid: uuid.uuid4())
    leg = _leg(swap_id="not-a-uuid")
    status, error = BundleRebalanceExecutor._sign_leg_server_side(
        MagicMock(), MagicMock(), leg_result=leg, client_id=uuid.uuid4(),
    )
    assert status == "expired"
    assert error == "server_sign_swap_invalid"
