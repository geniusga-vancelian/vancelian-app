#!/usr/bin/env python3
"""
CLI pour le reset complet de l'état financier de test (custody + flux crypto/EUR).

- NE supprime PAS : schéma, tables, providers, comptes, clients, ledger_accounts,
  produits/templates/bundles/portfolio engine.
- REMET À ZÉRO : transactions, webhooks, ledger entries, orders, positions,
  settlement deltas; remet les balances custody à 0.

Usage (depuis la racine du repo ou depuis api/) :
  python -m api.scripts.reset_financial_test_state
  python -m api.scripts.reset_financial_test_state --dry-run
  python api/scripts/reset_financial_test_state.py

Environnement : DATABASE_URL doit être défini (.env.local / .env).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Quand on exécute le script en CLI, s'assurer que api est sur le path
def _ensure_api_path():
    api_dir = Path(__file__).resolve().parent.parent
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    os.chdir(api_dir)
    try:
        from dotenv import load_dotenv
        for p in (api_dir / ".env.local", api_dir / ".env"):
            if p.exists():
                load_dotenv(p)
                break
    except ImportError:
        pass


def print_report(report: dict) -> None:
    """Affiche le rapport structuré."""
    from services.financial_reset import TABLES_DELETE_ORDER

    print()
    print("=" * 60)
    print("FINANCIAL TEST STATE RESET REPORT")
    print("=" * 60)
    if report.get("dry_run"):
        print("(DRY RUN - aucune modification)")
    print()

    print("1. BEFORE (row counts)")
    print("-" * 40)
    for table in TABLES_DELETE_ORDER + ["custody_account_balances", "custody_accounts"]:
        v = report.get("before", {}).get(table)
        print(f"  {table}: {v}")
    v = report.get("before", {}).get("custody_total_eur")
    print(f"  custody_total_eur (sum): {v}")
    by_type = report.get("before", {}).get("custody_accounts_by_type") or {}
    if by_type:
        print("  custody_accounts by type:", by_type)
    print()

    if not report.get("dry_run"):
        print("2. DELETED (rows)")
        print("-" * 40)
        for table in TABLES_DELETE_ORDER:
            v = report.get("deleted", {}).get(table)
            print(f"  {table}: {v}")
        print(f"  custody_account_balances (updated to 0): {report.get('balances_updated')}")
        print()

    print("3. AFTER (row counts)")
    print("-" * 40)
    if report.get("dry_run"):
        print("  (N/A - dry run, no changes applied)")
    else:
        for table in TABLES_DELETE_ORDER + ["custody_account_balances", "custody_accounts"]:
            v = report.get("after", {}).get(table)
            print(f"  {table}: {v}")
        v = report.get("after", {}).get("custody_total_eur")
        print(f"  custody_total_eur (sum): {v}")
        by_type = report.get("after", {}).get("custody_accounts_by_type") or {}
        if by_type:
            print("  custody_accounts by type (preserved):", by_type)
    print()

    if report.get("errors"):
        print("4. ERRORS")
        print("-" * 40)
        for e in report["errors"]:
            print(f"  - {e}")
        print()

    print("5. FINAL STATUS")
    print("-" * 40)
    if report.get("success"):
        print("  Reset completed successfully.")
        print("  - custody_accounts: preserved")
        print("  - custody_account_balances: preserved (balances set to 0)")
        print("  - custody_transactions: 0")
        print("  - custody_webhook_events: 0")
        print("  - pe_ledger_entries: 0")
        print("  - exchange_orders: 0")
        print("  - crypto_positions: 0")
        print("  - crypto_settlement_deltas: 0")
        print("  - Total EUR balance: 0")
        print()
        print("  You can now run clean end-to-end fiat/crypto tests.")
    else:
        print("  Reset completed with errors. Check section 4.")
    print("=" * 60)


def main() -> None:
    import argparse
    _ensure_api_path()

    from services.financial_reset import run_reset

    parser = argparse.ArgumentParser(description="Reset financial test state (custody + crypto/EUR flows)")
    parser.add_argument("--dry-run", action="store_true", help="Count only, do not delete or update")
    args = parser.parse_args()

    if not os.getenv("DATABASE_URL"):
        print("ERROR: DATABASE_URL is not set. Use .env.local or .env in the api directory.")
        sys.exit(1)

    report = run_reset(dry_run=args.dry_run)
    print_report(report)
    sys.exit(0 if report["success"] else 1)


if __name__ == "__main__":
    main()
