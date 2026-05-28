"""Phase 1 — BundleExecutionAdapter parity and tagging."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution import (
    BundleExecutionAdapter,
    ExecutionLeg,
    get_bundle_execution_provider_name,
)
from services.portfolio_engine.bundle_execution.exchange_provider import ExchangeExecutionProvider
from services.portfolio_engine.bundle_execution.lifi_provider import LifiExecutionProvider
from services.portfolio_engine.bundle_execution.providers import get_execution_provider
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.bundles.rebalance import BundleRebalanceOrchestrator
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.invariants.invariant_g import check_invariant_g


def test_default_provider_is_exchange(monkeypatch):
    monkeypatch.delenv("BUNDLE_EXECUTION_PROVIDER", raising=False)
    monkeypatch.delenv("LIFI_API_KEY", raising=False)
    monkeypatch.setenv("LIFI_SWAPS_ENABLED", "0")
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "0")
    assert get_bundle_execution_provider_name() == "exchange"
    provider = get_execution_provider()
    assert provider.name == "exchange"


def test_auto_defaults_to_lifi_when_configured(monkeypatch):
    monkeypatch.delenv("BUNDLE_EXECUTION_PROVIDER", raising=False)
    monkeypatch.setenv("LIFI_SWAPS_ENABLED", "1")
    monkeypatch.setenv("LIFI_API_KEY", "test-key")
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "0")
    assert get_bundle_execution_provider_name() == "lifi_base"


def test_lifi_provider_resolves(monkeypatch):
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
    provider = get_execution_provider()
    assert isinstance(provider, LifiExecutionProvider)
    assert provider.name == "lifi_base"


def test_orchestrator_delegates_funding_to_adapter():
    adapter = MagicMock(spec=BundleExecutionAdapter)
    legacy = {
        "amount_crypto": Decimal("100"),
        "order_id": uuid.uuid4(),
        "status": "completed",
    }
    result_mock = MagicMock()
    result_mock.to_buy_legacy_dict.return_value = legacy
    adapter.execute_leg.return_value = result_mock

    orch = BundleOrchestrator(execution_adapter=adapter)
    assert orch._execution is adapter


def test_orchestrator_swap_delegates_to_adapter():
    adapter = MagicMock(spec=BundleExecutionAdapter)
    result_mock = MagicMock()
    result_mock.to_swap_legacy_dict.return_value = {
        "amount_to": Decimal("0.5"),
        "reference_value_net": 100.0,
        "swap_group_id": uuid.uuid4(),
        "status": "completed",
    }
    adapter.execute_leg.return_value = result_mock

    orch = BundleOrchestrator(execution_adapter=adapter)
    db = MagicMock()
    client_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    actor = ActorContext(actor_type="system", actor_id="test")

    with patch.object(orch, "_tag_order_metadata"):
        out = orch._execute_swap_from_entry(
            db, client_id, "USDC", "ETH", Decimal("100"),
            "bundle-alloc-x", portfolio_id, "batch", actor,
        )

    adapter.execute_leg.assert_called_once()
    leg = adapter.execute_leg.call_args[0][1]
    assert leg.action == "allocation"
    assert leg.bundle_action == "allocation"
    assert leg.leg_id == "bundle-alloc-x"
    assert out["amount_to"] == Decimal("0.5")


def test_rebalance_swap_leg_action():
    adapter = MagicMock(spec=BundleExecutionAdapter)
    result_mock = MagicMock()
    result_mock.to_swap_legacy_dict.return_value = {
        "amount_to": Decimal("1"),
        "reference_value_net": 50.0,
        "status": "completed",
    }
    adapter.execute_leg.return_value = result_mock

    rebal = BundleRebalanceOrchestrator(execution_adapter=adapter)
    db = MagicMock()
    client_id = uuid.uuid4()
    portfolio_id = uuid.uuid4()
    actor = ActorContext(actor_type="system", actor_id="test")

    rebal._execute_swap(
        db, client_id, "BTC", "USDC", Decimal("0.01"),
        "bundle-rebal-sell-x", portfolio_id, "batch", actor,
        leg_action="rebalance_sell",
    )
    leg = adapter.execute_leg.call_args[0][1]
    assert leg.action == "rebalance_sell"
    assert leg.bundle_action == "rebalance"


def test_tag_order_metadata_includes_execution_fields(db: Session, pe_client):
    from services.exchange.models import ExchangeOrder
    from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

    client_id = pe_client.id
    portfolio_id = uuid.uuid4()
    ext_ref = f"bundle-fund-{uuid.uuid4()}"
    order = ExchangeOrder(
        id=uuid.uuid4(),
        client_id=client_id,
        side="buy",
        asset="USDC",
        amount_crypto=Decimal("10"),
        amount_fiat=Decimal("10"),
        price=Decimal("1"),
        currency="EUR",
        status="completed",
        external_reference=ext_ref,
        metadata_={},
    )
    db.add(order)
    db.flush()

    BundleOrchestrator._tag_order_metadata(
        db, ext_ref, portfolio_id, "batch-xyz", "funding",
    )
    db.refresh(order)
    meta = order.metadata_ or {}
    assert meta["portfolio_scope"] == "bundle"
    assert meta["portfolio_id"] == str(portfolio_id)
    assert meta["bundle_action"] == "funding"
    assert meta["execution_provider"] == "exchange"
    assert meta["batch_id"] == "batch-xyz"
    assert meta["leg_id"] == ext_ref


def test_invariant_g_dry_run_no_person(db: Session, pe_client):
    from services.portfolio_engine.clients.models import Client

    client = db.query(Client).filter(Client.id == pe_client.id).first()
    if client is not None:
        client.person_id = None
        db.flush()

    report = check_invariant_g(db, pe_client.id, dry_run=True)
    assert report["dry_run"] is True
    assert report["status"] in ("unavailable", "ok", "skipped")


@pytest.fixture
def pe_client(db: Session):
    from services.portfolio_engine.clients.models import Client

    c = Client(
        id=uuid.uuid4(),
        email=f"inv-g-{uuid.uuid4().hex[:6]}@test.com",
        status="active",
        kyc_status="approved",
    )
    db.add(c)
    db.flush()
    return c
