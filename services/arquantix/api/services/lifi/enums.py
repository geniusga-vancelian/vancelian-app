"""Enums swap LI.FI."""
from __future__ import annotations

from enum import Enum


class SwapSessionStatus(str, Enum):
    PENDING = "PENDING"
    QUOTE_RECEIVED = "QUOTE_RECEIVED"
    AWAITING_SIGNATURE = "AWAITING_SIGNATURE"
    # État durable posé AVANT la diffusion on-chain de la signature serveur (D1).
    # Garantit qu'un retry après crash entre broadcast et commit ne re-signe jamais
    # aveuglément : on rejoue via la clé d'idempotence Privy, jamais une nouvelle tx.
    BROADCASTING = "BROADCASTING"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
