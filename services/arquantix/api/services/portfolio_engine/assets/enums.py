"""Enums for the Assets module (Portfolio Engine registry layer)."""
from enum import Enum


class AssetType(str, Enum):
    CRYPTO = "crypto"
    STABLECOIN = "stablecoin"
    FIAT = "fiat"
    REAL_ESTATE = "real_estate"
    PRIVATE_EQUITY = "private_equity"
    TOKENIZED_SECURITY = "tokenized_security"
    DERIVATIVE = "derivative"


class LiquidityProfile(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ILLIQUID = "illiquid"


class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"
