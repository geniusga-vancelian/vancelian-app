"""Tests SwapCoreConfirmPoll — confirm bundle vs standalone."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.models import PersonWalletSwap
from services.lifi.schemas import SwapConfirmExecuteResponse, SwapExecuteResponse
from services.swap_core.confirm_poll import SwapCoreConfirmPoll
from conftest import make_linked_client


def _migration_159_applied() -> bool:
    try:
        from sqlalchemy import inspect

        from database import engine

        return inspect(engine).has_table("person_wallet_swaps")
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_159_applied(),
    reason="Appliquer `alembic upgrade head` (159) pour les tests swap LI.FI.",
)


def _bundle_rebalance_swap(db: Session, person_id: uuid.UUID) -> PersonWalletSwap:
    swap = PersonWalletSwap(
        person_id=person_id,
        status=SwapSessionStatus.QUOTE_RECEIVED.value,
        from_asset="AAVE",
        to_asset="USDC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("0.068624940000000000"),
        slippage_bps=50,
        estimated_receive=Decimal("4.31"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        audit_log=[
            {
                "event": "bundle_leg_context",
                "bundle_execution": True,
                "batch_id": str(uuid.uuid4()),
                "portfolio_id": str(uuid.uuid4()),
                "bundle_action": "rebalance_v3",
                "leg_action": "rebalance_sell",
            },
        ],
    )
    db.add(swap)
    db.flush()
    return swap


def _standalone_swap(db: Session, person_id: uuid.UUID) -> PersonWalletSwap:
    swap = PersonWalletSwap(
        person_id=person_id,
        status=SwapSessionStatus.QUOTE_RECEIVED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        slippage_bps=50,
        estimated_receive=Decimal("0.003"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        audit_log=[],
    )
    db.add(swap)
    db.flush()
    return swap


def _fresh_quote(*, amount_in: str = "10", estimated_receive: str = "0.003"):
    return type(
        "Q",
        (),
        {
            "amount_in": amount_in,
            "estimated_receive": estimated_receive,
            "slippage_bps": 50,
        },
    )()


def _mock_confirm_deps(*, fresh_quote):
    execute = SwapExecuteResponse(
        swap_id=uuid.uuid4(),
        status="AWAITING_SIGNATURE",
        lifecycle_message="Signez la transaction.",
    )
    confirm_response = SwapConfirmExecuteResponse(
        freshness="verified",
        quote=MagicMock(),
        execute=execute,
    )
    return execute, confirm_response


def test_bundle_internal_skips_review_amount_in_mismatch(db: Session):
    pe = make_linked_client(db)
    swap = _bundle_rebalance_swap(db, pe.person_id)
    db.commit()

    fresh = _fresh_quote(
        amount_in="0.068624940000000000",
        estimated_receive="4.31",
    )
    execute = SwapExecuteResponse(
        swap_id=swap.id,
        status="AWAITING_SIGNATURE",
        lifecycle_message="Signez la transaction.",
    )

    with patch.object(
        SwapCoreConfirmPoll,
        "_quote",
        create=True,
    ) as quote_mock, patch.object(
        SwapCoreConfirmPoll,
        "_execute",
        create=True,
    ) as execute_mock, patch(
        "services.swap_core.confirm_poll.lifi_intent_orchestrator_enabled_for_person",
        return_value=False,
    ), patch(
        "services.lifi.lifi_swap_global_lock.acquire_lifi_swap_global_lock_or_raise",
    ):
        quote_mock.refresh_quote.return_value = fresh
        execute_mock.prepare_execute.return_value = execute
        svc = SwapCoreConfirmPoll(quote_service=quote_mock, execute_service=execute_mock)

        out = svc.confirm_and_execute(
            db,
            person_id=pe.person_id,
            swap_id=swap.id,
            review_estimated_receive="4.31",
            review_amount_in="0.06862494",
        )

    assert out.execute.status == "AWAITING_SIGNATURE"
    execute_mock.prepare_execute.assert_called_once()


def test_standalone_rejects_review_amount_mismatch(db: Session):
    pe = make_linked_client(db)
    swap = _standalone_swap(db, pe.person_id)
    db.commit()

    fresh = _fresh_quote(amount_in="10", estimated_receive="0.003")

    with patch.object(
        SwapCoreConfirmPoll,
        "_quote",
        create=True,
    ) as quote_mock, patch(
        "services.swap_core.confirm_poll.lifi_intent_orchestrator_enabled_for_person",
        return_value=False,
    ):
        quote_mock.refresh_quote.return_value = fresh
        svc = SwapCoreConfirmPoll(quote_service=quote_mock)

        with pytest.raises(SwapValidationError) as exc_info:
            svc.confirm_and_execute(
                db,
                person_id=pe.person_id,
                swap_id=swap.id,
                review_estimated_receive="0.003",
                review_amount_in="9.99",
            )

    assert exc_info.value.code == "swap.amount_changed"
    db.refresh(swap)
    assert any(
        e.get("event") == "confirm_prepare_failed" and e.get("code") == "swap.amount_changed"
        for e in (swap.audit_log or [])
        if isinstance(e, dict)
    )
