"""
Reset complet de l'état financier de test — version 2.

Supprime TOUTE l'activité client (transactions, orders, positions, alertes,
notifications, audit, envelopes, commitments, chatbot sessions, …) tout en
PRÉSERVANT la configuration :

  CONSERVÉ :
    ├── Identité          pe_clients, persons, pe_advisor_client_assignments
    ├── Comptes           custody_accounts, custody_providers, crypto_custody_accounts
    ├── Portfolios        pe_portfolios, pe_sleeves, pe_wallet_containers
    ├── Produits          pe_product_definitions, pe_portfolio_templates,
    │                     pe_template_allocations, pe_target_allocations,
    │                     pe_product_subscriptions
    ├── Stratégies        pe_strategy_definitions, pe_strategy_instances,
    │                     pe_rebalance_policies, pe_risk_policies
    ├── Fees              pe_trading_fee_configs, exchange_fee_config
    ├── Ledger struct     pe_ledger_accounts
    ├── Référentiels      pe_instruments, pe_assets
    ├── Bundles           bundles, bundle_components
    ├── Lending (config)  lending_pools (stats reset), lending_pool_products (raised reset)
    ├── Market data       market_data_* tables
    ├── CMS               pages, news, global_settings, admin_users
    ├── Système           pe_scheduled_jobs, app_runtime_settings, field_definitions,
    │                     jurisdiction_configs, chatbot_prompt_versions, email_*
    └── Backtest          backtest_* tables

  PURGÉ :
    ├── Envelopes         investment_envelope_entries, investment_envelopes
    ├── Pool lending      pool_allocations, pool_borrow_positions, pool_supply_commitments
    ├── Pool interest     borrower/lender_interest_accruals, pool_interest_snapshots
    ├── P2P lending       loan_interest_accruals, loans
    ├── Custody fiat      custody_webhook_events, custody_transactions, pe_ledger_entries
    ├── PE trades         pe_settlement_instructions, pe_trades, pe_execution_instructions
    ├── PE positions      pe_position_valuations, pe_position_relations, pe_position_atoms
    ├── PE valuations     pe_portfolio_return_series, pe_portfolio_valuations
    ├── PE orchestration  pe_rebalance_preview_items, pe_orchestration_runs,
    │                     pe_rebalance_previews, pe_strategy_evaluations
    ├── PE orders         pe_orders
    ├── Exchange/crypto   exchange_orders, crypto_positions, crypto_settlement_deltas
    ├── Alertes           notifications, price_alerts
    ├── Audit             pe_audit_events, audit_events
    ├── Opérationnel      pe_idempotency_keys, pe_job_runs, pe_reconciliation_reports
    ├── Chatbot           chatbot_portfolio_proposals, chatbot_audit_events,
    │                     chatbot_conversation_turns, chatbot_sessions, chatbot_profiles
    └── Soumissions       documents, contact_submissions

  REMIS À ZÉRO :
    ├── custody_account_balances  → available/pending = 0
    ├── crypto_custody_balances   → actual/expected = 0
    ├── lending_pools             → total_committed/borrowed/utilization = 0
    ├── lending_pool_products     → current_raised = 0, status → fundraising (si actif)
    └── Redis                     → alerts:* + notif_dedup:* keys
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import text

from database import SessionLocal

logger = logging.getLogger(__name__)


# FK-safe deletion order: children before parents.
TABLES_DELETE_ORDER = [
    # ── Envelope (Phase 2A.16) ────────────────────────────
    "investment_envelope_entries",
    "investment_envelopes",
    # ── Pool interest ─────────────────────────────────────
    "borrower_interest_accruals",
    "lender_interest_accruals",
    "pool_interest_snapshots",
    # ── Pool lending activity (NOT pools/products — those are config) ──
    "pool_allocations",
    "pool_borrow_positions",
    "pool_supply_commitments",
    # ── P2P Lending ───────────────────────────────────────
    "loan_interest_accruals",
    "loans",
    # ── Custody / fiat ────────────────────────────────────
    "custody_webhook_events",
    "custody_transactions",
    "pe_ledger_entries",
    # ── PE trades & execution ─────────────────────────────
    "pe_settlement_instructions",
    "pe_trades",
    "pe_execution_instructions",
    # ── PE positions ──────────────────────────────────────
    "pe_position_valuations",
    "pe_position_relations",
    "pe_position_atoms",
    # ── PE valuations ─────────────────────────────────────
    "pe_portfolio_return_series",
    "pe_portfolio_valuations",
    # ── PE orchestration ──────────────────────────────────
    "pe_rebalance_preview_items",
    "pe_orchestration_runs",
    "pe_rebalance_previews",
    "pe_strategy_evaluations",
    # ── PE orders ─────────────────────────────────────────
    "pe_orders",
    # ── Exchange / crypto ─────────────────────────────────
    "exchange_orders",
    "crypto_positions",
    "crypto_settlement_deltas",
    # ── Alerts & notifications ────────────────────────────
    "notifications",
    "price_alerts",
    # ── Favorites (FK → pe_clients) ───────────────────────
    "client_favorites",
    # ── Audit ─────────────────────────────────────────────
    "pe_audit_events",
    "audit_events",
    # ── Operational runtime ───────────────────────────────
    "pe_idempotency_keys",
    "pe_job_runs",
    "pe_reconciliation_reports",
    # ── Chatbot sessions ──────────────────────────────────
    "chatbot_portfolio_proposals",
    "chatbot_audit_events",
    "chatbot_conversation_turns",
    "chatbot_sessions",
    "chatbot_profiles",
    # ── User-generated content ────────────────────────────
    "documents",
    "contact_submissions",
]

# Tables for counting (activity + balance tables)
COUNTED_TABLES = TABLES_DELETE_ORDER + [
    "custody_account_balances",
    "custody_accounts",
    "crypto_custody_accounts",
    "crypto_custody_balances",
    "lending_pools",
    "lending_pool_products",
]


def _safe_count(db, table: str) -> int | None:
    try:
        r = db.execute(text(f"SELECT COUNT(*) FROM public.{table}"))
        return r.scalar() or 0
    except Exception:
        db.rollback()
        return None


def _safe_delete(db, table: str) -> tuple[int | None, str | None]:
    try:
        r = db.execute(text(f"DELETE FROM public.{table}"))
        count = r.rowcount
        db.commit()
        return count, None
    except Exception as e:
        db.rollback()
        err_str = str(e)
        if "does not exist" in err_str or "UndefinedTable" in err_str:
            return 0, None
        return None, f"delete {table}: {e}"


def _purge_redis() -> tuple[int, list[str]]:
    errors = []
    purged = 0
    try:
        from services.redis_client import get_redis
        r = get_redis()
        if r is None:
            return 0, ["Redis unavailable — alert cache not purged"]

        for pattern in ("alerts:*", "notif_dedup:*"):
            cursor = 0
            while True:
                cursor, keys = r.scan(cursor=cursor, match=pattern, count=500)
                if keys:
                    r.delete(*keys)
                    purged += len(keys)
                if cursor == 0:
                    break
    except Exception as e:
        errors.append(f"purge redis: {e}")

    return purged, errors


def run_reset(dry_run: bool = False) -> dict:
    """
    Exécute le reset et retourne un rapport (counts avant/après, erreurs).
    Utilisable depuis le script CLI ou l'endpoint admin.
    """
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    report: dict = {
        "dry_run": dry_run,
        "before": {},
        "after": {},
        "deleted": {},
        "balances_updated": 0,
        "crypto_balances_updated": 0,
        "lending_pools_reset": 0,
        "lending_products_reset": 0,
        "redis_keys_purged": 0,
        "errors": [],
        "success": False,
        "account_types_preserved": {},
    }
    try:
        # ─── 1. Comptages avant ─────────────────────────────
        for table in COUNTED_TABLES:
            report["before"][table] = _safe_count(db, table)

        # Somme balances EUR
        try:
            r = db.execute(text("""
                SELECT COALESCE(SUM(available_balance), 0) + COALESCE(SUM(pending_balance), 0)
                FROM public.custody_account_balances cab
                JOIN public.custody_accounts ca ON ca.id = cab.account_id
                WHERE ca.currency = 'EUR'
            """))
            report["before"]["custody_total_eur"] = float(r.scalar() or 0)
        except Exception as e:
            report["before"]["custody_total_eur"] = None
            report["errors"].append(f"sum EUR before: {e}")

        # Somme crypto custody
        try:
            r = db.execute(text("""
                SELECT COALESCE(SUM(actual_balance), 0), COALESCE(SUM(expected_balance), 0)
                FROM public.crypto_custody_balances
            """))
            row = r.fetchone()
            report["before"]["crypto_total_actual"] = float(row[0])
            report["before"]["crypto_total_expected"] = float(row[1])
        except Exception as e:
            report["before"]["crypto_total_actual"] = None
            report["before"]["crypto_total_expected"] = None
            report["errors"].append(f"sum crypto before: {e}")

        # Comptes par type
        try:
            r = db.execute(text("""
                SELECT account_type, COUNT(*) FROM public.custody_accounts
                GROUP BY account_type
            """))
            report["before"]["custody_accounts_by_type"] = {
                row[0]: row[1] for row in r.fetchall()
            }
        except Exception as e:
            report["before"]["custody_accounts_by_type"] = {}
            report["errors"].append(f"count by account_type: {e}")

        # Lending stats
        try:
            r = db.execute(text("""
                SELECT COUNT(*),
                       COALESCE(SUM(current_raised), 0),
                       COUNT(*) FILTER (WHERE status NOT IN ('draft', 'closed'))
                FROM public.lending_pool_products
            """))
            row = r.fetchone()
            report["before"]["lending_products_count"] = row[0]
            report["before"]["lending_total_raised"] = float(row[1])
            report["before"]["lending_active_products"] = row[2]
        except Exception:
            pass

        # ─── DRY RUN → return report ────────────────────────
        if dry_run:
            report["success"] = True
            report["after"] = report["before"].copy()
            report["account_types_preserved"] = report["before"].get(
                "custody_accounts_by_type"
            ) or {}
            return report

        # ─── 2. Suppressions dans l'ordre FK ────────────────
        for table in TABLES_DELETE_ORDER:
            count, err = _safe_delete(db, table)
            report["deleted"][table] = count
            if err:
                report["errors"].append(err)

        # ─── 3. Purge Redis ─────────────────────────────────
        purged, redis_errs = _purge_redis()
        report["redis_keys_purged"] = purged
        report["errors"].extend(redis_errs)

        # ─── 4. Reset balances custody fiat → 0 ─────────────
        try:
            r = db.execute(text("""
                UPDATE public.custody_account_balances
                SET available_balance = 0,
                    pending_balance = 0,
                    version = version + 1,
                    last_updated_at = :now
            """), {"now": now})
            report["balances_updated"] = r.rowcount
            db.commit()
        except Exception as e:
            db.rollback()
            report["errors"].append(f"update custody_account_balances: {e}")

        # ─── 5. Reset balances crypto custody → 0 ───────────
        try:
            r = db.execute(text("""
                UPDATE public.crypto_custody_balances
                SET actual_balance = 0,
                    expected_balance = 0,
                    updated_from_provider_at = NULL,
                    updated_at = :now
            """), {"now": now})
            report["crypto_balances_updated"] = r.rowcount
            db.commit()
        except Exception as e:
            db.rollback()
            report["errors"].append(f"update crypto_custody_balances: {e}")

        # ─── 6. Reset lending_pools stats → 0 ───────────────
        try:
            r = db.execute(text("""
                UPDATE public.lending_pools
                SET total_committed = 0,
                    total_borrowed = 0,
                    utilization_rate = 0,
                    updated_at = :now
            """), {"now": now})
            report["lending_pools_reset"] = r.rowcount
            db.commit()
        except Exception as e:
            db.rollback()
            report["errors"].append(f"update lending_pools: {e}")

        # ─── 7. Reset lending_pool_products → fundraising ───
        #   current_raised = 0
        #   status → fundraising (pour tout produit qui avait de l'activité)
        try:
            r = db.execute(text("""
                UPDATE public.lending_pool_products
                SET current_raised = 0,
                    status = CASE
                        WHEN status IN ('funded', 'active', 'repaid') THEN 'fundraising'
                        ELSE status
                    END,
                    updated_at = :now
            """), {"now": now})
            report["lending_products_reset"] = r.rowcount
            db.commit()
        except Exception as e:
            db.rollback()
            report["errors"].append(f"update lending_pool_products: {e}")

        # ─── 8. Comptages après ─────────────────────────────
        for table in COUNTED_TABLES:
            report["after"][table] = _safe_count(db, table)

        try:
            r = db.execute(text("""
                SELECT COALESCE(SUM(available_balance), 0) + COALESCE(SUM(pending_balance), 0)
                FROM public.custody_account_balances cab
                JOIN public.custody_accounts ca ON ca.id = cab.account_id
                WHERE ca.currency = 'EUR'
            """))
            report["after"]["custody_total_eur"] = float(r.scalar() or 0)
        except Exception:
            report["after"]["custody_total_eur"] = None

        try:
            r = db.execute(text("""
                SELECT COALESCE(SUM(actual_balance), 0), COALESCE(SUM(expected_balance), 0)
                FROM public.crypto_custody_balances
            """))
            row = r.fetchone()
            report["after"]["crypto_total_actual"] = float(row[0])
            report["after"]["crypto_total_expected"] = float(row[1])
        except Exception:
            report["after"]["crypto_total_actual"] = None
            report["after"]["crypto_total_expected"] = None

        try:
            r = db.execute(text("""
                SELECT account_type, COUNT(*) FROM public.custody_accounts
                GROUP BY account_type
            """))
            report["after"]["custody_accounts_by_type"] = {
                row[0]: row[1] for row in r.fetchall()
            }
            report["account_types_preserved"] = report["after"]["custody_accounts_by_type"]
        except Exception:
            report["after"]["custody_accounts_by_type"] = {}
            report["account_types_preserved"] = {}

        try:
            r = db.execute(text("""
                SELECT COUNT(*),
                       COALESCE(SUM(current_raised), 0),
                       COUNT(*) FILTER (WHERE status NOT IN ('draft', 'closed'))
                FROM public.lending_pool_products
            """))
            row = r.fetchone()
            report["after"]["lending_products_count"] = row[0]
            report["after"]["lending_total_raised"] = float(row[1])
            report["after"]["lending_active_products"] = row[2]
        except Exception:
            pass

        report["success"] = len(report["errors"]) == 0
        return report
    finally:
        db.close()
