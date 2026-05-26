"""Soldes Privy par réseau — dérivés des dépôts confirmés (lecture API)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from database import PersonCryptoWallet

from .enums import PersonWalletDepositStatus, PersonWalletDirection
from .models import PersonWalletDeposit
from .repository import PersonWalletBalanceRepository, PersonWalletDepositRepository


@dataclass(frozen=True)
class ChainBalanceBucket:
    wallet_id: UUID
    asset: str
    chain_id: int
    balance: Decimal


def resolve_deposit_chain_id(
    deposit: PersonWalletDeposit,
    wallet: PersonCryptoWallet | None,
) -> int:
    if deposit.chain_id is not None:
        return int(deposit.chain_id)
    if wallet is not None and wallet.chain_id is not None:
        return int(wallet.chain_id)
    if (deposit.chain_type or "").lower() == "solana":
        return 0
    return 1


def aggregate_confirmed_deposit_balances(
    db: Session,
    *,
    person_id: UUID,
    wallets: list[PersonCryptoWallet],
) -> list[ChainBalanceBucket]:
    wallet_by_id = {wallet.id: wallet for wallet in wallets}
    deposits = PersonWalletDepositRepository.list_for_person(db, person_id, limit=5000)
    buckets: dict[tuple[UUID, str, int], Decimal] = {}

    for deposit in deposits:
        if deposit.status != PersonWalletDepositStatus.CONFIRMED.value:
            continue
        wallet = wallet_by_id.get(deposit.person_crypto_wallet_id)
        chain_id = resolve_deposit_chain_id(deposit, wallet)
        asset = str(deposit.asset or "").upper()
        if not asset:
            continue
        amount = Decimal(str(deposit.amount or 0))
        if amount <= 0:
            continue
        key = (deposit.person_crypto_wallet_id, asset, chain_id)
        if deposit.direction == PersonWalletDirection.DEBIT.value:
            buckets[key] = buckets.get(key, Decimal("0")) - amount
        else:
            buckets[key] = buckets.get(key, Decimal("0")) + amount

    out: list[ChainBalanceBucket] = []
    for (wallet_id, asset, chain_id), balance in buckets.items():
        if balance <= 0:
            continue
        out.append(
            ChainBalanceBucket(
                wallet_id=wallet_id,
                asset=asset,
                chain_id=chain_id,
                balance=balance,
            )
        )
    return out


def reconcile_chain_buckets_with_ledger(
    db: Session,
    *,
    person_id: UUID,
    wallets: list[PersonCryptoWallet],
    buckets: list[ChainBalanceBucket],
) -> list[ChainBalanceBucket]:
    """Répartit l'écart ledger agrégé ↔ somme des dépôts sur le chain_id du wallet."""
    wallet_by_id = {wallet.id: wallet for wallet in wallets}
    bucket_totals: dict[tuple[UUID, str], Decimal] = {}
    for row in buckets:
        key = (row.wallet_id, row.asset)
        bucket_totals[key] = bucket_totals.get(key, Decimal("0")) + row.balance

    adjusted = list(buckets)
    for balance_row in PersonWalletBalanceRepository().list_for_person(db, person_id):
        ledger_total = Decimal(str(balance_row.balance or 0))
        if ledger_total <= 0:
            continue
        key = (balance_row.person_crypto_wallet_id, balance_row.asset.upper())
        deposit_total = bucket_totals.get(key, Decimal("0"))
        remainder = ledger_total - deposit_total
        if remainder <= 0:
            continue
        wallet = wallet_by_id.get(balance_row.person_crypto_wallet_id)
        chain_id = int(wallet.chain_id) if wallet and wallet.chain_id is not None else 1
        adjusted.append(
            ChainBalanceBucket(
                wallet_id=balance_row.person_crypto_wallet_id,
                asset=balance_row.asset.upper(),
                chain_id=chain_id,
                balance=remainder,
            )
        )
    return adjusted
