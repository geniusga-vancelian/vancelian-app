"""Exceptions S4 product locks."""
from __future__ import annotations

from uuid import UUID


class ProductLockConflict(Exception):
    """Un lock actif existe déjà pour ce slot, porté par un autre intent."""

    def __init__(
        self,
        *,
        lock_key: str,
        existing_intent_id: UUID,
        requested_intent_id: UUID,
    ) -> None:
        self.lock_key = lock_key
        self.existing_intent_id = existing_intent_id
        self.requested_intent_id = requested_intent_id
        super().__init__(
            f"product lock conflict on {lock_key}: "
            f"held by intent {existing_intent_id}, requested {requested_intent_id}"
        )
