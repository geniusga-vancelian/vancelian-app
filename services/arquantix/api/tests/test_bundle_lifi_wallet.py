"""Tests résolution wallet Privy EVM pour bundle LI.FI Base."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from services.portfolio_engine.bundle_execution.bundle_lifi_validation import (
    BundleLifiValidationError,
)
from services.portfolio_engine.bundle_execution.bundle_lifi_wallet import (
    BASE_LIFI_CHAIN_ID,
    _pick_privy_evm_wallet,
    resolve_evm_wallet_for_person,
    wallet_supports_evm_network,
)


def _wallet(
    *,
    chain_type: str,
    provider: str = "privy",
    is_primary: bool = True,
    chain_id: int | None = None,
    address: str = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
) -> SimpleNamespace:
    return SimpleNamespace(
        provider=provider,
        chain_type=chain_type,
        chain_id=chain_id,
        is_primary=is_primary,
        address=address,
        revoked_at=None,
    )


def test_bundle_lifi_accepts_ethereum_chain_type_for_base():
    w = _wallet(chain_type="ethereum")
    assert wallet_supports_evm_network(w, network_chain_key="base", network_chain_id=8453)


def test_bundle_lifi_accepts_evm_chain_type_for_base():
    w = _wallet(chain_type="evm")
    assert wallet_supports_evm_network(w, network_chain_key="base", network_chain_id=BASE_LIFI_CHAIN_ID)


def test_bundle_lifi_resolves_base_to_evm_privy_wallet():
    wallets = [
        _wallet(chain_type="solana", address="So11111111111111111111111111111111111111112"),
        _wallet(chain_type="ethereum", is_primary=True),
        _wallet(chain_type="base", is_primary=False, chain_id=8453),
    ]
    picked = _pick_privy_evm_wallet(
        wallets, network_chain_key="base", network_chain_id=8453,
    )
    assert picked is not None
    assert picked.chain_type == "ethereum"


@patch(
    "services.portfolio_engine.bundle_execution.bundle_lifi_wallet.PersonCryptoWalletRepository.list_active_for_person",
)
def test_resolve_evm_wallet_for_person_returns_checksum(mock_list):
    person_id = uuid.uuid4()
    mock_list.return_value = [_wallet(chain_type="evm")]
    db = MagicMock()
    addr = resolve_evm_wallet_for_person(db, person_id=person_id, chain="base", chain_id=8453)
    assert addr.startswith("0x")
    assert len(addr) == 42


@patch(
    "services.portfolio_engine.bundle_execution.bundle_lifi_wallet.PersonCryptoWalletRepository.list_active_for_person",
)
def test_resolve_evm_wallet_raises_when_no_evm_wallet(mock_list):
    mock_list.return_value = [_wallet(chain_type="solana", provider="privy")]
    with pytest.raises(BundleLifiValidationError) as exc:
        resolve_evm_wallet_for_person(MagicMock(), person_id=uuid.uuid4())
    assert exc.value.code == "bundle.lifi.wallet_missing"


@patch("services.portfolio_engine.bundle_execution.bundle_lifi_leg_service.swaps_mock_mode", return_value=True)
@patch("services.portfolio_engine.bundle_execution.bundle_lifi_leg_service.bundle_lifi_sync_mock", return_value=True)
def test_bundle_lifi_mock_sync_prepare_then_submit(_sync, _mock):
    from services.lifi.enums import SwapSessionStatus
    from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import BundleLifiLegService
    from services.portfolio_engine.bundle_execution.types import ExecutionLeg
    from decimal import Decimal

    person_id = uuid.uuid4()
    swap_id = uuid.uuid4()
    swap = SimpleNamespace(
        id=swap_id,
        status=SwapSessionStatus.QUOTE_RECEIVED.value,
        from_asset="USDC",
        to_asset="ETH",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("9"),
        tx_hash=None,
        audit_log=[],
    )

    leg = ExecutionLeg(
        leg_id="bundle-alloc-mock",
        portfolio_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        action="allocation",
        from_asset="USDC",
        to_asset="ETH",
        amount_from=Decimal("10"),
        batch_id="batch-mock",
        bundle_action="allocation",
        chain="base",
    )

    svc = BundleLifiLegService()
    svc._swap_repo = MagicMock()
    svc._swap_repo.get_for_person.return_value = swap

    prepare_resp = MagicMock()
    prepare_resp.model_dump.return_value = {"swap_id": str(swap_id)}
    svc._execute = MagicMock()
    svc._execute.prepare_execute.return_value = prepare_resp

    exec_result = MagicMock()
    exec_result.status = "completed"
    exec_result.from_asset = "USDC"
    exec_result.to_asset = "ETH"
    exec_result.estimated_receive = "9"
    exec_result.tx_hash = "0xmock"
    svc.submit_leg_tx = MagicMock(return_value=exec_result)

    out = svc._auto_complete_mock(db=MagicMock(), leg=leg, swap_id=swap_id, person_id=person_id)
    svc._execute.prepare_execute.assert_called_once()
    svc.submit_leg_tx.assert_called_once()
    assert out.status == "completed"
