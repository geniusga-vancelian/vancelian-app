"""Enums for the Products module (Portfolio Engine — catalog layer)."""
from enum import Enum


class ProductType(str, Enum):
    CRYPTO_BUNDLE = "crypto_bundle"
    YIELD_VAULT = "yield_vault"
    STRATEGY_PORTFOLIO = "strategy_portfolio"
    SAVINGS_PLAN = "savings_plan"


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class RiskLabel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
