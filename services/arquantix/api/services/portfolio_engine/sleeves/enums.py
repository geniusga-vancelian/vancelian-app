"""Enums for the Sleeves module (Portfolio Engine)."""
from enum import Enum


class SleeveType(str, Enum):
    CORE = "core"
    SATELLITE = "satellite"
    YIELD = "yield"
    ALTERNATIVE = "alternative"
    CASH = "cash"
