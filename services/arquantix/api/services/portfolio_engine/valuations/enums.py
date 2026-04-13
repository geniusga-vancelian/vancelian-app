"""Enums for the Valuation Engine (Phase 5)."""


class ValuationSource:
    ON_DEMAND = "on_demand_snapshot"
    SCHEDULED = "scheduled_snapshot"
    MANUAL_REBUILD = "manual_rebuild"


class PricingStatus:
    PRICED = "priced"
    UNPRICED = "unpriced"
