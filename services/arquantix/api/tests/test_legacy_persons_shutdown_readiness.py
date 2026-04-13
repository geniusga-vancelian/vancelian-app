"""Phase 4C.4 — readiness shutdown legacy persons."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from services.persons.legacy_persons_metrics import LEGACY_PERSONS_ENDPOINT_HIT_TOTAL
from services.persons.legacy_persons_shutdown_readiness import (
    LegacyPersonsShutdownReadinessConfig,
    _compute_confidence_score,
    evaluate_legacy_persons_shutdown_readiness,
    summarize_traffic_from_metrics_snapshot,
)
from tests.conftest import make_admin_headers

_EMPTY = {
    "metric": LEGACY_PERSONS_ENDPOINT_HIT_TOTAL,
    LEGACY_PERSONS_ENDPOINT_HIT_TOTAL: 0,
    "series": [],
}

_UNAUTH_GET = {
    "metric": LEGACY_PERSONS_ENDPOINT_HIT_TOTAL,
    LEGACY_PERSONS_ENDPOINT_HIT_TOTAL: 2,
    "series": [
        {
            "labels": {
                "endpoint_name": "GET /api/persons/{person_id}",
                "method": "GET",
                "authenticated": "false",
                "caller_category": "unauthenticated",
                "allow_legacy_unauthenticated_kyc": "true",
            },
            "value": 2,
        }
    ],
}

_ADMIN_ONLY = {
    "metric": LEGACY_PERSONS_ENDPOINT_HIT_TOTAL,
    LEGACY_PERSONS_ENDPOINT_HIT_TOTAL: 100,
    "series": [
        {
            "labels": {
                "endpoint_name": "GET /api/persons/{person_id}",
                "method": "GET",
                "authenticated": "true",
                "caller_category": "admin",
                "allow_legacy_unauthenticated_kyc": "false",
            },
            "value": 100,
        }
    ],
}

# Cumul élevé (historique) mais fenêtres récentes à zéro — scénario typique post Phase 4C.5.
_SNAPSHOT_HIGH_CUMULATIVE_ZERO_ROLLING = {
    "metric": LEGACY_PERSONS_ENDPOINT_HIT_TOTAL,
    LEGACY_PERSONS_ENDPOINT_HIT_TOTAL: 500,
    "last_24h_hits": 0,
    "last_7d_hits": 0,
    "series": [
        {
            "labels": {
                "endpoint_name": "GET /api/persons/{person_id}",
                "method": "GET",
                "authenticated": "true",
                "caller_category": "admin",
                "allow_legacy_unauthenticated_kyc": "false",
            },
            "value": 500,
        }
    ],
}


class TestEvaluateLegacyPersonsShutdownReadiness:
    def test_ready_true_when_criteria_met(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_EMPTY,
            config=LegacyPersonsShutdownReadinessConfig(),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is True
        assert r.blocking_reasons == []
        assert r.recommendation in ("disable_in_staging_first", "ready_to_disable_production")
        assert r.as_dict()["allow_legacy_unauthenticated_kyc"] is True
        assert r.confidence_score == 1.0
        assert r.confidence_band == "very_safe"

    def test_ready_false_when_unauthenticated_traffic(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_UNAUTH_GET,
            config=LegacyPersonsShutdownReadinessConfig(max_unauthenticated_hits=0),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is False
        assert "unauthenticated_traffic_above_threshold" in r.blocking_reasons
        assert r.recommendation == "keep_enabled"
        assert r.confidence_score == 0.5
        assert r.confidence_band == "caution"

    def test_ready_false_when_total_above_threshold(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_ADMIN_ONLY,
            config=LegacyPersonsShutdownReadinessConfig(
                max_total_hits=50,
                max_admin_hits=-1,
            ),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is False
        assert "total_traffic_above_threshold" in r.blocking_reasons

    def test_ready_false_when_admin_usage_above_threshold(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_ADMIN_ONLY,
            config=LegacyPersonsShutdownReadinessConfig(
                max_total_hits=0,
                max_admin_hits=0,
                max_owner_hits=-1,
            ),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is False
        assert "admin_usage_above_threshold" in r.blocking_reasons

    def test_already_disabled_flag(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_UNAUTH_GET,
            config=LegacyPersonsShutdownReadinessConfig(),
            allow_legacy_kyc_flag=False,
        )
        assert r.ready is True
        assert r.recommendation == "already_disabled"
        assert r.blocking_reasons == []

    def test_manual_override_block(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_EMPTY,
            config=LegacyPersonsShutdownReadinessConfig(manual_override_block=True),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is False
        assert r.blocking_reasons == ["manual_override_block"]
        assert r.confidence_score == 0.0
        assert r.confidence_band == "not_safe"

    def test_manual_override_ready(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_UNAUTH_GET,
            config=LegacyPersonsShutdownReadinessConfig(manual_override_ready=True),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is True
        assert r.recommendation == "manual_override_ready"

    def test_successor_evidence_required(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_EMPTY,
            config=LegacyPersonsShutdownReadinessConfig(
                require_successor_identity_evidence=True,
                min_successor_identity_hits=5,
            ),
            successor_identity_hits=0,
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is False
        assert "insufficient_successor_identity_evidence" in r.blocking_reasons

    def test_output_dict_stable_keys(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_EMPTY,
            config=LegacyPersonsShutdownReadinessConfig(),
            allow_legacy_kyc_flag=True,
        )
        d = r.as_dict()
        assert set(d.keys()) == {
            "ready",
            "confidence_score",
            "confidence_band",
            "blocking_reasons",
            "traffic_summary",
            "recommendation",
            "observation_note",
            "allow_legacy_unauthenticated_kyc",
            "config_effective",
        }
        assert set(d["traffic_summary"].keys()) == {
            "total_hits",
            "unauthenticated_hits",
            "admin_hits",
            "owner_hits",
            "last_24h_hits",
            "last_7d_hits",
        }

    def test_summarize_traffic_consistent(self):
        t = summarize_traffic_from_metrics_snapshot(_UNAUTH_GET)
        assert t["unauthenticated_hits"] == 2
        assert t["total_hits"] == 2
        assert t["last_24h_hits"] == 0
        assert t["last_7d_hits"] == 0

    def test_ready_true_high_cumulative_but_recent_windows_zero(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_SNAPSHOT_HIGH_CUMULATIVE_ZERO_ROLLING,
            config=LegacyPersonsShutdownReadinessConfig(
                max_unauthenticated_hits=0,
                max_total_hits=0,
                max_last_24h_hits=10,
                max_last_7d_hits=50,
            ),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is True
        assert r.traffic_summary["total_hits"] == 500
        assert r.traffic_summary["last_24h_hits"] == 0
        assert r.blocking_reasons == []

    def test_ready_false_when_last_24h_exceeds_threshold(self):
        snap = {
            **_EMPTY,
            "last_24h_hits": 12,
            "last_7d_hits": 5,
        }
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=snap,
            config=LegacyPersonsShutdownReadinessConfig(max_last_24h_hits=10, max_last_7d_hits=100),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is False
        assert "recent_24h_traffic_above_threshold" in r.blocking_reasons
        assert r.recommendation == "keep_enabled"

    def test_ready_false_when_last_7d_exceeds_threshold(self):
        snap = {
            **_EMPTY,
            "last_24h_hits": 1,
            "last_7d_hits": 200,
        }
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=snap,
            config=LegacyPersonsShutdownReadinessConfig(max_last_24h_hits=0, max_last_7d_hits=100),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is False
        assert "recent_7d_traffic_above_threshold" in r.blocking_reasons

    def test_backward_compat_snapshot_without_rolling_keys(self):
        """Anciens snapshots sans clés Phase 4C.5 → 0, seuils 0 = inchangé vs avant."""
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_EMPTY,
            config=LegacyPersonsShutdownReadinessConfig(),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is True
        assert r.traffic_summary["last_24h_hits"] == 0
        assert r.traffic_summary["last_7d_hits"] == 0

    def test_confidence_zero_traffic_is_one(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_EMPTY,
            config=LegacyPersonsShutdownReadinessConfig(),
            allow_legacy_kyc_flag=True,
        )
        assert r.as_dict()["confidence_score"] == 1.0

    def test_confidence_multiple_penalties(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_UNAUTH_GET,
            config=LegacyPersonsShutdownReadinessConfig(
                max_unauthenticated_hits=10,
                max_total_hits=1,
                max_admin_hits=-1,
            ),
            allow_legacy_kyc_flag=True,
        )
        # unauth présent -0.5 ; total 2 > 1 → -0.2 ; ready=false (total) mais score combine les deux
        assert r.ready is False
        assert "total_traffic_above_threshold" in r.blocking_reasons
        assert r.confidence_score == pytest.approx(0.3)

    def test_confidence_clamped_to_zero(self):
        cfg = LegacyPersonsShutdownReadinessConfig(
            max_total_hits=50,
            max_admin_hits=0,
            max_owner_hits=0,
            require_successor_identity_evidence=True,
            min_successor_identity_hits=5,
        )
        traffic = {
            "total_hits": 100,
            "unauthenticated_hits": 1,
            "admin_hits": 1,
            "owner_hits": 1,
            "last_24h_hits": 0,
            "last_7d_hits": 0,
        }
        assert _compute_confidence_score(cfg, traffic, 0) == 0.0

    def test_ready_unchanged_by_confidence_field(self):
        r = evaluate_legacy_persons_shutdown_readiness(
            metrics_snapshot=_UNAUTH_GET,
            config=LegacyPersonsShutdownReadinessConfig(max_unauthenticated_hits=0),
            allow_legacy_kyc_flag=True,
        )
        assert r.ready is False
        assert r.as_dict()["ready"] is False


class TestShutdownReadinessAdminEndpoint:
    def test_requires_auth(self, client: TestClient):
        r = client.get("/admin/security/legacy-persons/shutdown-readiness")
        assert r.status_code == 401

    def test_returns_json_with_headers(self, client: TestClient, db: Session):
        h = make_admin_headers(db)
        r = client.get("/admin/security/legacy-persons/shutdown-readiness", headers=h)
        assert r.status_code == 200
        body = r.json()
        assert "ready" in body and isinstance(body["ready"], bool)
        assert "recommendation" in body
        assert "observation_note" in body
        assert "confidence_score" in body and isinstance(body["confidence_score"], (int, float))
        assert "confidence_band" in body
