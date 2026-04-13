"""Enums for the Portfolios module (Portfolio Engine)."""
from enum import Enum


class PortfolioType(str, Enum):
    SINGLE_ASSET_WALLET = "single_asset_wallet"
    DIRECT_PORTFOLIO = "direct_portfolio"
    BUNDLE_PORTFOLIO = "bundle_portfolio"
    YIELD_PORTFOLIO = "yield_portfolio"
    STRUCTURED_PORTFOLIO = "structured_portfolio"
    MANAGED_PORTFOLIO = "managed_portfolio"
    ADVISORY_PORTFOLIO = "advisory_portfolio"


class PortfolioStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
