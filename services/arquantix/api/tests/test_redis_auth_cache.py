"""PR G — Redis cache distribué (identité, risque, RL) avec fallback local."""
from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from services.auth.identity_cache import (
    CachedUserIdentity,
    clear_identity_cache_for_tests,
    get_user_identity_cached,
    set_user_identity_cache,
)
from services.auth.redis_metrics import get_redis_metrics, reset_redis_metrics_for_tests
from services.auth.risk_cache import (
    get_risk_cache_payload,
    maybe_cache_risk_evaluation_result,
    risk_evaluation_result_to_payload,
    set_risk_cache_payload,
)
from services.auth.device_risk_engine_pr_f import RiskEvaluationContext, RiskEvaluationResult


class _FakeRedis:
    """Client Redis minimal pour tests (sans serveur)."""

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}

    def get(self, key: str):
        return self.kv.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.kv[key] = value

    def set(self, key: str, value: str, ex: int | None = None, nx: bool = False):
        if nx and key in self.kv:
            return None
        self.kv[key] = value
        return True

    def incr(self, key: str) -> int:
        cur = int(self.kv.get(key) or 0) + 1
        self.kv[key] = str(cur)
        return cur

    def expire(self, key: str, _ttl: int) -> None:
        pass

    def delete(self, key: str) -> None:
        self.kv.pop(key, None)


@pytest.fixture(autouse=True)
def _reset_caches():
    clear_identity_cache_for_tests()
    reset_redis_metrics_for_tests()
    yield
    clear_identity_cache_for_tests()
    reset_redis_metrics_for_tests()


def test_identity_redis_hit(monkeypatch):
    monkeypatch.setenv("REDIS_ENABLED", "true")
    fake = _FakeRedis()
    pid, cid = uuid4(), uuid4()
    ident = CachedUserIdentity(person_id=pid, client_id=cid, email="a@b.c", zero_trust_role="admin")
    raw = (
        '{"person_id":"%s","client_id":"%s","email":"a@b.c","zero_trust_role":"admin"}'
        % (str(pid), str(cid))
    )
    fake.kv["auth:user:7"] = raw
    with patch("services.auth.identity_cache.get_redis_client", return_value=fake):
        out = get_user_identity_cached(7)
        assert isinstance(out, CachedUserIdentity)
        assert out.person_id == pid
    m = get_redis_metrics()
    assert m["redis_hit"] >= 1


def test_identity_fallback_local_when_redis_none(monkeypatch):
    monkeypatch.setenv("REDIS_ENABLED", "true")
    ident = CachedUserIdentity(person_id=uuid4(), client_id=uuid4(), email="x@y.z", zero_trust_role="admin")
    set_user_identity_cache(3, ident)
    with patch("services.auth.identity_cache.get_redis_client", return_value=None):
        out = get_user_identity_cached(3)
        assert isinstance(out, CachedUserIdentity)
        assert out.email == "x@y.z"


def test_risk_cache_roundtrip(monkeypatch):
    monkeypatch.setenv("REDIS_ENABLED", "true")
    monkeypatch.setenv("DEVICE_RISK_CACHE_TTL_SEC", "10")
    fake = _FakeRedis()
    ctx = RiskEvaluationContext(
        device_trust_level="HIGH",
        attestation_absent=False,
        attestation_stale=False,
        last_ip="1.1.1.1",
        current_ip="1.1.1.1",
        last_country="FR",
        current_country="FR",
        velocity_count=0,
        signature_failure_count=0,
        device_churn_distinct_24h=0,
        session_is_new=False,
        login_failures_recent=0,
        refresh_failures_recent=0,
        current_hour_utc=10,
        weekday_utc=2,
        session_duration_sec=60.0,
        action_type="login",
        amount_eur=None,
    )
    r = RiskEvaluationResult(score=22, decision="allow", context=ctx, risk_reasons=["x"])
    with patch("services.auth.risk_cache.get_redis_client", return_value=fake):
        set_risk_cache_payload(1, "dev-1", risk_evaluation_result_to_payload(r))
        raw = get_risk_cache_payload(1, "dev-1")
        assert raw is not None
        assert raw["score"] == 22
        assert raw["decision"] == "allow"


def test_maybe_cache_skips_dry_run_payload(monkeypatch):
    monkeypatch.setenv("REDIS_ENABLED", "true")
    fake = _FakeRedis()
    ctx = RiskEvaluationContext(
        device_trust_level="HIGH",
        attestation_absent=False,
        attestation_stale=False,
        last_ip=None,
        current_ip=None,
        last_country=None,
        current_country=None,
        velocity_count=0,
        signature_failure_count=0,
        device_churn_distinct_24h=0,
        session_is_new=False,
        login_failures_recent=0,
        refresh_failures_recent=0,
        current_hour_utc=0,
        weekday_utc=0,
        session_duration_sec=0.0,
        action_type="unknown",
        amount_eur=None,
    )
    r = RiskEvaluationResult(
        score=10,
        decision="allow",
        context=ctx,
        risk_reasons=[],
        dry_run_result={"would_trigger": "t", "would_action": "BLOCK"},
    )
    with patch("services.auth.risk_cache.get_redis_client", return_value=fake):
        maybe_cache_risk_evaluation_result(1, "d", r, allow=True)
    assert len(fake.kv) == 0


def test_rate_limit_redis_incr(monkeypatch):
    monkeypatch.setenv("REDIS_ENABLED", "true")
    monkeypatch.setenv("DEVICE_SIGNATURE_FAILURE_RL_REDIS", "true")
    from services.auth.rate_limit_redis import redis_increment_signature_failure, redis_get_signature_failure_count

    fake = _FakeRedis()
    with patch("services.auth.rate_limit_redis.get_redis_client", return_value=fake):
        n1 = redis_increment_signature_failure(5, "iphone")
        n2 = redis_increment_signature_failure(5, "iphone")
        assert n1 == 1 and n2 == 2
        assert redis_get_signature_failure_count(5, "iphone") == 2


def test_redis_disabled_no_keys(monkeypatch):
    monkeypatch.delenv("REDIS_ENABLED", raising=False)
    fake = _FakeRedis()
    with patch("services.auth.risk_cache.get_redis_client", return_value=fake):
        set_risk_cache_payload(1, "x", {"score": 1, "decision": "allow", "risk_reasons": []})
    assert len(fake.kv) == 0
