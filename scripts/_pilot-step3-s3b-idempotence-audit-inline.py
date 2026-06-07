"""Audit idempotence S3b vs crédit webhook — swap 6996ea11 (lecture seule)."""
import json
import sys

from sqlalchemy import text

from database import SessionLocal
from services.lifi.lifi_swap_reconciliation import detect_swap_ledger_legs
from services.lifi.lifi_swap_settlement import (
    swap_credit_idempotency_key,
    swap_debit_idempotency_key,
)
from services.lifi.models import PersonWalletSwap
from services.settlement.lifi_ledger import _ledger_leg_exists

SWAP_ID = "6996ea11-aab1-4460-98fc-ea1ed4f7283c"
TX_HASH = "0x782a53355bab16e1df08252dc7bda92ccc7a30bc7129214e84c20403dfcc420c"


def main() -> None:
    db = SessionLocal()
    try:
        swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == SWAP_ID).first()
        if not swap:
            print(json.dumps({"error": "swap_not_found"}))
            sys.exit(1)

        debit_key = swap_debit_idempotency_key(SWAP_ID)
        credit_key = swap_credit_idempotency_key(SWAP_ID)

        s3b_debit_exists = _ledger_leg_exists(db, debit_key)
        s3b_credit_key_exists = _ledger_leg_exists(db, credit_key)

        legs = detect_swap_ledger_legs(db, swap)

        tx_deposits = [
            dict(r._mapping)
            for r in db.execute(
                text(
                    """
                    SELECT id::text, idempotency_key, direction, asset, amount,
                           transaction_kind,
                           metadata_json->>'source' AS meta_source
                    FROM person_wallet_deposits
                    WHERE person_id = :pid
                      AND lower(tx_hash) = lower(:tx)
                    ORDER BY created_at
                    """
                ),
                {"pid": str(swap.person_id), "tx": TX_HASH},
            )
        ]

        would_write_debit = not legs.debit_exists
        would_write_credit = not legs.credit_exists

        report = {
            "phase": "s3b_idempotence_audit",
            "swap_id": SWAP_ID,
            "tx_hash": TX_HASH,
            "s3b_lifi_swap_keys": {
                "debit_key": debit_key,
                "credit_key": credit_key,
                "debit_key_exists": s3b_debit_exists,
                "credit_key_exists": s3b_credit_key_exists,
            },
            "s3b_effective_legs_detect_swap_ledger_legs": {
                "debit_exists": legs.debit_exists,
                "credit_exists": legs.credit_exists,
                "credit_amount": str(legs.credit_amount) if legs.credit_amount is not None else None,
                "credit_source": legs.credit_source,
                "credit_deposit_id": str(legs.credit_deposit_id) if legs.credit_deposit_id else None,
                "would_write_debit": would_write_debit,
                "would_write_credit": would_write_credit,
            },
            "deposits_on_tx_hash": tx_deposits,
            "verdict": (
                "UNSAFE_DOUBLE_CREDIT_RISK"
                if (would_write_credit and legs.credit_exists is False and any(
                    d.get("direction") == "credit" and d.get("asset", "").upper() == str(swap.to_asset).upper()
                    for d in tx_deposits
                ))
                else (
                    "SAFE_WEBHOOK_CREDIT_REUSE"
                    if (legs.credit_exists and not s3b_credit_key_exists)
                    else (
                        "SAFE_NO_DOUBLE_CREDIT"
                        if not would_write_credit or s3b_credit_key_exists
                        else "SAFE_NO_PRIOR_CREDIT"
                    )
                )
            ),
            "explanation": (
                "Post-patch S3b: crédit webhook détecté via detect_swap_ledger_legs — "
                "settlement créera uniquement le débit si manquant."
                if (legs.credit_exists and not s3b_credit_key_exists)
                else (
                    "S3b apply_lifi_standalone_ledger_settlement() ne consulte que "
                    "find_by_deposit_idempotency_key(lifi-swap:{swap_id}:credit). "
                    "Un crédit webhook (autre clé) n'empêche pas l'insert S3b."
                    if (would_write_credit and not legs.credit_exists)
                    else "Pas de risque double crédit détecté."
                )
            ),
        }
        print(json.dumps(report, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
