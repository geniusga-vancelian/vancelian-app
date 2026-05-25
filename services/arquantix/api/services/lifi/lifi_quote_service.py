"""Service quote LI.FI — validation, appel API, simplification UX."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from config.supported_swap_assets import (
    atomic_amount_to_human,
    human_amount_to_atomic,
    resolve_swap_token,
)
from services.lifi.config import QUOTE_TTL_SECONDS, swap_fee_bps
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_client import LifiClient, LifiClientError
from services.lifi.lifi_validation_service import SwapValidationError, validate_quote_request
from services.lifi.schemas import SwapQuoteResponse, SwapRouteStep
from services.lifi.signing_wallet_service import resolve_swap_signing_wallet
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.privy_wallet.repository import PersonCryptoWalletRepository

logger = logging.getLogger(__name__)


class LifiQuoteService:
    def __init__(self, *, lifi_client: LifiClient | None = None):
        self._lifi = lifi_client or LifiClient()
        self._swap_repo = PersonWalletSwapRepository()
        self._wallet_repo = PersonCryptoWalletRepository()

    def create_quote(
        self,
        db: Session,
        *,
        person_id: UUID,
        from_asset: str,
        to_asset: str,
        amount: str,
        from_chain: str,
        to_chain: str,
        slippage_bps: int | None = None,
        signing_wallet_mode: str | None = None,
        signing_wallet_address: str | None = None,
    ) -> SwapQuoteResponse:
        parsed_amount, slippage = validate_quote_request(
            from_asset=from_asset,
            to_asset=to_asset,
            amount=amount,
            from_chain=from_chain,
            to_chain=to_chain,
            slippage_bps=slippage_bps,
        )
        from_token = resolve_swap_token(from_asset, from_chain)
        to_token = resolve_swap_token(to_asset, to_chain)
        resolved_mode, from_address = resolve_swap_signing_wallet(
            db,
            person_id=person_id,
            chain_key=from_token.chain_key,
            signing_wallet_mode=signing_wallet_mode,
            signing_wallet_address=signing_wallet_address,
        )
        _, to_address = resolve_swap_signing_wallet(
            db,
            person_id=person_id,
            chain_key=to_token.chain_key,
            signing_wallet_mode=signing_wallet_mode,
            signing_wallet_address=signing_wallet_address if resolved_mode == "external_evm" else None,
        )

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=QUOTE_TTL_SECONDS)
        swap_row = self._swap_repo.create(
            db,
            person_id=person_id,
            from_asset=from_token.asset,
            to_asset=to_token.asset,
            from_chain=from_token.chain_key,
            to_chain=to_token.chain_key,
            amount_in=parsed_amount,
            slippage_bps=slippage,
            expires_at=expires_at,
        )
        self._swap_repo.append_audit(
            swap_row,
            {
                "event": "quote_requested",
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
            self._swap_repo.append_audit(swap_row, {"event": "quote_failed", "code": exc.code})
            db.commit()
            raise

        simplified = self._simplify_quote(
            lifi_quote,
            amount_in=parsed_amount,
            from_asset=from_token.asset,
            to_asset=to_token.asset,
            to_decimals=to_token.decimals,
        )

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
        self._swap_repo.append_audit(swap_row, {"event": "quote_received", "tool": swap_row.lifi_tool})
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

    def _simplify_quote(
        self,
        lifi_quote: dict[str, Any],
        *,
        amount_in: Decimal,
        from_asset: str,
        to_asset: str,
        to_decimals: int,
    ) -> dict[str, Any]:
        estimate = lifi_quote.get("estimate") or {}
        to_amount_atomic = estimate.get("toAmount") or "0"
        to_amount_min_atomic = estimate.get("toAmountMin") or to_amount_atomic
        estimated_receive = atomic_amount_to_human(to_amount_atomic, to_decimals)
        estimated_receive_min = atomic_amount_to_human(to_amount_min_atomic, to_decimals)

        network_fees = _parse_network_fees(
            estimate=estimate,
            default_asset=from_asset,
            amount_in=amount_in,
        )
        network_fee = network_fees["network_fee"]
        network_fee_asset = network_fees["network_fee_asset"]
        network_fee_usd = network_fees["network_fee_usd"]

        v_fee_bps = swap_fee_bps()
        vancelian_fee = (amount_in * Decimal(v_fee_bps) / Decimal(10_000)).quantize(Decimal("0.000001"))

        route_steps = _build_route_steps(lifi_quote, from_asset, to_asset)
        exchange_rate = None
        if amount_in > 0:
            exchange_rate = str((estimated_receive / amount_in).quantize(Decimal("0.00000001")))

        execution_duration = estimate.get("executionDuration")
        estimated_duration_seconds = int(execution_duration) if execution_duration else None

        return {
            "vancelian_fee": vancelian_fee,
            "network_fee": network_fee,
            "network_fee_asset": network_fee_asset,
            "network_fee_usd": network_fee_usd,
            "estimated_receive": estimated_receive,
            "estimated_receive_min": estimated_receive_min,
            "route_steps": route_steps,
            "exchange_rate": exchange_rate,
            "estimated_duration_seconds": estimated_duration_seconds,
        }


def _parse_network_fees(
    *,
    estimate: dict[str, Any],
    default_asset: str,
    amount_in: Decimal,
) -> dict[str, Any]:
    """Frais réseau LI.FI — priorité à ``amountUSD`` (feeCosts + gasCosts)."""
    max_sane_usd = max(Decimal("5"), amount_in * Decimal("1.5"))
    network_fee_usd = Decimal("0")

    for fee in estimate.get("feeCosts") or []:
        if not isinstance(fee, dict):
            continue
        # Frais déjà inclus dans le montant source : pas un surcoût réseau à afficher.
        if fee.get("included") is True:
            continue
        network_fee_usd += _read_lifi_amount_usd(fee, max_usd=max_sane_usd)

    for gas in estimate.get("gasCosts") or []:
        if isinstance(gas, dict):
            network_fee_usd += _read_lifi_amount_usd(gas, max_usd=max_sane_usd)

    network_fee_human = Decimal("0")
    network_fee_asset = default_asset
    if network_fee_usd <= 0:
        network_fee_human, network_fee_asset = _parse_gas_costs_human(estimate.get("gasCosts") or [])

    if network_fee_usd > 0:
        display_fee = network_fee_usd
        display_asset = "USD"
    elif network_fee_human > 0:
        display_fee = network_fee_human
        display_asset = network_fee_asset
    else:
        display_fee = Decimal("0")
        display_asset = default_asset

    return {
        "network_fee": display_fee,
        "network_fee_asset": display_asset,
        "network_fee_usd": network_fee_usd if network_fee_usd > 0 else None,
    }


def _read_lifi_amount_usd(entry: dict[str, Any], *, max_usd: Decimal) -> Decimal:
    raw = entry.get("amountUSD")
    if raw is None:
        return Decimal("0")
    try:
        value = Decimal(str(raw))
    except Exception:
        return Decimal("0")
    if value <= 0 or value > max_usd:
        return Decimal("0")
    return value


def _parse_gas_costs_human(gas_costs: list[Any]) -> tuple[Decimal, str]:
    total = Decimal("0")
    asset = "ETH"
    for gas in gas_costs:
        if not isinstance(gas, dict):
            continue
        token = gas.get("token") if isinstance(gas.get("token"), dict) else {}
        decimals = int(token.get("decimals") or 18)
        symbol = str(token.get("symbol") or "ETH").upper()
        amount_atomic = gas.get("amount")
        if amount_atomic is None:
            continue
        try:
            human = atomic_amount_to_human(amount_atomic, decimals)
        except Exception:
            continue
        if human > 0:
            total += human
            asset = symbol
    return total, asset


def _wallet_chain_type_matches(stored: str | None, expected: str) -> bool:
    """Privy stocke souvent ``evm`` ; la whitelist swap expose ``ethereum``."""
    s = (stored or "").strip().lower()
    e = (expected or "").strip().lower()
    if not s or not e:
        return False
    if s == e:
        return True
    evm_aliases = frozenset({"evm", "ethereum"})
    return s in evm_aliases and e in evm_aliases


def _build_route_steps(lifi_quote: dict[str, Any], from_asset: str, to_asset: str) -> list[SwapRouteStep]:
    steps: list[SwapRouteStep] = []
    action = lifi_quote.get("action") or {}
    from_chain = _chain_label(action.get("fromChainId"))
    to_chain = _chain_label(action.get("toChainId"))
    tool = str(lifi_quote.get("tool") or "route").lower()

    steps.append(
        SwapRouteStep(
            label=f"{from_asset} ({from_chain})",
            kind="source",
            chain=from_chain,
        )
    )
    if tool and "bridge" in tool:
        steps.append(SwapRouteStep(label="Bridge", kind="bridge", chain=to_chain))
    else:
        steps.append(SwapRouteStep(label="Swap", kind="swap", chain=from_chain))
    steps.append(
        SwapRouteStep(
            label=f"{to_asset} ({to_chain})",
            kind="destination",
            chain=to_chain,
        )
    )
    return steps


def _chain_label(chain_id: Any) -> str:
    mapping = {
        1: "Ethereum",
        42161: "Arbitrum",
        8453: "Base",
        137: "Polygon",
        "SOL": "Solana",
    }
    if chain_id in mapping:
        return mapping[chain_id]
    return str(chain_id or "unknown")


def _fmt(value: Decimal | None) -> str:
    if value is None:
        return "0"
    text = format(value.normalize(), "f")
    return text.rstrip("0").rstrip(".") or "0"


def _fmt_optional(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return _fmt(value)
