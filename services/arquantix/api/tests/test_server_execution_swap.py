"""Tests unitaires — exécution serveur d'un swap (signature déléguée + fallback)."""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.lifi.enums import SwapSessionStatus
from services.privy_wallet.privy_api_client import PrivyApiError
from services.trade_core import server_execution as se


# --------------------------------------------------------------- helpers calldata


def test_build_approve_calldata_shape():
    data = se.build_approve_calldata("0x" + "ab" * 20, "1000")
    assert data.startswith("0x095ea7b3")
    assert len(data) == 2 + 8 + 64 + 64  # 0x + selector + addr + amount
    assert data.endswith(format(1000, "x").rjust(64, "0"))
    assert ("ab" * 20).rjust(64, "0") in data


# ------------------------------------------------- résolution adresse embedded


def test_evm_chain_types_includes_evm():
    # Garde-fou : le wallet embedded Privy est stocké avec chain_type='evm' en base
    # (régression prod : un filtre 'ethereum' renvoyait None -> fallback signature client).
    assert "evm" in se._EVM_CHAIN_TYPES


def test_resolve_embedded_prefers_primary():
    class _Query:
        def __init__(self, rows):
            self._rows = rows

        def filter(self, *a, **k):
            return self

        def all(self):
            return self._rows

    class _DB:
        def __init__(self, rows):
            self._rows = rows

        def query(self, *a, **k):
            return _Query(self._rows)

    rows = [
        SimpleNamespace(address="0xSECONDARY", is_primary=False),
        SimpleNamespace(address="0xPRIMARY", is_primary=True),
    ]
    assert se.resolve_privy_embedded_evm_address(_DB(rows), person_id=PERSON_ID) == "0xPRIMARY"


# --------------------------------------------------------------- fixtures fakes


PERSON_ID = uuid4()
SWAP_ID = uuid4()


def _fake_repo(status: str):
    swap = SimpleNamespace(status=status)
    return SimpleNamespace(get_for_person=lambda db, swap_id, person_id: swap)


def _fake_prepared(*, approval=None, mode="privy_embedded", address="0xWALLET"):
    transaction = SimpleNamespace(
        chain_id=8453, to="0xrouter", data="0xdead", value="0x0", gas_limit="0x5208"
    )
    return SimpleNamespace(
        signing_wallet_address=address,
        signing_wallet_mode=mode,
        transaction=transaction,
        token_approval=approval,
    )


class _FakeExecuteSvc:
    def __init__(self, prepared):
        self._prepared = prepared
        self.approval_calls = []

    def prepare_execute(self, db, *, person_id, swap_id):
        return self._prepared

    def record_token_approval(self, db, *, person_id, swap_id, tx_hash, signing_wallet_address):
        self.approval_calls.append(tx_hash)


def _patch_common(monkeypatch, *, configured=True, delegated=True, privy_id="wallet-abc"):
    monkeypatch.setattr(se, "privy_delegated_signing_configured", lambda: configured)
    monkeypatch.setattr(
        se, "resolve_privy_embedded_evm_address", lambda db, *, person_id: "0xWALLET"
    )
    monkeypatch.setattr(
        se, "is_signing_wallet_delegated", lambda db, *, person_id, wallet_address: delegated
    )
    monkeypatch.setattr(
        se, "resolve_privy_wallet_id", lambda db, *, person_id, wallet_address: privy_id
    )
    # Hermétique : pas de RPC réseau par défaut (chemin best-effort sans attente on-chain).
    monkeypatch.setattr(se, "resolve_chain_rpc_url", lambda chain_id: None)


# --------------------------------------------------------------- états terminaux


def test_confirmed_swap_is_noop():
    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.CONFIRMED.value),
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "confirmed"
    assert res.signed_server_side is False
    assert res.settled is True


def test_submitted_swap_finalizes(monkeypatch):
    monkeypatch.setattr(
        se, "finalize_virtual_wallet_swap",
        lambda db, *, person_id, swap_id: SimpleNamespace(status="confirmed", tx_hash="0xabc", settled=True),
    )
    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.SUBMITTED.value),
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "confirmed"
    assert res.tx_hash == "0xabc"
    assert res.signed_server_side is False


# --------------------------------------------------------------- fallbacks


def test_fallback_when_not_configured(monkeypatch):
    _patch_common(monkeypatch, configured=False)
    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value),
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "awaiting_signature"
    assert res.fallback_reason == "delegated_signing_not_configured"
    assert res.signed_server_side is False


def test_fallback_when_wallet_not_delegated(monkeypatch):
    _patch_common(monkeypatch, delegated=False)
    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.AWAITING_SIGNATURE.value),
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "awaiting_signature"
    assert res.fallback_reason == "wallet_not_delegated"


def test_fallback_on_sign_error(monkeypatch):
    _patch_common(monkeypatch)

    def _raise(**kwargs):
        raise PrivyApiError("privy.rpc_failed", "boom")

    monkeypatch.setattr(se, "send_delegated_sponsored_transaction", _raise)
    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value),
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "awaiting_signature"
    assert res.fallback_reason == "sign_failed:privy.rpc_failed"


def test_not_delegated_skips_prepare(monkeypatch):
    """Zéro effet de bord : si non délégué, prepare_execute n'est jamais appelé (pas de lock)."""
    _patch_common(monkeypatch, delegated=False)

    class _NoPrepare(_FakeExecuteSvc):
        def prepare_execute(self, db, *, person_id, swap_id):
            raise AssertionError("prepare_execute ne doit pas être appelé si non délégué")

    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value),
        execute_svc=_NoPrepare(_fake_prepared()),
    )
    assert res.fallback_reason == "wallet_not_delegated"
    assert res.signed_server_side is False


def test_fallback_when_embedded_address_unresolved(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(se, "resolve_privy_embedded_evm_address", lambda db, *, person_id: None)
    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value),
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.fallback_reason == "signing_wallet_unresolved"
    assert res.signed_server_side is False


# --------------------------------------------------------------- happy paths


def test_happy_path_no_approval(monkeypatch):
    _patch_common(monkeypatch)
    sent = []
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction",
        lambda **kw: sent.append(kw) or {"hash": "0xfeed", "transaction_id": "t1"},
    )
    completed = SimpleNamespace(
        finalize=SimpleNamespace(status="confirmed", settled=True, tx_hash="0xfeed"), phase="confirmed"
    )
    captured = {}
    monkeypatch.setattr(
        se, "complete_virtual_wallet_swap",
        lambda db, *, person_id, swap_id, tx_hash, signing_wallet_address: captured.update(
            {"tx_hash": tx_hash, "addr": signing_wallet_address}
        )
        or completed,
    )

    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value),
        execute_svc=_FakeExecuteSvc(_fake_prepared(approval=None)),
    )

    assert res.phase == "confirmed"
    assert res.signed_server_side is True
    assert res.tx_hash == "0xfeed"
    assert res.settled is True
    assert len(sent) == 1  # uniquement le swap, pas d'approval
    assert captured == {"tx_hash": "0xfeed", "addr": "0xWALLET"}


def test_happy_path_with_approval(monkeypatch):
    _patch_common(monkeypatch)
    sent = []
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction",
        lambda **kw: sent.append(kw) or {"hash": f"0x{len(sent)}", "transaction_id": None},
    )
    monkeypatch.setattr(
        se, "complete_virtual_wallet_swap",
        lambda db, **kw: SimpleNamespace(
            finalize=SimpleNamespace(status="confirmed", settled=True, tx_hash=kw["tx_hash"]),
            phase="confirmed",
        ),
    )
    approval = SimpleNamespace(
        required=True, token_address="0xtoken", spender_address="0xspender", amount_atomic="1000"
    )
    svc = _FakeExecuteSvc(_fake_prepared(approval=approval))

    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value),
        execute_svc=svc,
    )

    assert res.signed_server_side is True
    assert len(sent) == 2  # approval + swap
    assert sent[0]["to"] == "0xtoken"
    assert sent[0]["data"].startswith("0x095ea7b3")
    assert svc.approval_calls == ["0x1"]  # record_token_approval reçu avec le hash d'approval


def test_swap_not_found_raises():
    repo = SimpleNamespace(get_for_person=lambda db, swap_id, person_id: None)
    with pytest.raises(ValueError, match="swap_not_found"):
        se.execute_prepared_swap_server_side(
            None, person_id=PERSON_ID, swap_id=SWAP_ID, swap_repo=repo,
            execute_svc=_FakeExecuteSvc(_fake_prepared()),
        )


# --------------------------------------------------- gating allowance / receipt


def test_read_erc20_allowance_calldata_and_parse(monkeypatch):
    captured = {}

    def _rpc(rpc_url, method, params, **kw):
        captured["url"] = rpc_url
        captured["method"] = method
        captured["params"] = params
        return "0x" + format(123456, "x")

    monkeypatch.setattr(se, "json_rpc_call", _rpc)
    out = se.read_erc20_allowance(
        "https://rpc", token_address="0xtoken", owner_address="0x" + "11" * 20,
        spender_address="0x" + "22" * 20,
    )
    assert out == 123456
    assert captured["method"] == "eth_call"
    data = captured["params"][0]["data"]
    assert data.startswith(se.ALLOWANCE_SELECTOR)
    assert ("11" * 20).rjust(64, "0") in data  # owner padded
    assert ("22" * 20).rjust(64, "0") in data  # spender padded


def test_wait_for_approval_confirmed_success(monkeypatch):
    monkeypatch.setattr(se, "fetch_transaction_receipt", lambda url, h: {"status": "0x1"})
    assert se.wait_for_approval_confirmed("https://rpc", "0xhash", sleep_fn=lambda *_: None) is True


def test_wait_for_approval_confirmed_revert(monkeypatch):
    monkeypatch.setattr(se, "fetch_transaction_receipt", lambda url, h: {"status": "0x0"})
    assert se.wait_for_approval_confirmed("https://rpc", "0xhash", sleep_fn=lambda *_: None) is False


def test_wait_for_approval_confirmed_timeout(monkeypatch):
    # Receipt jamais disponible (tx pending) : EvmRpcError à chaque poll → timeout → False.
    def _raise(url, h):
        raise se.EvmRpcError("pending", code="evm.rpc.receipt_missing")

    monkeypatch.setattr(se, "fetch_transaction_receipt", _raise)
    clock = {"t": 0.0}

    def _now():
        return clock["t"]

    def _sleep(s):
        clock["t"] += s

    assert (
        se.wait_for_approval_confirmed(
            "https://rpc", "0xhash", timeout_s=10, poll_s=3, sleep_fn=_sleep, now_fn=_now
        )
        is False
    )


def _approval(amount="1000"):
    return SimpleNamespace(
        required=True, token_address="0xtoken", spender_address="0xspender", amount_atomic=amount
    )


def test_approval_skipped_when_allowance_sufficient(monkeypatch):
    """Allowance live suffisante → aucune approval émise, swap seul (pas de tx redondante)."""
    _patch_common(monkeypatch)
    monkeypatch.setattr(se, "resolve_chain_rpc_url", lambda chain_id: "https://rpc")
    monkeypatch.setattr(se, "read_erc20_allowance", lambda *a, **k: 5000)  # >= 1000
    waited = []
    monkeypatch.setattr(
        se, "wait_for_approval_confirmed", lambda *a, **k: waited.append(1) or True
    )
    sent = []
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction",
        lambda **kw: sent.append(kw) or {"hash": "0xswap"},
    )
    monkeypatch.setattr(
        se, "complete_virtual_wallet_swap",
        lambda db, **kw: SimpleNamespace(
            finalize=SimpleNamespace(status="confirmed", settled=True, tx_hash=kw["tx_hash"]),
            phase="confirmed",
        ),
    )
    svc = _FakeExecuteSvc(_fake_prepared(approval=_approval()))
    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value), execute_svc=svc,
    )
    assert res.signed_server_side is True
    assert len(sent) == 1  # uniquement le swap
    assert sent[0]["to"] == "0xrouter"
    assert svc.approval_calls == []  # pas d'approval enregistrée
    assert waited == []  # pas d'attente puisque pas d'approval


def test_approval_waits_for_confirmation_then_swaps(monkeypatch):
    """Allowance insuffisante → approval émise PUIS attente confirmation AVANT le swap."""
    _patch_common(monkeypatch)
    monkeypatch.setattr(se, "resolve_chain_rpc_url", lambda chain_id: "https://rpc")
    monkeypatch.setattr(se, "read_erc20_allowance", lambda *a, **k: 0)  # < 1000
    order = []
    monkeypatch.setattr(
        se, "wait_for_approval_confirmed",
        lambda url, h, **k: order.append(("wait", h)) or True,
    )

    def _send(**kw):
        order.append(("send", kw["to"]))
        return {"hash": "0xapprove" if kw["to"] == "0xtoken" else "0xswap"}

    monkeypatch.setattr(se, "send_delegated_sponsored_transaction", _send)
    monkeypatch.setattr(
        se, "complete_virtual_wallet_swap",
        lambda db, **kw: SimpleNamespace(
            finalize=SimpleNamespace(status="confirmed", settled=True, tx_hash=kw["tx_hash"]),
            phase="confirmed",
        ),
    )
    svc = _FakeExecuteSvc(_fake_prepared(approval=_approval()))
    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value), execute_svc=svc,
    )
    assert res.signed_server_side is True
    # Ordre critique : approval → attente confirmation → swap.
    assert order == [("send", "0xtoken"), ("wait", "0xapprove"), ("send", "0xrouter")]
    assert svc.approval_calls == ["0xapprove"]


def test_fallback_when_approval_unconfirmed(monkeypatch):
    """Approval non confirmée dans le délai → fallback propre, swap NON diffusé."""
    _patch_common(monkeypatch)
    monkeypatch.setattr(se, "resolve_chain_rpc_url", lambda chain_id: "https://rpc")
    monkeypatch.setattr(se, "read_erc20_allowance", lambda *a, **k: 0)
    monkeypatch.setattr(se, "wait_for_approval_confirmed", lambda *a, **k: False)
    sent = []
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction",
        lambda **kw: sent.append(kw["to"]) or {"hash": "0xapprove"},
    )
    monkeypatch.setattr(
        se, "complete_virtual_wallet_swap",
        lambda *a, **k: pytest.fail("le swap ne doit pas être diffusé si approval non confirmée"),
    )
    res = se.execute_prepared_swap_server_side(
        None, person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value),
        execute_svc=_FakeExecuteSvc(_fake_prepared(approval=_approval())),
    )
    assert res.phase == "awaiting_signature"
    assert res.fallback_reason == "approval_unconfirmed"
    assert res.signed_server_side is False
    assert sent == ["0xtoken"]  # approval émise, mais pas le swap
