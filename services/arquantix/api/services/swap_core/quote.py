"""ADR 007 S2 — Swap Core quote (standalone + bundle policies)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from config.supported_swap_assets import human_amount_to_atomic, resolve_swap_token
from services.lifi.config import QUOTE_TTL_SECONDS, swap_fee_bps
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_client import LifiClient, LifiClientError
from services.lifi.lifi_quote_service import LifiQuoteService
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.orchestrator_allowlist import lifi_intent_orchestrator_enabled_for_person
from services.lifi.schemas import SwapQuoteResponse
from services.lifi.signing_wallet_service import resolve_swap_signing_wallet
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.portfolio_engine.bundle_execution.bundle_lifi_validation import (
    BundleLifiValidationError,
    validate_bundle_exit_quote_request,
    validate_bundle_quote_request,
)
from services.portfolio_engine.bundle_execution.bundle_lifi_wallet import (
    resolve_bundle_lifi_signing_wallet,
)
from services.portfolio_engine.bundle_execution.lifi_base_config import (
    BUNDLE_LIFI_CHAIN_KEY,
    resolve_bundle_base_token,
)
from services.swap_core.context import QuotePolicy, ResolvedQuoteTokens, SwapQuoteContext

logger = logging.getLogger(__name__)


class SwapCore:
    """Rail LI.FI unifié — quote uniquement (ADR 007)."""

    def __init__(
        self,
        *,
        lifi_client: LifiClient | None = None,
        quote_helpers: LifiQuoteService | None = None,
    ) -> None:
        self._helpers = quote_helpers or LifiQuoteService(lifi_client=lifi_client)
        self._lifi = self._helpers._lifi
        self._swap_repo = PersonWalletSwapRepository()

    def quote(self, db: Session, ctx: SwapQuoteContext) -> SwapQuoteResponse:
        resolved = self._resolve_tokens(db, ctx)
        signing = self._resolve_signing_wallet(db, ctx, resolved)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=QUOTE_TTL_SECONDS)
        swap_row = self._bootstrap_swap_row(
            db,
            ctx=ctx,
            resolved=resolved,
            expires_at=expires_at,
            signing_mode=signing["mode"],
            from_address=signing["from_address"],
        )

        atomic_amount = human_amount_to_atomic(resolved.parsed_amount, resolved.from_decimals)
        slippage_ratio = resolved.slippage_bps / 10_000

        try:
            lifi_quote = self._lifi.get_quote(
                from_chain=resolved.from_lifi_chain_id,
                to_chain=resolved.to_lifi_chain_id,
                from_token=resolved.from_token_address,
                to_token=resolved.to_token_address,
                from_amount=atomic_amount,
                from_address=signing["from_address"],
                to_address=signing["to_address"],
                slippage=slippage_ratio,
                fee_bps=swap_fee_bps(),
            )
        except LifiClientError as exc:
            self._mark_quote_failed(db, swap_row, exc=exc, ctx=ctx)
            db.commit()
            if ctx.policy == QuotePolicy.BUNDLE_BASE:
                raise BundleLifiValidationError("bundle.lifi.quote_failed", str(exc)) from exc
            raise

        simplified = self._helpers._simplify_quote(
            lifi_quote,
            amount_in=resolved.parsed_amount,
            from_asset=resolved.from_asset,
            to_asset=resolved.to_asset,
            to_decimals=resolved.to_decimals,
        )
        if signing["mode"] == "privy_embedded":
            simplified["network_fee"] = Decimal("0")
            simplified["network_fee_asset"] = None
            simplified["network_fee_usd"] = None

        swap_row.status = SwapSessionStatus.QUOTE_RECEIVED.value
        swap_row.lifi_quote_id = str(lifi_quote.get("id") or "")
        swap_row.lifi_tool = str(lifi_quote.get("tool") or "")
        swap_row.lifi_quote_raw = lifi_quote
        swap_row.transaction_request = lifi_quote.get("transactionRequest")
        swap_row.vancelian_fee = simplified["vancelian_fee"]
        swap_row.vancelian_fee_bps = swap_fee_bps()
        swap_row.network_fee = simplified["network_fee"]
        swap_row.network_fee_asset = simplified["network_fee_asset"]
        swap_row.estimated_receive = simplified["estimated_receive"]
        swap_row.estimated_receive_min = simplified["estimated_receive_min"]
        swap_row.route_steps = [step.model_dump() for step in simplified["route_steps"]]

        received_event = (
            "bundle_quote_received" if ctx.policy == QuotePolicy.BUNDLE_BASE else "quote_received"
        )
        self._swap_repo.append_audit(swap_row, {"event": received_event, "tool": swap_row.lifi_tool})

        if ctx.policy == QuotePolicy.STANDALONE:
            from services.lifi.swap_trace_service import log_swap_trace
            from services.transaction_intents.lifi_intent_sync import sync_lifi_swap_intent

            if not lifi_intent_orchestrator_enabled_for_person(db, ctx.person_id):
                sync_lifi_swap_intent(db, swap_row)
            log_swap_trace(
                db,
                swap_row,
                event="quote_received",
                status=swap_row.status,
                source="swap_core.quote",
            )

        db.commit()
        db.refresh(swap_row)

        return self._helpers._build_quote_response(
            swap_row,
            simplified=simplified,
            expires_at=expires_at,
            slippage_bps=resolved.slippage_bps,
            signing_wallet_mode=signing["mode"],
            signing_wallet_address=signing["from_address"],
        )

    def _resolve_tokens(self, db: Session, ctx: SwapQuoteContext) -> ResolvedQuoteTokens:
        if ctx.policy == QuotePolicy.BUNDLE_BASE:
            leg_action = ctx.leg_action
            if leg_action in ("withdraw_sell", "rebalance_sell"):
                parsed_amount, slippage = validate_bundle_exit_quote_request(
                    from_asset=ctx.from_asset,
                    to_asset=ctx.to_asset,
                    amount=ctx.amount,
                    slippage_bps=ctx.slippage_bps,
                )
            else:
                parsed_amount, slippage = validate_bundle_quote_request(
                    from_asset=ctx.from_asset,
                    to_asset=ctx.to_asset,
                    amount=ctx.amount,
                    slippage_bps=ctx.slippage_bps,
                )
            from_token = resolve_bundle_base_token(ctx.from_asset)
            to_token = resolve_bundle_base_token(ctx.to_asset)
            chain_key = BUNDLE_LIFI_CHAIN_KEY
            return ResolvedQuoteTokens(
                from_asset=from_token.asset,
                to_asset=to_token.asset,
                from_chain=chain_key,
                to_chain=chain_key,
                from_lifi_chain_id=from_token.lifi_chain_id,
                to_lifi_chain_id=to_token.lifi_chain_id,
                from_token_address=from_token.token_address,
                to_token_address=to_token.token_address,
                from_decimals=from_token.decimals,
                to_decimals=to_token.decimals,
                parsed_amount=parsed_amount,
                slippage_bps=slippage,
            )

        from services.lifi.lifi_validation_service import validate_quote_request

        from_chain = ctx.from_chain or ""
        to_chain = ctx.to_chain or from_chain
        parsed_amount, slippage = validate_quote_request(
            from_asset=ctx.from_asset,
            to_asset=ctx.to_asset,
            amount=ctx.amount,
            from_chain=from_chain,
            to_chain=to_chain,
            slippage_bps=ctx.slippage_bps,
        )
        from_token = resolve_swap_token(ctx.from_asset, from_chain)
        to_token = resolve_swap_token(ctx.to_asset, to_chain)
        return ResolvedQuoteTokens(
            from_asset=from_token.asset,
            to_asset=to_token.asset,
            from_chain=from_token.chain_key,
            to_chain=to_token.chain_key,
            from_lifi_chain_id=from_token.lifi_chain_id,
            to_lifi_chain_id=to_token.lifi_chain_id,
            from_token_address=from_token.token_address,
            to_token_address=to_token.token_address,
            from_decimals=from_token.decimals,
            to_decimals=to_token.decimals,
            parsed_amount=parsed_amount,
            slippage_bps=slippage,
        )

    def _resolve_signing_wallet(
        self,
        db: Session,
        ctx: SwapQuoteContext,
        resolved: ResolvedQuoteTokens,
    ) -> dict[str, str | None]:
        if ctx.policy == QuotePolicy.BUNDLE_BASE:
            mode, from_address = resolve_bundle_lifi_signing_wallet(
                db,
                person_id=ctx.person_id,
                chain_key=resolved.from_chain,
            )
            _, to_address = resolve_bundle_lifi_signing_wallet(
                db,
                person_id=ctx.person_id,
                chain_key=resolved.to_chain,
            )
            return {"mode": mode, "from_address": from_address, "to_address": to_address}

        resolved_mode, from_address = resolve_swap_signing_wallet(
            db,
            person_id=ctx.person_id,
            chain_key=resolved.from_chain,
            signing_wallet_mode=ctx.signing_wallet_mode,
            signing_wallet_address=ctx.signing_wallet_address,
        )
        _, to_address = resolve_swap_signing_wallet(
            db,
            person_id=ctx.person_id,
            chain_key=resolved.to_chain,
            signing_wallet_mode=ctx.signing_wallet_mode,
            signing_wallet_address=(
                ctx.signing_wallet_address if resolved_mode == "external_evm" else None
            ),
        )
        return {"mode": resolved_mode, "from_address": from_address, "to_address": to_address}

    def _bootstrap_swap_row(
        self,
        db: Session,
        *,
        ctx: SwapQuoteContext,
        resolved: ResolvedQuoteTokens,
        expires_at: datetime,
        signing_mode: str | None,
        from_address: str | None,
    ):
        swap_row = self._swap_repo.create(
            db,
            person_id=ctx.person_id,
            from_asset=resolved.from_asset,
            to_asset=resolved.to_asset,
            from_chain=resolved.from_chain,
            to_chain=resolved.to_chain,
            amount_in=resolved.parsed_amount,
            slippage_bps=resolved.slippage_bps,
            expires_at=expires_at,
        )
        requested_event = (
            "bundle_quote_requested" if ctx.policy == QuotePolicy.BUNDLE_BASE else "quote_requested"
        )
        audit: dict[str, Any] = {
            "event": requested_event,
            "signing_wallet_mode": signing_mode,
            "signing_wallet_address": from_address,
        }
        if ctx.policy == QuotePolicy.BUNDLE_BASE:
            audit["bundle_execution"] = True
        audit.update(ctx.extra_audit)
        self._swap_repo.append_audit(swap_row, audit)

        if ctx.policy == QuotePolicy.STANDALONE:
            if lifi_intent_orchestrator_enabled_for_person(db, ctx.person_id):
                return swap_row
            from services.transaction_intents.lifi_intent_sync import on_swap_created

            on_swap_created(db, swap_row)
        return swap_row

    def _mark_quote_failed(
        self,
        db: Session,
        swap_row,
        *,
        exc: LifiClientError,
        ctx: SwapQuoteContext,
    ) -> None:
        failed_event = (
            "bundle_quote_failed" if ctx.policy == QuotePolicy.BUNDLE_BASE else "quote_failed"
        )
        self._helpers._mark_quote_failed(db, swap_row, exc=exc, event=failed_event)
