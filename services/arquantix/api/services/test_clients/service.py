"""Données agrégées pour l’app mobile (/api/app/*) — le PeClient vient toujours du JWT."""
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.clients.models import Client

logger = logging.getLogger(__name__)


class TestClientService:
    """Agrégation custody / exchange / portefeuille pour une session mobile authentifiée."""

    @staticmethod
    def _mask_iban(raw: str) -> str:
        if len(raw) <= 8:
            return raw
        return raw[:4] + "****" + raw[-4:]

    @staticmethod
    def _fmt_balance(val) -> str:
        """Format a Decimal balance to a clean fixed-point string."""
        if val is None:
            return "0.00"
        from decimal import Decimal
        d = Decimal(str(val))
        return f"{d:.2f}"

    def get_cash_data(self, db: Session, *, client: Client) -> dict:
        """Return the client's fiat cash account, balance and recent transactions."""
        from datetime import datetime, timezone

        from services.custody.models import CustodyProvider
        from services.custody.repository import (
            CustodyAccountRepository,
            CustodyBalanceRepository,
            CustodyTransactionRepository,
        )
        from .schemas import CURRENCY_SYMBOLS

        account = CustodyAccountRepository.find_client_account(db, client.id, "EUR")

        result: dict = {
            "client": client,
            "cash_account": None,
            "recent_transactions": [],
            "last_updated": datetime.now(timezone.utc),
        }

        if account is None:
            return result

        balance = CustodyBalanceRepository.get_by_account_id(db, account.id)

        result["cash_account"] = {
            "account_id": account.id,
            "iban": self._mask_iban(account.iban) if account.iban else None,
            "currency": account.currency,
            "currency_symbol": CURRENCY_SYMBOLS.get(account.currency, account.currency),
            "available_balance": self._fmt_balance(balance.available_balance) if balance else "0.00",
            "pending_balance": self._fmt_balance(balance.pending_balance) if balance else "0.00",
        }

        provider_cache: dict = {}

        def _resolve_provider_name(provider_id) -> str:
            if provider_id is None:
                return ""
            pid = str(provider_id)
            if pid not in provider_cache:
                prov = db.query(CustodyProvider).filter(CustodyProvider.id == provider_id).first()
                provider_cache[pid] = prov.name if prov else ""
            return provider_cache[pid]

        txs, _ = CustodyTransactionRepository.list(
            db, account_id=account.id, skip=0, limit=5
        )
        result["recent_transactions"] = [
            {
                "id": tx.id,
                "type": tx.transaction_type,
                "transaction_kind": tx.transaction_kind,
                "direction": tx.direction,
                "amount": str(tx.amount),
                "currency": tx.currency,
                "status": tx.status,
                "external_reference": tx.external_reference,
                "provider": _resolve_provider_name(tx.provider_id),
                "remitter_name": (tx.metadata_ or {}).get("remitter_name"),
                "narrative": (tx.metadata_ or {}).get("narrative"),
                "created_at": tx.created_at,
            }
            for tx in txs
        ]

        if balance and balance.last_updated_at:
            result["last_updated"] = balance.last_updated_at

        return result

    def get_euro_account_data(self, db: Session, *, client: Client) -> dict:
        """Return the client's EUR custody account with full transaction list."""
        from services.custody.models import CustodyProvider
        from services.custody.repository import (
            CustodyAccountRepository,
            CustodyBalanceRepository,
            CustodyTransactionRepository,
        )
        from .schemas import (
            CURRENCY_SYMBOLS,
            TRANSACTION_KIND_TITLE_MAP,
            TRANSACTION_TITLE_MAP,
        )

        account = CustodyAccountRepository.find_client_account(db, client.id, "EUR")

        result: dict = {
            "client": client,
            "account": None,
            "transactions": [],
        }

        if account is None:
            return result

        balance = CustodyBalanceRepository.get_by_account_id(db, account.id)

        result["account"] = {
            "account_id": account.id,
            "currency": account.currency,
            "currency_symbol": CURRENCY_SYMBOLS.get(account.currency, account.currency),
            "balance": self._fmt_balance(balance.available_balance) if balance else "0.00",
            "pending_balance": self._fmt_balance(balance.pending_balance) if balance else "0.00",
            "iban_masked": self._mask_iban(account.iban) if account.iban else None,
            "account_holder_name": account.account_holder_name,
        }

        provider_cache: dict = {}

        def _resolve_provider_name(provider_id) -> str:
            if provider_id is None:
                return ""
            pid = str(provider_id)
            if pid not in provider_cache:
                prov = db.query(CustodyProvider).filter(CustodyProvider.id == provider_id).first()
                provider_cache[pid] = prov.name if prov else ""
            return provider_cache[pid]

        txs, _ = CustodyTransactionRepository.list(
            db, account_id=account.id, skip=0, limit=50
        )

        result["transactions"] = [
            self._build_euro_tx_payload(tx, _resolve_provider_name)
            for tx in txs
        ]

        return result

    def get_iban_details(self, db: Session, *, client: Client) -> dict:
        """Return full IBAN, BIC and account holder name for the client's EUR account."""
        from services.custody.repository import CustodyAccountRepository
        from .schemas import CURRENCY_SYMBOLS

        account = CustodyAccountRepository.find_client_account(db, client.id, "EUR")

        result: dict = {
            "client": client,
            "iban_details": None,
        }

        if account is None:
            return result

        result["iban_details"] = {
            "account_holder_name": account.account_holder_name,
            "iban": account.iban,
            "bic": account.bic,
            "currency": account.currency,
            "currency_symbol": CURRENCY_SYMBOLS.get(account.currency, account.currency),
        }

        return result

    def _build_euro_tx_payload(self, tx, resolve_provider) -> dict:
        from .schemas import (
            CURRENCY_SYMBOLS,
            TRANSACTION_KIND_TITLE_MAP,
            TRANSACTION_TITLE_MAP,
        )

        kind = tx.transaction_kind
        title = (
            TRANSACTION_KIND_TITLE_MAP.get(kind) if kind else None
        ) or TRANSACTION_TITLE_MAP.get(
            tx.transaction_type,
            tx.transaction_type.replace("_", " ").title(),
        )

        meta = tx.metadata_ or {}
        remitter_name = meta.get("remitter_name")
        narrative = meta.get("narrative")
        subtitle = remitter_name or narrative or "Compte Euro"

        return {
            "id": tx.id,
            "transaction_kind": kind,
            "transaction_type": tx.transaction_type,
            "direction": tx.direction,
            "amount": self._fmt_balance(tx.amount),
            "currency": tx.currency,
            "currency_symbol": CURRENCY_SYMBOLS.get(tx.currency, tx.currency),
            "status": tx.status,
            "title": title,
            "subtitle": subtitle,
            "created_at": tx.created_at,
            "external_reference": tx.external_reference,
            "provider": resolve_provider(tx.provider_id),
            "remitter_name": remitter_name,
            "narrative": narrative,
        }

    def get_crypto_positions(self, db: Session, *, client: Client) -> dict:
        """Return the client's crypto positions with EUR valuations."""
        from decimal import Decimal, ROUND_HALF_UP

        from database import MarketDataBar1d, MarketDataInstrument, MarketDataLatestQuote
        from services.exchange.assets import ASSET_PRECISION, ASSET_PROVIDER_SYMBOL_MAP
        from services.exchange.repository import CryptoPositionRepository
        from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
        from services.portfolio_engine.portfolios.models import Portfolio
        from services.portfolio_engine.positions.models import PositionAtom
        from services.portfolio_engine.instruments.models import Instrument
        from services.portfolio_engine.assets.models import Asset
        from .schemas import ASSET_NAMES

        positions = CryptoPositionRepository.list_by_client(db, client.id)

        eurusdt_rate = get_eurusdt_rate(db, strict=False)

        # Build set of assets that belong to at least one bundle
        bundle_portfolios = (
            db.query(Portfolio)
            .filter(
                Portfolio.client_id == client.id,
                Portfolio.portfolio_type == "bundle_portfolio",
                Portfolio.status == "active",
            )
            .all()
        )
        bundle_asset_symbols: set[str] = set()
        bundles_with_holdings = 0
        for bp in bundle_portfolios:
            atoms = (
                db.query(PositionAtom)
                .filter(
                    PositionAtom.portfolio_id == bp.id,
                    PositionAtom.status == "open",
                    PositionAtom.position_type == "spot",
                    PositionAtom.quantity > 0,
                )
                .all()
            )
            if atoms:
                bundles_with_holdings += 1
                for atom in atoms:
                    instr = db.query(Instrument).filter(Instrument.id == atom.instrument_id).first()
                    if instr:
                        asset_obj = db.query(Asset).filter(Asset.id == instr.asset_id).first()
                        if asset_obj:
                            bundle_asset_symbols.add(asset_obj.symbol.upper())

        enriched = []
        total_value_eur = Decimal("0")
        total_value_usd = Decimal("0")
        direct_count = 0

        for pos in positions:
            total_balance = Decimal(str(pos.balance))
            free_balance = Decimal(str(pos.available_balance))
            if total_balance <= 0:
                continue
            # Use free (non-committed) balance for valuation to avoid
            # double-counting funds already shown under Placements/Lending.
            display_balance = free_balance if free_balance >= 0 else total_balance

            if display_balance <= 0:
                continue

            precision = ASSET_PRECISION.get(pos.asset, 8)
            balance_str = f"{display_balance:.{precision}f}"
            avail_str = f"{free_balance:.{precision}f}"

            price_eur = None
            estimated_value_eur = None
            price_usd = None
            estimated_value_usd = None
            perf_1d_pct = None

            provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(pos.asset)
            if provider_symbol:
                inst = (
                    db.query(MarketDataInstrument)
                    .filter(MarketDataInstrument.provider_symbol == provider_symbol)
                    .first()
                )
                if inst:
                    quote = (
                        db.query(MarketDataLatestQuote)
                        .filter(MarketDataLatestQuote.instrument_id == inst.id)
                        .first()
                    )
                    if quote and quote.last_price is not None:
                        p_usdt = Decimal(str(quote.last_price))

                        p_eur = usdt_to_eur(p_usdt, eurusdt_rate)
                        price_eur = f"{p_eur:.2f}"
                        val_eur = (display_balance * p_eur).quantize(Decimal("0.01"))
                        estimated_value_eur = f"{val_eur:.2f}"
                        total_value_eur += val_eur

                        price_usd = f"{p_usdt:.2f}"
                        val_usd = (display_balance * p_usdt).quantize(Decimal("0.01"))
                        estimated_value_usd = f"{val_usd:.2f}"
                        total_value_usd += val_usd

                    prev_bar = (
                        db.query(MarketDataBar1d)
                        .filter(MarketDataBar1d.instrument_id == inst.id)
                        .order_by(MarketDataBar1d.open_time.desc())
                        .offset(1)
                        .limit(1)
                        .first()
                    )
                    if prev_bar and prev_bar.close and quote and quote.last_price:
                        prev_close = Decimal(str(prev_bar.close))
                        if prev_close > 0:
                            pct = ((Decimal(str(quote.last_price)) - prev_close) / prev_close * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                            perf_1d_pct = f"{pct:+.2f}"

            is_bundle_only = pos.asset.upper() in bundle_asset_symbols
            if not is_bundle_only:
                direct_count += 1

            enriched.append({
                "asset": pos.asset,
                "name": ASSET_NAMES.get(pos.asset, pos.asset),
                "balance": balance_str,
                "available_balance": avail_str,
                "total_balance": f"{total_balance:.{precision}f}",
                "price_eur": price_eur,
                "estimated_value_eur": estimated_value_eur,
                "price_usd": price_usd,
                "estimated_value_usd": estimated_value_usd,
                "performance_1d_pct": perf_1d_pct,
                "icon_key": pos.asset.lower(),
                "portfolio_scope": "bundle" if is_bundle_only else "direct",
            })

        enriched.sort(
            key=lambda x: Decimal(x["estimated_value_eur"]) if x["estimated_value_eur"] else Decimal("0"),
            reverse=True,
        )

        from services.privy_wallet.patrimony_merge import merge_app_crypto_positions

        person_id = getattr(client, "person_id", None)
        merged = merge_app_crypto_positions(enriched, db, person_id=person_id)

        total_value_eur = Decimal("0")
        total_value_usd = Decimal("0")
        direct_count = 0
        for row in merged:
            if row.get("estimated_value_eur"):
                total_value_eur += Decimal(str(row["estimated_value_eur"]))
            if row.get("estimated_value_usd"):
                total_value_usd += Decimal(str(row["estimated_value_usd"]))
            scope = row.get("portfolio_scope") or "direct"
            if scope in ("direct", "privy", "merged"):
                direct_count += 1

        return {
            "client": client,
            "summary": {
                "total_value_eur": f"{total_value_eur:.2f}",
                "total_value_usd": f"{total_value_usd:.2f}",
                "positions_count": len(merged),
                "direct_positions_count": direct_count,
                "bundles_count": bundles_with_holdings,
            },
            "positions": merged,
        }

    def get_crypto_wallet_detail(
        self, db: Session, asset: str, *, client: Client
    ) -> dict:
        """Return detailed wallet info for a single crypto asset including PRU and gains.

        P&L values are delegated to build_wallet_statistics to guarantee
        WAC-consistent figures everywhere (detail screen, statistics screen,
        charts).
        """
        from decimal import Decimal, ROUND_HALF_UP

        from database import MarketDataInstrument, MarketDataLatestQuote
        from services.exchange.assets import ASSET_PRECISION, ASSET_PROVIDER_SYMBOL_MAP
        from services.exchange.repository import CryptoPositionRepository
        from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
        from services.wallet_statistics.service import build_wallet_statistics
        from .schemas import ASSET_NAMES

        asset = asset.upper()

        positions = CryptoPositionRepository.list_by_client(db, client.id)
        pos = next((p for p in positions if p.asset == asset), None)

        from services.privy_wallet.patrimony_merge import find_merged_position

        merged = find_merged_position(db, person_id=getattr(client, "person_id", None), asset=asset)
        if pos is None and merged is None:
            return {"client": client, "detail": None}

        if pos is None and merged is not None:
            return self._build_privy_only_wallet_detail(db, client=client, merged=merged, asset=asset)

        precision = ASSET_PRECISION.get(asset, 8)
        total_balance = Decimal(str(pos.balance))
        free_balance = Decimal(str(pos.available_balance))
        # Show only free (non-committed) balance to avoid double-counting
        # with Placements. Positions fully committed to lending return None.
        display_balance = free_balance if free_balance >= 0 else total_balance
        if display_balance <= 0:
            return {"client": client, "detail": None}
        balance_str = f"{display_balance:.{precision}f}"

        eurusdt_rate = get_eurusdt_rate(db, strict=False)
        current_price_eur = None
        current_price_usd = None
        provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(asset)
        if provider_symbol:
            quote = (
                db.query(MarketDataLatestQuote)
                .join(MarketDataInstrument, MarketDataLatestQuote.instrument_id == MarketDataInstrument.id)
                .filter(MarketDataInstrument.provider_symbol == provider_symbol)
                .first()
            )
            if quote and quote.last_price is not None:
                current_price_usd = Decimal(str(quote.last_price))
                current_price_eur = usdt_to_eur(current_price_usd, eurusdt_rate)

        total_value_eur = (display_balance * current_price_eur).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if current_price_eur else Decimal("0")
        total_value_usd = (display_balance * current_price_usd).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if current_price_usd else Decimal("0")

        stats_eur = build_wallet_statistics(db, client.id, asset, reference_currency="EUR")
        stats_usd = build_wallet_statistics(db, client.id, asset, reference_currency="USD")

        avg_price_eur = Decimal(str(stats_eur["average_entry_price"]))
        avg_price_usd = Decimal(str(stats_usd["average_entry_price"]))
        cost_basis_eur = (display_balance * avg_price_eur).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if avg_price_eur > 0 else None
        cost_basis_usd = (display_balance * avg_price_usd).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if avg_price_usd > 0 else None

        unrealized_eur = Decimal(str(stats_eur["unrealized_pnl"]))
        realized_eur = Decimal(str(stats_eur["realized_pnl"]))
        total_pnl_eur = Decimal(str(stats_eur["total_pnl"]))

        unrealized_usd = Decimal(str(stats_usd["unrealized_pnl"]))
        realized_usd = Decimal(str(stats_usd["realized_pnl"]))
        total_pnl_usd = Decimal(str(stats_usd["total_pnl"]))

        unrealized_eur_pct = None
        unrealized_usd_pct = None
        total_gains_eur_pct = None
        total_gains_usd_pct = None
        if cost_basis_eur and cost_basis_eur > 0:
            unrealized_eur_pct = ((unrealized_eur / cost_basis_eur) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_gains_eur_pct = ((total_pnl_eur / cost_basis_eur) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if cost_basis_usd and cost_basis_usd > 0:
            unrealized_usd_pct = ((unrealized_usd / cost_basis_usd) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_gains_usd_pct = ((total_pnl_usd / cost_basis_usd) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        def _signed(val: Decimal) -> str:
            if val > 0:
                return f"+{val:.2f}"
            return f"{val:.2f}"

        detail = {
                "asset": asset,
                "name": ASSET_NAMES.get(asset, asset),
                "icon_key": asset.lower(),
                "volume": balance_str,
                "current_price_eur": f"{current_price_eur:.2f}" if current_price_eur else None,
                "current_price_usd": f"{current_price_usd:.2f}" if current_price_usd else None,
                "total_value_eur": f"{total_value_eur:.2f}",
                "total_value_usd": f"{total_value_usd:.2f}",
                "avg_buy_price_eur": f"{avg_price_eur:.2f}" if avg_price_eur > 0 else None,
                "avg_buy_price_usd": f"{avg_price_usd:.2f}" if avg_price_usd > 0 else None,
                "average_purchase_price": f"{avg_price_eur:.2f}" if avg_price_eur > 0 else None,
                "cost_basis": f"{cost_basis_eur:.2f}" if cost_basis_eur else None,
                "unrealized_gain_eur": _signed(unrealized_eur),
                "unrealized_gain_usd": _signed(unrealized_usd),
                "unrealized_gains": _signed(unrealized_eur),
                "unrealized_gains_pct": f"{unrealized_eur_pct:+.2f}" if unrealized_eur_pct is not None else None,
                "realized_gain_eur": _signed(realized_eur),
                "realized_gain_usd": _signed(realized_usd),
                "realized_gains": _signed(realized_eur),
                "total_gain_eur": _signed(total_pnl_eur),
                "total_gain_usd": _signed(total_pnl_usd),
                "total_gains": _signed(total_pnl_eur),
                "total_gains_pct": f"{total_gains_eur_pct:+.2f}" if total_gains_eur_pct is not None else None,
            }
        if merged is not None:
            detail["portfolio_scope"] = merged.get("portfolio_scope")
            detail["privy_balance"] = merged.get("privy_balance")
            detail["platform_balance"] = merged.get("platform_balance")
            merged_bal = Decimal(str(merged.get("balance") or balance_str))
            if merged_bal > 0:
                detail["volume"] = f"{merged_bal:.{precision}f}"
            if merged.get("estimated_value_eur"):
                detail["total_value_eur"] = merged["estimated_value_eur"]
            if merged.get("estimated_value_usd"):
                detail["total_value_usd"] = merged["estimated_value_usd"]

        return {
            "client": client,
            "detail": detail,
        }

    @staticmethod
    def _build_privy_only_wallet_detail(
        db: Session,
        *,
        client: Client,
        merged: dict,
        asset: str,
    ) -> dict:
        from decimal import Decimal, ROUND_HALF_UP

        from services.exchange.assets import ASSET_PRECISION
        from .schemas import ASSET_NAMES

        asset = asset.upper()
        precision = ASSET_PRECISION.get(asset, 8)
        balance = Decimal(str(merged.get("balance") or "0"))
        balance_str = f"{balance:.{precision}f}"
        total_value_eur = merged.get("estimated_value_eur") or "0.00"
        total_value_usd = merged.get("estimated_value_usd")

        return {
            "client": client,
            "detail": {
                "asset": asset,
                "name": ASSET_NAMES.get(asset, asset),
                "icon_key": asset.lower(),
                "volume": balance_str,
                "current_price_eur": merged.get("price_eur"),
                "current_price_usd": merged.get("price_usd"),
                "total_value_eur": total_value_eur,
                "total_value_usd": total_value_usd,
                "avg_buy_price_eur": None,
                "avg_buy_price_usd": None,
                "average_purchase_price": None,
                "cost_basis": None,
                "unrealized_gain_eur": "0.00",
                "unrealized_gain_usd": "0.00",
                "unrealized_gains": "0.00",
                "unrealized_gains_pct": None,
                "realized_gain_eur": "0.00",
                "realized_gain_usd": "0.00",
                "realized_gains": "0.00",
                "total_gain_eur": "0.00",
                "total_gain_usd": "0.00",
                "total_gains": "0.00",
                "total_gains_pct": None,
                "portfolio_scope": merged.get("portfolio_scope") or "privy",
                "privy_balance": merged.get("privy_balance") or balance_str,
                "platform_balance": merged.get("platform_balance") or "0",
            },
        }

    def get_crypto_transactions(
        self, db: Session, asset: str, *, client: Client
    ) -> dict:
        """Return exchange orders + Privy ledger entries for the asset."""
        from services.exchange.repository import ExchangeOrderRepository
        from services.privy_wallet.repository import PersonWalletDepositRepository
        from services.lifi.swap_repository import PersonWalletSwapRepository
        from services.privy_wallet.transaction_merge import (
            exchange_order_to_crypto_tx,
            list_orphan_webhook_crypto_txs,
            merge_crypto_transactions,
            person_wallet_swap_to_crypto_tx,
        )

        asset = asset.upper()
        orders = ExchangeOrderRepository.list_by_client_asset(db, client.id, asset)
        exchange_txs = [
            exchange_order_to_crypto_tx(o, asset=asset) for o in orders
        ]

        person_id = getattr(client, "person_id", None)
        privy_rows: list = []
        orphan_txs: list = []
        swap_txs: list = []
        if person_id is not None:
            privy_rows = PersonWalletDepositRepository().list_for_person(
                db, person_id, asset=asset, limit=200
            )
            orphan_txs = list_orphan_webhook_crypto_txs(
                db, person_id=person_id, asset=asset, limit=200
            )
            swap_rows = PersonWalletSwapRepository.list_confirmed_for_person_asset(
                db, person_id=person_id, asset=asset, limit=200
            )
            for swap in swap_rows:
                mapped = person_wallet_swap_to_crypto_tx(swap, asset=asset)
                if mapped is not None:
                    swap_txs.append(mapped)

        txs = merge_crypto_transactions(
            exchange_txs,
            privy_rows,
            extra_txs=[*orphan_txs, *swap_txs],
        )

        return {
            "client": client,
            "asset": asset,
            "transactions": txs,
        }

    def get_transaction_detail(
        self, db: Session, transaction_id: UUID, *, client: Client
    ) -> dict:
        """Return full detail for a single custody transaction or exchange order."""
        from services.custody.models import CustodyProvider
        from services.custody.repository import (
            CustodyAccountRepository,
            CustodyTransactionRepository,
        )
        from .operation_resolver import OperationResolver
        from .schemas import (
            CURRENCY_SYMBOLS,
            TRANSACTION_KIND_TITLE_MAP,
            TRANSACTION_TITLE_MAP,
            STATUS_LABEL_MAP,
        )

        ref = OperationResolver.resolve(db, client, transaction_id)
        if ref is None:
            return None

        if ref.source_system == "privy":
            return self._get_privy_deposit_detail(db, client, transaction_id, STATUS_LABEL_MAP)

        if ref.source_system == "custody":
            tx = CustodyTransactionRepository.get_by_id(db, transaction_id)
            account = CustodyAccountRepository.get_by_id(db, tx.account_id)

            provider_name = None
            if tx.provider_id:
                prov = db.query(CustodyProvider).filter(CustodyProvider.id == tx.provider_id).first()
                provider_name = prov.name if prov else None

            meta = tx.metadata_ or {}

            remitter_iban_raw = meta.get("remitter_iban")
            target_iban_raw = account.iban

            kind = tx.transaction_kind
            title = (
                TRANSACTION_KIND_TITLE_MAP.get(kind, None) if kind
                else None
            ) or TRANSACTION_TITLE_MAP.get(
                tx.transaction_type,
                tx.transaction_type.replace("_", " ").title(),
            )

            return {
                "id": tx.id,
                "transaction_type": tx.transaction_type,
                "transaction_kind": kind,
                "direction": tx.direction,
                "amount": str(tx.amount),
                "currency": tx.currency,
                "currency_symbol": CURRENCY_SYMBOLS.get(tx.currency, tx.currency),
                "status": tx.status,
                "created_at": tx.created_at,
                "updated_at": tx.updated_at,
                "title": title,
                "status_label": STATUS_LABEL_MAP.get(tx.status, tx.status.title()),
                "source_system": "custody",
                "source_id": str(tx.id),
                "external_reference": tx.external_reference,
                "provider_reference": tx.provider_reference,
                "provider_name": provider_name,
                "remitter_name": meta.get("remitter_name"),
                "remitter_iban": self._mask_iban(remitter_iban_raw) if remitter_iban_raw else None,
                "remitter_bank_name": meta.get("remitter_bank_name"),
                "account_holder_name": meta.get("account_holder_name") or account.account_holder_name,
                "target_iban": self._mask_iban(target_iban_raw) if target_iban_raw else None,
                "booking_date": meta.get("booking_date"),
                "value_date": meta.get("value_date"),
                "narrative": meta.get("narrative"),
            }

        return self._get_exchange_order_detail(db, client, transaction_id, CURRENCY_SYMBOLS, STATUS_LABEL_MAP)

    def _get_privy_deposit_detail(
        self,
        db: Session,
        client: Client,
        deposit_id: UUID,
        status_labels: dict,
    ) -> Optional[dict]:
        from services.privy_wallet.repository import PersonWalletDepositRepository
        from services.privy_wallet.service import _format_decimal

        person_id = getattr(client, "person_id", None)
        if person_id is None:
            return None

        row = PersonWalletDepositRepository().get_for_person(db, deposit_id, person_id)
        if row is None:
            return None

        chain_label = row.chain_type.upper()
        if row.chain_id is not None:
            chain_label = f"{chain_label} (chain {row.chain_id})"

        narrative_parts = [
            f"Hash : {row.tx_hash}",
            f"Réseau : {chain_label}",
        ]
        if row.from_address:
            narrative_parts.append(f"De : {row.from_address}")
        narrative_parts.append(f"Vers : {row.to_address}")
        if row.confirmations:
            narrative_parts.append(f"Confirmations : {row.confirmations}")

        amount = _format_decimal(row.amount)
        return {
            "id": str(row.id),
            "transaction_type": "crypto_deposit",
            "transaction_kind": row.transaction_kind,
            "direction": row.direction,
            "amount": amount,
            "currency": row.asset,
            "currency_symbol": row.asset,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "title": row.title,
            "status_label": status_labels.get(row.status, row.status.title()),
            "source_system": "privy",
            "source_id": str(row.id),
            "external_reference": row.tx_hash,
            "provider_reference": row.tx_hash,
            "provider_name": "Privy",
            "remitter_name": None,
            "remitter_iban": None,
            "remitter_bank_name": None,
            "account_holder_name": None,
            "target_iban": None,
            "booking_date": None,
            "value_date": None,
            "narrative": " · ".join(narrative_parts),
        }

    def _get_exchange_order_detail(
        self, db: Session, client, order_id: UUID,
        currency_symbols: dict, status_labels: dict,
    ) -> Optional[dict]:
        """Fallback: look up an exchange_order by ID."""
        from services.exchange.models import ExchangeOrder

        order = db.query(ExchangeOrder).filter(
            ExchangeOrder.id == order_id,
            ExchangeOrder.client_id == client.id,
        ).first()
        if order is None:
            return None

        side_label = "Achat" if order.side == "buy" else "Vente"
        title = f"{side_label} {order.asset}"
        direction = "debit" if order.side == "buy" else "credit"

        if order.side == "buy":
            amount = order.amount_fiat
            currency = order.currency or "EUR"
        else:
            amount = order.amount_crypto
            currency = order.asset

        meta = order.metadata_ or {}
        fee_info = None
        if order.fee_amount and order.fee_asset:
            fee_info = f"{float(order.fee_amount):.8f} {order.fee_asset}"

        narrative_parts = [f"Prix : {float(order.price):,.2f} USD"]
        if order.amount_crypto:
            narrative_parts.append(f"Quantité : {float(order.amount_crypto):.8f} {order.asset}")
        if order.amount_fiat:
            narrative_parts.append(f"Montant : {float(order.amount_fiat):,.2f} {order.currency or 'EUR'}")
        if fee_info:
            narrative_parts.append(f"Frais : {fee_info}")
        narrative = " · ".join(narrative_parts)

        return {
            "id": str(order.id),
            "transaction_type": "exchange",
            "transaction_kind": f"exchange_{order.side}",
            "direction": direction,
            "amount": str(amount),
            "currency": currency,
            "currency_symbol": currency_symbols.get(currency, currency),
            "status": order.status,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "title": title,
            "status_label": status_labels.get(order.status, order.status.title()),
            "source_system": "exchange",
            "source_id": str(order.id),
            "external_reference": order.external_reference,
            "provider_reference": None,
            "provider_name": meta.get("portfolio_scope", "Exchange"),
            "remitter_name": None,
            "remitter_iban": None,
            "remitter_bank_name": None,
            "account_holder_name": None,
            "target_iban": None,
            "booking_date": None,
            "value_date": None,
            "narrative": narrative,
            "custody_provider": "privy",
        }
