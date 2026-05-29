"""Service layer for Exchange Engine v1 — EUR ↔ Crypto buy/sell + daily net settlement."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import ROUND_DOWN, Decimal
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote
from services.market_data.fx import (
    EURUSDT_PROVIDER_SYMBOL,
    FxQuoteStaleError,
    FxQuoteUnavailableError,
    get_eurusdt_rate,
    usdt_to_eur,
)
from services.market_data.market_summary_repo import refresh_binance_quotes_for_provider_symbols
from services.custody.enums import (
    CustodyAccountType,
    TransactionDirection,
    TransactionKind,
    TransactionStatus,
    TransactionType,
)
from services.custody.repository import (
    CustodyAccountRepository,
    CustodyBalanceRepository,
    CustodyTransactionRepository,
)
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.ledger_entries.service import LedgerEntryService

from .assets import (
    ASSET_PRECISION,
    ASSET_PROVIDER_SYMBOL_MAP,
    SUPPORTED_ASSETS,
    get_settlement_wallet_balance,
)
from .custody_repository import (
    ACCOUNT_TYPE_SETTLEMENT_WALLET,
    CryptoCustodyAccountRepository,
    CryptoCustodyBalanceRepository,
)
from .repository import (
    CryptoPositionRepository,
    CryptoSettlementDeltaRepository,
    ExchangeFeeConfigRepository,
    ExchangeOrderRepository,
)
from .schemas import ExchangeBuyRequest, ExchangeSellRequest, SwapPreviewRequest, SwapRequest

from services.portfolio_engine.direct_overlay import (
    ensure_direct_portfolio,
    sync_direct_atom,
    _resolve_or_create_instrument as _resolve_pe_instrument,
)


def _get_settlement_wallet_balance_for_settlement(db: Session, asset: str) -> Decimal:
    """Settlement wallet balance: DB (crypto_custody_balances.actual_balance) first, then in-memory fallback."""
    account = CryptoCustodyAccountRepository.get_by_asset_and_type(
        db, asset, ACCOUNT_TYPE_SETTLEMENT_WALLET
    )
    if account:
        bal = CryptoCustodyBalanceRepository.get_balance(db, account.id)
        if bal is not None:
            return Decimal(str(bal.actual_balance))
    return get_settlement_wallet_balance(asset)

logger = logging.getLogger(__name__)


class ExchangeError(Exception):
    pass


class UnsupportedAssetError(ExchangeError):
    pass


class PriceUnavailableError(ExchangeError):
    pass


class InsufficientFundsError(ExchangeError):
    pass


class DuplicateOrderError(ExchangeError):
    pass


class InsufficientCryptoBalanceError(ExchangeError):
    pass


class FxUnavailableError(ExchangeError):
    """Raised when the EURUSDT FX quote is missing or stale (strict mode)."""
    pass


class MarketQuoteStaleError(ExchangeError):
    """Raised when the market quote is older than MAX_QUOTE_AGE_SECONDS."""
    pass


MAX_QUOTE_AGE_SECONDS = 60
MAX_QUOTE_AGE_SECONDS_STABLECOIN = 600
STABLECOIN_ASSETS = frozenset({"USDC", "USDT", "EURC", "DAI", "BUSD"})
USD_PEGGED_STABLECOINS = frozenset({"USDC", "USDT", "DAI", "BUSD"})
EUR_PEGGED_STABLECOINS = frozenset({"EURC"})


class AccountNotFoundError(ExchangeError):
    pass


def _ingest_order_cost_basis(db: Session, order) -> None:
    try:
        from services.cost_basis.ingest_exchange import ingest_exchange_order

        ingest_exchange_order(db, order)
    except Exception:
        logger.exception("cost_basis.exchange_ingest_failed order_id=%s", getattr(order, "id", None))


class ExchangeService:

    def __init__(self) -> None:
        self._account_repo = CustodyAccountRepository
        self._balance_repo = CustodyBalanceRepository
        self._tx_repo = CustodyTransactionRepository
        self._order_repo = ExchangeOrderRepository
        self._position_repo = CryptoPositionRepository
        self._delta_repo = CryptoSettlementDeltaRepository
        self._fee_repo = ExchangeFeeConfigRepository
        self._ledger_entry_svc = LedgerEntryService()

    def preview_buy(self, db: Session, asset: str, fiat_amount: Decimal, currency: str = "EUR") -> dict:
        """Compute a BUY preview using the exact same pricing logic as the real buy.

        Returns estimated price, gross/net crypto, fee, and quote freshness.
        No side-effects — read-only.
        """
        asset = asset.upper()
        if asset not in SUPPORTED_ASSETS:
            raise UnsupportedAssetError(f"unsupported_asset: {asset}")

        price = self._resolve_price(db, asset, override_price=None, side="buy")

        decimals = ASSET_PRECISION.get(asset, 8)
        quant = Decimal(10) ** -decimals

        volume_raw = (fiat_amount / price).quantize(quant, rounding=ROUND_DOWN)
        fee_bps = self._fee_repo.get_active_fee_bps(db, asset)
        fee_crypto = (volume_raw * fee_bps / Decimal("10000")).quantize(quant, rounding=ROUND_DOWN)
        client_crypto = volume_raw - fee_crypto

        return {
            "asset": asset,
            "amount_fiat": float(fiat_amount),
            "estimated_price": float(price),
            "estimated_crypto_gross": float(volume_raw),
            "fee_amount": float(fee_crypto),
            "fee_asset": asset,
            "fee_bps": fee_bps,
            "estimated_crypto_net": float(client_crypto),
            "currency": currency.upper(),
            "is_fresh": True,
        }

    def preview_sell(
        self, db: Session, asset: str, amount_crypto: Decimal, currency: str = "EUR"
    ) -> dict:
        """Compute a SELL preview using the exact same pricing logic as the real sell.

        Returns estimated price, gross/net EUR, fee (in EUR), and quote freshness.
        No side-effects — read-only.
        """
        asset = asset.upper()
        if asset not in SUPPORTED_ASSETS:
            raise UnsupportedAssetError(f"unsupported_asset: {asset}")

        price = self._resolve_price(db, asset, override_price=None, side="sell")

        eur_quant = Decimal("0.01")
        gross_eur = (amount_crypto * price).quantize(eur_quant, rounding=ROUND_DOWN)
        fee_bps = self._fee_repo.get_active_fee_bps(db, asset)
        fee_eur = (gross_eur * fee_bps / Decimal("10000")).quantize(
            eur_quant, rounding=ROUND_DOWN
        )
        net_eur = gross_eur - fee_eur

        return {
            "asset": asset,
            "amount_crypto": float(amount_crypto),
            "estimated_price": float(price),
            "estimated_fiat_gross": float(gross_eur),
            "fee_amount": float(fee_eur),
            "fee_asset": currency.upper(),
            "fee_bps": fee_bps,
            "estimated_fiat_net": float(net_eur),
            "currency": currency.upper(),
            "is_fresh": True,
        }

    def buy(
        self,
        db: Session,
        payload: ExchangeBuyRequest,
        actor: ActorContext,
    ) -> dict:
        """Execute a EUR → Crypto buy order.

        Flow:
        0. Eligibility gate
        1. Idempotency check
        2. Validate asset
        3. Resolve price
        4. Compute crypto amount
        5. Validate client EUR balance
        6. Debit client EUR, credit settlement EUR
        7. Create exchange_order
        8. Credit crypto_position
        9. Increment crypto_settlement_delta
        10. Ledger entries + audit
        """

        # --- 0. Eligibility gate ---
        from services.compliance.eligibility_service import EligibilityService
        EligibilityService.require_eligible_by_client_id(db, payload.client_id)

        # --- 1. Idempotency ---
        existing = self._order_repo.find_by_reference(db, payload.external_reference)
        if existing is not None:
            return {
                "status": "ignored",
                "reason": "duplicate_external_reference",
                "order_id": existing.id,
            }

        # --- 2. Validate asset ---
        asset = payload.asset.upper()
        if asset not in SUPPORTED_ASSETS:
            raise UnsupportedAssetError(f"unsupported_asset: {asset}")

        # --- 3. Resolve price (BUY → ask) ---
        price = self._resolve_price(db, asset, payload.price, side="buy")

        # --- 4. Compute crypto amount + fee ---
        decimals = ASSET_PRECISION.get(asset, 8)
        quant = Decimal(10) ** -decimals

        volume_raw = (payload.fiat_amount / price).quantize(quant, rounding=ROUND_DOWN)
        if volume_raw <= 0:
            raise ExchangeError("computed_crypto_amount_is_zero")

        fee_bps = self._fee_repo.get_active_fee_bps(db, asset)
        fee_crypto = (volume_raw * fee_bps / Decimal("10000")).quantize(quant, rounding=ROUND_DOWN)
        client_crypto = volume_raw - fee_crypto

        # --- 5. Validate client EUR accounts ---
        client_account = self._account_repo.find_client_account(
            db, payload.client_id, payload.currency
        )
        if client_account is None:
            raise AccountNotFoundError("client_eur_account_not_found")

        settlement = self._account_repo.find_settlement_account(db, payload.currency)
        if settlement is None:
            raise AccountNotFoundError("settlement_eur_account_not_found")

        # --- 6. Balance check with row-level lock ---
        client_balance = self._balance_repo.get_for_update(db, client_account.id)
        if client_balance is None:
            raise AccountNotFoundError("client_balance_not_found")

        settlement_balance = self._balance_repo.get_for_update(db, settlement.id)
        if settlement_balance is None:
            raise AccountNotFoundError("settlement_balance_not_found")

        current_client = Decimal(str(client_balance.available_balance))
        if current_client < payload.fiat_amount:
            raise InsufficientFundsError(
                f"insufficient_funds: available={current_client}, requested={payload.fiat_amount}"
            )

        # --- 7. Create exchange order (processing) ---
        order = self._order_repo.create(
            db,
            data={
                "client_id": payload.client_id,
                "side": "buy",
                "asset": asset,
                "amount_crypto": client_crypto,
                "amount_fiat": payload.fiat_amount,
                "price": price,
                "currency": payload.currency,
                "from_asset": payload.currency,
                "to_asset": asset,
                "amount_from": payload.fiat_amount,
                "amount_to": client_crypto,
                "fee_amount": fee_crypto,
                "fee_asset": asset,
                "status": "processing",
                "external_reference": payload.external_reference,
                "metadata_": {
                    "client_account_id": str(client_account.id),
                    "settlement_account_id": str(settlement.id),
                    "volume_raw": str(volume_raw),
                    "fee_bps": fee_bps,
                },
            },
        )

        try:
            # --- 8. Custody transaction (EUR debit from client) ---
            custody_tx = self._tx_repo.create(
                db,
                data={
                    "account_id": client_account.id,
                    "provider_id": None,
                    "transaction_type": TransactionType.WITHDRAWAL.value,
                    "transaction_kind": TransactionKind.EXCHANGE_BUY.value,
                    "direction": TransactionDirection.DEBIT.value,
                    "amount": payload.fiat_amount,
                    "currency": payload.currency,
                    "status": TransactionStatus.COMPLETED.value,
                    "external_reference": f"exchange-{order.id}",
                    "metadata_": {
                        "exchange_order_id": str(order.id),
                        "asset": asset,
                        "volume_raw": str(volume_raw),
                        "client_crypto": str(client_crypto),
                        "fee_crypto": str(fee_crypto),
                        "fee_bps": fee_bps,
                        "price": str(price),
                        "narrative": f"Buy {client_crypto} {asset} @ {price} {payload.currency} (fee {fee_crypto} {asset})",
                    },
                },
            )

            # --- 9. Ledger double entry (EUR: client debit → settlement credit) ---
            if client_account.ledger_account_id and settlement.ledger_account_id:
                self._ledger_entry_svc.post_double_entry(
                    db,
                    debit_account_id=client_account.ledger_account_id,
                    credit_account_id=settlement.ledger_account_id,
                    amount=payload.fiat_amount,
                    currency=payload.currency,
                    reference_type="exchange_order",
                    reference_id=order.id,
                    effective_at=datetime.now(timezone.utc),
                    description=f"Exchange buy {asset} — {payload.fiat_amount} {payload.currency}",
                    metadata={
                        "external_reference": payload.external_reference,
                        "client_id": str(payload.client_id),
                        "asset": asset,
                        "volume_raw": str(volume_raw),
                        "client_crypto": str(client_crypto),
                        "fee_crypto": str(fee_crypto),
                    },
                )

            # --- 10. Update EUR balances ---
            self._balance_repo.update_balance(db, client_balance, delta=-payload.fiat_amount)
            self._balance_repo.update_balance(db, settlement_balance, delta=payload.fiat_amount)

            # --- 11. Credit crypto position (post-fee amount) ---
            position = self._position_repo.get_or_create_for_update(db, payload.client_id, asset)
            self._position_repo.credit(db, position, client_crypto)

            # --- 11b. Sync direct portfolio atom (PE overlay) ---
            is_bundle_order = (
                payload.external_reference
                and payload.external_reference.startswith("bundle-")
            )
            if not is_bundle_order:
                try:
                    direct_pf = ensure_direct_portfolio(db, payload.client_id)
                    pe_instr = _resolve_pe_instrument(db, asset)
                    sync_direct_atom(db, direct_pf.id, pe_instr.id, client_crypto, payload.fiat_amount)
                    meta = dict(order.metadata_ or {})
                    meta["portfolio_scope"] = "direct"
                    meta["portfolio_id"] = str(direct_pf.id)
                    order.metadata_ = meta
                    db.flush()
                except Exception as exc:
                    logger.warning("Direct atom sync failed on BUY: %s", exc)

            # --- 12. Settlement delta uses RAW volume (fees belong to platform) ---
            today = date.today()
            delta_row = self._delta_repo.get_or_create(db, asset, today)
            self._delta_repo.increment(db, delta_row, volume_raw)

            # --- 13. Finalize order ---
            self._order_repo.update_status(db, order, new_status="completed")
            _ingest_order_cost_basis(db, order)

        except Exception as exc:
            logger.error("Exchange buy failed: %s", exc, exc_info=True)
            self._order_repo.update_status(
                db, order, new_status="failed", failure_reason=str(exc)
            )
            raise

        # --- 14. Audit ---
        AuditService.log_success(
            db,
            entity_type="exchange_order",
            entity_id=str(order.id),
            action="exchange_buy_completed",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "order_id": str(order.id),
                "client_id": str(payload.client_id),
                "asset": asset,
                "volume_raw": str(volume_raw),
                "client_crypto": str(client_crypto),
                "fee_crypto": str(fee_crypto),
                "fee_bps": fee_bps,
                "amount_fiat": str(payload.fiat_amount),
                "price": str(price),
                "currency": payload.currency,
                "client_eur_balance_after": str(client_balance.available_balance),
                "crypto_position_after": str(position.balance),
            },
        )

        return {
            "status": "completed",
            "order_id": order.id,
            "asset": asset,
            "from_asset": payload.currency,
            "to_asset": asset,
            "amount_from": payload.fiat_amount,
            "amount_to": client_crypto,
            "amount_crypto": client_crypto,
            "amount_fiat": payload.fiat_amount,
            "volume_raw": volume_raw,
            "fee_amount": fee_crypto,
            "fee_asset": asset,
            "fee_bps": fee_bps,
            "price": price,
            "currency": payload.currency,
            "client_eur_balance_after": client_balance.available_balance,
            "crypto_position_after": position.balance,
        }

    def sell(
        self,
        db: Session,
        payload: ExchangeSellRequest,
        actor: ActorContext,
    ) -> dict:
        """Execute a Crypto → EUR sell order.

        Flow (mirrors BUY symmetrically):
        A. Idempotency check
        B. Validate asset + precision
        C. Resolve price
        D. Compute EUR amounts (gross, fee, net)
        E. Lock crypto position + validate balance
        F. Lock EUR accounts + validate settlement balance
        G. Create exchange order
        H. Atomic execution:
           - Custody transaction (EUR credit to client)
           - Debit crypto position (virtual entitlement)
           - Credit settlement EUR + debit client EUR transfer (net_eur)
           - Ledger double entry (settlement debit → client credit)
           - Settlement delta (-amount_crypto)
           - Finalize order
        I. Audit
        """

        # --- 0. Eligibility gate ---
        from services.compliance.eligibility_service import EligibilityService
        EligibilityService.require_eligible_by_client_id(db, payload.client_id)

        # --- A. Idempotency ---
        existing = self._order_repo.find_by_reference(db, payload.external_reference)
        if existing is not None:
            return {
                "status": "ignored",
                "reason": "duplicate_external_reference",
                "order_id": existing.id,
            }

        # --- B. Validate asset + precision ---
        asset = payload.asset.upper()
        if asset not in SUPPORTED_ASSETS:
            raise UnsupportedAssetError(f"unsupported_asset: {asset}")

        decimals = ASSET_PRECISION.get(asset, 8)
        quant = Decimal(10) ** -decimals
        normalized = payload.amount_crypto.quantize(quant, rounding=ROUND_DOWN)
        if normalized != payload.amount_crypto:
            raise ExchangeError(
                f"invalid_amount_precision: {asset} supports {decimals} decimals"
            )
        if payload.amount_crypto <= 0:
            raise ExchangeError("invalid_amount: amount_crypto must be > 0")

        # --- C. Resolve price (SELL → bid) ---
        price = self._resolve_price(db, asset, payload.price, side="sell")

        # --- D. Compute EUR amounts ---
        eur_quant = Decimal("0.01")
        gross_eur = (payload.amount_crypto * price).quantize(eur_quant, rounding=ROUND_DOWN)
        if gross_eur <= 0:
            raise ExchangeError("computed_eur_amount_is_zero")

        fee_bps = self._fee_repo.get_active_fee_bps(db, asset)
        fee_eur = (gross_eur * fee_bps / Decimal("10000")).quantize(eur_quant, rounding=ROUND_DOWN)
        net_eur = gross_eur - fee_eur

        # --- E. Lock crypto position + validate ---
        position = self._position_repo.get_or_create_for_update(db, payload.client_id, asset)
        current_crypto = Decimal(str(position.balance))
        if current_crypto < payload.amount_crypto:
            raise InsufficientCryptoBalanceError(
                f"insufficient_crypto_balance: available={current_crypto}, requested={payload.amount_crypto}"
            )

        # --- F. Lock EUR accounts ---
        client_account = self._account_repo.find_client_account(
            db, payload.client_id, payload.currency
        )
        if client_account is None:
            raise AccountNotFoundError("client_eur_account_not_found")

        settlement = self._account_repo.find_settlement_account(db, payload.currency)
        if settlement is None:
            raise AccountNotFoundError("settlement_eur_account_not_found")

        client_balance = self._balance_repo.get_for_update(db, client_account.id)
        if client_balance is None:
            raise AccountNotFoundError("client_balance_not_found")

        settlement_balance = self._balance_repo.get_for_update(db, settlement.id)
        if settlement_balance is None:
            raise AccountNotFoundError("settlement_balance_not_found")

        current_settlement_eur = Decimal(str(settlement_balance.available_balance))
        if current_settlement_eur < net_eur:
            raise InsufficientFundsError(
                f"insufficient_settlement_eur: available={current_settlement_eur}, requested={net_eur}"
            )

        # --- G1. Compute WAC cost basis consumed and realized PnL (PnL hardening) ---
        cost_basis_total, position_qty = self._order_repo.get_wac_state_before_sell(
            db, payload.client_id, asset
        )
        cost_basis_consumed: Optional[Decimal] = None
        realized_pnl_generated: Optional[Decimal] = None
        if position_qty > 0:
            avg_cost = cost_basis_total / position_qty
            cost_basis_consumed = (payload.amount_crypto * avg_cost).quantize(
                eur_quant, rounding=ROUND_DOWN
            )
            realized_pnl_generated = (net_eur - cost_basis_consumed).quantize(
                eur_quant, rounding=ROUND_DOWN
            )

        # --- G2. Create exchange order (processing) ---
        order = self._order_repo.create(
            db,
            data={
                "client_id": payload.client_id,
                "side": "sell",
                "asset": asset,
                "amount_crypto": payload.amount_crypto,
                "amount_fiat": gross_eur,
                "price": price,
                "currency": payload.currency,
                "from_asset": asset,
                "to_asset": payload.currency,
                "amount_from": payload.amount_crypto,
                "amount_to": net_eur,
                "fee_amount": fee_eur,
                "fee_asset": payload.currency,
                "status": "processing",
                "external_reference": payload.external_reference,
                "cost_basis_consumed": cost_basis_consumed,
                "realized_pnl_generated": realized_pnl_generated,
                "metadata_": {
                    "client_account_id": str(client_account.id),
                    "settlement_account_id": str(settlement.id),
                    "gross_eur": str(gross_eur),
                    "fee_bps": fee_bps,
                },
            },
        )

        try:
            # --- H1. Custody transaction (EUR credit to client) ---
            custody_tx = self._tx_repo.create(
                db,
                data={
                    "account_id": client_account.id,
                    "provider_id": None,
                    "transaction_type": TransactionType.DEPOSIT.value,
                    "transaction_kind": TransactionKind.EXCHANGE_SELL.value,
                    "direction": TransactionDirection.CREDIT.value,
                    "amount": net_eur,
                    "currency": payload.currency,
                    "status": TransactionStatus.COMPLETED.value,
                    "external_reference": f"exchange-sell-{order.id}",
                    "metadata_": {
                        "exchange_order_id": str(order.id),
                        "asset": asset,
                        "amount_crypto": str(payload.amount_crypto),
                        "gross_eur": str(gross_eur),
                        "fee_eur": str(fee_eur),
                        "net_eur": str(net_eur),
                        "fee_bps": fee_bps,
                        "price": str(price),
                        "narrative": f"Sell {payload.amount_crypto} {asset} @ {price} EUR → {net_eur} EUR (fee {fee_eur} EUR)",
                    },
                },
            )

            # --- H2. Ledger double entry (EUR: settlement debit → client credit) ---
            if settlement.ledger_account_id and client_account.ledger_account_id:
                self._ledger_entry_svc.post_double_entry(
                    db,
                    debit_account_id=settlement.ledger_account_id,
                    credit_account_id=client_account.ledger_account_id,
                    amount=net_eur,
                    currency=payload.currency,
                    reference_type="exchange_order",
                    reference_id=order.id,
                    effective_at=datetime.now(timezone.utc),
                    description=f"Exchange sell {asset} — {net_eur} {payload.currency}",
                    metadata={
                        "external_reference": payload.external_reference,
                        "client_id": str(payload.client_id),
                        "asset": asset,
                        "amount_crypto": str(payload.amount_crypto),
                        "gross_eur": str(gross_eur),
                        "fee_eur": str(fee_eur),
                    },
                )

            # --- H3. Update EUR balances (settlement -gross, client +net; fee stays as profit) ---
            self._balance_repo.update_balance(db, settlement_balance, delta=-net_eur)
            self._balance_repo.update_balance(db, client_balance, delta=net_eur)

            # --- H4. Debit crypto position (virtual entitlement only) ---
            self._position_repo.debit(db, position, payload.amount_crypto)

            # --- H4b. Sync direct portfolio atom (PE overlay) ---
            is_bundle_order = (
                payload.external_reference
                and payload.external_reference.startswith("bundle-")
            )
            if not is_bundle_order:
                try:
                    direct_pf = ensure_direct_portfolio(db, payload.client_id)
                    pe_instr = _resolve_pe_instrument(db, asset)
                    cost_consumed = cost_basis_consumed if cost_basis_consumed is not None else Decimal("0")
                    sync_direct_atom(db, direct_pf.id, pe_instr.id, -payload.amount_crypto, -cost_consumed)
                    meta = dict(order.metadata_ or {})
                    meta["portfolio_scope"] = "direct"
                    meta["portfolio_id"] = str(direct_pf.id)
                    order.metadata_ = meta
                    db.flush()
                except Exception as exc:
                    logger.warning("Direct atom sync failed on SELL: %s", exc)

            # --- H5. Settlement delta (negative = crypto must leave pool) ---
            today = date.today()
            delta_row = self._delta_repo.get_or_create(db, asset, today)
            self._delta_repo.increment(db, delta_row, -payload.amount_crypto)

            # --- H6. Finalize order ---
            self._order_repo.update_status(db, order, new_status="completed")
            _ingest_order_cost_basis(db, order)

        except Exception as exc:
            logger.error("Exchange sell failed: %s", exc, exc_info=True)
            self._order_repo.update_status(
                db, order, new_status="failed", failure_reason=str(exc)
            )
            raise

        # --- I. Audit ---
        AuditService.log_success(
            db,
            entity_type="exchange_order",
            entity_id=str(order.id),
            action="exchange_sell_completed",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "order_id": str(order.id),
                "client_id": str(payload.client_id),
                "asset": asset,
                "amount_crypto": str(payload.amount_crypto),
                "gross_eur": str(gross_eur),
                "fee_eur": str(fee_eur),
                "net_eur": str(net_eur),
                "fee_bps": fee_bps,
                "price": str(price),
                "currency": payload.currency,
                "client_eur_balance_after": str(client_balance.available_balance),
                "crypto_position_after": str(position.balance),
            },
        )

        return {
            "status": "completed",
            "order_id": order.id,
            "asset": asset,
            "from_asset": asset,
            "to_asset": payload.currency,
            "amount_from": payload.amount_crypto,
            "amount_to": net_eur,
            "amount_crypto": payload.amount_crypto,
            "price_eur": price,
            "gross_eur": gross_eur,
            "fee_eur": fee_eur,
            "fee_bps": fee_bps,
            "net_eur": net_eur,
            "currency": payload.currency,
            "client_eur_balance_after": client_balance.available_balance,
            "crypto_position_after": position.balance,
            "cost_basis_consumed": str(cost_basis_consumed) if cost_basis_consumed is not None else None,
            "realized_pnl_generated": str(realized_pnl_generated) if realized_pnl_generated is not None else None,
        }

    # ------------------------------------------------------------------
    # Swap crypto ↔ crypto
    # ------------------------------------------------------------------

    def preview_swap(
        self, db: Session, payload: SwapPreviewRequest, currency: str = "EUR"
    ) -> dict:
        """Compute a swap preview: SELL leg (bid) + BUY leg (ask) with single reference value.

        Returns gross, fee, net (reference), estimated target quantity, and prices.
        """
        from_asset = payload.from_asset.upper()
        to_asset = payload.to_asset.upper()
        if from_asset not in SUPPORTED_ASSETS or to_asset not in SUPPORTED_ASSETS:
            raise UnsupportedAssetError(f"unsupported_asset: {from_asset} or {to_asset}")
        if from_asset == to_asset:
            raise ExchangeError("swap_same_asset: from_asset must differ from to_asset")

        price_from = self._resolve_price(db, from_asset, override_price=None, side="sell")
        price_to = self._resolve_price(db, to_asset, override_price=None, side="buy")

        eur_quant = Decimal("0.01")
        gross = (payload.amount_from * price_from).quantize(eur_quant, rounding=ROUND_DOWN)
        fee_bps = self._fee_repo.get_active_fee_bps(db, from_asset)
        fee_eur = (gross * fee_bps / Decimal("10000")).quantize(eur_quant, rounding=ROUND_DOWN)
        net = gross - fee_eur
        if net <= 0:
            raise ExchangeError("computed_net_value_is_zero")

        decimals_to = ASSET_PRECISION.get(to_asset, 8)
        quant_to = Decimal(10) ** -decimals_to
        to_amount = (net / price_to).quantize(quant_to, rounding=ROUND_DOWN)

        return {
            "from_asset": from_asset,
            "to_asset": to_asset,
            "amount_from": float(payload.amount_from),
            "estimated_reference_value_gross": float(gross),
            "fee_in_reference_currency": float(fee_eur),
            "estimated_reference_value_net": float(net),
            "estimated_to_amount": float(to_amount),
            "from_price_in_ref_ccy": float(price_from),
            "to_price_in_ref_ccy": float(price_to),
            "reference_currency": currency,
            "is_fresh": True,
        }

    def swap(
        self,
        db: Session,
        client_id: UUID,
        payload: SwapRequest,
        actor: ActorContext,
    ) -> dict:
        """Execute a crypto ↔ crypto swap as SELL source + BUY target with single reference value.

        No EUR custody movement. Net from SELL = cost basis for BUY.
        """
        import uuid as uuid_mod

        # --- 0. Eligibility gate ---
        from services.compliance.eligibility_service import EligibilityService
        EligibilityService.require_eligible_by_client_id(db, client_id)

        from_asset = payload.from_asset.upper()
        to_asset = payload.to_asset.upper()
        if from_asset not in SUPPORTED_ASSETS or to_asset not in SUPPORTED_ASSETS:
            raise UnsupportedAssetError(f"unsupported_asset: {from_asset} or {to_asset}")
        if from_asset == to_asset:
            raise ExchangeError("swap_same_asset: from_asset must differ from to_asset")

        decimals_from = ASSET_PRECISION.get(from_asset, 8)
        quant_from = Decimal(10) ** -decimals_from
        amount_from = payload.amount_from.quantize(quant_from, rounding=ROUND_DOWN)
        if amount_from <= 0:
            raise ExchangeError("invalid_amount_from")

        ext_ref = payload.external_reference or f"swap-{uuid_mod.uuid4()}"

        # Idempotency: check if we already have orders for this reference
        sell_ref = f"{ext_ref}-sell"
        buy_ref = f"{ext_ref}-buy"
        existing_sell = self._order_repo.find_by_reference(db, sell_ref)
        if existing_sell is not None and existing_sell.client_id == client_id:
            existing_buy = self._order_repo.find_by_reference(db, buy_ref)
            if (
                existing_buy is not None
                and existing_buy.client_id == client_id
                and existing_sell.swap_group_id == existing_buy.swap_group_id
            ):
                return {
                    "status": "ignored",
                    "reason": "duplicate_external_reference",
                    "swap_group_id": existing_sell.swap_group_id,
                    "sell_order_id": existing_sell.id,
                    "buy_order_id": existing_buy.id,
                }

        # Resolve prices (same freshness guard as buy/sell)
        price_from = self._resolve_price(db, from_asset, override_price=None, side="sell")
        price_to = self._resolve_price(db, to_asset, override_price=None, side="buy")

        eur_quant = Decimal("0.01")
        gross = (amount_from * price_from).quantize(eur_quant, rounding=ROUND_DOWN)
        fee_bps = self._fee_repo.get_active_fee_bps(db, from_asset)
        fee_eur = (gross * fee_bps / Decimal("10000")).quantize(eur_quant, rounding=ROUND_DOWN)
        net_reference = gross - fee_eur
        if net_reference <= 0:
            raise ExchangeError("computed_net_value_is_zero")

        decimals_to = ASSET_PRECISION.get(to_asset, 8)
        quant_to = Decimal(10) ** -decimals_to
        amount_to = (net_reference / price_to).quantize(quant_to, rounding=ROUND_DOWN)
        if amount_to <= 0:
            raise ExchangeError("computed_target_amount_is_zero")

        # Lock source position
        position_from = self._position_repo.get_or_create_for_update(
            db, client_id, from_asset
        )
        current_from = Decimal(str(position_from.balance))
        if current_from < amount_from:
            raise InsufficientCryptoBalanceError(
                f"insufficient_crypto_balance: {from_asset} available={current_from}, requested={amount_from}"
            )

        # WAC for source
        cost_basis_total, position_qty = self._order_repo.get_wac_state_before_sell(
            db, client_id, from_asset
        )
        cost_basis_consumed: Optional[Decimal] = None
        realized_pnl: Optional[Decimal] = None
        if position_qty > 0:
            avg_cost = cost_basis_total / position_qty
            cost_basis_consumed = (amount_from * avg_cost).quantize(
                eur_quant, rounding=ROUND_DOWN
            )
            realized_pnl = (net_reference - cost_basis_consumed).quantize(
                eur_quant, rounding=ROUND_DOWN
            )

        swap_group_id = uuid_mod.uuid4()

        # Create SELL order (swap leg) — no EUR custody
        sell_order = self._order_repo.create(
            db,
            data={
                "client_id": client_id,
                "side": "sell",
                "asset": from_asset,
                "amount_crypto": amount_from,
                "amount_fiat": gross,
                "price": price_from,
                "currency": "EUR",
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount_from": amount_from,
                "amount_to": net_reference,
                "fee_amount": fee_eur,
                "fee_asset": "EUR",
                "status": "processing",
                "external_reference": sell_ref,
                "cost_basis_consumed": cost_basis_consumed,
                "realized_pnl_generated": realized_pnl,
                "swap_group_id": swap_group_id,
                "metadata_": {
                    "swap_leg": "sell",
                    "reference_value_gross": str(gross),
                    "reference_value_net": str(net_reference),
                    "fee_in_reference_currency": str(fee_eur),
                },
            },
        )

        # Create BUY order (swap leg) — cost basis = net_reference
        buy_order = self._order_repo.create(
            db,
            data={
                "client_id": client_id,
                "side": "buy",
                "asset": to_asset,
                "amount_crypto": amount_to,
                "amount_fiat": net_reference,
                "price": price_to,
                "currency": "EUR",
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount_from": net_reference,
                "amount_to": amount_to,
                "fee_amount": Decimal("0"),
                "fee_asset": to_asset,
                "status": "processing",
                "external_reference": buy_ref,
                "swap_group_id": swap_group_id,
                "metadata_": {
                    "swap_leg": "buy",
                    "reference_value_net": str(net_reference),
                    "source_asset": from_asset,
                },
            },
        )

        try:
            # Debit source position
            self._position_repo.debit(db, position_from, amount_from)

            # Credit target position
            position_to = self._position_repo.get_or_create_for_update(
                db, client_id, to_asset
            )
            self._position_repo.credit(db, position_to, amount_to)

            # Sync direct portfolio atoms for swap (unless bundle)
            is_bundle_swap = (
                sell_ref.startswith("bundle-")
                or ext_ref.startswith("bundle-")
            )
            if not is_bundle_swap:
                try:
                    direct_pf = ensure_direct_portfolio(db, client_id)
                    pe_from = _resolve_pe_instrument(db, from_asset)
                    pe_to = _resolve_pe_instrument(db, to_asset)
                    cost_consumed = cost_basis_consumed if cost_basis_consumed is not None else Decimal("0")
                    sync_direct_atom(db, direct_pf.id, pe_from.id, -amount_from, -cost_consumed)
                    sync_direct_atom(db, direct_pf.id, pe_to.id, amount_to, net_reference)
                    for swap_ord in (sell_order, buy_order):
                        meta = dict(swap_ord.metadata_ or {})
                        meta["portfolio_scope"] = "direct"
                        meta["portfolio_id"] = str(direct_pf.id)
                        swap_ord.metadata_ = meta
                    db.flush()
                except Exception as exc:
                    logger.warning("Direct atom sync failed on SWAP: %s", exc)

            # Settlement deltas
            today = date.today()
            delta_from = self._delta_repo.get_or_create(db, from_asset, today)
            self._delta_repo.increment(db, delta_from, -amount_from)
            delta_to = self._delta_repo.get_or_create(db, to_asset, today)
            self._delta_repo.increment(db, delta_to, amount_to)

            self._order_repo.update_status(db, sell_order, new_status="completed")
            self._order_repo.update_status(db, buy_order, new_status="completed")
            _ingest_order_cost_basis(db, sell_order)
            _ingest_order_cost_basis(db, buy_order)

        except Exception as exc:
            logger.error("Swap failed: %s", exc, exc_info=True)
            self._order_repo.update_status(db, sell_order, new_status="failed", failure_reason=str(exc))
            self._order_repo.update_status(db, buy_order, new_status="failed", failure_reason=str(exc))
            raise

        AuditService.log_success(
            db,
            entity_type="exchange_order",
            entity_id=str(swap_group_id),
            action="swap_completed",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "swap_group_id": str(swap_group_id),
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount_from": str(amount_from),
                "amount_to": str(amount_to),
                "net_reference": str(net_reference),
                "cost_basis_consumed": str(cost_basis_consumed) if cost_basis_consumed else None,
                "realized_pnl": str(realized_pnl) if realized_pnl else None,
            },
        )

        return {
            "status": "completed",
            "swap_group_id": swap_group_id,
            "sell_order_id": sell_order.id,
            "buy_order_id": buy_order.id,
            "from_asset": from_asset,
            "to_asset": to_asset,
            "amount_from": amount_from,
            "amount_to": amount_to,
            "reference_value_gross": float(gross),
            "fee_in_reference_currency": float(fee_eur),
            "reference_value_net": float(net_reference),
            "cost_basis_consumed": str(cost_basis_consumed) if cost_basis_consumed else None,
            "realized_pnl_generated": str(realized_pnl) if realized_pnl else None,
            "from_position_after": position_from.balance,
            "to_position_after": position_to.balance,
        }

    def run_settlement(self, db: Session, actor: ActorContext) -> dict:
        """Daily net settlement: process all unsettled crypto deltas.

        Before settling each delta, verify pool liquidity:
        - delta > 0 (buys) → settlement wallet must hold >= delta
        - delta < 0 (sells) → clients pool must hold >= abs(delta)

        Blocked deltas are NOT settled and remain pending.
        In production the actual Fireblocks transfers would be triggered here.
        """
        unsettled = self._delta_repo.list_unsettled(db)
        details: list[dict] = []

        for delta in unsettled:
            amount = Decimal(str(delta.delta_amount))

            if amount == 0:
                self._delta_repo.mark_settled(db, delta)
                details.append({
                    "asset": delta.asset,
                    "date": str(delta.settlement_date),
                    "delta_amount": "0",
                    "direction": "none",
                    "action": "marked_settled",
                })
                continue

            if amount > 0:
                wallet_balance = _get_settlement_wallet_balance_for_settlement(db, delta.asset)
                if wallet_balance < amount:
                    details.append({
                        "asset": delta.asset,
                        "date": str(delta.settlement_date),
                        "delta_amount": str(amount),
                        "direction": "clients_pool ← settlement_wallet",
                        "status": "blocked",
                        "reason": "insufficient_settlement_wallet_liquidity",
                        "wallet_balance": str(wallet_balance),
                    })
                    AuditService.log_failure(
                        db,
                        entity_type="settlement_delta",
                        entity_id=str(delta.id),
                        action="settlement_blocked",
                        actor_type=actor.actor_type,
                        actor_id=actor.actor_id,
                        error=(
                            f"insufficient_settlement_wallet_liquidity: "
                            f"need={amount}, available={wallet_balance}"
                        ),
                        metadata={
                            "asset": delta.asset,
                            "delta_amount": str(amount),
                            "wallet_balance": str(wallet_balance),
                        },
                    )
                    continue
            else:
                pool_balance = self._position_repo.get_aggregate_balance(db, delta.asset)
                if pool_balance < abs(amount):
                    details.append({
                        "asset": delta.asset,
                        "date": str(delta.settlement_date),
                        "delta_amount": str(amount),
                        "direction": "settlement_wallet ← clients_pool",
                        "status": "blocked",
                        "reason": "insufficient_pool_liquidity",
                        "pool_balance": str(pool_balance),
                    })
                    AuditService.log_failure(
                        db,
                        entity_type="settlement_delta",
                        entity_id=str(delta.id),
                        action="settlement_blocked",
                        actor_type=actor.actor_type,
                        actor_id=actor.actor_id,
                        error=(
                            f"insufficient_pool_liquidity: "
                            f"need={abs(amount)}, available={pool_balance}"
                        ),
                        metadata={
                            "asset": delta.asset,
                            "delta_amount": str(amount),
                            "pool_balance": str(pool_balance),
                        },
                    )
                    continue

            direction = "clients_pool ← settlement_wallet" if amount > 0 else "settlement_wallet ← clients_pool"
            self._delta_repo.mark_settled(db, delta)
            details.append({
                "asset": delta.asset,
                "date": str(delta.settlement_date),
                "delta_amount": str(amount),
                "direction": direction,
                "action": "marked_settled",
            })

        settled_details = [d for d in details if d.get("action") == "marked_settled"]
        blocked_details = [d for d in details if d.get("status") == "blocked"]

        if settled_details:
            AuditService.log_success(
                db,
                entity_type="settlement_run",
                entity_id="daily",
                action="crypto_settlement_executed",
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                metadata={"settled_count": len(settled_details), "details": settled_details},
            )

        return {
            "settled_count": len(settled_details),
            "blocked_count": len(blocked_details),
            "details": details,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_price(
        self,
        db: Session,
        asset: str,
        override_price: Optional[Decimal],
        side: Literal["buy", "sell"] = "buy",
    ) -> Decimal:
        """Return the price per 1 unit of crypto in **EUR**.

        If override_price is provided, it is assumed to already be in EUR and
        freshness checks are skipped (operator-driven).

        Otherwise, fetch the latest quote from market_data_latest_quotes:
        - Enforce freshness: quote_time must be within MAX_QUOTE_AGE_SECONDS.
        - If bid_price and ask_price are available:
            BUY → use ask_price, SELL → use bid_price.
        - Otherwise, build simulated bid/ask from last_price using spread_bps.
        - Convert the selected USDT price to EUR via the FX module.
        """
        if override_price is not None:
            return override_price

        upper = asset.upper()

        # --- EUR-pegged stablecoins: always use synthetic 1.0 EUR ---
        provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(asset)
        if provider_symbol is None:
            if upper in EUR_PEGGED_STABLECOINS:
                return self._eur_pegged_fallback_price(asset)
            if upper in USD_PEGGED_STABLECOINS:
                return self._stablecoin_fallback_price(db, asset)
            raise PriceUnavailableError(f"no_provider_symbol_for_{asset}")

        # Refresh stale quotes from Binance REST before reading from DB
        try:
            refresh_binance_quotes_for_provider_symbols(
                db, [provider_symbol, EURUSDT_PROVIDER_SYMBOL],
            )
        except Exception:
            logger.warning("Failed to refresh Binance quotes for %s / EURUSDT", provider_symbol, exc_info=True)

        quote = (
            db.query(MarketDataLatestQuote)
            .join(
                MarketDataInstrument,
                MarketDataLatestQuote.instrument_id == MarketDataInstrument.id,
            )
            .filter(MarketDataInstrument.provider_symbol == provider_symbol)
            .first()
        )

        if quote is None or quote.last_price is None:
            if upper in EUR_PEGGED_STABLECOINS:
                return self._eur_pegged_fallback_price(asset)
            if upper in USD_PEGGED_STABLECOINS:
                logger.info("No live quote for %s, using stablecoin fallback (1.0 USDT)", asset)
                return self._stablecoin_fallback_price(db, asset)
            raise PriceUnavailableError(f"no_market_quote_for_{asset}")

        # --- Freshness guard ---
        if quote.quote_time is None:
            if upper in EUR_PEGGED_STABLECOINS:
                return self._eur_pegged_fallback_price(asset)
            if upper in USD_PEGGED_STABLECOINS:
                logger.info("No quote_time for %s, using stablecoin fallback (1.0 USDT)", asset)
                return self._stablecoin_fallback_price(db, asset)
            raise MarketQuoteStaleError(
                f"market_quote_stale: no quote_time for {asset}"
            )

        now_utc = datetime.now(timezone.utc)
        quote_time = quote.quote_time
        if quote_time.tzinfo is None:
            quote_time = quote_time.replace(tzinfo=timezone.utc)
        age_seconds = (now_utc - quote_time).total_seconds()

        max_age = (
            MAX_QUOTE_AGE_SECONDS_STABLECOIN
            if upper in STABLECOIN_ASSETS
            else MAX_QUOTE_AGE_SECONDS
        )
        if age_seconds > max_age:
            if upper in EUR_PEGGED_STABLECOINS:
                return self._eur_pegged_fallback_price(asset)
            if upper in USD_PEGGED_STABLECOINS:
                logger.info(
                    "%s quote is %ds old (max %ds), using stablecoin fallback (1.0 USDT)",
                    asset, int(age_seconds), max_age,
                )
                return self._stablecoin_fallback_price(db, asset)
            raise MarketQuoteStaleError(
                f"market_quote_stale: {asset} quote is {int(age_seconds)}s old "
                f"(max {max_age}s)"
            )

        # --- Select price based on side ---
        bid = Decimal(str(quote.bid_price)) if quote.bid_price else None
        ask = Decimal(str(quote.ask_price)) if quote.ask_price else None

        if bid and ask and bid > 0 and ask > 0:
            price_usdt = ask if side == "buy" else bid
        else:
            mid = Decimal(str(quote.last_price))
            spread_bps = self._fee_repo.get_active_spread_bps(db, asset)
            half_spread = Decimal(str(spread_bps)) / Decimal("20000")
            if side == "buy":
                price_usdt = mid * (1 + half_spread)
            else:
                price_usdt = mid * (1 - half_spread)

        try:
            eurusdt_rate = get_eurusdt_rate(db, strict=True)
        except (FxQuoteUnavailableError, FxQuoteStaleError) as exc:
            raise FxUnavailableError(f"fx_unavailable: {exc}") from exc
        price_eur = usdt_to_eur(price_usdt, eurusdt_rate)

        return price_eur

    def _stablecoin_fallback_price(self, db: Session, asset: str) -> Decimal:
        """Return a synthetic EUR price for a USD-pegged stablecoin (≈ 1.0 USDT → EUR)."""
        try:
            eurusdt_rate = get_eurusdt_rate(db, strict=False)
        except Exception:
            eurusdt_rate = Decimal("1.08")
        return usdt_to_eur(Decimal("1"), eurusdt_rate)

    @staticmethod
    def _eur_pegged_fallback_price(asset: str) -> Decimal:
        """Return a synthetic EUR price for an EUR-pegged stablecoin (1 EURC = 1 EUR)."""
        logger.info("Using EUR-pegged fallback for %s: price_eur = 1.0", asset)
        return Decimal("1")

    # ------------------------------------------------------------------
    # Sell-all: liquidate all crypto positions for a client
    # ------------------------------------------------------------------

    def preview_sell_all(
        self, db: Session, client_id: UUID, currency: str = "EUR"
    ) -> dict:
        """Preview selling 100 % of every crypto position with balance > 0.

        Read-only — no side-effects.  Returns per-asset estimates and a total.
        """
        positions = self._position_repo.list_by_client(db, client_id)
        items: list[dict] = []
        total_estimated = Decimal("0")

        for pos in positions:
            balance = Decimal(str(pos.balance))
            if balance <= 0:
                continue
            asset = pos.asset.upper()
            try:
                preview = self.preview_sell(db, asset, balance, currency)
                net = Decimal(str(preview["estimated_fiat_net"]))
                total_estimated += net
                items.append({
                    "asset": asset,
                    "amount_available": str(balance),
                    "estimated_eur_gross": preview["estimated_fiat_gross"],
                    "fee_amount": preview["fee_amount"],
                    "estimated_eur_net": float(net),
                    "price": preview["estimated_price"],
                    "status": "ready",
                })
            except ExchangeError as exc:
                error_code = type(exc).__name__
                items.append({
                    "asset": asset,
                    "amount_available": str(balance),
                    "estimated_eur_gross": 0,
                    "fee_amount": 0,
                    "estimated_eur_net": 0,
                    "price": 0,
                    "status": "unavailable",
                    "error_code": error_code,
                    "error_message": str(exc),
                })

        return {
            "total_assets": len(items),
            "estimated_total_eur": float(total_estimated),
            "items": items,
        }

    def sell_all(
        self, db: Session, client_id: UUID, actor: ActorContext, currency: str = "EUR"
    ) -> dict:
        """Liquidate all crypto positions sequentially (best-effort).

        Uses the real ``sell()`` method for each asset, preserving all
        accounting logic (WAC, realized P&L, ledger, audit).
        """
        import uuid as uuid_mod

        # --- 0. Eligibility gate ---
        from services.compliance.eligibility_service import EligibilityService
        EligibilityService.require_eligible_by_client_id(db, client_id)

        positions = self._position_repo.list_by_client(db, client_id)
        results: list[dict] = []
        total_estimated_before = Decimal("0")
        total_actually_received = Decimal("0")
        sold = 0
        failed = 0
        batch_id = str(uuid_mod.uuid4())

        active_positions = [
            p for p in positions if Decimal(str(p.balance)) > 0
        ]

        for pos in active_positions:
            balance = Decimal(str(pos.balance))
            asset = pos.asset.upper()
            decimals = ASSET_PRECISION.get(asset, 8)
            quant = Decimal(10) ** -decimals
            amount = balance.quantize(quant, rounding=ROUND_DOWN)
            if amount <= 0:
                continue

            try:
                preview = self.preview_sell(db, asset, amount, currency)
                total_estimated_before += Decimal(str(preview["estimated_fiat_net"]))
            except ExchangeError:
                pass

            ext_ref = f"sell-all-{batch_id}-{asset}"
            sell_payload = ExchangeSellRequest(
                client_id=client_id,
                asset=asset,
                amount_crypto=amount,
                currency=currency,
                external_reference=ext_ref,
            )

            try:
                result = self.sell(db, sell_payload, actor)
                net = Decimal(str(result.get("net_eur", 0)))
                total_actually_received += net
                sold += 1
                results.append({
                    "asset": asset,
                    "status": "completed",
                    "amount_sold": str(amount),
                    "eur_received": str(net),
                    "order_id": str(result.get("order_id", "")),
                    "realized_pnl": result.get("realized_pnl_generated"),
                })
            except ExchangeError as exc:
                failed += 1
                error_code = type(exc).__name__
                results.append({
                    "asset": asset,
                    "status": "failed",
                    "error_code": error_code,
                    "error_message": str(exc),
                })

        AuditService.log_success(
            db,
            entity_type="sell_all_batch",
            entity_id=batch_id,
            action="sell_all_completed",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "client_id": str(client_id),
                "batch_id": batch_id,
                "total_detected": len(active_positions),
                "sold": sold,
                "failed": failed,
                "total_eur_received": str(total_actually_received),
            },
        )

        return {
            "status": "completed",
            "batch_id": batch_id,
            "total_assets_detected": len(active_positions),
            "total_assets_sold": sold,
            "total_assets_failed": failed,
            "estimated_total_eur_before": float(total_estimated_before),
            "actual_total_eur_received": float(total_actually_received),
            "results": results,
        }
