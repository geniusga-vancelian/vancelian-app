"""Tests structured bundle invest preview warnings."""
from __future__ import annotations

from services.portfolio_engine.bundle_execution.bundle_lifi_validation import (
    BundleLifiValidationError,
)
from services.portfolio_engine.bundles.preview_warnings import (
    build_exchange_preview_warning,
    build_lifi_preview_warning,
    build_lifi_preview_warning_from_exc,
    parse_preview_warning,
)


def test_build_and_parse_lifi_preview_warning():
    raw = build_lifi_preview_warning(
        asset="CBBTC",
        display="cbBTC",
        code="bundle.lifi.quote_failed",
        detail="Route unavailable",
    )
    parsed = parse_preview_warning(raw)
    assert parsed["kind"] == "lifi_preview_failed"
    assert parsed["asset"] == "CBBTC"
    assert parsed["display"] == "cbBTC"
    assert parsed["code"] == "bundle.lifi.quote_failed"
    assert parsed["detail"] == "Route unavailable"


def test_build_lifi_preview_warning_from_exc():
    exc = BundleLifiValidationError("bundle.lifi.quote_failed", "LI.FI timeout")
    raw = build_lifi_preview_warning_from_exc(asset="CBETH", display="cbETH", exc=exc)
    parsed = parse_preview_warning(raw)
    assert parsed["code"] == "bundle.lifi.quote_failed"
    assert parsed["detail"] == "LI.FI timeout"


def test_build_exchange_preview_warning_encodes_detail():
    raw = build_exchange_preview_warning(
        asset="CBBTC",
        display="cbBTC",
        detail="market_quote_stale: cbBTC quote is old",
    )
    parsed = parse_preview_warning(raw)
    assert parsed["kind"] == "exchange_preview_failed"
    assert "market_quote_stale" in parsed["detail"]
