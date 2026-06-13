"""PR2 — worker serveur autoritaire : le chemin d'exécution client legacy est refusé.

Périmètre strict : swap simple LI.FI, allowlist, flag OFF par défaut. On vérifie
(1) la logique du helper d'éligibilité et (2) que les routes d'exécution client
(`/execute`, `/{id}/submit`, `/{id}/server-execute`, `/{id}/approval`) renvoient 409
`swap.server_authoritative` quand le worker est autoritaire — empêchant double signature
et fallback client.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from services.lifi.orchestrator_allowlist import (
    lifi_authoritative_execution_enabled_for_person,
)
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.test_lifi_swap_routes import _auth_headers, _migration_159_applied, _seed_wallet

pytestmark = pytest.mark.skipif(
    not _migration_159_applied(),
    reason="Appliquer `alembic upgrade head` (159) pour les tests swap LI.FI.",
)


def _enable_authoritative(monkeypatch, pe) -> None:
    """Active la chaîne complète : orchestrateur + worker exécution + autoritaire + allowlist."""
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    monkeypatch.setenv("LIFI_EXECUTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("LIFI_AUTHORITATIVE_EXECUTION_ENABLED", "true")
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)


# --------------------------------------------------------------- helper logic


def test_helper_false_when_authoritative_flag_off(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_EXECUTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("LIFI_AUTHORITATIVE_EXECUTION_ENABLED", "false")
    pe = make_linked_client(db, email="auth-off@example.com")
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    assert lifi_authoritative_execution_enabled_for_person(db, pe.person_id) is False


def test_helper_false_when_execution_worker_off(db: Session, monkeypatch):
    """Garde-fou : autoritaire ON mais aucun exécuteur serveur → on ne bloque pas le client."""
    monkeypatch.setenv("LIFI_AUTHORITATIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("LIFI_EXECUTION_WORKER_ENABLED", "false")
    pe = make_linked_client(db, email="worker-off@example.com")
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    assert lifi_authoritative_execution_enabled_for_person(db, pe.person_id) is False


def test_helper_true_when_all_on_and_allowlisted(db: Session, monkeypatch):
    pe = make_linked_client(db, email="auth-on@example.com")
    _enable_authoritative(monkeypatch, pe)
    assert lifi_authoritative_execution_enabled_for_person(db, pe.person_id) is True


def test_helper_false_when_not_allowlisted(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_AUTHORITATIVE_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("LIFI_EXECUTION_WORKER_ENABLED", "true")
    monkeypatch.setenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", "someone-else@example.com")
    pe = make_linked_client(db, email="not-listed@example.com")
    assert lifi_authoritative_execution_enabled_for_person(db, pe.person_id) is False


# --------------------------------------------------------------- route gating


def _tx_hash() -> str:
    return "0x" + "ab" * 33


def test_submit_blocked_when_authoritative(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db, email="block-submit@example.com")
    _seed_wallet(db, pe)
    _enable_authoritative(monkeypatch, pe)

    res = client.post(
        f"/api/swaps/{uuid4()}/submit",
        headers=_auth_headers(db, pe),
        json={"tx_hash": _tx_hash()},
    )
    assert res.status_code == 409, res.text
    assert res.json()["detail"]["code"] == "swap.server_authoritative"


def test_server_execute_blocked_when_authoritative(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db, email="block-serverexec@example.com")
    _seed_wallet(db, pe)
    _enable_authoritative(monkeypatch, pe)

    res = client.post(
        f"/api/swaps/{uuid4()}/server-execute",
        headers=_auth_headers(db, pe),
    )
    assert res.status_code == 409, res.text
    assert res.json()["detail"]["code"] == "swap.server_authoritative"


def test_approval_blocked_when_authoritative(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db, email="block-approval@example.com")
    _seed_wallet(db, pe)
    _enable_authoritative(monkeypatch, pe)

    res = client.post(
        f"/api/swaps/{uuid4()}/approval",
        headers=_auth_headers(db, pe),
        json={"tx_hash": _tx_hash()},
    )
    assert res.status_code == 409, res.text
    assert res.json()["detail"]["code"] == "swap.server_authoritative"


def test_legacy_execute_blocked_when_authoritative(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db, email="block-execute@example.com")
    _seed_wallet(db, pe)
    _enable_authoritative(monkeypatch, pe)

    res = client.post(
        "/api/swaps/execute",
        headers=_auth_headers(db, pe),
        json={"swap_id": str(uuid4())},
    )
    assert res.status_code == 409, res.text
    assert res.json()["detail"]["code"] == "swap.server_authoritative"


def test_submit_not_blocked_when_flag_off(client: TestClient, db: Session, monkeypatch):
    """Contrôle : sans flag autoritaire, la route n'est pas refusée par le garde-fou PR2."""
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    monkeypatch.setenv("LIFI_AUTHORITATIVE_EXECUTION_ENABLED", "false")
    pe = make_linked_client(db, email="legacy-submit@example.com")
    _seed_wallet(db, pe)

    res = client.post(
        f"/api/swaps/{uuid4()}/submit",
        headers=_auth_headers(db, pe),
        json={"tx_hash": _tx_hash()},
    )
    # Peut échouer pour d'autres raisons (swap introuvable), mais jamais via le garde-fou PR2.
    if res.status_code == 409:
        assert res.json()["detail"].get("code") != "swap.server_authoritative"
