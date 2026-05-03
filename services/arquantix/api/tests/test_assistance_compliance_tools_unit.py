"""Tests unitaires des tools compliance — Phase 2a.

Couvre :
  - `repositories.compliance_repo.fetch_client_status_summary` (public).
  - `repositories.compliance_repo.fetch_safe_signals` (gated, anti-tipping-off).
  - `repositories.compliance_repo.fetch_compliance_state_snapshot` (agrégateur).
  - `tools.compliance.read_compliance_state.execute` (tool L0 introspectif).

Aucune dépendance Postgres : on mocke la session SQLAlchemy avec
`MagicMock` et on configure le retour des chaînes
`db.query(...).filter(...).one_or_none()`.

Spec de référence : `MULTI_AGENTS_RUNTIME.md` § 5.2 (filtrage matériel).
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.compliance import (
    read_compliance_state,
    read_documents,
    read_external_aml_signals,
    read_registration_progress,
    read_transactions,
)
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared.classify_actor import ActorKind


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _ctx(
    *,
    client_id: str | None = None,
    person_id: str | None = None,
    actor_kind: ActorKind = ActorKind.CUSTOMER,
    db: MagicMock | None = None,
) -> ToolContext:
    return ToolContext(
        db=db or MagicMock(),
        client_id=client_id,
        person_id=person_id,
        user_id=42,
        actor_kind=actor_kind,
        agent_id="compliance",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-1234",
    )


def _db_returning(*, status_row, risk_row=None, user_id_row=None) -> MagicMock:
    """Build un mock de Session qui dispatche selon la query.

    Stratégie naive : on configure `one_or_none` à retourner les valeurs
    dans l'ordre des appels successifs (status_summary puis risk).
    """
    db = MagicMock()
    seq = []
    if user_id_row is not None:
        seq.append(user_id_row)
    if status_row is not None:
        seq.append(status_row)
    if risk_row is not None:
        seq.append(risk_row)

    def _next(*_a, **_kw):
        return seq.pop(0) if seq else None

    db.query.return_value.filter.return_value.one_or_none.side_effect = _next
    db.query.return_value.outerjoin.return_value.filter.return_value.one_or_none.side_effect = (
        _next
    )
    db.query.return_value.join.return_value.filter.return_value.one_or_none.side_effect = (
        _next
    )
    return db


# ─────────────────────────────────────────────────────────────────────────
# A. fetch_client_status_summary — non-leak public info
# ─────────────────────────────────────────────────────────────────────────


class TestClientStatusSummary:
    def test_returns_defaults_when_client_id_invalid(self):
        result = compliance_repo.fetch_client_status_summary(
            MagicMock(), client_id="not-a-uuid"
        )
        assert result == {
            "client_status": None,
            "kyc_status": None,
            "account_state": None,
            "login_frozen": None,
        }

    def test_returns_defaults_when_client_id_none(self):
        result = compliance_repo.fetch_client_status_summary(
            MagicMock(), client_id=None
        )
        assert result["client_status"] is None
        assert result["kyc_status"] is None

    def test_returns_normalized_row(self):
        db = MagicMock()
        db.query.return_value.outerjoin.return_value.filter.return_value.one_or_none.return_value = (
            "active",
            "approved",
            "ACTIVE",
            False,
        )
        cid = uuid4()
        result = compliance_repo.fetch_client_status_summary(db, client_id=cid)
        assert result == {
            "client_status": "active",
            "kyc_status": "approved",
            "account_state": "ACTIVE",
            "login_frozen": False,
        }

    def test_returns_login_frozen_true(self):
        db = MagicMock()
        db.query.return_value.outerjoin.return_value.filter.return_value.one_or_none.return_value = (
            "active",
            "approved",
            "BLOCKED",
            True,
        )
        cid = uuid4()
        result = compliance_repo.fetch_client_status_summary(db, client_id=cid)
        assert result["login_frozen"] is True
        assert result["account_state"] == "BLOCKED"

    def test_db_error_returns_defaults_no_exception(self):
        db = MagicMock()
        db.query.side_effect = RuntimeError("db down")
        cid = uuid4()
        result = compliance_repo.fetch_client_status_summary(db, client_id=cid)
        assert result["client_status"] is None


# ─────────────────────────────────────────────────────────────────────────
# B. fetch_safe_signals — anti-tipping-off (LE TEST CRITIQUE)
# ─────────────────────────────────────────────────────────────────────────


class TestSafeSignalsGating:
    """Toutes les valeurs sensibles doivent être absentes du retour."""

    def test_no_risk_score_in_payload_low_level(self):
        db = MagicMock()
        # 1ère query: user_id resolution → 42; 2ème: level=LOW
        db.query.return_value.join.return_value.filter.return_value.one_or_none.return_value = (
            42,
        )
        db.query.return_value.filter.return_value.one_or_none.return_value = (
            "LOW",
        )
        result = compliance_repo.fetch_safe_signals(db, client_id=uuid4())
        # Le retour ne contient que les 3 clés safe
        assert set(result.keys()) == {
            "requires_doc_upload",
            "requires_step_up",
            "client_facing_message",
        }
        # LOW → pas de demande
        assert result["requires_doc_upload"] is False
        assert result["requires_step_up"] is False
        assert result["client_facing_message"] is None

    def test_medium_level_triggers_step_up_only(self):
        db = MagicMock()
        db.query.return_value.join.return_value.filter.return_value.one_or_none.return_value = (
            42,
        )
        db.query.return_value.filter.return_value.one_or_none.return_value = (
            "MEDIUM",
        )
        result = compliance_repo.fetch_safe_signals(db, client_id=uuid4())
        assert result["requires_doc_upload"] is False
        assert result["requires_step_up"] is True
        assert result["client_facing_message"] is None

    def test_high_level_triggers_doc_upload_and_step_up(self):
        db = MagicMock()
        db.query.return_value.join.return_value.filter.return_value.one_or_none.return_value = (
            42,
        )
        db.query.return_value.filter.return_value.one_or_none.return_value = (
            "HIGH",
        )
        result = compliance_repo.fetch_safe_signals(db, client_id=uuid4())
        assert result["requires_doc_upload"] is True
        assert result["requires_step_up"] is True
        assert isinstance(result["client_facing_message"], str)
        # Le message client-facing est neutre (anti-tipping-off)
        msg = result["client_facing_message"].lower()
        for forbidden in ("risk", "fraude", "watchlist", "high", "kyc", "aml"):
            assert forbidden not in msg

    def test_orphaned_client_returns_neutral_signals(self):
        """Si la chaîne client → admin_users casse, signaux neutres."""
        db = MagicMock()
        db.query.return_value.join.return_value.filter.return_value.one_or_none.return_value = (
            None
        )
        result = compliance_repo.fetch_safe_signals(db, client_id=uuid4())
        assert result["requires_doc_upload"] is False
        assert result["requires_step_up"] is False
        assert result["client_facing_message"] is None

    def test_no_risk_row_returns_neutral_signals(self):
        db = MagicMock()
        db.query.return_value.join.return_value.filter.return_value.one_or_none.return_value = (
            42,
        )
        db.query.return_value.filter.return_value.one_or_none.return_value = None
        result = compliance_repo.fetch_safe_signals(db, client_id=uuid4())
        assert result == {
            "requires_doc_upload": False,
            "requires_step_up": False,
            "client_facing_message": None,
        }

    def test_invalid_client_id_returns_neutral_signals(self):
        result = compliance_repo.fetch_safe_signals(
            MagicMock(), client_id="not-a-uuid"
        )
        assert result["requires_doc_upload"] is False

    def test_db_error_returns_neutral_signals(self):
        db = MagicMock()
        db.query.side_effect = RuntimeError("db boom")
        result = compliance_repo.fetch_safe_signals(db, client_id=uuid4())
        assert result["requires_doc_upload"] is False
        assert result["client_facing_message"] is None


# ─────────────────────────────────────────────────────────────────────────
# C. read_compliance_state.execute — tool L0
# ─────────────────────────────────────────────────────────────────────────


class TestReadComplianceStateTool:
    def test_returns_partial_payload_when_no_client_id(self):
        ctx = _ctx(client_id=None, actor_kind=ActorKind.ONBOARDING)
        result = read_compliance_state.execute(ctx)
        assert result["actor_kind"] == "onboarding"
        assert result["client"]["client_status"] is None
        assert result["safe_signals"]["requires_doc_upload"] is False

    def test_returns_full_payload_for_customer(self, monkeypatch):
        ctx = _ctx(client_id=str(uuid4()), actor_kind=ActorKind.CUSTOMER)

        fake_snapshot = {
            "status": {
                "client_status": "active",
                "kyc_status": "approved",
                "account_state": "ACTIVE",
                "login_frozen": False,
            },
            "safe_signals": {
                "requires_doc_upload": False,
                "requires_step_up": False,
                "client_facing_message": None,
            },
        }
        monkeypatch.setattr(
            compliance_repo,
            "fetch_compliance_state_snapshot",
            lambda *a, **kw: fake_snapshot,
        )

        result = read_compliance_state.execute(ctx)
        assert result["actor_kind"] == "customer"
        assert result["client"]["kyc_status"] == "approved"
        assert result["safe_signals"]["requires_doc_upload"] is False

    def test_repo_error_returns_safe_default(self, monkeypatch):
        ctx = _ctx(client_id=str(uuid4()))

        def _bomb(*a, **kw):
            raise RuntimeError("boom")

        monkeypatch.setattr(
            compliance_repo, "fetch_compliance_state_snapshot", _bomb
        )

        result = read_compliance_state.execute(ctx)
        assert result.get("error") == "repo_unavailable"
        assert result["safe_signals"]["requires_doc_upload"] is False

    def test_spec_metadata(self):
        spec = read_compliance_state.SPEC
        assert spec["type"] == "function"
        assert spec["autonomy_level"] == "L0"
        assert spec["agent_id"] == "compliance"
        assert spec["function"]["name"] == "read_compliance_state"
        assert spec["function"]["parameters"]["properties"] == {}

    def test_tool_payload_never_leaks_blacklisted_terms(self, monkeypatch):
        """Même avec un repo qui renvoie des données pourries, le tool ne
        doit jamais introduire de terme tipping-off de son côté."""
        ctx = _ctx(client_id=str(uuid4()))

        # On feinte un repo qui retourne des champs OK
        monkeypatch.setattr(
            compliance_repo,
            "fetch_compliance_state_snapshot",
            lambda *a, **kw: {
                "status": {
                    "client_status": "active",
                    "kyc_status": "rejected",
                    "account_state": "PARTIAL",
                    "login_frozen": True,
                },
                "safe_signals": {
                    "requires_doc_upload": True,
                    "requires_step_up": True,
                    "client_facing_message": "Téléverse tes pièces.",
                },
            },
        )

        result = read_compliance_state.execute(ctx)
        import json as _json

        payload_str = _json.dumps(result, ensure_ascii=False).lower()
        # Le tool n'introduit AUCUN terme blacklisté de lui-même
        for forbidden in (
            "risk_score",
            "level_high",
            "watchlist",
            "ofac",
            "fraude",
            "blanchiment",
            "soupcon",
        ):
            assert forbidden not in payload_str


# ─────────────────────────────────────────────────────────────────────────
# D. read_registration_progress
# ─────────────────────────────────────────────────────────────────────────


class TestReadRegistrationProgressTool:
    def test_no_person_id_returns_empty_payload(self):
        ctx = _ctx(client_id=None, person_id=None, actor_kind=ActorKind.ADMIN_BO)
        r = read_registration_progress.execute(ctx)
        assert r["session_status"] is None
        assert r["completed_steps"] == 0

    def test_with_person_id_calls_repo(self, monkeypatch):
        ctx = _ctx(person_id=str(uuid4()), actor_kind=ActorKind.ONBOARDING)
        monkeypatch.setattr(
            compliance_repo,
            "fetch_registration_progress",
            lambda *a, **kw: {
                "session_status": "in_progress",
                "current_step_id": "step-uuid",
                "completed_steps": 3,
                "total_steps_recorded": 5,
                "last_activity_at": "2026-05-02T10:00:00Z",
            },
        )
        r = read_registration_progress.execute(ctx)
        assert r["session_status"] == "in_progress"
        assert r["completed_steps"] == 3

    def test_repo_error_returns_safe(self, monkeypatch):
        ctx = _ctx(person_id=str(uuid4()))

        def _bomb(*a, **kw):
            raise RuntimeError("x")

        monkeypatch.setattr(
            compliance_repo, "fetch_registration_progress", _bomb
        )
        r = read_registration_progress.execute(ctx)
        assert r.get("error") == "repo_unavailable"

    def test_spec_metadata(self):
        spec = read_registration_progress.SPEC
        assert spec["autonomy_level"] == "L0"
        assert spec["function"]["name"] == "read_registration_progress"


# ─────────────────────────────────────────────────────────────────────────
# E. read_documents
# ─────────────────────────────────────────────────────────────────────────


class TestReadDocumentsTool:
    def test_no_person_id_returns_empty(self):
        ctx = _ctx(person_id=None)
        r = read_documents.execute(ctx)
        assert r["total_count"] == 0
        assert r["by_type"] == {}

    def test_aggregates_via_repo(self, monkeypatch):
        ctx = _ctx(person_id=str(uuid4()))
        monkeypatch.setattr(
            compliance_repo,
            "fetch_documents_summary",
            lambda *a, **kw: {
                "total_count": 4,
                "by_type": {"id_proof": 2, "address_proof": 2},
                "by_status": {"approved": 2, "pending_review": 2},
                "latest_uploaded_at": "2026-05-01T12:00:00Z",
            },
        )
        r = read_documents.execute(ctx)
        assert r["total_count"] == 4
        assert r["by_status"]["approved"] == 2

    def test_repo_summary_never_leaks_storage(self, monkeypatch):
        """La structure de retour ne doit jamais contenir storage_*."""
        ctx = _ctx(person_id=str(uuid4()))
        monkeypatch.setattr(
            compliance_repo,
            "fetch_documents_summary",
            lambda *a, **kw: {
                "total_count": 1,
                "by_type": {"id_proof": 1},
                "by_status": {"approved": 1},
                "latest_uploaded_at": None,
            },
        )
        r = read_documents.execute(ctx)
        keys = set(r.keys())
        for forbidden in (
            "storage_bucket",
            "storage_key",
            "storage_provider",
            "metadata_json",
        ):
            assert forbidden not in keys


# ─────────────────────────────────────────────────────────────────────────
# F. read_transactions
# ─────────────────────────────────────────────────────────────────────────


class TestReadTransactionsTool:
    def test_no_client_id_returns_empty(self):
        ctx = _ctx(client_id=None)
        r = read_transactions.execute(ctx)
        assert r["orders_count"] == 0
        assert r["recent_order_ids"] == []

    def test_calls_repo_with_limit(self, monkeypatch):
        ctx = _ctx(client_id=str(uuid4()))
        captured = {}

        def _capture(db, *, client_id, limit):
            captured["limit"] = limit
            return {
                "orders_count": 7,
                "by_status": {"completed": 5, "pending": 2},
                "last_order_at": None,
                "recent_order_ids": [],
            }

        monkeypatch.setattr(
            compliance_repo, "fetch_transactions_summary", _capture
        )
        r = read_transactions.execute(ctx, limit=10)
        assert captured["limit"] == 10
        assert r["orders_count"] == 7

    def test_default_limit_is_25(self, monkeypatch):
        ctx = _ctx(client_id=str(uuid4()))
        captured = {}

        def _capture(db, *, client_id, limit):
            captured["limit"] = limit
            return {
                "orders_count": 0,
                "by_status": {},
                "last_order_at": None,
                "recent_order_ids": [],
            }

        monkeypatch.setattr(
            compliance_repo, "fetch_transactions_summary", _capture
        )
        read_transactions.execute(ctx)
        assert captured["limit"] == 25


# ─────────────────────────────────────────────────────────────────────────
# G. read_external_aml_signals (mock provider — Phase 2a)
# ─────────────────────────────────────────────────────────────────────────


class TestReadExternalAmlSignalsTool:
    def test_returns_mock_provider_safe_payload(self):
        ctx = _ctx(person_id=str(uuid4()))
        r = read_external_aml_signals.execute(ctx)
        assert r["kyc_provider"] == "mock"
        assert r["watchlist_status"] == "approved"
        # Aucun terme blacklisté ne doit apparaître
        import json as _json

        payload = _json.dumps(r, ensure_ascii=False).lower()
        for forbidden in (
            "ofac",
            "pep",
            "watchlist_match",
            "risk_score",
            "fraud",
            "fraude",
            "blanchiment",
        ):
            assert forbidden not in payload

    def test_no_person_id_still_safe(self):
        ctx = _ctx(person_id=None)
        r = read_external_aml_signals.execute(ctx)
        assert r["kyc_provider"] == "mock"
        assert isinstance(r.get("flags"), list)

    def test_spec_metadata(self):
        spec = read_external_aml_signals.SPEC
        assert spec["autonomy_level"] == "L0"
        assert spec["agent_id"] == "compliance"
