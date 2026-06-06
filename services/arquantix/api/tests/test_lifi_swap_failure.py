"""Tests échecs swap — failure record, abandon explicite, wallet lock."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_client import LifiClient
from services.lifi.models import PersonWalletSwap
from services.lifi.routes import _confirm_svc, _execute_svc, _quote_svc
from services.lifi.signing_wallet_service import read_signing_wallet_from_audit
from services.lifi.swap_failure_enums import SwapFailureCode, SwapFailurePhase
from services.lifi.swap_failure_service import record_swap_failure, validate_swap_failure_payload
from services.lifi.lifi_validation_service import SwapValidationError
from tests.conftest import ensure_admin_for_linked_client, make_linked_client


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

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
EVM_ADDR_OTHER = "0x1111111111111111111111111111111111111111"
PRIVY_USER = "did:privy:testswapfailure01"


def _auth_headers(db: Session, client_id):
    user = ensure_admin_for_linked_client(db, client_id)
    token = create_access_token(build_user_jwt_access_base_claims(user))
    return {"Authorization": f"Bearer {token}"}


def _seed_wallet(db: Session, pe):
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=PRIVY_USER,
        external_email="swap-failure@test.local",
    )
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-fail"},
    )
    db.commit()


def _mock_lifi_quote():
    return {
        "id": "quote-fail-1",
        "tool": "sushiswap",
        "action": {"fromChainId": 8453, "toChainId": 8453},
        "estimate": {
            "toAmount": "16000",
            "toAmountMin": "15000",
            "executionDuration": 60,
            "feeCosts": [],
        },
        "transactionRequest": {
            "to": "0x1234567890123456789012345678901234567890",
            "data": "0xdeadbeef",
            "value": "0",
            "chainId": 8453,
        },
    }


def _create_awaiting_swap(client: TestClient, db: Session, pe, monkeypatch) -> str:
    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_quote.return_value = _mock_lifi_quote()
    _quote_svc._lifi = mock_client
    _confirm_svc._quote._lifi = mock_client
    monkeypatch.setenv("LIFI_API_KEY", "test-key")

    quote_res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDC",
            "to_asset": "CBBTC",
            "amount": "1",
            "from_chain": "base",
            "to_chain": "base",
        },
    )
    assert quote_res.status_code == 200, quote_res.text
    swap_id = quote_res.json()["swap_id"]
    confirm_res = client.post(
        "/api/swaps/confirm-execute",
        headers=_auth_headers(db, pe),
        json={
            "swap_id": swap_id,
            "review_estimated_receive": quote_res.json()["estimated_receive"],
            "review_amount_in": quote_res.json()["amount_in"],
        },
    )
    assert confirm_res.status_code == 200, confirm_res.text
    return swap_id


def test_record_swap_failure_persists_audit(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = _create_awaiting_swap(client, db, pe, monkeypatch)

    res = client.post(
        f"/api/swaps/{swap_id}/failure",
        headers=_auth_headers(db, pe),
        json={
            "failure_phase": SwapFailurePhase.APPROVAL.value,
            "error_code": SwapFailureCode.USER_REJECTED_APPROVAL.value,
            "technical_message": "user rejected",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == SwapSessionStatus.FAILED.value
    assert "refusée" in (body.get("error_message") or "").lower()

    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_id).first()
    audit = swap.audit_log if isinstance(swap.audit_log, list) else []
    failed_events = [e for e in audit if isinstance(e, dict) and e.get("event") == "execution_failed"]
    assert len(failed_events) == 1
    assert failed_events[0]["error_code"] == SwapFailureCode.USER_REJECTED_APPROVAL.value


def test_abandon_requires_explicit_flag(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = _create_awaiting_swap(client, db, pe, monkeypatch)

    res = client.post(
        f"/api/swaps/{swap_id}/abandon",
        headers=_auth_headers(db, pe),
        json={},
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "swap.abandon_requires_explicit"


def test_explicit_abandon_records_user_abandoned(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = _create_awaiting_swap(client, db, pe, monkeypatch)

    res = client.post(
        f"/api/swaps/{swap_id}/abandon",
        headers=_auth_headers(db, pe),
        json={"explicit_user_abandon": True, "failure_phase": "approval"},
    )
    assert res.status_code == 200, res.text
    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_id).first()
    audit = swap.audit_log if isinstance(swap.audit_log, list) else []
    failed = [e for e in audit if isinstance(e, dict) and e.get("event") == "execution_failed"]
    assert failed and failed[-1]["error_code"] == SwapFailureCode.USER_ABANDONED.value


def test_failure_rejects_invalid_error_code(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = _create_awaiting_swap(client, db, pe, monkeypatch)

    res = client.post(
        f"/api/swaps/{swap_id}/failure",
        headers=_auth_headers(db, pe),
        json={
            "failure_phase": SwapFailurePhase.APPROVAL.value,
            "error_code": "not_a_real_code",
            "technical_message": "bad code",
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "swap.invalid_error_code"


def test_failure_rejects_invalid_failure_phase(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = _create_awaiting_swap(client, db, pe, monkeypatch)

    res = client.post(
        f"/api/swaps/{swap_id}/failure",
        headers=_auth_headers(db, pe),
        json={
            "failure_phase": "not_a_phase",
            "error_code": SwapFailureCode.UNKNOWN_ERROR.value,
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "swap.invalid_failure_phase"


def test_validate_swap_failure_payload_unit():
    validate_swap_failure_payload(
        failure_phase=SwapFailurePhase.SIGNING.value,
        error_code=SwapFailureCode.WALLET_ERROR.value,
    )
    with pytest.raises(SwapValidationError) as exc_info:
        validate_swap_failure_payload(
            failure_phase="bogus",
            error_code=SwapFailureCode.UNKNOWN_ERROR.value,
        )
    assert exc_info.value.code == "swap.invalid_failure_phase"
    with pytest.raises(SwapValidationError) as exc_info:
        validate_swap_failure_payload(
            failure_phase=SwapFailurePhase.POLLING.value,
            error_code="bogus",
        )
    assert exc_info.value.code == "swap.invalid_error_code"


def test_submit_requires_wallet_address_when_locked(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = _create_awaiting_swap(client, db, pe, monkeypatch)

    res = client.post(
        f"/api/swaps/{swap_id}/submit",
        headers=_auth_headers(db, pe),
        json={
            "tx_hash": "0xabc123def4567890abc123def4567890abc123def4567890abc123def4567890",
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "swap.wallet_address_required"


def test_approval_requires_wallet_address_when_locked(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = _create_awaiting_swap(client, db, pe, monkeypatch)

    res = client.post(
        f"/api/swaps/{swap_id}/approval",
        headers=_auth_headers(db, pe),
        json={
            "tx_hash": "0xabc123def4567890abc123def4567890abc123def4567890abc123def4567890",
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "swap.wallet_address_required"


def test_submit_without_address_ok_legacy_swap_no_wallet_lock(
    client: TestClient,
    db: Session,
    monkeypatch,
):
    """Rétrocompat : swaps sans wallet_locked n'exigent pas signing_wallet_address."""
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "1")
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = uuid4()
    swap = PersonWalletSwap(
        id=swap_id,
        person_id=pe.person_id,
        status=SwapSessionStatus.AWAITING_SIGNATURE.value,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        slippage_bps=50,
        audit_log=[
            {
                "event": "quote_requested",
                "signing_wallet_mode": "privy_embedded",
                "signing_wallet_address": EVM_ADDR,
            }
        ],
    )
    db.add(swap)
    db.commit()

    res = client.post(
        f"/api/swaps/{swap_id}/submit",
        headers=_auth_headers(db, pe),
        json={"tx_hash": f"0xmock{swap_id.hex[:16]}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == SwapSessionStatus.CONFIRMED.value


def test_wallet_mismatch_on_submit(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = _create_awaiting_swap(client, db, pe, monkeypatch)

    res = client.post(
        f"/api/swaps/{swap_id}/submit",
        headers=_auth_headers(db, pe),
        json={
            "tx_hash": "0xabc123def4567890abc123def4567890abc123def4567890abc123def4567890",
            "signing_wallet_address": EVM_ADDR_OTHER,
        },
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "swap.wallet_mismatch"


def test_wallet_locked_on_confirm_execute(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap_id = _create_awaiting_swap(client, db, pe, monkeypatch)

    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_id).first()
    audit = swap.audit_log if isinstance(swap.audit_log, list) else []
    assert any(isinstance(e, dict) and e.get("event") == "wallet_locked" for e in audit)
    mode, addr = read_signing_wallet_from_audit(audit)
    assert addr and addr.lower() == EVM_ADDR.lower()


def test_usdc_one_dollar_quote(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_quote.return_value = _mock_lifi_quote()
    _quote_svc._lifi = mock_client
    monkeypatch.setenv("LIFI_API_KEY", "test-key")

    res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDC",
            "to_asset": "CBBTC",
            "amount": "1",
            "from_chain": "base",
            "to_chain": "base",
        },
    )
    assert res.status_code == 200, res.text
    assert Decimal(res.json()["amount_in"]) == Decimal("1")
