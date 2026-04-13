"""Lending Invest Orchestrator — Phase 2A.12 / 2A.16.

Bundle-style invest flow for Exclusive Offer Lending Products:
  1. Accept any funding asset (EUR, BTC, USDC, …)
  2. Convert to pool asset if needed (via ExchangeService.buy / swap)
  3. Supply to lending pool (via PoolLendingService.create_supply_commitment)
  4. Debit intermediate crypto balance (envelope pattern — Phase 2A.16)
  5. Create investment envelope entry for clean tracking
  6. Update current_raised on the product

Phase 2A.16 — Envelope Entry Wallet Abstraction:
  After conversion + supply, the orchestrator debits the intermediate
  crypto balance so that converted funds NEVER appear in the user's
  crypto wallet. The envelope entry records the full investment lifecycle
  (entry_asset, conversion, fees, net_allocated) for clean tracking.

Separation of responsibilities:
  - ExchangeService → conversion only (untouched)
  - PoolLendingService → supply commitment only (untouched)
  - This orchestrator → sequencing + validation + envelope tracking
"""
from __future__ import annotations

import logging
import uuid as uuid_mod
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.service import ExchangeService
from services.exchange.schemas import (
    ExchangeBuyRequest,
    SwapPreviewRequest,
    SwapRequest,
)
from services.portfolio_engine.hardening.security.context import ActorContext

from services.exchange.repository import CryptoPositionRepository
from services.portfolio_engine.positions.models import PositionAtom

from .envelope_models import InvestmentEnvelope, InvestmentEnvelopeEntry
from .offer_models import LendingPoolProduct
from .offer_service import OfferService, OfferError, OfferNotFoundError, SubscriptionError
from .pool_service import PoolLendingService

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_FIAT_CURRENCIES = {"EUR", "USD", "CHF", "GBP"}
_ROUND = Decimal("0.01")


class LendingInvestError(Exception):
    pass


class FundingAssetNotAllowedError(LendingInvestError):
    pass


class ProductNotInvestableError(LendingInvestError):
    pass


class LendingInvestOrchestrator:

    def __init__(self) -> None:
        self._exchange = ExchangeService()
        self._pool_svc = PoolLendingService()
        self._offer_svc = OfferService()

    # ── RESOLVE ENTRY CONFIG ─────────────────────────────────────

    @staticmethod
    def _resolve_entry_config(product: LendingPoolProduct) -> dict:
        pool_asset = product.asset.upper()
        entry_default = (product.entry_asset_default or pool_asset).upper()
        entry_allowed = product.entry_assets_allowed or [entry_default]
        entry_allowed = [a.upper() for a in entry_allowed]
        if entry_default not in entry_allowed:
            entry_allowed.insert(0, entry_default)
        return {
            "pool_asset": pool_asset,
            "entry_asset_default": entry_default,
            "entry_assets_allowed": entry_allowed,
        }

    @staticmethod
    def _validate_funding_asset(funding_asset: str, entry_config: dict) -> None:
        upper = funding_asset.upper()
        if upper in _FIAT_CURRENCIES:
            return
        if upper in entry_config["entry_assets_allowed"]:
            return
        raise FundingAssetNotAllowedError(
            f"Funding asset '{upper}' not allowed. "
            f"Accepted: {entry_config['entry_assets_allowed']} + fiat {sorted(_FIAT_CURRENCIES)}"
        )

    @staticmethod
    def _determine_conversion_type(funding_asset: str, pool_asset: str) -> str:
        upper = funding_asset.upper()
        if upper == pool_asset:
            return "none"
        if upper in _FIAT_CURRENCIES:
            return "buy"
        return "swap"

    # ── PREVIEW (READ-ONLY) ──────────────────────────────────────

    def preview_invest(
        self,
        db: Session,
        *,
        product_id: UUID,
        client_id: UUID,
        funding_asset: str,
        funding_amount: Decimal,
    ) -> dict:
        """Preview an investment into an exclusive offer — zero side-effects.

        Returns estimated conversion details, supply amount, and fees.
        """
        product = self._load_investable_product(db, product_id)
        entry_config = self._resolve_entry_config(product)
        pool_asset = entry_config["pool_asset"]
        funding_upper = funding_asset.upper()

        self._validate_funding_asset(funding_upper, entry_config)

        conversion_type = self._determine_conversion_type(funding_upper, pool_asset)

        if conversion_type == "none":
            return {
                "product_id": str(product_id),
                "pool_asset": pool_asset,
                "funding_asset": funding_upper,
                "funding_amount": float(funding_amount),
                "conversion_type": "none",
                "requires_conversion": False,
                "estimated_pool_asset_amount": float(funding_amount),
                "estimated_supply_amount": float(funding_amount),
                "conversion_fee": 0.0,
                "conversion_fee_asset": pool_asset,
                "entry_asset_used": pool_asset,
            }

        if conversion_type == "buy":
            preview = self._exchange.preview_buy(
                db, pool_asset, funding_amount, funding_upper,
            )
            estimated_pool_qty = Decimal(str(preview["estimated_crypto_net"]))
            fee = Decimal(str(preview["fee_amount"]))
            return {
                "product_id": str(product_id),
                "pool_asset": pool_asset,
                "funding_asset": funding_upper,
                "funding_amount": float(funding_amount),
                "conversion_type": "buy",
                "requires_conversion": True,
                "estimated_price": preview["estimated_price"],
                "estimated_crypto_gross": preview["estimated_crypto_gross"],
                "estimated_pool_asset_amount": float(estimated_pool_qty),
                "estimated_supply_amount": float(estimated_pool_qty),
                "conversion_fee": float(fee),
                "conversion_fee_asset": pool_asset,
                "entry_asset_used": pool_asset,
            }

        # swap
        swap_preview = self._exchange.preview_swap(
            db,
            SwapPreviewRequest(
                from_asset=funding_upper,
                to_asset=pool_asset,
                amount_from=funding_amount,
            ),
        )
        estimated_pool_qty = Decimal(str(swap_preview["estimated_to_amount"]))
        fee = Decimal(str(swap_preview["fee_in_reference_currency"]))
        return {
            "product_id": str(product_id),
            "pool_asset": pool_asset,
            "funding_asset": funding_upper,
            "funding_amount": float(funding_amount),
            "conversion_type": "swap",
            "requires_conversion": True,
            "estimated_reference_value_gross": swap_preview["estimated_reference_value_gross"],
            "estimated_reference_value_net": swap_preview["estimated_reference_value_net"],
            "estimated_pool_asset_amount": float(estimated_pool_qty),
            "estimated_supply_amount": float(estimated_pool_qty),
            "conversion_fee": float(fee),
            "conversion_fee_asset": "EUR",
            "from_price": swap_preview["from_price_in_ref_ccy"],
            "to_price": swap_preview["to_price_in_ref_ccy"],
            "entry_asset_used": pool_asset,
        }

    # ── INVEST (EXECUTION) ───────────────────────────────────────

    def invest_into_product(
        self,
        db: Session,
        *,
        product_id: UUID,
        client_id: UUID,
        funding_asset: str,
        funding_amount: Decimal,
    ) -> dict:
        """Execute an investment into an exclusive offer — atomic.

        Flow:
          1. Load & validate product
          2. Convert funding asset → pool asset (if needed)
          3. Supply to lending pool (create_supply_commitment)
          4. Update current_raised + auto-transition
          5. Return result
        """
        from services.compliance.eligibility_service import EligibilityService
        EligibilityService.require_eligible_by_client_id(db, client_id)

        product = self._load_investable_product(db, product_id)
        entry_config = self._resolve_entry_config(product)
        pool_asset = entry_config["pool_asset"]
        funding_upper = funding_asset.upper()

        self._validate_funding_asset(funding_upper, entry_config)

        conversion_type = self._determine_conversion_type(funding_upper, pool_asset)
        actor = ActorContext(actor_type="system", actor_id="lending_invest_orchestrator")
        ext_ref = f"lending-invest-{uuid_mod.uuid4()}"

        pool_asset_received = _ZERO
        conversion_details: dict = {}

        # Step 1: convert if needed
        if conversion_type == "none":
            pool_asset_received = funding_amount

        elif conversion_type == "buy":
            buy_result = self._exchange.buy(
                db,
                ExchangeBuyRequest(
                    client_id=client_id,
                    asset=pool_asset,
                    fiat_amount=funding_amount,
                    currency=funding_upper,
                    external_reference=ext_ref,
                ),
                actor,
            )
            pool_asset_received = Decimal(str(buy_result.get("amount_crypto", 0)))
            conversion_details = {
                "order_id": str(buy_result.get("order_id", "")),
                "price": buy_result.get("price"),
                "fee_amount": buy_result.get("fee_amount"),
            }

        elif conversion_type == "swap":
            swap_result = self._exchange.swap(
                db,
                client_id,
                SwapRequest(
                    from_asset=funding_upper,
                    to_asset=pool_asset,
                    amount_from=funding_amount,
                    external_reference=ext_ref,
                ),
                actor,
            )
            pool_asset_received = Decimal(str(swap_result.get("amount_to", 0)))
            conversion_details = {
                "swap_group_id": str(swap_result.get("swap_group_id", "")),
                "sell_order_id": str(swap_result.get("sell_order_id", "")),
                "buy_order_id": str(swap_result.get("buy_order_id", "")),
            }

        if pool_asset_received <= 0:
            raise LendingInvestError("Conversion resulted in zero pool asset — investment aborted")

        # Step 2: validate against remaining capacity
        raised = Decimal(str(product.current_raised))
        target = Decimal(str(product.target_size))
        remaining = target - raised
        supply_amount = min(pool_asset_received, remaining) if remaining > 0 else pool_asset_received

        # Step 3: supply to pool via OfferService.subscribe (validates tickets, cap, etc.)
        commitment = self._offer_svc.subscribe(
            db,
            product_id=product_id,
            lender_client_id=client_id,
            amount=supply_amount,
        )

        # Step 4 (Phase 2A.16): debit intermediate crypto balance so converted
        # funds never appear in the user's crypto wallet. Only needed when a
        # conversion happened (buy/swap) — direct USDC invest comes from the
        # user's existing wallet and should remain tracked there.
        if conversion_type != "none":
            pos = CryptoPositionRepository.get_or_create_for_update(
                db, client_id, pool_asset,
            )
            pos.balance = Decimal(str(pos.balance)) - supply_amount
            db.flush()

            # Also debit the PE direct portfolio atom. ExchangeService.buy/swap
            # writes to BOTH crypto_positions AND pe_position_atoms (via
            # sync_direct_atom). Without this second debit, /crypto-positions/direct
            # reads stale atoms and causes double-counting with Placements.
            from services.portfolio_engine.direct_overlay import (
                ensure_direct_portfolio,
                sync_direct_atom,
                _resolve_or_create_instrument as _resolve_pe_instrument,
            )
            direct_pf = ensure_direct_portfolio(db, client_id)
            pe_instr = _resolve_pe_instrument(db, pool_asset)

            existing_atom = (
                db.query(PositionAtom)
                .filter(
                    PositionAtom.portfolio_id == direct_pf.id,
                    PositionAtom.instrument_id == pe_instr.id,
                    PositionAtom.position_type == "spot",
                    PositionAtom.status == "open",
                )
                .first()
            )
            cost_delta = _ZERO
            if existing_atom and Decimal(str(existing_atom.quantity)) > 0:
                ratio = supply_amount / Decimal(str(existing_atom.quantity))
                cost_delta = (Decimal(str(existing_atom.cost_basis or 0)) * ratio).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP,
                )

            sync_direct_atom(db, direct_pf.id, pe_instr.id, -supply_amount, -cost_delta)

            logger.info(
                "Envelope debit: removed %s %s from crypto_positions.balance "
                "AND pe_position_atoms (intermediate conversion balance)",
                supply_amount, pool_asset,
            )

        # Step 5 (Phase 2A.16): create investment envelope for clean tracking
        conversion_fee = _ZERO
        fx_rate = None
        if conversion_details:
            conversion_fee = Decimal(str(conversion_details.get("fee_amount") or 0))
            conversion_fee = conversion_fee.quantize(Decimal("0.0000000001"))
            price = conversion_details.get("price")
            if price is not None:
                fx_rate = Decimal(str(price))

        envelope = InvestmentEnvelope(
            client_id=client_id,
            type="exclusive_offer",
            reference_id=product.project_id or str(product_id),
            status="active",
            metadata_={"product_id": str(product_id), "pool_id": str(product.lending_pool_id)},
        )
        db.add(envelope)
        db.flush()

        safe_details = None
        if conversion_details:
            safe_details = {
                k: (str(v) if isinstance(v, Decimal) else v)
                for k, v in conversion_details.items()
            }

        entry = InvestmentEnvelopeEntry(
            envelope_id=envelope.id,
            commitment_id=commitment.id,
            entry_asset=funding_upper,
            entry_amount=funding_amount,
            target_asset=pool_asset,
            converted_amount=pool_asset_received,
            fx_rate=fx_rate,
            conversion_type=conversion_type,
            conversion_fee=conversion_fee,
            platform_fee=_ZERO,
            net_allocated=supply_amount,
            external_reference=ext_ref,
            conversion_details=safe_details,
        )
        db.add(entry)
        db.flush()

        logger.info(
            "Lending invest: client %s invested %s %s → %s %s into product %s "
            "(commitment %s, envelope %s)",
            client_id, funding_amount, funding_upper,
            supply_amount, pool_asset, product_id, commitment.id, envelope.id,
        )

        return {
            "status": "completed",
            "product_id": str(product_id),
            "commitment_id": str(commitment.id),
            "envelope_id": str(envelope.id),
            "pool_id": str(product.lending_pool_id),
            "funding_asset": funding_upper,
            "funding_amount": float(funding_amount),
            "conversion_type": conversion_type,
            "entry_asset_used": pool_asset,
            "total_pool_asset_received": float(pool_asset_received),
            "amount_supplied": float(supply_amount),
            "conversion_fee": float(conversion_fee),
            "net_allocated": float(supply_amount),
            "conversion_details": conversion_details,
        }

    # ── PRIVATE HELPERS ──────────────────────────────────────────

    def _load_investable_product(self, db: Session, product_id: UUID) -> LendingPoolProduct:
        product = db.query(LendingPoolProduct).filter(
            LendingPoolProduct.id == product_id,
        ).first()
        if product is None:
            raise OfferNotFoundError(f"Product {product_id} not found")
        if product.status != "fundraising":
            raise ProductNotInvestableError(
                f"Product {product_id} is not investable (status={product.status})"
            )
        return product
