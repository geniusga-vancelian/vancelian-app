"""One-shot cleanup: reduce test sandbox to canonical minimal state.

Preserves:
  - 1 provider: Modulr
  - 1 PE client (référence canonique ci-dessous, plus de « client test » / fichier courant)
  - 1 client EUR account (on Modulr)
  - 1 settlement EUR account
  - crypto_custody_accounts + balances
  - bundles / templates / products

Removes:
  - All Bank-* providers
  - All exchange-*@example.com test clients
  - All orphan client_deposit_accounts + balances

Usage:
  cd arquantix && python3 -m api.scripts.cleanup_sandbox
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path


def _ensure_api_path():
    api_dir = Path(__file__).resolve().parent.parent
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))
    import os
    os.chdir(api_dir)


_ensure_api_path()

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from database import SessionLocal
from sqlalchemy import text


CURRENT_CLIENT_ID = "e34ff297-ba21-44b9-9d49-a2305b21d59a"
MODULR_PROVIDER_ID = "817eed08-1109-459a-b704-bf6a01d9bf56"
CURRENT_CLIENT_ACCOUNT_ID = "ead746c7-322e-421b-bbec-6aa055719f6b"
SETTLEMENT_ACCOUNT_ID = "9a6e0406-99ed-43d9-8adc-3e5fd05b29fc"


def run():
    # Ancien fichier `.current_test_client_id` supprimé — l’identité mobile = JWT + inscription.
    print("1. (obsolète) plus d’écriture .current_test_client_id")

    db = SessionLocal()
    try:

        # 2. Delete runtime financial data (FK-safe order)
        for table in [
            "loan_interest_accruals",
            "loans",
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
        ]:
            r = db.execute(text(f"DELETE FROM public.{table}"))
            print(f"2. {table}: deleted {r.rowcount}")
            db.commit()

        # 3. Delete balances for non-canonical accounts
        r = db.execute(text("""
            DELETE FROM public.custody_account_balances
            WHERE account_id NOT IN (
                SELECT id FROM public.custody_accounts
                WHERE id = :acc OR id = :sett
            )
        """), {"acc": uuid.UUID(CURRENT_CLIENT_ACCOUNT_ID), "sett": uuid.UUID(SETTLEMENT_ACCOUNT_ID)})
        print(f"3. non-canonical custody_account_balances: deleted {r.rowcount}")
        db.commit()

        # 4. Delete non-canonical client deposit accounts
        r = db.execute(text("""
            DELETE FROM public.custody_accounts
            WHERE account_type = 'client_deposit_account'
              AND id != :acc
        """), {"acc": uuid.UUID(CURRENT_CLIENT_ACCOUNT_ID)})
        print(f"4. non-canonical client_deposit_accounts: deleted {r.rowcount}")
        db.commit()

        # 5. Delete pe_ledger_accounts for non-current clients
        r = db.execute(text("""
            DELETE FROM public.pe_ledger_accounts
            WHERE client_id IS NOT NULL
              AND client_id != :cid
        """), {"cid": uuid.UUID(CURRENT_CLIENT_ID)})
        print(f"5. non-current pe_ledger_accounts: deleted {r.rowcount}")
        db.commit()

        # 6. Delete non-current pe_clients
        r = db.execute(text("""
            DELETE FROM public.pe_clients WHERE id != :cid
        """), {"cid": uuid.UUID(CURRENT_CLIENT_ID)})
        print(f"6. non-current pe_clients: deleted {r.rowcount}")
        db.commit()

        # 7. Delete non-Modulr providers
        r = db.execute(text("""
            DELETE FROM public.custody_providers WHERE id != :mid
        """), {"mid": uuid.UUID(MODULR_PROVIDER_ID)})
        print(f"7. non-Modulr custody_providers: deleted {r.rowcount}")
        db.commit()

        # 8. Reset canonical balances to zero
        r = db.execute(text("""
            UPDATE public.custody_account_balances
            SET available_balance = 0, pending_balance = 0, version = version + 1
        """))
        print(f"8. custody_account_balances reset: {r.rowcount}")
        db.commit()

        # Verify
        print("\n=== VERIFICATION ===")
        providers = db.execute(text("SELECT count(*) FROM public.custody_providers")).scalar()
        clients = db.execute(text("SELECT count(*) FROM public.pe_clients")).scalar()
        cda = db.execute(text(
            "SELECT count(*) FROM public.custody_accounts WHERE account_type = 'client_deposit_account'"
        )).scalar()
        csa = db.execute(text(
            "SELECT count(*) FROM public.custody_accounts WHERE account_type = 'company_settlement_account'"
        )).scalar()
        crypto = db.execute(text("SELECT count(*) FROM public.crypto_custody_accounts")).scalar()
        bal = db.execute(text("SELECT count(*) FROM public.custody_account_balances")).scalar()
        print(f"  custody_providers: {providers} (expect 1)")
        print(f"  pe_clients: {clients} (expect 1)")
        print(f"  client_deposit_account: {cda} (expect 1)")
        print(f"  company_settlement_account: {csa} (expect 1)")
        print(f"  crypto_custody_accounts: {crypto} (preserved)")
        print(f"  custody_account_balances: {bal}")
        all_ok = providers == 1 and clients == 1 and cda == 1 and csa == 1
        print(f"\n{'ALL OK' if all_ok else 'ISSUES DETECTED'}")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
