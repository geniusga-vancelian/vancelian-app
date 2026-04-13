"""Enums for the Position Relations module (Portfolio Engine — relation layer)."""
from enum import Enum


class RelationType(str, Enum):
    SETTLES_INTO = "settles_into"
    COLLATERALIZES = "collateralizes"
    FUNDS = "funds"
    DERIVED_FROM = "derived_from"
    DEPENDS_ON = "depends_on"
    HEDGES = "hedges"
    REWARDS_FROM = "rewards_from"
