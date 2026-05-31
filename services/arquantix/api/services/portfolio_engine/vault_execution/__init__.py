"""Vault scope movements — Phase 3A (trading_available ↔ vault_position)."""
from .vault_funding import (
    VaultFundingError,
    fund_vault_from_self_trading,
    release_vault_to_self_trading,
    resolve_trading_available_for_vault,
    resolve_vault_position_available,
    sum_vault_position_quantity,
)

__all__ = [
    "VaultFundingError",
    "fund_vault_from_self_trading",
    "release_vault_to_self_trading",
    "resolve_trading_available_for_vault",
    "resolve_vault_position_available",
    "sum_vault_position_quantity",
]
