"""Tests configuration LI.FI."""
from services.lifi.config import (
    DEFAULT_LIFI_INTEGRATOR_ID,
    lifi_api_configured,
    lifi_api_key,
    lifi_fee_bps,
    lifi_integrator_id,
    lifi_quote_base_params,
    lifi_request_headers,
)


def test_lifi_api_configured_when_env_set(monkeypatch):
    monkeypatch.setenv("LIFI_API_KEY", "test-key-123")
    assert lifi_api_configured() is True
    assert lifi_api_key() == "test-key-123"


def test_lifi_api_not_configured_when_missing(monkeypatch):
    monkeypatch.delenv("LIFI_API_KEY", raising=False)
    assert lifi_api_configured() is False


def test_lifi_integrator_defaults_to_vancelian_finance(monkeypatch):
    monkeypatch.delenv("LIFI_INTEGRATOR_ID", raising=False)
    assert lifi_integrator_id() == DEFAULT_LIFI_INTEGRATOR_ID


def test_lifi_quote_params_include_integrator(monkeypatch):
    monkeypatch.setenv("LIFI_INTEGRATOR_ID", "vancelian.finance")
    params = lifi_quote_base_params(fromChain=1, toChain=1)
    assert params["integrator"] == "vancelian.finance"
    assert params["fromChain"] == 1


def test_lifi_request_headers_include_api_key(monkeypatch):
    monkeypatch.setenv("LIFI_API_KEY", "secret-key")
    headers = lifi_request_headers()
    assert headers["x-lifi-api-key"] == "secret-key"


def test_lifi_fee_bps_default(monkeypatch):
    monkeypatch.delenv("LIFI_FEE_BPS", raising=False)
    assert lifi_fee_bps() == 25
