"""Virtual wallet swap — quote LI.FI → signature client → settlement (ADR 008)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.lifi_base_config import normalize_bundle_asset
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.wallets.enums import WalletType
from services.portfolio_engine.wallets.models import WalletContainer

from .execute_trade import execute_trade
from .submit import submit_signed_trade
from .types import TradeExecutionResult, TradeRequest, TradeReviewSnapshot

logger = logging.getLogger(__name__)

VirtualWalletSwapSide = Literal["buy", "sell"]
VirtualWalletSwapPhase = Literal[
    "awaiting_signature",
    "submitted",
    "confirmed",
    "failed",
    "expired",
]


class VirtualWalletSwapError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class VirtualWalletSwapRequest:
    """Entrée unique : wallets virtuels + montants + sens."""

    wallet_from_id: UUID
    wallet_to_id: UUID
    quantity_from: Decimal
    estimated_quantity_to: Decimal | None
    side: VirtualWalletSwapSide
    correlation_id: UUID
    client_id: UUID
    portfolio_id: UUID
    leg_id: str
    batch_id: str
    bundle_action: str
    leg_action: str
    chain: str = "base"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VirtualWalletSwapQuoteResult:
    swap_id: UUID
    from_asset: str
    to_asset: str
    amount_in: Decimal
    estimated_receive: Decimal | None
    status: str
    review_snapshot: TradeReviewSnapshot
    requires_client_signature: bool
    trade: TradeExecutionResult


@dataclass
class VirtualWalletSwapFinalizeResult:
    swap_id: UUID
    status: str
    tx_hash: str | None
    settled: bool
    settlement_scope: str | None = None
    error: str | None = None


@dataclass
class VirtualWalletSwapRunResult:
    """Résultat après quote (phase awaiting_signature) ou après submit+sync."""

    phase: VirtualWalletSwapPhase
    quote: VirtualWalletSwapQuoteResult | None = None
    finalize: VirtualWalletSwapFinalizeResult | None = None


def _load_wallet(db: Session, wallet_id: UUID) -> WalletContainer:
    wallet = db.query(WalletContainer).filter(WalletContainer.id == wallet_id).first()
    if wallet is None:
        raise VirtualWalletSwapError("wallet_not_found", f"Wallet introuvable: {wallet_id}")
    if str(wallet.status or "") != "active":
        raise VirtualWalletSwapError("wallet_inactive", f"Wallet inactif: {wallet_id}")
    return wallet


def _asset_symbol_for_wallet(db: Session, wallet: WalletContainer) -> str:
    if wallet.instrument_id is None:
        raise VirtualWalletSwapError(
            "wallet_missing_instrument",
            f"Wallet sans instrument: {wallet.id}",
        )
    instrument = (
        db.query(Instrument)
        .options(joinedload(Instrument.asset))
        .filter(Instrument.id == wallet.instrument_id)
        .first()
    )
    if instrument is None or instrument.asset is None:
        raise VirtualWalletSwapError(
            "instrument_not_found",
            f"Instrument introuvable: {wallet.instrument_id}",
        )
    asset = instrument.asset
    if not isinstance(asset, Asset):
        raise VirtualWalletSwapError("asset_not_found", f"Actif introuvable pour {wallet.instrument_id}")
    return normalize_bundle_asset(asset.symbol)


def _validate_side_wallets(
    side: VirtualWalletSwapSide,
    wallet_from: WalletContainer,
    wallet_to: WalletContainer,
    *,
    portfolio_id: UUID,
) -> None:
    if wallet_from.portfolio_id != portfolio_id or wallet_to.portfolio_id != portfolio_id:
        raise VirtualWalletSwapError(
            "portfolio_wallet_mismatch",
            "Les wallets doivent appartenir au même portefeuille.",
        )
    cash = WalletType.CASH_WALLET.value
    spot = WalletType.SPOT_WALLET.value
    if side == "buy":
        if wallet_from.wallet_type != cash or wallet_to.wallet_type != spot:
            raise VirtualWalletSwapError(
                "side_wallet_mismatch",
                "Achat : wallet_from=cash, wallet_to=spot.",
            )
    elif side == "sell":
        if wallet_from.wallet_type != spot or wallet_to.wallet_type != cash:
            raise VirtualWalletSwapError(
                "side_wallet_mismatch",
                "Vente : wallet_from=spot, wallet_to=cash.",
            )


def build_trade_request_from_wallets(
    db: Session,
    request: VirtualWalletSwapRequest,
) -> TradeRequest:
    wallet_from = _load_wallet(db, request.wallet_from_id)
    wallet_to = _load_wallet(db, request.wallet_to_id)
    _validate_side_wallets(
        request.side,
        wallet_from,
        wallet_to,
        portfolio_id=request.portfolio_id,
    )
    if wallet_from.instrument_id is None or wallet_to.instrument_id is None:
        raise VirtualWalletSwapError("wallet_missing_instrument", "Instrument manquant sur un wallet.")

    from_asset = _asset_symbol_for_wallet(db, wallet_from)
    to_asset = _asset_symbol_for_wallet(db, wallet_to)

    return TradeRequest(
        wallet_from_id=request.wallet_from_id,
        wallet_to_id=request.wallet_to_id,
        instrument_from_id=wallet_from.instrument_id,
        instrument_to_id=wallet_to.instrument_id,
        quantity_from=request.quantity_from,
        correlation_id=request.correlation_id,
        client_id=request.client_id,
        portfolio_id=request.portfolio_id,
        from_asset=from_asset,
        to_asset=to_asset,
        leg_id=request.leg_id,
        batch_id=request.batch_id,
        bundle_action=request.bundle_action,
        leg_action=request.leg_action,
        chain=request.chain,
        metadata={
            **request.metadata,
            "swap_side": request.side,
            "estimated_quantity_to": (
                str(request.estimated_quantity_to)
                if request.estimated_quantity_to is not None
                else None
            ),
        },
    )


def _review_snapshot_from_trade(
    trade: TradeExecutionResult,
    request: VirtualWalletSwapRequest,
) -> TradeReviewSnapshot:
    amount_in = str(trade.amount_from)
    estimated = (
        str(trade.amount_to)
        if trade.amount_to is not None
        else (
            str(request.estimated_quantity_to)
            if request.estimated_quantity_to is not None
            else "0"
        )
    )
    return TradeReviewSnapshot(
        review_amount_in=amount_in,
        review_estimated_receive=estimated,
    )


def quote_virtual_wallet_swap(
    db: Session,
    request: VirtualWalletSwapRequest,
    actor: ActorContext,
) -> VirtualWalletSwapQuoteResult:
    """Quote LI.FI + contexte wallets — arrêt avant signature Privy."""
    if request.quantity_from <= 0:
        raise VirtualWalletSwapError("invalid_quantity", "quantity_from doit être > 0.")

    trade_req = build_trade_request_from_wallets(db, request)
    trade = execute_trade(db, trade_req, actor)
    snapshot = _review_snapshot_from_trade(trade, request)

    return VirtualWalletSwapQuoteResult(
        swap_id=trade.swap_id,
        from_asset=trade.from_asset,
        to_asset=trade.to_asset,
        amount_in=trade.amount_from,
        estimated_receive=trade.amount_to,
        status=trade.status,
        review_snapshot=snapshot,
        requires_client_signature=trade.requires_client_signature,
        trade=trade,
    )


def finalize_virtual_wallet_swap(
    db: Session,
    *,
    person_id: UUID,
    swap_id: UUID,
) -> VirtualWalletSwapFinalizeResult:
    """Rafraîchit le statut LI.FI une fois et règle la comptabilité si CONFIRMED."""
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.lifi_execute_service import LifiExecuteService
    from services.lifi.swap_repository import PersonWalletSwapRepository
    from services.portfolio_engine.bundle_execution.pe_settlement import swap_confirmed
    from services.settlement.swap_router import settle_confirmed_swap

    repo = PersonWalletSwapRepository()
    swap = repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
    if swap is None:
        raise VirtualWalletSwapError("swap_not_found", "Swap introuvable.")

    execute = LifiExecuteService()
    if swap.status == SwapSessionStatus.SUBMITTED.value:
        execute.refresh_lifi_status(db, swap)
        db.refresh(swap)
    else:
        execute.get_status(db, person_id=person_id, swap_id=swap_id)
        db.refresh(swap)

    settled = False
    scope: str | None = None
    if swap_confirmed(swap):
        result = settle_confirmed_swap(db, swap)
        settled = result.settled
        scope = result.scope
        db.commit()
        db.refresh(swap)

    phase: VirtualWalletSwapPhase
    if swap_confirmed(swap):
        phase = "confirmed"
    elif swap.status in (
        SwapSessionStatus.FAILED.value,
        SwapSessionStatus.EXPIRED.value,
    ):
        phase = "failed" if swap.status == SwapSessionStatus.FAILED.value else "expired"
    elif swap.status == SwapSessionStatus.SUBMITTED.value:
        phase = "submitted"
    else:
        phase = "awaiting_signature"

    return VirtualWalletSwapFinalizeResult(
        swap_id=swap_id,
        status=phase,
        tx_hash=swap.tx_hash,
        settled=settled,
        settlement_scope=scope,
        error=str(swap.error_message or "") or None,
    )


def complete_virtual_wallet_swap(
    db: Session,
    *,
    person_id: UUID,
    swap_id: UUID,
    tx_hash: str,
    signing_wallet_address: str | None = None,
) -> VirtualWalletSwapRunResult:
    """Après signature Privy : submit tx + sync settlement."""
    submit_signed_trade(
        db,
        person_id=person_id,
        swap_id=swap_id,
        tx_hash=tx_hash,
        signing_wallet_address=signing_wallet_address,
    )
    db.commit()
    finalize = finalize_virtual_wallet_swap(db, person_id=person_id, swap_id=swap_id)
    return VirtualWalletSwapRunResult(phase=finalize.status, finalize=finalize)


def run_virtual_wallet_swap_server_side(
    db: Session,
    request: VirtualWalletSwapRequest,
    actor: ActorContext,
    *,
    person_id: UUID,
) -> VirtualWalletSwapRunResult:
    """Action atomique réutilisable — chaîne complète d'un swap **100 % serveur**.

    ``f(wallet_from, wallet_to, quantity_from)`` → ``confirmed + settled`` :

      1. **Quote** LI.FI (exact-in : on fige ``quantity_from``, ``to`` estimé puis réconcilié au réel)
      2. **Signature** Privy déléguée côté serveur (Session Signers, self-custody)
      3. **Submit** via le submit unifié (swap simple **ou** leg bundle)
      4. **Settlement** : ledger wallets from/to (débit/crédit du montant réel reçu),
         atoms PE, PRU/PnL, valorisation figée native/USDC/EUR (``eurusd_rate_at_execution``)

    Le routage compta (self-trading vs bundle) est automatique via ``settle_confirmed_swap``.
    Réutilisable tel quel pour le chaînage d'un rééquilibrage (leg après leg) ou pour
    d'autres produits futurs.

    Garde-fou : si la signature déléguée est indisponible (wallet non délégué, Privy non
    configuré, mode non-embedded…), retombe sur ``awaiting_signature`` — le swap reste quoté
    et signable côté client (zéro régression).
    """
    from services.trade_core.server_execution import execute_prepared_swap_server_side

    if request.quantity_from <= 0:
        raise VirtualWalletSwapError("invalid_quantity", "quantity_from doit être > 0.")

    quote = quote_virtual_wallet_swap(db, request, actor)
    exec_result = execute_prepared_swap_server_side(
        db,
        person_id=person_id,
        swap_id=quote.swap_id,
    )
    finalize = VirtualWalletSwapFinalizeResult(
        swap_id=quote.swap_id,
        status=exec_result.phase,
        tx_hash=exec_result.tx_hash,
        settled=exec_result.settled,
        error=exec_result.fallback_reason if not exec_result.signed_server_side else None,
    )
    return VirtualWalletSwapRunResult(
        phase=exec_result.phase,
        quote=quote,
        finalize=finalize,
    )


def run_virtual_wallet_swap(
    db: Session,
    request: VirtualWalletSwapRequest,
    actor: ActorContext,
    *,
    person_id: UUID | None = None,
    tx_hash: str | None = None,
    signing_wallet_address: str | None = None,
) -> VirtualWalletSwapRunResult:
    """
    Point d'entrée unique côté serveur.

    Sans ``tx_hash`` : quote LI.FI → ``awaiting_signature``.
    Avec ``tx_hash`` : submit + sync comptabilité (post-signature client).
    """
    quote = quote_virtual_wallet_swap(db, request, actor)
    if not tx_hash:
        return VirtualWalletSwapRunResult(
            phase="awaiting_signature",
            quote=quote,
        )
    if person_id is None:
        raise VirtualWalletSwapError("person_id_required", "person_id requis après signature.")
    completed = complete_virtual_wallet_swap(
        db,
        person_id=person_id,
        swap_id=quote.swap_id,
        tx_hash=tx_hash,
        signing_wallet_address=signing_wallet_address,
    )
    completed.quote = quote
    return completed
