"""Annulation de crédits ledger Privy sans preuve on-chain (simulate / mock)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from .admin_service import PrivyWalletAdminService, PrivySimulateDepositError
from .enums import PersonWalletDepositStatus, PersonWalletDirection
from .repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from .schemas import PrivyVoidDepositRequest


@dataclass(frozen=True)
class PhantomDepositRow:
    deposit_id: UUID
    asset: str
    amount: Decimal
    tx_hash: str
    transaction_kind: str
    reason: str


def _is_phantom_deposit(*, tx_hash: str, idempotency_key: str | None, metadata_json: dict | None) -> str | None:
    hash_l = (tx_hash or "").strip().lower()
    if hash_l.startswith("0xsim"):
        return "simulated_tx_hash"
    if hash_l.startswith("0xmock"):
        return "mock_swap_tx_hash"
    key = (idempotency_key or "").strip().lower()
    if key.startswith("admin_sim_"):
        return "admin_simulate_deposit"
    meta = metadata_json if isinstance(metadata_json, dict) else {}
    if meta.get("lombard_mock") is True or meta.get("mock_usdc_ledger_credited") is True:
        return "lombard_mock_metadata"
    source = str(meta.get("source") or meta.get("sync_source") or "").lower()
    if "simulate" in source or "mock" in source:
        return "mock_metadata_source"
    return None


def list_phantom_confirmed_deposits(db: Session, *, person_id: UUID) -> list[PhantomDepositRow]:
    repo = PersonWalletDepositRepository()
    rows = repo.list_for_person(db, person_id, limit=5000)
    out: list[PhantomDepositRow] = []
    for row in rows:
        if row.status != PersonWalletDepositStatus.CONFIRMED.value:
            continue
        if str(row.direction or "").lower() != "credit":
            continue
        reason = _is_phantom_deposit(
            tx_hash=str(row.tx_hash or ""),
            idempotency_key=row.idempotency_key,
            metadata_json=row.metadata_json if isinstance(row.metadata_json, dict) else None,
        )
        if not reason:
            continue
        out.append(
            PhantomDepositRow(
                deposit_id=row.id,
                asset=str(row.asset or "").upper(),
                amount=Decimal(str(row.amount or 0)),
                tx_hash=str(row.tx_hash or ""),
                transaction_kind=str(row.transaction_kind or ""),
                reason=reason,
            )
        )
    return out


def _void_for_repair(
    admin: PrivyWalletAdminService,
    db: Session,
    *,
    person_id: UUID,
    deposit_id: UUID,
    reason: str,
) -> str:
    try:
        admin.void_deposit(
            db,
            PrivyVoidDepositRequest(
                person_id=person_id,
                deposit_id=deposit_id,
                reason=reason,
            ),
        )
        return "voided"
    except PrivySimulateDepositError as exc:
        if "insuffisant" not in str(exc).lower():
            raise

    deposit_repo = PersonWalletDepositRepository()
    balance_repo = PersonWalletBalanceRepository()
    deposit = deposit_repo.get_for_person(db, deposit_id, person_id)
    if deposit is None or deposit.status != PersonWalletDepositStatus.CONFIRMED.value:
        return "skipped"

    amount = Decimal(str(deposit.amount))
    direction = str(deposit.direction or PersonWalletDirection.CREDIT.value).lower()
    balance = balance_repo.get_or_create_for_update(
        db,
        wallet_id=deposit.person_crypto_wallet_id,
        person_id=person_id,
        asset=deposit.asset,
    )
    current = Decimal(str(balance.balance))
    if direction == PersonWalletDirection.DEBIT.value:
        balance_repo.increment_balance(db, balance, delta=amount, sync_source="repair_void_deposit")
    elif current > Decimal("0"):
        balance_repo.increment_balance(
            db,
            balance,
            delta=-min(current, amount),
            sync_source="repair_void_deposit_clamped",
        )

    metadata = dict(deposit.metadata_json or {})
    metadata["repair_void"] = {"reason": reason, "clamped": True}
    deposit.status = PersonWalletDepositStatus.FAILED.value
    deposit.metadata_json = metadata
    db.add(deposit)
    db.flush()
    return "voided_clamped"


def void_phantom_confirmed_deposits(
    db: Session,
    *,
    person_id: UUID,
    dry_run: bool = True,
    reason: str = "Ledger phantom repair — simulated deposit without on-chain proof",
) -> list[dict[str, str]]:
    admin = PrivyWalletAdminService()
    actions: list[dict[str, str]] = []

    for phantom in list_phantom_confirmed_deposits(db, person_id=person_id):
        entry = {
            "deposit_id": str(phantom.deposit_id),
            "asset": phantom.asset,
            "amount": str(phantom.amount),
            "tx_hash": phantom.tx_hash,
            "phantom_reason": phantom.reason,
            "action": "would_void" if dry_run else "void",
        }
        if not dry_run:
            admin.void_deposit(
                db,
                PrivyVoidDepositRequest(
                    person_id=person_id,
                    deposit_id=phantom.deposit_id,
                    reason=reason,
                ),
            )
            entry["action"] = "voided"
        actions.append(entry)

    return actions


def void_untrusted_ledger_entries(
    db: Session,
    *,
    person_id: UUID,
    dry_run: bool = True,
    reason: str = "Ledger repair — simulated or mock entry without on-chain proof",
) -> list[dict[str, str]]:
    """Annule d'abord les crédits mock/sim, puis les débits mock (void direction-aware)."""
    admin = PrivyWalletAdminService()
    phantoms = list_phantom_confirmed_deposits(db, person_id=person_id)
    credits = [p for p in phantoms if p.reason != "mock_swap_tx_hash"]
    mock_swaps = [p for p in phantoms if p.reason == "mock_swap_tx_hash"]

    repo = PersonWalletDepositRepository()
    mock_debits: list[PhantomDepositRow] = []
    for row in repo.list_for_person(db, person_id, limit=5000):
        if row.status != PersonWalletDepositStatus.CONFIRMED.value:
            continue
        if str(row.direction or "").lower() != "debit":
            continue
        hash_l = str(row.tx_hash or "").strip().lower()
        if not hash_l.startswith("0xmock"):
            continue
        mock_debits.append(
            PhantomDepositRow(
                deposit_id=row.id,
                asset=str(row.asset or "").upper(),
                amount=Decimal(str(row.amount or 0)),
                tx_hash=str(row.tx_hash or ""),
                transaction_kind=str(row.transaction_kind or ""),
                reason="mock_swap_tx_hash",
            )
        )

    ordered = [*mock_debits, *credits, *mock_swaps]
    actions: list[dict[str, str]] = []

    for phantom in ordered:
        entry = {
            "deposit_id": str(phantom.deposit_id),
            "asset": phantom.asset,
            "amount": str(phantom.amount),
            "tx_hash": phantom.tx_hash,
            "phantom_reason": phantom.reason,
            "action": "would_void" if dry_run else "void",
        }
        if not dry_run:
            entry["action"] = _void_for_repair(
                admin,
                db,
                person_id=person_id,
                deposit_id=phantom.deposit_id,
                reason=reason,
            )
        actions.append(entry)

    return actions
