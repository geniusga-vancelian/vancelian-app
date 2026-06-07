"""S4 L4a — middleware 409 validation skeleton (non branché runtime)."""
from __future__ import annotations

import pathlib
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.product_locks.balance_snapshot import (
    BalanceSnapshot,
    build_balance_snapshot,
    compute_balance_snapshot_hash,
)
from services.product_locks.enums import ProductLockScope, ProductLockStatus
from services.product_locks.error_codes import ProductLockErrorCode
from services.product_locks.exceptions import (
    BalanceChanged409,
    BalanceVersionMismatch409,
    ProductLockConflict409,
    ProductLockDisabled409,
)
from services.product_locks.middleware import (
    validate_balance_snapshot_or_raise,
    validate_product_lock_or_raise,
)
from services.product_locks.models import TransactionProductLock
from services.product_locks.service import acquire_product_lock
from tests.test_product_locks_l2_engine import _intent, _slot, pytestmark


PERSON_ID = uuid.UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
WALLET_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def locks_on(monkeypatch):
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", "true")


@pytest.fixture
def locks_off(monkeypatch):
    monkeypatch.delenv("TRANSACTION_PRODUCT_LOCKS_ENABLED", raising=False)


def _stored_snapshot(*, available: str = "100", version: int = 15) -> BalanceSnapshot:
    return BalanceSnapshot(
        asset="USDC",
        available=available,
        version=version,
        hash=compute_balance_snapshot_hash(
            person_id=PERSON_ID,
            wallet_id=WALLET_ID,
            asset="USDC",
            scope=ProductLockScope.TRADING_AVAILABLE,
            available=available,
            version=version,
        ),
    )


def test_error_codes_are_stable():
    assert ProductLockErrorCode.PRODUCT_LOCK_CONFLICT.value == "PRODUCT_LOCK_CONFLICT"
    assert ProductLockErrorCode.BALANCE_CHANGED.value == "BALANCE_CHANGED"
    assert ProductLockErrorCode.BALANCE_VERSION_MISMATCH.value == "BALANCE_VERSION_MISMATCH"
    assert ProductLockErrorCode.PRODUCT_LOCK_DISABLED.value == "PRODUCT_LOCK_DISABLED"


def test_disabled_exception_maps_to_error_code():
    exc = ProductLockDisabled409()
    assert exc.error_code == ProductLockErrorCode.PRODUCT_LOCK_DISABLED.value
    assert exc.http_status == 409


def test_flag_off_product_lock_validation_is_no_op(db: Session, locks_off):
    pe, wallet = _slot(db)
    intent = _intent(db, pe.person_id)

    result = validate_product_lock_or_raise(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        intent_id=intent.id,
    )

    assert result.skipped is True
    assert result.ok is True


def test_flag_off_balance_snapshot_validation_is_no_op(locks_off):
    result = validate_balance_snapshot_or_raise(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        stored_snapshot=_stored_snapshot(),
        current_available="999",
        current_version=99,
    )

    assert result.skipped is True
    assert result.ok is True


def test_validate_product_lock_conflict_raises_409(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent_a = _intent(db, pe.person_id)
    intent_b = _intent(db, pe.person_id)

    acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent_a.id,
    )

    with pytest.raises(ProductLockConflict409) as exc:
        validate_product_lock_or_raise(
            db,
            person_id=pe.person_id,
            wallet_id=wallet.id,
            asset="USDC",
            scope=ProductLockScope.TRADING_AVAILABLE,
            intent_id=intent_b.id,
        )

    assert exc.value.error_code == ProductLockErrorCode.PRODUCT_LOCK_CONFLICT.value
    assert exc.value.existing_intent_id == intent_a.id
    assert exc.value.requested_intent_id == intent_b.id


def test_validate_product_lock_same_intent_ok(db: Session, locks_on):
    pe, wallet = _slot(db)
    intent = _intent(db, pe.person_id)

    acquire_product_lock(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        product_type="lifi_swap",
        intent_id=intent.id,
    )

    result = validate_product_lock_or_raise(
        db,
        person_id=pe.person_id,
        wallet_id=wallet.id,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        intent_id=intent.id,
    )

    assert result.skipped is False
    assert result.ok is True


def test_validate_balance_snapshot_identical_ok(locks_on):
    snapshot = _stored_snapshot(available="100", version=15)

    result = validate_balance_snapshot_or_raise(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        stored_snapshot=snapshot,
        current_available="100",
        current_version=15,
    )

    assert result.skipped is False
    assert result.ok is True


def test_validate_balance_snapshot_version_mismatch_raises_409(locks_on):
    snapshot = _stored_snapshot(available="100", version=15)

    with pytest.raises(BalanceVersionMismatch409) as exc:
        validate_balance_snapshot_or_raise(
            person_id=PERSON_ID,
            wallet_id=WALLET_ID,
            asset="USDC",
            scope=ProductLockScope.TRADING_AVAILABLE,
            stored_snapshot=snapshot,
            current_available="100",
            current_version=16,
        )

    assert exc.value.error_code == ProductLockErrorCode.BALANCE_VERSION_MISMATCH.value
    assert exc.value.expected_version == 15
    assert exc.value.actual_version == 16


def test_validate_balance_snapshot_hash_mismatch_raises_409(locks_on):
    snapshot = _stored_snapshot(available="100", version=15)

    with pytest.raises(BalanceChanged409) as exc:
        validate_balance_snapshot_or_raise(
            person_id=PERSON_ID,
            wallet_id=WALLET_ID,
            asset="USDC",
            scope=ProductLockScope.TRADING_AVAILABLE,
            stored_snapshot=snapshot,
            current_available="101",
            current_version=15,
        )

    assert exc.value.error_code == ProductLockErrorCode.BALANCE_CHANGED.value
    assert exc.value.expected_hash == snapshot.hash
    assert exc.value.actual_hash != snapshot.hash


def test_validate_balance_snapshot_accepts_dict_payload(locks_on):
    built = build_balance_snapshot(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        version=15,
        available=Decimal("100"),
    )
    assert built.snapshot is not None

    result = validate_balance_snapshot_or_raise(
        person_id=PERSON_ID,
        wallet_id=WALLET_ID,
        asset="USDC",
        scope=ProductLockScope.TRADING_AVAILABLE,
        stored_snapshot=built.snapshot.to_dict(),
        current_available=built.snapshot.available,
        current_version=built.snapshot.version,
    )

    assert result.ok is True


def test_middleware_module_has_no_runtime_wiring_imports():
    root = pathlib.Path(__file__).resolve().parents[1] / "services" / "product_locks"
    forbidden = (
        "services.lifi",
        "services.settlement",
        "transaction_outbox",
        "services.onchain_indexer.controller",
    )
    for name in ("middleware.py", "error_codes.py", "exceptions.py"):
        source = (root / name).read_text()
        for token in forbidden:
            assert token not in source, f"{name} must not reference {token}"
