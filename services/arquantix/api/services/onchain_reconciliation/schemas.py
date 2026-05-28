"""Schémas Pydantic admin — réconciliation on-chain (Phase 5A)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DiscrepancyRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    person_id: str
    wallet_address: Optional[str] = None
    layer: str
    asset: Optional[str] = None
    discrepancy_type: str
    db_amount: Optional[str] = None
    onchain_amount: Optional[str] = None
    delta: Optional[str] = None
    severity: str
    status: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    fingerprint: str
    metadata_json: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None


class RawOnChainEventSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    chain_id: int
    tx_hash: str
    log_index: int
    wallet_address: str
    asset: str
    amount_raw: str
    block_number: Optional[int] = None
    event_type: str
    payload_json: Optional[dict[str, Any]] = None
    consumed_by_correction_id: Optional[str] = None


class CorrectionAuditRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    discrepancy_id: str
    action: str
    status: str = "preview"
    before_json: Optional[dict[str, Any]] = None
    after_json: Optional[dict[str, Any]] = None
    requested_by: Optional[str] = None
    approved_by: Optional[str] = None
    applied_by: Optional[str] = None
    rejected_by: Optional[str] = None
    reject_reason: Optional[str] = None
    requested_at: Optional[str] = None
    approved_at: Optional[str] = None
    dry_run: bool
    applied_at: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None


class AutoFixRiskRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str
    label: str
    detail: str


class OnchainProofRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chain_id: int
    tx_hash: Optional[str] = None
    log_index: Optional[int] = None
    block_number: Optional[int] = None
    explorer_tx_url: Optional[str] = None
    explorer_label: Optional[str] = None
    candidate_events: list[dict[str, Any]] = Field(default_factory=list)
    inferred_from_latest_raw_event: Optional[bool] = None


class DiscrepancyListItem(DiscrepancyRead):
    likely_sources: list[str] = Field(default_factory=list)
    likely_source_summary: Optional[str] = None
    auto_fix_risk: AutoFixRiskRead


class DiscrepancyListResponse(BaseModel):
    items: list[DiscrepancyListItem]
    total: int
    skip: int
    limit: int


class TransactionIntentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    person_id: Optional[str] = None
    wallet_address: Optional[str] = None
    chain_id: Optional[int] = None
    product_type: str
    operation_type: str
    status: str
    tx_hash: Optional[str] = None
    raw_onchain_event_id: Optional[str] = None
    linked_table: Optional[str] = None
    linked_id: Optional[str] = None
    linked_reference_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class IntentListResponse(BaseModel):
    items: list[TransactionIntentSummary]
    total: int
    skip: int
    limit: int


class IntentHealthProductSummary(BaseModel):
    product_type: str
    total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    stale: int = 0
    without_raw_onchain_event: int = 0
    submitted_too_old: int = 0
    confirmed_without_ledger: int = 0
    success_rate: Optional[float] = None
    partial_rate: Optional[float] = None


class IntentStalePreview(BaseModel):
    intent_id: str
    person_id: str
    product_type: str
    status: str
    age_minutes: float
    ttl_minutes: int
    severity: str
    discrepancy_type: str


class IntentTopAnomaly(BaseModel):
    discrepancy_type: str
    count: int


class IntentHealthResponse(BaseModel):
    generated_at: str
    global_summary: dict[str, Any] = Field(
        validation_alias="global",
        serialization_alias="global",
    )
    by_product: list[IntentHealthProductSummary]
    stale_preview: list[IntentStalePreview] = Field(default_factory=list)
    top_anomalies: list[IntentTopAnomaly] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class IntentStaleReconcileResponse(BaseModel):
    dry_run: bool
    stale_detected: int
    discrepancies_written: int
    stale_items: list[dict[str, Any]] = Field(default_factory=list)


class DefiJobRunSummary(BaseModel):
    id: str
    job_name: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    summary_json: Optional[dict[str, Any]] = None
    error_json: Optional[dict[str, Any]] = None


class DefiJobRunListResponse(BaseModel):
    items: list[DefiJobRunSummary]
    total: int
    skip: int
    limit: int


class DiscrepancyDetailResponse(BaseModel):
    discrepancy: DiscrepancyRead
    likely_sources: list[str] = Field(default_factory=list)
    auto_fix_risk: AutoFixRiskRead
    onchain_proof: OnchainProofRead
    raw_onchain_event: Optional[RawOnChainEventSummary] = None
    transaction_intent: Optional[TransactionIntentSummary] = None
    corrections: list[CorrectionAuditRead] = Field(default_factory=list)


class StatusChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: Optional[str] = Field(default=None, max_length=2000)


class ResolveManuallyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str = Field(..., min_length=1, max_length=4000)
    resolution_code: Optional[str] = Field(default=None, max_length=64)
    metadata_json: Optional[dict[str, Any]] = None


class PreviewCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Optional[str] = Field(
        default=None,
        description="Action explicite ; sinon déduite du discrepancy_type.",
    )


class CorrectionPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    before_json: dict[str, Any]
    after_json: dict[str, Any]
    risk_level: str
    requires_second_approval: bool
    allowed_to_apply: bool = False
    correction_id: Optional[str] = None
    dry_run: bool = True


class RequestCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., min_length=1, max_length=64)
    raw_onchain_event_id: Optional[UUID] = None
    deposit_id: Optional[UUID] = Field(
        default=None,
        description="Requis pour link_raw_event_to_existing_ledger_entry.",
    )


class RejectCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Optional[str] = Field(default=None, max_length=2000)


class CorrectionApplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correction_id: str
    discrepancy: DiscrepancyRead
    apply_result: dict[str, Any]
