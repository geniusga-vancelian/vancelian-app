"""LINK Base — 18 décimales on-chain (pas 8 comme ancien ASSET_PRECISION Exchange)."""
from decimal import Decimal

from config.base_allowed_assets import BASE_LIFI_CHAIN_ID, base_token_decimals
from services.privy_wallet.evm_rpc_client import atomic_to_decimal, evm_token_decimals


def test_base_token_decimals_link_is_18():
    assert base_token_decimals("LINK") == 18


def test_evm_token_decimals_link_on_base():
    assert evm_token_decimals("LINK", chain_id=BASE_LIFI_CHAIN_ID) == 18


def test_atomic_to_decimal_one_and_half_link():
    atomic = int(Decimal("1.5") * (Decimal(10) ** 18))
    human = atomic_to_decimal(atomic, "LINK", chain_id=8453)
    assert human == Decimal("1.5")


def test_atomic_to_decimal_link_not_inflated_by_legacy_exchange_precision():
    """Régression : 1 LINK avec ancien diviseur 10^8 → 10^10 LINK."""
    one_link_atomic = 10**18
    wrong = atomic_to_decimal(one_link_atomic, "LINK", chain_id=8453)
    assert wrong == Decimal("1")
    assert wrong < Decimal("1000")
