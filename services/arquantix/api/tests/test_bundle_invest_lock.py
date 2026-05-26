"""Tests verrou anti-double investissement bundle LI.FI."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from services.portfolio_engine.bundles.bundle_invest_lock import (
    ACTIVE_INVEST_LOCK_STATUSES,
    BundleInvestAlreadyPendingError,
    acquire_invest_lock,
    assert_no_active_invest_lock,
    clear_invest_lock,
    get_invest_lock,
    release_invest_lock,
)
from services.portfolio_engine.portfolios.models import Portfolio


def _portfolio(metadata=None) -> Portfolio:
    p = Portfolio(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_type="bundle_portfolio",
        name="Test Bundle",
        base_currency="EUR",
        status="active",
    )
    p.metadata_ = metadata or {}
    return p


def _db_with_portfolio(portfolio: Portfolio) -> MagicMock:
    db = MagicMock()
    chain = MagicMock()
    chain.filter.return_value.with_for_update.return_value.first.return_value = portfolio
    chain.filter.return_value.first.return_value = portfolio
    db.query.return_value = chain
    return db


def test_first_invest_acquires_pending_signature_lock():
    p = _portfolio()
    client_id = p.client_id
    batch_id = str(uuid.uuid4())
    lock = acquire_invest_lock(
        MagicMock(),
        p,
        client_id=client_id,
        batch_id=batch_id,
        status="pending_signature",
    )
    assert lock["batch_id"] == batch_id
    assert lock["status"] == "pending_signature"
    assert lock["bundle_action"] == "invest"
    stored = get_invest_lock(p.metadata_)
    assert stored is not None
    assert stored["batch_id"] == batch_id


def test_second_invest_raises_already_pending():
    p = _portfolio()
    client_id = p.client_id
    acquire_invest_lock(
        MagicMock(),
        p,
        client_id=client_id,
        batch_id=str(uuid.uuid4()),
        status="pending_signature",
    )
    with pytest.raises(BundleInvestAlreadyPendingError) as exc_info:
        assert_no_active_invest_lock(p, client_id)
    assert exc_info.value.batch_id
    resp = exc_info.value.to_response()
    assert resp["status"] == "already_pending"
    assert "batch_id" in resp


def test_completed_lock_allows_new_invest():
    p = _portfolio()
    client_id = p.client_id
    batch_id = str(uuid.uuid4())
    db = _db_with_portfolio(p)
    acquire_invest_lock(db, p, client_id=client_id, batch_id=batch_id, status="pending_signature")
    clear_invest_lock(db, client_id=client_id, portfolio_id=p.id, batch_id=batch_id)
    assert get_invest_lock(p.metadata_) is None
    assert_no_active_invest_lock(p, client_id)
    acquire_invest_lock(
        db,
        p,
        client_id=client_id,
        batch_id=str(uuid.uuid4()),
        status="pending_signature",
    )


def test_failed_lock_allows_new_invest():
    p = _portfolio()
    client_id = p.client_id
    batch_id = str(uuid.uuid4())
    db = _db_with_portfolio(p)
    acquire_invest_lock(db, p, client_id=client_id, batch_id=batch_id, status="finalizing")
    release_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=p.id,
        batch_id=batch_id,
        terminal_status="failed",
    )
    assert get_invest_lock(p.metadata_) is None
    assert_no_active_invest_lock(p, client_id)


def test_expired_terminal_releases_lock():
    p = _portfolio()
    client_id = p.client_id
    batch_id = str(uuid.uuid4())
    db = _db_with_portfolio(p)
    acquire_invest_lock(
        db, p, client_id=client_id, batch_id=batch_id, status="pending_confirmation",
    )
    release_invest_lock(
        db,
        client_id=client_id,
        portfolio_id=p.id,
        batch_id=batch_id,
        terminal_status="expired",
    )
    assert get_invest_lock(p.metadata_) is None


def test_active_statuses_include_pipeline_states():
    for st in (
        "pending_signature",
        "signature_requested",
        "submitted",
        "pending_confirmation",
        "finalizing",
    ):
        assert st in ACTIVE_INVEST_LOCK_STATUSES


def test_clear_invest_lock_removes_active_guard():
    p = _portfolio()
    client_id = p.client_id
    batch_id = str(uuid.uuid4())
    db = _db_with_portfolio(p)
    acquire_invest_lock(db, p, client_id=client_id, batch_id=batch_id, status="pending_signature")
    clear_invest_lock(db, client_id=client_id, portfolio_id=p.id, batch_id=batch_id)
    assert_no_active_invest_lock(p, client_id)

