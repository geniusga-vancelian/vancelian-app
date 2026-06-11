"""Trade primitive — execute_trade(wallet_from, wallet_to, instruments, qty)."""
from .execute_trade import attach_trade_wallet_context, execute_trade, read_trade_wallet_context
from .submit import submit_signed_trade
from .types import TradeExecutionResult, TradeRequest, TradeReviewSnapshot

__all__ = [
    "TradeRequest",
    "TradeReviewSnapshot",
    "TradeExecutionResult",
    "execute_trade",
    "attach_trade_wallet_context",
    "read_trade_wallet_context",
    "submit_signed_trade",
]
