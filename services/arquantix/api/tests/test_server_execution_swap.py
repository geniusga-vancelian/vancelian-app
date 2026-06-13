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


class _FakeDB:
    """DB minimal : commit/refresh no-op (le marquage BROADCASTING commit avant broadcast)."""

    def commit(self):
        pass

    def refresh(self, _obj):
        pass


def _fake_repo(status: str, *, broadcast_intent: dict | None = None):
    swap = SimpleNamespace(status=status, audit_log=[])
    if broadcast_intent is not None:
        swap._broadcast_intent = broadcast_intent

    def _mark_broadcasting(
        s,
        *,
        idempotency_key,
        privy_wallet_id,
        chain_id,
        to,
        data,
        value,
        gas_limit,
        signing_wallet_address=None,
    ):
        s.status = SwapSessionStatus.BROADCASTING.value
        s._broadcast_intent = {
            "event": "swap_broadcast_initiated",
            "idempotency_key": idempotency_key,
            "privy_wallet_id": privy_wallet_id,
            "chain_id": chain_id,
            "to": to,
            "data": data,
            "value": value,
            "gas_limit": gas_limit,
            "signing_wallet_address": signing_wallet_address,
        }

    def _read_broadcast_intent(s):
        return getattr(s, "_broadcast_intent", None)

    return SimpleNamespace(
        get_for_person=lambda db, swap_id, person_id: swap,
        mark_broadcasting=_mark_broadcasting,
        read_broadcast_intent=_read_broadcast_intent,
        append_audit=lambda s, e: None,
    )


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


def test_sign_error_after_broadcasting_stays_broadcasting(monkeypatch):
    """D1 — échec broadcast APRÈS marquage BROADCASTING : on ne retombe pas en
    awaiting_signature (qui créerait un nouveau swap). On reste en ``broadcasting``
    pour reprise idempotente sur le même swap_id."""
    _patch_common(monkeypatch)

    def _raise(**kwargs):
        raise PrivyApiError("privy.rpc_failed", "boom")

    monkeypatch.setattr(se, "send_delegated_sponsored_transaction", _raise)
    repo = _fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value)
    res = se.execute_prepared_swap_server_side(
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=repo,
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "broadcasting"
    assert res.fallback_reason == "sign_failed:privy.rpc_failed"
    assert res.signed_server_side is False
    # Le swap est laissé en BROADCASTING avec l'intent de rejeu persisté.
    swap = repo.get_for_person(None, swap_id=SWAP_ID, person_id=PERSON_ID)
    assert swap.status == SwapSessionStatus.BROADCASTING.value
    assert repo.read_broadcast_intent(swap)["idempotency_key"] == f"vance-swap:{SWAP_ID}"


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
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value),
        execute_svc=_FakeExecuteSvc(_fake_prepared(approval=None)),
    )

    assert res.phase == "confirmed"
    assert res.signed_server_side is True
    assert res.tx_hash == "0xfeed"
    assert res.settled is True
    assert len(sent) == 1  # uniquement le swap, pas d'approval
    assert captured == {"tx_hash": "0xfeed", "addr": "0xWALLET"}
    # D1 — la diffusion du swap porte la clé d'idempotence Privy déterministe.
    assert sent[0]["idempotency_key"] == f"vance-swap:{SWAP_ID}"


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
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID,
        swap_repo=_fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value),
        execute_svc=svc,
    )

    assert res.signed_server_side is True
    assert len(sent) == 2  # approval + swap
    assert sent[0]["to"] == "0xtoken"
    assert sent[0]["data"].startswith("0x095ea7b3")
    assert svc.approval_calls == ["0x1"]  # record_token_approval reçu avec le hash d'approval
    # D1 — approval et swap portent des clés d'idempotence distinctes (corps différents).
    assert sent[0]["idempotency_key"] == f"vance-approve:{SWAP_ID}"
    assert sent[1]["idempotency_key"] == f"vance-swap:{SWAP_ID}"


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
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID,
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
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID,
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


# ----------------------------------------------- D1 reprise BROADCASTING (idempotence)


def _broadcast_intent():
    return {
        "event": "swap_broadcast_initiated",
        "idempotency_key": f"vance-swap:{SWAP_ID}",
        "privy_wallet_id": "wallet-abc",
        "chain_id": 8453,
        "to": "0xrouter",
        "data": "0xdead",
        "value": "0x0",
        "gas_limit": "0x5208",
        "signing_wallet_address": "0xWALLET",
    }


def test_broadcasting_entry_recovers_via_idempotency(monkeypatch):
    """Swap déjà BROADCASTING : rejeu avec la MÊME clé d'idempotence (pas de nouvelle
    signature) ; Privy renvoie la tx d'origine → CONFIRMED."""
    sent = []
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction",
        lambda **kw: sent.append(kw) or {"hash": "0xorig", "transaction_id": "t1"},
    )
    captured = {}
    monkeypatch.setattr(
        se, "complete_virtual_wallet_swap",
        lambda db, *, person_id, swap_id, tx_hash, signing_wallet_address=None: captured.update(
            {"tx_hash": tx_hash}
        )
        or SimpleNamespace(
            finalize=SimpleNamespace(status="confirmed", settled=True, tx_hash=tx_hash),
            phase="confirmed",
        ),
    )
    repo = _fake_repo(SwapSessionStatus.BROADCASTING.value, broadcast_intent=_broadcast_intent())
    res = se.execute_prepared_swap_server_side(
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID, swap_repo=repo,
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "confirmed"
    assert res.tx_hash == "0xorig"
    assert len(sent) == 1
    assert sent[0]["idempotency_key"] == f"vance-swap:{SWAP_ID}"  # MÊME clé
    assert sent[0]["to"] == "0xrouter"  # MÊME corps RPC (rejoué depuis l'intent persisté)
    assert captured["tx_hash"] == "0xorig"


def test_broadcasting_entry_never_calls_prepare(monkeypatch):
    """La reprise n'appelle JAMAIS prepare_execute (pas de nouvelle quote/calldata)."""
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction", lambda **kw: {"hash": "0xorig"}
    )
    monkeypatch.setattr(
        se, "complete_virtual_wallet_swap",
        lambda db, **kw: SimpleNamespace(
            finalize=SimpleNamespace(status="submitted", settled=False, tx_hash="0xorig"),
            phase="submitted",
        ),
    )

    class _NoPrepare(_FakeExecuteSvc):
        def prepare_execute(self, db, *, person_id, swap_id):
            raise AssertionError("prepare_execute interdit en reprise BROADCASTING")

    repo = _fake_repo(SwapSessionStatus.BROADCASTING.value, broadcast_intent=_broadcast_intent())
    res = se.execute_prepared_swap_server_side(
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID, swap_repo=repo,
        execute_svc=_NoPrepare(_fake_prepared()),
    )
    assert res.phase == "submitted"


def test_broadcasting_recovery_pending_on_privy_error(monkeypatch):
    """Erreur Privy en reprise → reste broadcasting (pending) ; aucune double exécution."""

    def _raise(**kw):
        raise PrivyApiError("privy.rpc_unreachable", "down")

    monkeypatch.setattr(se, "send_delegated_sponsored_transaction", _raise)
    monkeypatch.setattr(
        se, "complete_virtual_wallet_swap",
        lambda *a, **k: pytest.fail("complete interdit si la reprise échoue"),
    )
    repo = _fake_repo(SwapSessionStatus.BROADCASTING.value, broadcast_intent=_broadcast_intent())
    res = se.execute_prepared_swap_server_side(
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID, swap_repo=repo,
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "broadcasting"
    assert res.fallback_reason == "recovery_pending:privy.rpc_unreachable"
    assert res.signed_server_side is False


def test_broadcasting_without_intent_never_broadcasts(monkeypatch):
    """Marqueur de rejeu perdu → on ne rediffuse PAS (impossible de garantir l'unicité)."""
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction",
        lambda **kw: pytest.fail("aucune diffusion sans intent de rejeu"),
    )
    repo = _fake_repo(SwapSessionStatus.BROADCASTING.value, broadcast_intent=None)
    res = se.execute_prepared_swap_server_side(
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID, swap_repo=repo,
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "broadcasting"
    assert res.fallback_reason == "broadcast_intent_missing"


def test_crash_between_broadcast_and_commit_recovers_same_key(monkeypatch):
    """Bug D1 reproduit : 1ʳᵉ exécution diffuse puis 'crash' (complete lève) ; le retry
    reprend en BROADCASTING avec la MÊME clé d'idempotence → Privy ne diffuse qu'UNE tx."""
    _patch_common(monkeypatch)
    sent = []
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction",
        lambda **kw: sent.append(kw) or {"hash": "0xorig", "transaction_id": "t1"},
    )

    calls = {"n": 0}

    def _complete(db, *, person_id, swap_id, tx_hash, signing_wallet_address=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("worker crash après broadcast")
        return SimpleNamespace(
            finalize=SimpleNamespace(status="confirmed", settled=True, tx_hash=tx_hash),
            phase="confirmed",
        )

    monkeypatch.setattr(se, "complete_virtual_wallet_swap", _complete)
    repo = _fake_repo(SwapSessionStatus.QUOTE_RECEIVED.value)

    with pytest.raises(RuntimeError, match="worker crash"):
        se.execute_prepared_swap_server_side(
            _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID, swap_repo=repo,
            execute_svc=_FakeExecuteSvc(_fake_prepared()),
        )

    swap = repo.get_for_person(None, swap_id=SWAP_ID, person_id=PERSON_ID)
    assert swap.status == SwapSessionStatus.BROADCASTING.value  # laissé in-flight

    # Retry → reprise idempotente.
    res = se.execute_prepared_swap_server_side(
        _FakeDB(), person_id=PERSON_ID, swap_id=SWAP_ID, swap_repo=repo,
        execute_svc=_FakeExecuteSvc(_fake_prepared()),
    )
    assert res.phase == "confirmed"
    assert len(sent) == 2  # deux appels Privy émis...
    assert sent[0]["idempotency_key"] == sent[1]["idempotency_key"] == f"vance-swap:{SWAP_ID}"
    # ...mais MÊME clé d'idempotence → une seule transaction on-chain (exactly-once).
