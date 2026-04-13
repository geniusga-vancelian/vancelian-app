"""Transaction status state machine for the Custody module.

Defines valid transitions and enforces them at the service layer.
No status change should bypass this module.
"""
from .enums import TransactionStatus

_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    TransactionStatus.PENDING.value: frozenset({
        TransactionStatus.PROCESSING.value,
        TransactionStatus.FAILED.value,
    }),
    TransactionStatus.PROCESSING.value: frozenset({
        TransactionStatus.COMPLETED.value,
        TransactionStatus.FAILED.value,
    }),
    TransactionStatus.COMPLETED.value: frozenset({
        TransactionStatus.REVERSED.value,
    }),
    TransactionStatus.FAILED.value: frozenset(),
    TransactionStatus.REVERSED.value: frozenset(),
}


class InvalidTransitionError(Exception):
    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid transaction status transition: {current} -> {target}"
        )


def validate_transition(current: str, target: str) -> None:
    """Raise InvalidTransitionError if current -> target is not allowed."""
    allowed = _VALID_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidTransitionError(current, target)


def is_terminal(status: str) -> bool:
    """Return True if the status has no valid outgoing transitions."""
    return len(_VALID_TRANSITIONS.get(status, frozenset())) == 0
