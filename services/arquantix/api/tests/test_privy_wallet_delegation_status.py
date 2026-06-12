"""Tests unitaires — détection du statut de délégation Privy (flag ``delegated``)."""
from __future__ import annotations

from services.privy_wallet.privy_api_client import (
    extract_delegated_wallet_addresses,
    is_wallet_delegated,
)


def _user(*wallets: dict) -> dict:
    return {"linked_accounts": list(wallets)}


def test_extracts_only_delegated_wallets():
    payload = _user(
        {"type": "wallet", "address": "0xAAA", "delegated": True},
        {"type": "wallet", "address": "0xBBB", "delegated": False},
        {"type": "wallet", "address": "0xCCC"},  # delegated absent
        {"type": "email", "address": "a@b.c", "delegated": True},  # pas un wallet
    )
    assert extract_delegated_wallet_addresses(payload) == {"0xaaa"}


def test_is_wallet_delegated_case_insensitive():
    payload = _user({"type": "wallet", "address": "0xAbCdEf", "delegated": True})
    assert is_wallet_delegated(payload, "0xabcdef") is True
    assert is_wallet_delegated(payload, "0xABCDEF") is True
    assert is_wallet_delegated(payload, "0xother") is False


def test_is_wallet_delegated_handles_empty_and_missing():
    assert is_wallet_delegated({}, "0xaaa") is False
    assert is_wallet_delegated(_user(), "0xaaa") is False
    assert is_wallet_delegated(_user({"type": "wallet", "address": "0xaaa", "delegated": True}), "") is False


def test_delegated_flag_must_be_strict_true():
    payload = _user({"type": "wallet", "address": "0xaaa", "delegated": "true"})
    assert extract_delegated_wallet_addresses(payload) == set()
