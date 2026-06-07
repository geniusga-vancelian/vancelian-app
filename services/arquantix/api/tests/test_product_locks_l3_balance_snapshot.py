"""S4 L3 — balance snapshot metadata (hash · normalisation · flag OFF)."""
from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal

import pytest

from services.portfolio_engine.internal_scope_movements.types import CurrentPeScopeSnapshot
from services.product_locks.balance_snapshot import (
    BalanceSnapshot,
    build_balance_snapshot,
    compute_balance_snapshot_hash,
    resolve_available_from_pe_snapshot,
)
from services.product_locks.enums import ProductLockScope


PERSON_ID = uuid.UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
WALLET_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def locks_on(monkeypatch):
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", "true")


@pytest.fixture
def locks_off(monkeypatch):
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", raising=False)


def test_compute_hash_is_deterministic():
    kwargs = {
        "person_id": PERSON_ID,
        "wallet_id": WALLET_ID,
        "asset": "USDC",
        "scope": ProductLockScope.TRADING_AVAILABLE,
        "available": "100",
        "version": 15,
    }
    first = compute_balance_snapshot_hash(**kwargs)
    second = compute_balance_snapshot_hash(**kwargs)
    assert first == second
    assert first.startswith("sha256:")


def test_compute_hash_normalizes_asset_and_scope():
    base = compute_balance_snapshot_hash(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        available="100",
        version=1,
    )
    mixed = compute_balance_snapshot_hash(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset=" usdc ",
        scope="TRADING_AVAILABLE",
        available="100",
        version=1,
    )
    assert base == mixed


def test_compute_hash_changes_when_available_changes(locks_on):
    low = compute_balance_snapshot_hash(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        available="100",
        version=15,
    )
    high = compute_balance_snapshot_hash(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        available="101",
        version=15,
    )
    assert low != high


def test_compute_hash_changes_when_version_changes():
    v1 = compute_balance_snapshot_hash(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        available="100",
        version=15,
    )
    v2 = compute_balance_snapshot_hash(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        available="100",
        version=16,
    )
    assert v1 != v2


def test_compute_hash_uses_canonical_json_order():
    import hashlib
    import json

    kwargs = {
        "person_id": PERSON_ID,
        "wallet_id": WALLET_ID,
        "asset": "USDC",
        "scope": ProductLockScope.TRADING_AVAILABLE,
        "available": "62.64",
        "version": 15,
    }
    payload = {
        "person_id": str(PERSON_ID),
        "wallet_id": str(WALLET_ID),
        "asset": "USDC",
        "scope": "trading_available",
        "available": "62.64",
        "version": 15,
    }
    shuffled = {
        "version": payload["version"],
        "scope": payload["scope"],
        "available": payload["available"],
        "wallet_id": payload["wallet_id"],
        "asset": payload["asset"],
        "person_id": payload["person_id"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    assert json.dumps(shuffled, sort_keys=True, separators=(",", ":")) == canonical
    expected = f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
    assert compute_balance_snapshot_hash(**kwargs) == expected


def test_build_balance_snapshot_shape(locks_on):
    result = build_balance_snapshot(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="usdc",
        scope=ProductLockScope.TRADING_AVAILABLE,
        version=15,
        available=Decimal("100"),
    )

    assert result.skipped is False
    assert result.snapshot is not None
    assert result.snapshot == BalanceSnapshot(
        asset="USDC",
        available="100",
        version=15,
        hash=compute_balance_snapshot_hash(
            person_id=PERSON_ID,
            wallet_id=WALLET_ID,
            asset="USDC",
            scope=ProductLockScope.TRADING_AVAILABLE,
            available="100",
            version=15,
        ),
    )
    assert result.snapshot.to_dict() == {
        "asset": "USDC",
        "available": "100",
        "version": 15,
        "hash": result.snapshot.hash,
    }


def test_build_balance_snapshot_from_pe_snapshot(locks_on):
    pe = CurrentPeScopeSnapshot(
        person_id=PERSON_ID,
        client_id=None,
        trading_available={"USDC": Decimal("62.64")},
    )
    result = build_balance_snapshot(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        version=15,
        pe_snapshot=pe,
    )

    assert result.skipped is False
    assert result.snapshot is not None
    assert result.snapshot.available == "62.64"


def test_build_balance_snapshot_from_resolver(locks_on):
    result = build_balance_snapshot(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        version=15,
        resolve_available=lambda: Decimal("42.5"),
    )

    assert result.snapshot is not None
    assert result.snapshot.available == "42.5"


def test_resolve_available_from_pe_snapshot_trading_scope():
    pe = CurrentPeScopeSnapshot(
        person_id=PERSON_ID,
        client_id=None,
        trading_available={"usdc": Decimal("10")},
        bundle_cash={"USDC": Decimal("999")},
    )
    amount = resolve_available_from_pe_snapshot(
        pe,
        asset="usdc",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )
    assert amount == Decimal("10")


def test_resolve_available_from_pe_snapshot_bundle_scope():
    pe = CurrentPeScopeSnapshot(
        person_id=PERSON_ID,
        client_id=None,
        bundle_cash={"USDC": Decimal("3")},
        bundle_position={"USDC": Decimal("7")},
    )
    amount = resolve_available_from_pe_snapshot(
        pe,
        asset="USDC",
        scope=ProductLockScope.BUNDLE,
    )
    assert amount == Decimal("10")


def test_flag_off_build_is_no_op(locks_off):
    result = build_balance_snapshot(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        version=15,
        available=Decimal("100"),
    )

    assert result.skipped is True
    assert result.snapshot is None


def test_balance_snapshot_module_has_no_runtime_wiring_imports():
    root = pathlib.Path(__file__).resolve().parents[1] / "services" / "product_locks"
    forbidden = ("services.lifi", "services.settlement", "transaction_outbox")
    source = (root / "balance_snapshot.py").read_text()
    for token in forbidden:
        assert token not in source, f"balance_snapshot.py must not reference {token}"
