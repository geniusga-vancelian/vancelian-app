"""Schémas / DTOs onchain_transaction_attempts (Phase 2)."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttemptCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    chain_id: int
    protocol: str
    operation_type: str
    step_type: str
    idempotency_key: str
    step_index: int = 0
    group_key: Optional[str] = None
    intent_id: Optional[UUID] = None
    parent_intent_id: Optional[UUID] = None
    person_crypto_wallet_id: Optional[UUID] = None
    wallet_address: Optional[str] = None
    asset_in: Optional[str] = None
    asset_out: Optional[str] = None
    amount_in: Optional[str] = None
    amount_out_expected: Optional[str] = None
    linked_table: Optional[str] = None
    linked_id: Optional[UUID] = None
    linked_reference_id: Optional[str] = None
    metadata_patch: Optional[dict[str, Any]] = None
    raw_request_json: Optional[dict[str, Any]] = None
    raw_submission_json: Optional[dict[str, Any]] = None


class AttemptTransitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tx_hash: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    log_index: Optional[int] = None
    block_number: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    amount_out_actual: Optional[str] = None
    metadata_patch: Optional[dict[str, Any]] = None
    raw_submission_json: Optional[dict[str, Any]] = None
    raw_receipt_json: Optional[dict[str, Any]] = None
    raw_revert_json: Optional[dict[str, Any]] = None


class AttemptRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_id: UUID
    intent_id: Optional[UUID] = None
    chain_id: int
    protocol: str
    operation_type: str
    step_type: str
    step_index: int
    group_key: Optional[str] = None
    idempotency_key: str
    status: str
    tx_hash: Optional[str] = None
    linked_table: Optional[str] = None
    linked_id: Optional[UUID] = None
    linked_reference_id: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
