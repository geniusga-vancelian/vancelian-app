"""Comparaison quote Review vs quote fraîche (swap LI.FI)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SwapQuoteFreshnessResult:
    acceptable: bool
    delta_bps: int
    review_receive: Decimal
    fresh_receive: Decimal
    slippage_bps: int


def _dec(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        d = Decimal(str(value))
        return d if d > 0 else None
    except Exception:
        return None


def compare_receive_against_review(
    *,
    review_estimated_receive: str | Decimal,
    fresh_estimated_receive: str | Decimal,
    slippage_bps: int,
) -> SwapQuoteFreshnessResult:
    """True si la quote fraîche reste dans la bande slippage par rapport au Review."""
    review = _dec(review_estimated_receive)
    fresh = _dec(fresh_estimated_receive)
    slip = max(1, min(100, int(slippage_bps)))

    if review is None or fresh is None:
        return SwapQuoteFreshnessResult(
            acceptable=True,
            delta_bps=0,
            review_receive=review or Decimal("0"),
            fresh_receive=fresh or Decimal("0"),
            slippage_bps=slip,
        )

    if fresh >= review:
        delta_bps = 0
    else:
        shortfall = review - fresh
        delta_bps = int((shortfall / review * Decimal(10_000)).to_integral_value())

    min_acceptable = review * (Decimal(1) - Decimal(slip) / Decimal(10_000))
    acceptable = fresh >= min_acceptable

    return SwapQuoteFreshnessResult(
        acceptable=acceptable,
        delta_bps=delta_bps,
        review_receive=review,
        fresh_receive=fresh,
        slippage_bps=slip,
    )
