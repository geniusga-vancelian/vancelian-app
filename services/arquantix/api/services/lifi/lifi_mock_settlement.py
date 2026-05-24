"""Règlement mock swap — débit/crédit ledger Privy (comme simulate-deposit)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.lifi_validation_service import SwapValidationError
from services.privy_wallet.repository import (
    PersonCryptoWalletRepository,
    PersonWalletBalanceRepository,
)


def apply_mock_swap_settlement(db: Session, swap) -> None:
    """Applique le swap mock sur les soldes wallet Privy de la personne."""
    wallet_repo = PersonCryptoWalletRepository()
    balance_repo = PersonWalletBalanceRepository()

    wallets = wallet_repo.list_active_for_person(db, swap.person_id)
    if not wallets:
        raise SwapValidationError("swap.wallet_missing", "Aucun wallet Privy lié")

    wallet = wallets[0]
    person_id: UUID = swap.person_id
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    amount_in = Decimal(str(swap.amount_in))
    amount_out = Decimal(str(swap.estimated_receive or 0))

    if amount_in <= 0 or amount_out <= 0:
        raise SwapValidationError("swap.mock_invalid_amounts", "Montants mock invalides")

    from_row = balance_repo.get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=person_id,
        asset=from_asset,
    )
    available = Decimal(str(from_row.available_balance))
    if available < amount_in:
        raise SwapValidationError(
            "swap.insufficient_balance",
            f"Solde {from_asset} insuffisant pour le swap mock ({available} < {amount_in})",
        )

    balance_repo.increment_balance(
        db,
        from_row,
        delta=-amount_in,
        sync_source="lifi_mock_swap",
    )

    to_row = balance_repo.get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=person_id,
        asset=to_asset,
    )
    balance_repo.increment_balance(
        db,
        to_row,
        delta=amount_out,
        sync_source="lifi_mock_swap",
    )
