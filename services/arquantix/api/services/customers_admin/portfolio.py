"""Agrégation portefeuille client pour l’admin Customer 360."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import Person
from services.custody.repository import CustodyTransactionRepository
from services.exchange.models import ExchangeOrder
from services.lending.offer_models import LendingPoolProduct
from services.lending.product_surface import get_earn_positions
from services.portfolio_engine.clients.models import Client as PeClient
from services.portfolio_engine.instruments.price_bridge import get_instrument_price
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.allocations.models import TargetAllocation
from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
from services.privy_wallet.repository import PersonWalletDepositRepository
from services.privy_wallet.patrimony_merge import merge_app_crypto_positions, privy_nav_eur
from services.privy_wallet.service import _format_decimal
from services.test_clients.service import TestClientService

from .schemas import (
    CustomerPortfolioBundleItem,
    CustomerPortfolioBundlePosition,
    CustomerPortfolioCryptoItem,
    CustomerPortfolioExclusiveOfferItem,
    CustomerPortfolioResponse,
    CustomerPortfolioSummary,
    CustomerPortfolioTransactionItem,
)
from .service import _build_privy_wallets_section, _pe_client_for_person


def _source_from_row(row: dict[str, Any]) -> str:
    scope = row.get("portfolio_scope") or "direct"
    if scope == "merged":
        return "merged"
    if scope == "privy":
        return "privy"
    return "platform"


def _network_label_for_crypto_row(row: dict[str, Any]) -> str | None:
    chain_id = row.get("chain_id")
    chain_type = str(row.get("chain_type") or "").strip().lower()
    if chain_id is not None:
        try:
            cid = int(chain_id)
        except (TypeError, ValueError):
            cid = None
        if cid == 8453:
            return "Base"
        if cid == 1:
            return "Ethereum"
        if cid == 0 or chain_type == "solana":
            return "Solana"
        if cid is not None:
            return f"Chain {cid}"
    if chain_type == "solana":
        return "Solana"
    return None


def _crypto_item_from_row(row: dict[str, Any], *, force_source: str | None = None) -> CustomerPortfolioCryptoItem:
    chain_id = row.get("chain_id")
    parsed_chain_id: int | None
    try:
        parsed_chain_id = int(chain_id) if chain_id is not None else None
    except (TypeError, ValueError):
        parsed_chain_id = None
    source = force_source or _source_from_row(row)
    privy_balance = row.get("privy_balance") or ("0" if source != "privy" else row["balance"])
    privy_available = row.get("privy_available") or (
        row.get("available_balance") or "0" if source != "privy" else row["available_balance"]
    )
    return CustomerPortfolioCryptoItem(
        asset=row["asset"],
        name=row["name"],
        total_balance=row["balance"],
        total_available=row["available_balance"],
        platform_balance=row.get("platform_balance") or "0",
        platform_available=row.get("platform_available") or row.get("available_balance") or "0",
        privy_balance=privy_balance,
        privy_available=privy_available,
        source=source,  # type: ignore[arg-type]
        portfolio_scope=row.get("portfolio_scope") or ("privy" if source == "privy" else "direct"),
        chain_id=parsed_chain_id,
        network=_network_label_for_crypto_row(row),
        price_eur=row.get("price_eur"),
        estimated_value_eur=row.get("estimated_value_eur"),
    )


def get_customer_portfolio(
    db: Session,
    person_id: UUID,
    *,
    tx_limit: int = 100,
) -> CustomerPortfolioResponse | None:
    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        return None

    pe = _pe_client_for_person(db, person)
    privy = _build_privy_wallets_section(db, person.id)

    if pe is None:
        crypto_items = [
            _crypto_item_from_row(row, force_source="privy")
            for row in merge_app_crypto_positions([], db, person_id=person.id)
        ]
        return CustomerPortfolioResponse(
            person_id=person.id,
            pe_client_id=None,
            reference_currency=None,
            availability="partial",
            summary=CustomerPortfolioSummary(
                total_value_eur=_fmt_eur(Decimal(_sum_estimated_eur(crypto_items))),
                crypto_value_eur=_sum_estimated_eur(crypto_items),
                privy_value_eur=_sum_estimated_eur(crypto_items, privy_only=True),
            ),
            crypto=crypto_items,
            exclusive_offers=[],
            bundles=[],
            transactions=_list_privy_transactions(db, person.id, limit=tx_limit),
            privy_admin=privy,
        )

    svc = TestClientService()
    crypto_raw = svc.get_crypto_positions(db, client=pe)
    merged_dicts = crypto_raw.get("positions") or []
    crypto_items = [_crypto_item_from_row(row) for row in merged_dicts]

    breakdown = _safe_breakdown(db, pe.id)
    earn = get_earn_positions(db, pe.id)
    bundles = _list_bundles(db, pe)

    eo_items = _map_exclusive_offers(db, earn)
    tx_items = _list_transactions(db, person_id=person.id, pe_client_id=pe.id, limit=tx_limit)

    crypto_eur = Decimal(_sum_estimated_eur(crypto_items))
    privy_eur = Decimal(_sum_estimated_eur(crypto_items, privy_only=True))
    eo_eur = _decimal_sum(p.get("value_eur") for p in earn.get("positions") or [])
    bundle_eur = _decimal_sum(b.total_value_eur for b in bundles)

    fiat_eur = Decimal(str(breakdown.get("fiat") or 0))
    total_eur = fiat_eur + crypto_eur + eo_eur

    return CustomerPortfolioResponse(
        person_id=person.id,
        pe_client_id=pe.id,
        reference_currency=pe.reference_currency,
        availability="available",
        summary=CustomerPortfolioSummary(
            total_value_eur=_fmt_eur(total_eur),
            fiat_value_eur=_fmt_eur(fiat_eur),
            crypto_value_eur=_fmt_eur(crypto_eur),
            privy_value_eur=_fmt_eur(privy_eur),
            exclusive_offers_value_eur=_fmt_eur(eo_eur),
            bundles_value_eur=_fmt_eur(bundle_eur),
            crypto_direct_value_eur=str(breakdown.get("crypto_direct") or "0"),
            breakdown_bundles_eur=str(breakdown.get("bundles") or "0"),
            positions_count=len(crypto_items),
            exclusive_offers_count=len(eo_items),
            bundles_count=len(bundles),
            transactions_count=len(tx_items),
        ),
        crypto=crypto_items,
        exclusive_offers=eo_items,
        bundles=bundles,
        transactions=tx_items,
        privy_admin=privy,
    )


def _safe_breakdown(db: Session, pe_client_id: UUID) -> dict[str, Any]:
    try:
        from services.portfolio_engine.valuation import get_portfolio_breakdown

        return get_portfolio_breakdown(db, pe_client_id)
    except Exception:
        return {}


def _map_exclusive_offers(db: Session, earn: dict[str, Any]) -> list[CustomerPortfolioExclusiveOfferItem]:
    items: list[CustomerPortfolioExclusiveOfferItem] = []
    for pos in earn.get("positions") or []:
        product_id = pos.get("lending_pool_product_id")
        title = None
        status = None
        if product_id:
            product = db.query(LendingPoolProduct).filter(LendingPoolProduct.id == product_id).first()
            if product:
                title = product.title
                status = product.status
        items.append(
            CustomerPortfolioExclusiveOfferItem(
                pool_id=str(pos.get("pool_id") or ""),
                lending_pool_product_id=str(product_id) if product_id else None,
                project_id=pos.get("project_id"),
                title=title or f"Offre {pos.get('asset') or ''}".strip(),
                asset=str(pos.get("asset") or ""),
                status=status,
                total_supplied=str(pos.get("total_supplied") or "0"),
                earning_amount=str(pos.get("earning_amount") or "0"),
                idle_amount=str(pos.get("idle_amount") or "0"),
                accrued_interest=str(pos.get("accrued_interest") or "0"),
                value_eur=str(pos.get("value_eur") or "0"),
                apy=pos.get("apy"),
            )
        )
    return items


def _list_bundles(db: Session, pe: PeClient) -> list[CustomerPortfolioBundleItem]:
    eurusdt_rate = get_eurusdt_rate(db, strict=False)
    portfolios = (
        db.query(Portfolio)
        .filter(
            Portfolio.client_id == pe.id,
            Portfolio.portfolio_type == "bundle_portfolio",
            Portfolio.status == "active",
        )
        .all()
    )
    bundles: list[CustomerPortfolioBundleItem] = []
    for portfolio in portfolios:
        atoms = (
            db.query(PositionAtom)
            .filter(PositionAtom.portfolio_id == portfolio.id, PositionAtom.status == "open")
            .all()
        )
        total_market = Decimal("0")
        positions: list[CustomerPortfolioBundlePosition] = []
        for atom in atoms:
            instrument = atom.instrument or (
                db.query(Instrument).filter(Instrument.id == atom.instrument_id).first()
            )
            asset_obj = (
                db.query(Asset).filter(Asset.id == instrument.asset_id).first()
                if instrument
                else None
            )
            symbol = asset_obj.symbol if asset_obj else "?"
            qty = Decimal(str(atom.quantity or 0))
            market_value: str | None = None
            try:
                price_info = get_instrument_price(db, atom.instrument_id)
                price_usdt = Decimal(str(price_info["price"])) if price_info.get("price") else None
                if price_usdt is not None and qty > 0:
                    price_eur = usdt_to_eur(price_usdt, eurusdt_rate)
                    mv = (qty * price_eur).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    total_market += mv
                    market_value = f"{mv:.2f}"
            except Exception:
                pass
            positions.append(
                CustomerPortfolioBundlePosition(
                    asset=symbol,
                    quantity=_format_decimal(qty),
                    position_type=atom.position_type,
                    market_value_eur=market_value,
                )
            )
        bundles.append(
            CustomerPortfolioBundleItem(
                portfolio_id=portfolio.id,
                name=portfolio.name or "Bundle",
                status=portfolio.status,
                origin_product_id=str(portfolio.origin_product_id) if portfolio.origin_product_id else None,
                total_value_eur=f"{total_market:.2f}",
                positions_count=len([p for p in positions if p.position_type == "spot"]),
                positions=positions,
            )
        )
    bundles.sort(key=lambda b: Decimal(b.total_value_eur or "0"), reverse=True)
    return bundles


def _list_transactions(
    db: Session,
    *,
    person_id: UUID,
    pe_client_id: UUID,
    limit: int,
) -> list[CustomerPortfolioTransactionItem]:
    items: list[CustomerPortfolioTransactionItem] = []

    deposit_repo = PersonWalletDepositRepository()
    for row in deposit_repo.list_for_person(db, person_id, limit=limit):
        items.append(
            CustomerPortfolioTransactionItem(
                id=row.id,
                source="privy_deposit",
                category="crypto",
                direction=row.direction,
                asset=row.asset,
                amount=_format_decimal(row.amount),
                currency=row.asset,
                status=row.status,
                title=row.title,
                subtitle=row.subtitle,
                reference=row.tx_hash,
                created_at=row.created_at,
            )
        )

    txs, _ = CustodyTransactionRepository.list(db, client_id=pe_client_id, limit=limit)
    for tx in txs:
        items.append(
            CustomerPortfolioTransactionItem(
                id=tx.id,
                source="custody",
                category="fiat",
                direction=tx.direction,
                asset=tx.currency,
                amount=_format_decimal(tx.amount),
                currency=tx.currency,
                status=tx.status,
                title=tx.transaction_type.replace("_", " ").title(),
                subtitle=tx.transaction_kind,
                reference=tx.external_reference,
                created_at=tx.created_at,
            )
        )

    orders = (
        db.query(ExchangeOrder)
        .filter(ExchangeOrder.client_id == pe_client_id)
        .order_by(ExchangeOrder.created_at.desc())
        .limit(limit)
        .all()
    )
    for order in orders:
        items.append(
            CustomerPortfolioTransactionItem(
                id=order.id,
                source="exchange",
                category="crypto",
                direction=order.side,
                asset=order.asset,
                amount=_format_decimal(order.amount_crypto),
                currency=order.currency,
                status=order.status,
                title=f"{order.side.upper()} {order.asset}",
                subtitle=f"{_format_decimal(order.amount_fiat)} {order.currency}",
                reference=order.external_reference,
                created_at=order.created_at,
            )
        )

    items.sort(key=lambda x: x.created_at, reverse=True)
    return items[:limit]


def _list_privy_transactions(
    db: Session,
    person_id: UUID,
    *,
    limit: int,
) -> list[CustomerPortfolioTransactionItem]:
    deposit_repo = PersonWalletDepositRepository()
    items: list[CustomerPortfolioTransactionItem] = []
    for row in deposit_repo.list_for_person(db, person_id, limit=limit):
        items.append(
            CustomerPortfolioTransactionItem(
                id=row.id,
                source="privy_deposit",
                category="crypto",
                direction=row.direction,
                asset=row.asset,
                amount=_format_decimal(row.amount),
                currency=row.asset,
                status=row.status,
                title=row.title,
                subtitle=row.subtitle,
                reference=row.tx_hash,
                created_at=row.created_at,
            )
        )
    return items


def _sum_estimated_eur(
    crypto_items: list[CustomerPortfolioCryptoItem],
    *,
    privy_only: bool = False,
) -> str:
    total = Decimal("0")
    for item in crypto_items:
        if privy_only:
            privy_bal = Decimal(str(item.privy_balance or "0"))
            if privy_bal <= 0 or not item.price_eur:
                continue
            total += privy_bal * Decimal(str(item.price_eur))
            continue
        if item.estimated_value_eur:
            total += Decimal(str(item.estimated_value_eur))
    return _fmt_eur(total)


def _decimal_sum(values) -> Decimal:
    total = Decimal("0")
    for v in values:
        if v is None:
            continue
        try:
            total += Decimal(str(v))
        except Exception:
            pass
    return total


def _fmt_eur(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
