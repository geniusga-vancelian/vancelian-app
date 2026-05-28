"""Tests garde-fous mocks DeFi en production (Phase 1 P0)."""
from __future__ import annotations

import pytest

from services.security.production_mock_guard import (
    collect_production_mock_violations,
    enforce_production_mock_guard,
)


def test_collect_violations_empty_by_default(monkeypatch):
    monkeypatch.delenv("LIFI_SWAPS_MOCK", raising=False)
    monkeypatch.delenv("BUNDLE_LIFI_SYNC_MOCK", raising=False)
    assert collect_production_mock_violations() == []


def test_collect_violations_lifi_swaps_mock(monkeypatch):
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "true")
    assert "LIFI_SWAPS_MOCK" in collect_production_mock_violations()


def test_collect_violations_bundle_lifi_sync_mock(monkeypatch):
    monkeypatch.setenv("BUNDLE_LIFI_SYNC_MOCK", "1")
    assert "BUNDLE_LIFI_SYNC_MOCK" in collect_production_mock_violations()


def test_enforce_raises_in_production_with_lifi_mock(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "true")
    monkeypatch.delenv("BUNDLE_LIFI_SYNC_MOCK", raising=False)
    with pytest.raises(RuntimeError, match="LIFI_SWAPS_MOCK"):
        enforce_production_mock_guard(testing=False)


def test_enforce_raises_in_production_with_bundle_mock(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("BUNDLE_LIFI_SYNC_MOCK", "yes")
    monkeypatch.delenv("LIFI_SWAPS_MOCK", raising=False)
    with pytest.raises(RuntimeError, match="BUNDLE_LIFI_SYNC_MOCK"):
        enforce_production_mock_guard(testing=False)


def test_enforce_skips_when_testing(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "true")
    enforce_production_mock_guard(testing=True)


def test_enforce_skips_in_development(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "true")
    enforce_production_mock_guard(testing=False)
