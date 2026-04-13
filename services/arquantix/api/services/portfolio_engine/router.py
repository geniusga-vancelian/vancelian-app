"""
Aggregated API router for the Portfolio Engine.
Prefix: /api/portfolio-engine
"""
from fastapi import APIRouter

from .clients.router import router as clients_router
from .products.catalog_router import router as product_catalog_router
from .products.router import router as products_router
from .templates.router import templates_router, allocations_router as template_allocations_router
from .subscriptions.router import router as subscriptions_router
from .assets.router import router as assets_router
from .instruments.router import router as instruments_router
from .portfolios.router import router as portfolios_router
from .sleeves.router import router as sleeves_router
from .wallets.router import router as wallets_router
from .positions.router import router as positions_router
from .relations.router import router as relations_router
from .strategies.router import definitions_router as strategy_definitions_router
from .strategies.router import instances_router as strategy_instances_router
from .allocations.router import router as allocations_router
from .rebalancing.router import router as rebalancing_router
from .risk.router import router as risk_router
from .rebalance_preview.router import router as rebalance_preview_router
from .execution.router import router as execution_router
from .valuations.router import router as valuations_router
from .snapshots.router import router as snapshots_router
from .summary.router import router as summary_router
from .ledger_accounts.router import router as ledger_accounts_router
from .ledger_entries.router import router as ledger_entries_router
from .orders.router import router as orders_router
from .trades.router import router as trades_router
from .settlement.router import router as settlement_router
from .trading_fees.router import router as trading_fees_router
from .drift.router import router as drift_router
from .strategy_engine.router import router as strategy_engine_router
from .orchestrator.router import router as orchestrator_router
from .performance.router import router as performance_router
from .hardening.jobs.router import router as admin_jobs_router
from .hardening.reconciliation.router import router as admin_recon_router
from .hardening.scheduler.router import router as admin_scheduler_router
from .hardening.authorization.router import router as admin_authz_router
from .bundles.router import router as bundles_router

router = APIRouter(prefix="/api/portfolio-engine", tags=["portfolio-engine"])

router.include_router(clients_router, prefix="/clients", tags=["portfolio-clients"])
router.include_router(product_catalog_router, prefix="/product-catalog", tags=["portfolio-products"])
router.include_router(products_router, prefix="/products", tags=["portfolio-products"])
router.include_router(templates_router, prefix="/portfolio-templates", tags=["portfolio-templates"])
router.include_router(template_allocations_router, prefix="/template-allocations", tags=["portfolio-template-allocations"])
router.include_router(subscriptions_router, prefix="/subscriptions", tags=["portfolio-subscriptions"])
router.include_router(assets_router, prefix="/assets", tags=["portfolio-assets"])
router.include_router(instruments_router, prefix="/instruments", tags=["portfolio-instruments"])
router.include_router(portfolios_router, prefix="/portfolios", tags=["portfolio-portfolios"])
router.include_router(sleeves_router, prefix="/sleeves", tags=["portfolio-sleeves"])
router.include_router(wallets_router, prefix="/wallets", tags=["portfolio-wallets"])
router.include_router(positions_router, prefix="/positions", tags=["portfolio-positions"])
router.include_router(relations_router, prefix="/position-relations", tags=["portfolio-relations"])
router.include_router(strategy_definitions_router, prefix="/strategy-definitions", tags=["portfolio-strategy-definitions"])
router.include_router(strategy_instances_router, prefix="/strategy-instances", tags=["portfolio-strategy-instances"])
router.include_router(allocations_router, prefix="/target-allocations", tags=["portfolio-allocations"])
router.include_router(rebalancing_router, prefix="/rebalance-policies", tags=["portfolio-rebalancing"])
router.include_router(risk_router, prefix="/risk-policies", tags=["portfolio-risk"])
router.include_router(rebalance_preview_router, prefix="/rebalance-preview", tags=["portfolio-rebalance-preview"])
router.include_router(execution_router, prefix="/executions", tags=["portfolio-executions"])
router.include_router(valuations_router, tags=["portfolio-valuations"])
router.include_router(snapshots_router, prefix="/snapshots", tags=["portfolio-snapshots"])
router.include_router(summary_router, tags=["portfolio-summary"])
router.include_router(ledger_accounts_router, prefix="/ledger-accounts", tags=["portfolio-ledger-accounts"])
router.include_router(ledger_entries_router, prefix="/ledger-entries", tags=["portfolio-ledger-entries"])
router.include_router(orders_router, prefix="/orders", tags=["portfolio-orders"])
router.include_router(trades_router, prefix="/trades", tags=["portfolio-trades"])
router.include_router(settlement_router, prefix="/settlements", tags=["portfolio-settlements"])
router.include_router(trading_fees_router, prefix="/trading-fees", tags=["portfolio-trading-fees"])
router.include_router(drift_router, tags=["portfolio-drift"])
router.include_router(strategy_engine_router, tags=["portfolio-strategy-engine"])
router.include_router(orchestrator_router, tags=["portfolio-orchestrator"])
router.include_router(performance_router, tags=["portfolio-performance"])
router.include_router(admin_jobs_router, prefix="/admin", tags=["portfolio-admin"])
router.include_router(admin_recon_router, prefix="/admin", tags=["portfolio-admin"])
router.include_router(admin_scheduler_router, prefix="/admin", tags=["portfolio-admin"])
router.include_router(admin_authz_router, prefix="/admin", tags=["portfolio-admin"])
router.include_router(bundles_router, prefix="/admin", tags=["portfolio-bundles"])
