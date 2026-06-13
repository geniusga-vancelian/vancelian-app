"""Exécution serveur d'un swap (worker) — signature déléguée Privy sans navigateur.

Point d'entrée appelé par le worker quand un intent de la file est un swap
(`lifi_swap` / operation `swap`), ou un leg bundle. L'intent porte un ``swap_id``
déjà créé (quote effectuée). Cette fonction :

  prepare_execute → (approval ERC-20) → signature serveur (Privy Session Signers)
  → submit (submit_signed_trade : swap simple ET leg bundle) → poll + settlement

Garde-fou : si le wallet n'est pas délégué au signer serveur, ou si la signature
déléguée n'est pas configurée, on **retombe sur ``awaiting_signature``** — le
comportement client historique reste intact (zéro régression).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.privy_wallet.delegated_signer import (
    privy_delegated_signing_configured,
    send_delegated_sponsored_transaction,
)
from services.privy_wallet.evm_chain_config import resolve_chain_rpc_url
from services.privy_wallet.evm_rpc_client import (
    EvmRpcError,
    fetch_transaction_receipt,
    hex_to_int,
    json_rpc_call,
)
from services.privy_wallet.privy_api_client import (
    PrivyApiError,
    fetch_privy_user,
    is_wallet_delegated,
)

from .run_wallet_swap import complete_virtual_wallet_swap, finalize_virtual_wallet_swap

logger = logging.getLogger(__name__)

# Sélecteur ERC-20 approve(address,uint256) = keccak("approve(address,uint256)")[:4]
APPROVE_SELECTOR = "0x095ea7b3"
# Sélecteur ERC-20 allowance(address owner, address spender)
ALLOWANCE_SELECTOR = "0xdd62ed3e"

# Attente de confirmation on-chain de l'approval ERC-20 avant de diffuser le swap.
# Parité avec le flux client (``ensureSwapTokenApproval`` poll le receipt jusqu'à 180 s) :
# sans cette attente, le swap est diffusé alors que l'allowance n'est pas encore posée
# on-chain → revert → swap jamais "submitted" → leg bloqué en AWAITING_SIGNATURE puis
# purgé par le reaper (~10 min). Base : blocs ~2 s, donc confirme en quelques secondes.
_APPROVAL_CONFIRM_TIMEOUT_S = 90.0
_APPROVAL_CONFIRM_POLL_S = 3.0

_SIGN_STATES = {SwapSessionStatus.QUOTE_RECEIVED.value, SwapSessionStatus.AWAITING_SIGNATURE.value}


@dataclass
class ServerSwapExecutionResult:
    """Résultat d'une tentative d'exécution serveur."""

    phase: str  # confirmed | submitted | awaiting_signature | failed | expired
    swap_id: UUID
    signed_server_side: bool
    tx_hash: str | None = None
    settled: bool = False
    fallback_reason: str | None = None


# --------------------------------------------------------------- résolution wallet


def resolve_privy_wallet_id(db: Session, *, person_id: UUID, wallet_address: str) -> str | None:
    """``privy_wallet_id`` (id RPC Privy) depuis ``person_crypto_wallets.metadata_json``."""
    from database import PersonCryptoWallet

    target = (wallet_address or "").strip().lower()
    if not target:
        return None
    rows = (
        db.query(PersonCryptoWallet)
        .filter(
            PersonCryptoWallet.person_id == person_id,
            PersonCryptoWallet.provider == "privy",
        )
        .all()
    )
    for row in rows:
        if (row.address or "").strip().lower() != target:
            continue
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        wallet_id = meta.get("privy_wallet_id") if isinstance(meta, dict) else None
        if wallet_id:
            return str(wallet_id)
    return None


# chain_type EVM tels que stockés en base (selon environnement/historique).
_EVM_CHAIN_TYPES = ("evm", "ethereum")


def resolve_privy_embedded_evm_address(db: Session, *, person_id: UUID) -> str | None:
    """Adresse du wallet embedded EVM Privy de la personne.

    Permet de vérifier la délégation **avant** ``prepare_execute`` (donc sans verrouiller
    le wallet ni préparer la tx) : la source de vérité reste l'API Privy côté serveur,
    pas un flag client potentiellement périmé.

    NB : en base ``person_crypto_wallets.chain_type`` vaut ``'evm'`` pour le wallet
    embedded Privy (et non ``'ethereum'`` qui est la valeur côté payload API Privy).
    """
    from database import PersonCryptoWallet

    rows = (
        db.query(PersonCryptoWallet)
        .filter(
            PersonCryptoWallet.person_id == person_id,
            PersonCryptoWallet.provider == "privy",
            PersonCryptoWallet.chain_type.in_(_EVM_CHAIN_TYPES),
        )
        .all()
    )
    # Wallet primaire d'abord si plusieurs.
    rows.sort(key=lambda r: not bool(getattr(r, "is_primary", False)))
    for row in rows:
        if (row.address or "").strip():
            return row.address.strip()
    return None


def is_signing_wallet_delegated(db: Session, *, person_id: UUID, wallet_address: str) -> bool:
    """True si le wallet embedded est délégué au signer serveur (flag Privy ``delegated``)."""
    try:
        from services.privy.privy_wallet_service import get_privy_user_id_for_person

        privy_user_id = get_privy_user_id_for_person(db, person_id)
        user_payload = fetch_privy_user(privy_user_id)
    except (PrivyApiError, Exception):  # noqa: BLE001 — best-effort, on retombe en fallback
        return False
    return is_wallet_delegated(user_payload, wallet_address)


# ------------------------------------------------------------- calldata approve


def _hex_pad_address(address: str) -> str:
    return address.strip().lower().removeprefix("0x").rjust(64, "0")


def _hex_pad_amount(amount_atomic: str) -> str:
    return format(int(str(amount_atomic).strip()), "x").rjust(64, "0")


def build_approve_calldata(spender_address: str, amount_atomic: str) -> str:
    """Calldata ERC-20 ``approve(spender, amount)``."""
    return APPROVE_SELECTOR + _hex_pad_address(spender_address) + _hex_pad_amount(amount_atomic)


# --------------------------------------------------- allowance & confirmation approval


def read_erc20_allowance(
    rpc_url: str, *, token_address: str, owner_address: str, spender_address: str
) -> int:
    """Allowance ERC-20 ``allowance(owner, spender)`` en unités atomiques (``eth_call``)."""
    data = (
        ALLOWANCE_SELECTOR
        + _hex_pad_address(owner_address)
        + _hex_pad_address(spender_address)
    )
    result = json_rpc_call(rpc_url, "eth_call", [{"to": token_address, "data": data}, "latest"])
    return hex_to_int(result)


def wait_for_approval_confirmed(
    rpc_url: str,
    tx_hash: str,
    *,
    timeout_s: float = _APPROVAL_CONFIRM_TIMEOUT_S,
    poll_s: float = _APPROVAL_CONFIRM_POLL_S,
    sleep_fn=time.sleep,
    now_fn=time.monotonic,
) -> bool:
    """Attend que l'approval soit minée **avec succès** on-chain.

    Retourne ``True`` si le receipt a un statut succès, ``False`` si la tx reverte ou si
    le délai est dépassé (le swap ne sera alors pas diffusé → fallback propre).
    """
    deadline = now_fn() + timeout_s
    while True:
        try:
            receipt = fetch_transaction_receipt(rpc_url, tx_hash)
        except EvmRpcError:
            receipt = None
        if isinstance(receipt, dict) and receipt.get("status") is not None:
            return str(receipt.get("status")).lower() in ("0x1", "1")
        if now_fn() >= deadline:
            return False
        sleep_fn(poll_s)


# ------------------------------------------------------------- orchestration


def _phase_from_status(status: str) -> str:
    if status == SwapSessionStatus.CONFIRMED.value:
        return "confirmed"
    if status == SwapSessionStatus.SUBMITTED.value:
        return "submitted"
    if status == SwapSessionStatus.BROADCASTING.value:
        return "broadcasting"
    if status == SwapSessionStatus.FAILED.value:
        return "failed"
    if status == SwapSessionStatus.EXPIRED.value:
        return "expired"
    return "awaiting_signature"


def broadcast_idempotency_key(swap_id: UUID) -> str:
    """Clé d'idempotence Privy déterministe du swap (D1) — stable entre retries."""
    return f"vance-swap:{swap_id}"


def approval_idempotency_key(swap_id: UUID) -> str:
    """Clé d'idempotence Privy de l'approval ERC-20 (corps distinct du swap)."""
    return f"vance-approve:{swap_id}"


def _recover_broadcasting_swap(
    db: Session,
    *,
    person_id: UUID,
    swap_id: UUID,
    swap,
    swap_repo,
) -> ServerSwapExecutionResult:
    """Reprise d'un swap déjà passé en ``BROADCASTING`` (crash entre broadcast et commit).

    Règle D1 : on ne re-signe **jamais** aveuglément. On rejoue la diffusion avec la **même**
    clé d'idempotence Privy et le **même** corps RPC persisté. Privy renvoie la transaction
    d'origine sans double exécution (ou l'exécute une seule fois si le 1ᵉʳ appel avait échoué
    avant diffusion). Tant que la reprise n'aboutit pas, on reste en ``broadcasting`` (leg
    ``pending``) — jamais un nouveau swap_id, qui aurait une clé différente et pourrait
    doubler la transaction on-chain.
    """
    intent = swap_repo.read_broadcast_intent(swap)
    if intent is None:
        logger.error(
            "server_swap.broadcasting_without_intent swap_id=%s — reprise impossible sans rejeu",
            str(swap_id),
        )
        return ServerSwapExecutionResult(
            "broadcasting", swap_id, signed_server_side=False,
            fallback_reason="broadcast_intent_missing",
        )
    try:
        swap_send = send_delegated_sponsored_transaction(
            privy_wallet_id=str(intent["privy_wallet_id"]),
            chain_id=int(intent["chain_id"]),
            to=str(intent["to"]),
            data=str(intent["data"]),
            value=intent.get("value"),
            gas_limit=intent.get("gas_limit"),
            idempotency_key=str(intent["idempotency_key"]),
        )
    except PrivyApiError as exc:
        logger.warning(
            "server_swap.broadcast_recovery_pending swap_id=%s code=%s",
            str(swap_id), exc.code,
        )
        return ServerSwapExecutionResult(
            "broadcasting", swap_id, signed_server_side=False,
            fallback_reason=f"recovery_pending:{exc.code}",
        )

    tx_hash = str(swap_send["hash"])
    completed = complete_virtual_wallet_swap(
        db,
        person_id=person_id,
        swap_id=swap_id,
        tx_hash=tx_hash,
        signing_wallet_address=intent.get("signing_wallet_address"),
    )
    finalize = completed.finalize
    phase = finalize.status if finalize is not None else completed.phase
    return ServerSwapExecutionResult(
        phase,
        swap_id,
        signed_server_side=True,
        tx_hash=tx_hash,
        settled=bool(finalize.settled) if finalize is not None else False,
    )


def execute_prepared_swap_server_side(
    db: Session,
    *,
    person_id: UUID,
    swap_id: UUID,
    execute_svc=None,
    swap_repo=None,
) -> ServerSwapExecutionResult:
    """Exécute un swap déjà quoté côté serveur (worker). Idempotent vis-à-vis des états terminaux."""
    if swap_repo is None:
        from services.lifi.swap_repository import PersonWalletSwapRepository

        swap_repo = PersonWalletSwapRepository()
    if execute_svc is None:
        from services.lifi.lifi_execute_service import LifiExecuteService

        execute_svc = LifiExecuteService()

    swap = swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
    if swap is None:
        raise ValueError("swap_not_found")

    status = str(swap.status or "")

    # États terminaux / déjà soumis : on ne re-signe pas.
    if status == SwapSessionStatus.CONFIRMED.value:
        return ServerSwapExecutionResult("confirmed", swap_id, signed_server_side=False, settled=True)
    if status == SwapSessionStatus.SUBMITTED.value:
        finalize = finalize_virtual_wallet_swap(db, person_id=person_id, swap_id=swap_id)
        return ServerSwapExecutionResult(
            finalize.status, swap_id, signed_server_side=False,
            tx_hash=finalize.tx_hash, settled=finalize.settled,
        )
    if status in (SwapSessionStatus.FAILED.value, SwapSessionStatus.EXPIRED.value):
        return ServerSwapExecutionResult(_phase_from_status(status), swap_id, signed_server_side=False)
    # D1 — déjà en cours de diffusion : reprise idempotente, jamais une nouvelle signature.
    if status == SwapSessionStatus.BROADCASTING.value:
        return _recover_broadcasting_swap(
            db, person_id=person_id, swap_id=swap_id, swap=swap, swap_repo=swap_repo,
        )
    if status not in _SIGN_STATES:
        return ServerSwapExecutionResult(
            _phase_from_status(status), swap_id, signed_server_side=False,
            fallback_reason=f"unexpected_state:{status}",
        )

    def _fallback(reason: str) -> ServerSwapExecutionResult:
        logger.warning(
            "server_swap.fallback_awaiting_signature swap_id=%s reason=%s",
            str(swap_id),
            reason,
        )
        return ServerSwapExecutionResult(
            "awaiting_signature", swap_id, signed_server_side=False, fallback_reason=reason,
        )

    if not privy_delegated_signing_configured():
        return _fallback("delegated_signing_not_configured")

    # Pré-check délégation AVANT prepare_execute : source de vérité = API Privy (serveur),
    # jamais un flag client. Si non délégué, on retombe immédiatement en signature client
    # SANS verrouiller le wallet ni préparer la tx → zéro effet de bord, zéro régression.
    embedded_address = resolve_privy_embedded_evm_address(db, person_id=person_id)
    if not embedded_address:
        return _fallback("signing_wallet_unresolved")
    if not is_signing_wallet_delegated(db, person_id=person_id, wallet_address=embedded_address):
        return _fallback("wallet_not_delegated")

    prepared = execute_svc.prepare_execute(db, person_id=person_id, swap_id=swap_id)
    signing_address = (prepared.signing_wallet_address or "").strip() or embedded_address
    if prepared.signing_wallet_mode and prepared.signing_wallet_mode != "privy_embedded":
        return _fallback("non_privy_signing_mode")
    if prepared.transaction is None:
        return _fallback("transaction_unavailable")

    privy_wallet_id = resolve_privy_wallet_id(db, person_id=person_id, wallet_address=signing_address)
    if not privy_wallet_id:
        return _fallback("privy_wallet_id_unresolved")

    tx = prepared.transaction
    chain_id = int(tx.chain_id)

    try:
        approval = prepared.token_approval
        if (
            approval is not None
            and approval.required
            and approval.token_address
            and approval.spender_address
            and approval.amount_atomic
        ):
            rpc_url = resolve_chain_rpc_url(chain_id)
            required_atomic = int(str(approval.amount_atomic).strip())

            # 1) Allowance live : si déjà suffisante, on saute l'approval (évite une tx
            #    redondante + la contention de nonce entre tentatives quasi simultanées).
            allowance_sufficient = False
            if rpc_url:
                try:
                    current_allowance = read_erc20_allowance(
                        rpc_url,
                        token_address=approval.token_address,
                        owner_address=signing_address,
                        spender_address=approval.spender_address,
                    )
                    allowance_sufficient = current_allowance >= required_atomic
                except EvmRpcError:
                    allowance_sufficient = False

            if not allowance_sufficient:
                approve_send = send_delegated_sponsored_transaction(
                    privy_wallet_id=privy_wallet_id,
                    chain_id=chain_id,
                    to=approval.token_address,
                    data=build_approve_calldata(approval.spender_address, approval.amount_atomic),
                    value="0x0",
                    idempotency_key=approval_idempotency_key(swap_id),
                )
                execute_svc.record_token_approval(
                    db,
                    person_id=person_id,
                    swap_id=swap_id,
                    tx_hash=str(approve_send["hash"]),
                    signing_wallet_address=signing_address,
                )
                # 2) Parité flux client : attendre la confirmation on-chain de l'approval
                #    AVANT de diffuser le swap. Sans RPC dispo on conserve l'ancien
                #    comportement (best-effort) ; en prod (BASE_RPC_URL configuré) on attend.
                if rpc_url and not wait_for_approval_confirmed(rpc_url, str(approve_send["hash"])):
                    return _fallback("approval_unconfirmed")

        # D1 — état durable AVANT diffusion : on persiste de quoi rejouer à l'identique
        # (même corps + même clé d'idempotence) puis on commit. Si le worker crashe juste
        # après le broadcast, le retry passera par ``_recover_broadcasting_swap`` au lieu de
        # re-signer une nouvelle transaction.
        swap_idem = broadcast_idempotency_key(swap_id)
        swap_repo.mark_broadcasting(
            swap,
            idempotency_key=swap_idem,
            privy_wallet_id=privy_wallet_id,
            chain_id=chain_id,
            to=tx.to,
            data=tx.data,
            value=tx.value,
            gas_limit=tx.gas_limit,
            signing_wallet_address=signing_address,
        )
        db.commit()
        db.refresh(swap)

        swap_send = send_delegated_sponsored_transaction(
            privy_wallet_id=privy_wallet_id,
            chain_id=chain_id,
            to=tx.to,
            data=tx.data,
            value=tx.value,
            gas_limit=tx.gas_limit,
            idempotency_key=swap_idem,
        )
    except PrivyApiError as exc:
        logger.warning(
            "server_swap.sign_failed", extra={"swap_id": str(swap_id), "code": exc.code}
        )
        # Si BROADCASTING est déjà committé, on NE retombe PAS en awaiting_signature (qui
        # créerait un nouveau swap) : on reste en ``broadcasting`` pour reprise idempotente.
        if str(getattr(swap, "status", "")) == SwapSessionStatus.BROADCASTING.value:
            return ServerSwapExecutionResult(
                "broadcasting", swap_id, signed_server_side=False,
                fallback_reason=f"sign_failed:{exc.code}",
            )
        return _fallback(f"sign_failed:{exc.code}")

    tx_hash = str(swap_send["hash"])
    completed = complete_virtual_wallet_swap(
        db,
        person_id=person_id,
        swap_id=swap_id,
        tx_hash=tx_hash,
        signing_wallet_address=signing_address,
    )
    finalize = completed.finalize
    phase = finalize.status if finalize is not None else completed.phase
    return ServerSwapExecutionResult(
        phase,
        swap_id,
        signed_server_side=True,
        tx_hash=tx_hash,
        settled=bool(finalize.settled) if finalize is not None else False,
    )
