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
    validate_bundle_exit_quote_request,
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
        leg_action: str | None = None,
    ) -> SwapQuoteResponse:
        from services.swap_core import QuotePolicy, SwapCore, SwapQuoteContext

        return SwapCore(quote_helpers=self._inner).quote(
            db,
            SwapQuoteContext(
                person_id=person_id,
                from_asset=from_asset,
                to_asset=to_asset,
                amount=amount,
                policy=QuotePolicy.BUNDLE_BASE,
                slippage_bps=slippage_bps,
                leg_action=leg_action,
            ),
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
