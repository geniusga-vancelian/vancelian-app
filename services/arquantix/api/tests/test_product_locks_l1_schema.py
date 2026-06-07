"""S4 L1 — schéma transaction_product_locks (migration 175)."""
from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from database import engine
from services.product_locks.enums import ProductLockScope
from services.product_locks.lock_key import build_lock_key


def test_build_lock_key_canonical_format():
    person_id = uuid.UUID("8b0e0044-f1ef-47a5-99d4-370598a77492")
    wallet_id = uuid.UUID("11111111-2222-3333-4444-555555555555")
    key = build_lock_key(
        person_id=person_id,
        wallet_id=wallet_id,
        asset="usdc",
        scope=ProductLockScope.TRADING_AVAILABLE,
    )
    assert key == (
        f"person:{person_id}:wallet:{wallet_id}:asset:USDC:scope:trading_available"
    )


def _migration_175_ready() -> bool:
    try:
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_product_locks'"
                )
            ).fetchone()
            return row is not None
    except Exception:
        return False


_migration_175 = pytest.mark.skipif(
    not _migration_175_ready(),
    reason="Migration 175 requise (transaction_product_locks).",
)


@_migration_175
def test_product_locks_table_columns():
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'transaction_product_locks'
                ORDER BY ordinal_position
                """
            )
        ).fetchall()
    columns = {r[0] for r in rows}
    expected = {
        "id",
        "person_id",
        "wallet_id",
        "asset",
        "scope",
        "product_type",
        "intent_id",
        "status",
        "lock_key",
        "created_at",
        "expires_at",
        "released_at",
    }
    assert expected.issubset(columns)


@_migration_175
def test_product_locks_active_scope_unique_index():
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                """
                SELECT indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'uq_product_locks_active_scope'
                """
            )
        ).fetchone()
    assert row is not None
    indexdef = row[0].lower()
    assert "unique" in indexdef
    assert "person_id" in indexdef
    assert "wallet_id" in indexdef
    assert "asset" in indexdef
    assert "scope" in indexdef
    assert "active" in indexdef
