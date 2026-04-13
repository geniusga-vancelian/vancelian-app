"""Tests for the financial test state reset (v2).

Verifies:
- dry_run report structure covers all activity + balance tables
- TABLES_DELETE_ORDER never includes structural/config tables
- full reset zeroes crypto_custody_balances while preserving accounts
- lending_pools and lending_pool_products are PRESERVED but stats reset
"""
import os
import sys
from pathlib import Path

import pytest


def _import_reset_module():
    api_dir = Path(__file__).resolve().parent.parent
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    try:
        from services.financial_reset import run_reset, TABLES_DELETE_ORDER
        return run_reset, TABLES_DELETE_ORDER
    except ImportError:
        from api.services.financial_reset import run_reset, TABLES_DELETE_ORDER
        return run_reset, TABLES_DELETE_ORDER


def test_reset_dry_run_report_structure():
    """Run reset in dry-run and assert report has expected keys and success."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set; skip reset test")
    run_reset, _ = _import_reset_module()

    report = run_reset(dry_run=True)

    assert "dry_run" in report
    assert report["dry_run"] is True
    assert "before" in report
    assert "success" in report
    assert report["success"] is True

    required_tables = [
        "custody_webhook_events",
        "custody_transactions",
        "pe_ledger_entries",
        "pe_position_valuations",
        "pe_position_relations",
        "pe_position_atoms",
        "pe_portfolio_return_series",
        "pe_portfolio_valuations",
        "pe_rebalance_preview_items",
        "pe_orchestration_runs",
        "pe_rebalance_previews",
        "pe_strategy_evaluations",
        "pe_orders",
        "exchange_orders",
        "crypto_positions",
        "crypto_settlement_deltas",
        "notifications",
        "price_alerts",
        "investment_envelopes",
        "investment_envelope_entries",
        "pool_supply_commitments",
        "pool_borrow_positions",
        "pool_allocations",
        "custody_account_balances",
        "custody_accounts",
        "crypto_custody_accounts",
        "crypto_custody_balances",
        "lending_pools",
        "lending_pool_products",
    ]
    for t in required_tables:
        assert t in report["before"], f"missing before count for {t}"

    assert "custody_total_eur" in report["before"]
    assert "crypto_total_actual" in report["before"]
    assert "crypto_total_expected" in report["before"]


def test_reset_deleted_tables_constant():
    """Ensure TABLES_DELETE_ORDER never includes referential/config tables."""
    _, TABLES_DELETE_ORDER = _import_reset_module()

    forbidden = {
        # Identity
        "pe_clients", "persons", "pe_advisor_client_assignments",
        # Accounts (structure)
        "custody_accounts", "custody_providers", "crypto_custody_accounts",
        "crypto_custody_balances", "custody_account_balances",
        # Portfolios & products (config)
        "pe_portfolios", "pe_sleeves", "pe_wallet_containers",
        "pe_product_definitions", "pe_portfolio_templates",
        "pe_template_allocations", "pe_target_allocations",
        "pe_product_subscriptions",
        # Strategies
        "pe_strategy_definitions", "pe_strategy_instances",
        "pe_rebalance_policies", "pe_risk_policies",
        # Fees
        "pe_trading_fee_configs", "exchange_fee_config",
        # Ledger structure
        "pe_ledger_accounts",
        # Referentials
        "pe_instruments", "pe_assets",
        # Bundles (config)
        "bundles", "bundle_components",
        # Lending (config — preserved with stats reset)
        "lending_pools", "lending_pool_products",
        # Market data
        "market_data_instruments", "market_data_latest_quotes",
        "market_data_bars_1d", "market_data_bars_d1",
        # CMS
        "pages", "news", "global_settings", "admin_users",
        # System
        "pe_scheduled_jobs", "app_runtime_settings",
    }
    for t in TABLES_DELETE_ORDER:
        assert t not in forbidden, f"Reset must NOT delete config table: {t}"


def test_reset_preserves_lending_config():
    """After reset, lending_pools and lending_pool_products rows still exist."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set")

    from dotenv import load_dotenv
    api_dir = Path(__file__).resolve().parent.parent
    load_dotenv(api_dir / ".env.local")
    load_dotenv(api_dir / ".env")

    from database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        pools_before = db.execute(
            text("SELECT COUNT(*) FROM public.lending_pools")
        ).scalar()
        products_before = db.execute(
            text("SELECT COUNT(*) FROM public.lending_pool_products")
        ).scalar()
    except Exception:
        pytest.skip("lending tables not available")
    finally:
        db.close()

    if pools_before == 0 and products_before == 0:
        pytest.skip("No lending config to test")

    run_reset, _ = _import_reset_module()
    report = run_reset(dry_run=False)

    assert report.get("success") is True

    db = SessionLocal()
    try:
        pools_after = db.execute(
            text("SELECT COUNT(*) FROM public.lending_pools")
        ).scalar()
        products_after = db.execute(
            text("SELECT COUNT(*) FROM public.lending_pool_products")
        ).scalar()

        assert pools_after == pools_before, (
            f"lending_pools rows deleted: {pools_before} → {pools_after}"
        )
        assert products_after == products_before, (
            f"lending_pool_products rows deleted: {products_before} → {products_after}"
        )

        raised = db.execute(
            text("SELECT COALESCE(SUM(current_raised), 0) FROM public.lending_pool_products")
        ).scalar()
        assert float(raised) == 0.0, f"current_raised not reset: {raised}"

        committed = db.execute(
            text("SELECT COALESCE(SUM(total_committed), 0) FROM public.lending_pools")
        ).scalar()
        assert float(committed) == 0.0, f"total_committed not reset: {committed}"
    finally:
        db.close()


def test_reset_zeroes_crypto_custody_balances(client, db):
    """Full reset zeros crypto_custody_balances while preserving account rows."""
    ADMIN_HEADERS = {"X-User-Role": "admin", "X-User-Email": "admin@test.com"}

    client.post("/api/admin/exchange/crypto-custody/bootstrap", headers=ADMIN_HEADERS)

    list_res = client.get("/api/admin/exchange/crypto-custody", headers=ADMIN_HEADERS)
    accounts_before = list_res.json().get("accounts", [])
    if not accounts_before:
        pytest.skip("No crypto custody accounts to test")

    sw = next((a for a in accounts_before if a["account_type"] == "settlement_wallet"), None)
    if sw:
        client.post(
            f"/api/admin/exchange/crypto-custody/{sw['id']}/set-actual-balance",
            json={"actual_balance": "999.5"},
            headers=ADMIN_HEADERS,
        )

    reset_res = client.post(
        "/api/admin/custody/reset-financial-test-state",
        headers=ADMIN_HEADERS,
    )
    assert reset_res.status_code == 200
    report = reset_res.json()

    assert report["success"] is True
    assert report["crypto_balances_updated"] > 0

    assert report["before"]["crypto_custody_accounts"] == report["after"]["crypto_custody_accounts"]
    assert report["before"]["crypto_custody_balances"] == report["after"]["crypto_custody_balances"]

    assert report["after"]["crypto_total_actual"] == 0.0
    assert report["after"]["crypto_total_expected"] == 0.0

    list_after = client.get("/api/admin/exchange/crypto-custody", headers=ADMIN_HEADERS)
    for acct in list_after.json().get("accounts", []):
        assert float(acct.get("actual_balance", 0)) == 0.0
        assert float(acct.get("expected_balance", 0)) == 0.0
        assert float(acct.get("mismatch", 0)) == 0.0
