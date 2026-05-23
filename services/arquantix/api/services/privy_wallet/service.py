"""Read API service for Privy user-wallet ledger."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from services.test_clients.schemas import ASSET_NAMES

from .repository import (
    PersonCryptoWalletRepository,
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
)
from .schemas import (
    PrivyWalletBalancePayload,
    PrivyWalletBalancesResponse,
    PrivyWalletBalancesSummary,
    PrivyWalletDepositPayload,
    PrivyWalletDepositsResponse,
)

_ICON_KEYS = {
    "BTC": "btc",
    "ETH": "eth",
    "SOL": "sol",
    "XRP": "xrp",
    "ADA": "ada",
    "USDC": "usdc",
    "EURC": "eurc",
}


class PrivyWalletLedgerService:

    def __init__(self) -> None:
        self._balance_repo = PersonWalletBalanceRepository()
        self._deposit_repo = PersonWalletDepositRepository()
        self._wallet_repo = PersonCryptoWalletRepository()

    def get_balances(self, db: Session, *, person_id: UUID) -> PrivyWalletBalancesResponse:
        wallets = self._wallet_repo.list_active_for_person(db, person_id)
        wallet_by_id = {w.id: w for w in wallets}
        rows = self._balance_repo.list_for_person(db, person_id)

        balances: list[PrivyWalletBalancePayload] = []
        for row in rows:
            if Decimal(str(row.balance)) <= 0:
                continue
            wallet = wallet_by_id.get(row.person_crypto_wallet_id)
            asset = row.asset.upper()
            balances.append(
                PrivyWalletBalancePayload(
                    asset=asset,
                    name=ASSET_NAMES.get(asset, asset),
                    balance=_format_decimal(row.balance),
                    available_balance=_format_decimal(row.available_balance),
                    icon_key=_ICON_KEYS.get(asset, asset.lower()),
                    wallet_address=wallet.address if wallet else None,
                    chain_type=wallet.chain_type if wallet else None,
                    chain_id=wallet.chain_id if wallet else None,
                )
            )

        return PrivyWalletBalancesResponse(
            summary=PrivyWalletBalancesSummary(
                positions_count=len(balances),
                wallet_count=len(wallets),
            ),
            balances=balances,
        )

    def list_deposits(
        self,
        db: Session,
        *,
        person_id: UUID,
        asset: str | None = None,
        limit: int = 100,
    ) -> PrivyWalletDepositsResponse:
        wallets = self._wallet_repo.list_active_for_person(db, person_id)
        wallet_by_id = {w.id: w for w in wallets}
        rows = self._deposit_repo.list_for_person(
            db, person_id, asset=asset, limit=limit
        )

        deposits = [
            PrivyWalletDepositPayload(
                id=row.id,
                transaction_kind=row.transaction_kind,
                direction=row.direction,
                asset=row.asset,
                amount=_format_decimal(row.amount),
                status=row.status,
                chain_type=row.chain_type,
                chain_id=row.chain_id,
                tx_hash=row.tx_hash,
                from_address=row.from_address,
                to_address=row.to_address,
                confirmations=row.confirmations,
                title=row.title,
                subtitle=row.subtitle,
                wallet_address=wallet_by_id.get(row.person_crypto_wallet_id).address
                if wallet_by_id.get(row.person_crypto_wallet_id)
                else None,
                created_at=row.created_at,
                confirmed_at=row.confirmed_at,
            )
            for row in rows
        ]

        return PrivyWalletDepositsResponse(
            asset=asset.upper() if asset else None,
            deposits=deposits,
        )

    def get_deposit(
        self,
        db: Session,
        *,
        person_id: UUID,
        deposit_id: UUID,
    ) -> PrivyWalletDepositPayload | None:
        row = self._deposit_repo.get_for_person(db, deposit_id, person_id)
        if row is None:
            return None
        wallet = self._wallet_repo.list_active_for_person(db, person_id)
        wallet_map = {w.id: w for w in wallet}
        w = wallet_map.get(row.person_crypto_wallet_id)
        return PrivyWalletDepositPayload(
            id=row.id,
            transaction_kind=row.transaction_kind,
            direction=row.direction,
            asset=row.asset,
            amount=_format_decimal(row.amount),
            status=row.status,
            chain_type=row.chain_type,
            chain_id=row.chain_id,
            tx_hash=row.tx_hash,
            from_address=row.from_address,
            to_address=row.to_address,
            confirmations=row.confirmations,
            title=row.title,
            subtitle=row.subtitle,
            wallet_address=w.address if w else None,
            created_at=row.created_at,
            confirmed_at=row.confirmed_at,
        )


def _format_decimal(value: Decimal | object) -> str:
    d = Decimal(str(value))
    text = format(d.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
