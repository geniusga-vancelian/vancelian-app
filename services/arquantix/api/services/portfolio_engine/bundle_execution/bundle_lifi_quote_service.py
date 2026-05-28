"""Quote LI.FI dédiée aux bundles — whitelist ``lifi_base_config`` (pas swap portail V1)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from config.supported_swap_assets import human_amount_to_atomic
from services.lifi.config import QUOTE_TTL_SECONDS, swap_fee_bps
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_client import LifiClient, LifiClientError
from services.lifi.lifi_quote_service import LifiQuoteService, _fmt, _fmt_optional
from services.lifi.schemas import SwapQuoteResponse
from services.lifi.swap_repository import PersonWalletSwapRepository

from .bundle_lifi_wallet import resolve_bundle_lifi_signing_wallet
from .bundle_lifi_validation import (
    BundleLifiValidationError,
    validate_bundle_quote_request,
)
from .lifi_base_config import BUNDLE_LIFI_CHAIN_KEY, resolve_bundle_base_token


class BundleLifiQuoteService:
    """Quotes swap rows pour legs bundle — validation Base + CBBTC isolée du portail."""

    def __init__(
        self,
        *,
        lifi_client: LifiClient | None = None,
        inner: LifiQuoteService | None = None,
    ) -> None:
        self._inner = inner or LifiQuoteService(lifi_client=lifi_client)
        self._lifi = self._inner._lifi
        self._swap_repo = PersonWalletSwapRepository()

    def create_bundle_quote(
        self,
        db: Session,
        *,
        person_id: UUID,
        from_asset: str,
        to_asset: str,
        amount: str,
        slippage_bps: int | None = None,
    ) -> SwapQuoteResponse:
        parsed_amount, slippage = validate_bundle_quote_request(
            from_asset=from_asset,
            to_asset=to_asset,
            amount=amount,
            slippage_bps=slippage_bps,
        )
        from_token = resolve_bundle_base_token(from_asset)
        to_token = resolve_bundle_base_token(to_asset)
        chain_key = BUNDLE_LIFI_CHAIN_KEY

        resolved_mode, from_address = resolve_bundle_lifi_signing_wallet(
            db,
            person_id=person_id,
            chain_key=chain_key,
        )
        _, to_address = resolve_bundle_lifi_signing_wallet(
            db,
            person_id=person_id,
            chain_key=chain_key,
        )

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=QUOTE_TTL_SECONDS)
        swap_row = self._swap_repo.create(
            db,
            person_id=person_id,
            from_asset=from_token.asset,
            to_asset=to_token.asset,
            from_chain=chain_key,
            to_chain=chain_key,
            amount_in=parsed_amount,
            slippage_bps=slippage,
            expires_at=expires_at,
        )
        self._swap_repo.append_audit(
            swap_row,
            {
                "event": "bundle_quote_requested",
                "bundle_execution": True,
                "signing_wallet_mode": resolved_mode,
                "signing_wallet_address": from_address,
            },
        )

        atomic_amount = human_amount_to_atomic(parsed_amount, from_token.decimals)
        slippage_ratio = slippage / 10_000

        try:
            lifi_quote = self._lifi.get_quote(
                from_chain=from_token.lifi_chain_id,
                to_chain=to_token.lifi_chain_id,
                from_token=from_token.token_address,
                to_token=to_token.token_address,
                from_amount=atomic_amount,
                from_address=from_address,
                to_address=to_address,
                slippage=slippage_ratio,
                fee_bps=swap_fee_bps(),
            )
        except LifiClientError as exc:
            swap_row.status = SwapSessionStatus.FAILED.value
            swap_row.error_message = str(exc)
            self._swap_repo.append_audit(swap_row, {"event": "bundle_quote_failed", "code": exc.code})
            db.commit()
            raise BundleLifiValidationError("bundle.lifi.quote_failed", str(exc)) from exc

        simplified = self._inner._simplify_quote(
            lifi_quote,
            amount_in=parsed_amount,
            from_asset=from_token.asset,
            to_asset=to_token.asset,
            to_decimals=to_token.decimals,
        )
        if resolved_mode == "privy_embedded":
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
        self._swap_repo.append_audit(swap_row, {"event": "bundle_quote_received", "tool": swap_row.lifi_tool})
        db.commit()
        db.refresh(swap_row)

        return SwapQuoteResponse(
            swap_id=swap_row.id,
            status=swap_row.status,
            from_asset=swap_row.from_asset,
            to_asset=swap_row.to_asset,
            from_chain=swap_row.from_chain,
            to_chain=swap_row.to_chain,
            amount_in=_fmt(swap_row.amount_in),
            vancelian_fee=_fmt(swap_row.vancelian_fee),
            vancelian_fee_bps=int(swap_row.vancelian_fee_bps or swap_fee_bps()),
            network_fee=_fmt(swap_row.network_fee),
            network_fee_asset=swap_row.network_fee_asset,
            network_fee_usd=_fmt_optional(simplified.get("network_fee_usd")),
            estimated_receive=_fmt(swap_row.estimated_receive),
            estimated_receive_min=_fmt(swap_row.estimated_receive_min),
            exchange_rate=simplified.get("exchange_rate"),
            estimated_duration_seconds=simplified.get("estimated_duration_seconds"),
            route_steps=simplified["route_steps"],
            expires_at=expires_at.isoformat(),
            slippage_bps=slippage,
            signing_wallet_mode=resolved_mode,
            signing_wallet_address=from_address,
        )

    def preview_bundle_quote(
        self,
        db: Session,
        *,
        person_id: UUID,
        from_asset: str,
        to_asset: str,
        amount: str,
        slippage_bps: int | None = None,
    ) -> Decimal:
        """Read-only Li.FI quote for bundle invest preview — no swap row persisted."""
        parsed_amount, slippage = validate_bundle_quote_request(
            from_asset=from_asset,
            to_asset=to_asset,
            amount=amount,
            slippage_bps=slippage_bps,
        )
        from_token = resolve_bundle_base_token(from_asset)
        to_token = resolve_bundle_base_token(to_asset)
        chain_key = BUNDLE_LIFI_CHAIN_KEY

        _, from_address = resolve_bundle_lifi_signing_wallet(
            db,
            person_id=person_id,
            chain_key=chain_key,
        )
        _, to_address = resolve_bundle_lifi_signing_wallet(
            db,
            person_id=person_id,
            chain_key=chain_key,
        )

        atomic_amount = human_amount_to_atomic(parsed_amount, from_token.decimals)
        slippage_ratio = slippage / 10_000

        try:
            lifi_quote = self._lifi.get_quote(
                from_chain=from_token.lifi_chain_id,
                to_chain=to_token.lifi_chain_id,
                from_token=from_token.token_address,
                to_token=to_token.token_address,
                from_amount=atomic_amount,
                from_address=from_address,
                to_address=to_address,
                slippage=slippage_ratio,
                fee_bps=swap_fee_bps(),
            )
        except LifiClientError as exc:
            raise BundleLifiValidationError("bundle.lifi.quote_failed", str(exc)) from exc

        simplified = self._inner._simplify_quote(
            lifi_quote,
            amount_in=parsed_amount,
            from_asset=from_token.asset,
            to_asset=to_token.asset,
            to_decimals=to_token.decimals,
        )
        return Decimal(str(simplified["estimated_receive"]))
