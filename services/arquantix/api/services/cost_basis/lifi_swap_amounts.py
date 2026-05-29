"""Montants réellement exécutés pour swaps Li.FI (sans prix spot si possible)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from services.privy_wallet.enums import PersonWalletDirection
from services.privy_wallet.models import PersonWalletDeposit


def _dec(v: object) -> Decimal | None:
    if v is None:
        return None
    try:
        val = Decimal(str(v))
        return val if val > 0 else None
    except Exception:
        return None


def amount_out_from_audit_log(swap) -> tuple[Decimal | None, str]:
    """Lit ``actual_receive_amount`` depuis l'audit swap (post-settlement)."""
    for entry in reversed(swap.audit_log or []):
        if not isinstance(entry, dict):
            continue
        for key in ("actual_receive_amount", "amount_actual"):
            val = _dec(entry.get(key))
            if val is not None:
                source = str(entry.get("event") or entry.get("source") or "audit_log")
                return val, f"audit:{source}"
    return None, ""


def amount_out_from_ledger(db: Session, swap) -> tuple[Decimal | None, str]:
    """Crédit ledger Privy lié au swap (``swap_amount_to`` / ``amount_actual``)."""
    swap_id = str(swap.id)
    to_asset = str(swap.to_asset).upper()
    rows = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.person_id == swap.person_id,
            PersonWalletDeposit.asset == to_asset,
            PersonWalletDeposit.direction == PersonWalletDirection.CREDIT.value,
            PersonWalletDeposit.transaction_kind == "crypto_swap",
        )
        .order_by(PersonWalletDeposit.confirmed_at.desc(), PersonWalletDeposit.created_at.desc())
        .limit(50)
        .all()
    )
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        if str(meta.get("swap_id") or "") != swap_id:
            continue
        for key in ("swap_amount_to", "amount_actual", "actual_receive_amount"):
            val = _dec(meta.get(key))
            if val is not None:
                return val, f"ledger:{key}"
        val = _dec(row.amount)
        if val is not None:
            return val, "ledger:amount"
    return None, ""


def resolve_lifi_swap_amount_out(
    db: Session,
    swap,
    *,
    allow_onchain_resolve: bool = False,
    allow_mock_quote_amount: bool = False,
) -> tuple[Decimal, str]:
    """Résout ``amount_out`` pour ingestion / backfill cost basis.

    Priorité : audit settlement → ledger → quote enregistrée → résolution on-chain/API.
    """
    from services.lifi.lifi_actual_receive import resolve_lifi_actual_receive_amount

    audited, src = amount_out_from_audit_log(swap)
    if audited is not None:
        return audited, src

    ledger, src = amount_out_from_ledger(db, swap)
    if ledger is not None:
        return ledger, src

    quoted = _dec(swap.estimated_receive)
    if quoted is not None:
        return quoted, "swap:estimated_receive"

    if allow_onchain_resolve:
        resolved = resolve_lifi_actual_receive_amount(
            db,
            swap,
            allow_mock_quote_amount=allow_mock_quote_amount,
        )
        if resolved is not None and resolved.amount > 0:
            return resolved.amount, f"resolve:{resolved.source}"

    raise ValueError("amount_out_unavailable")
