"""API interne — sync intents Lombard depuis le portal Next.js."""
from __future__ import annotations

import os
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db

from .lombard_intent_sync import (
    ensure_lombard_parent_intent,
    recompute_lombard_parent_intent,
    sync_lombard_step_from_ledger_receipt,
)
from .lombard_retry_linking import LombardRetryLinkError

lombard_intent_internal_router = APIRouter(
    prefix="/api/internal/transaction-intents/lombard",
    tags=["transaction-intents-lombard-internal"],
)


class LombardStepInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: str
    tx_index: int = 0
    ledger_entry_id: str = Field(..., min_length=1, max_length=80)


class LombardPreparePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    group_key: str = Field(..., min_length=8, max_length=128)
    market_or_vault: str
    wallet_address: str
    chain_id: int = 8453
    steps: List[LombardStepInput]
    logical_borrow_id: Optional[str] = Field(default=None, min_length=8, max_length=128)
    retry_of_group_key: Optional[str] = Field(default=None, min_length=8, max_length=128)
    retry_attempt_number: int = Field(default=0, ge=0, le=4)


class LombardConfirmResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ledger_entry_id: str
    tx_hash: Optional[str] = None
    ledger_status: str


class LombardConfirmPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    group_key: str
    market_or_vault: str
    results: List[LombardConfirmResult]


def _verify_internal_key(x_internal_key: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("TRANSACTION_INTENTS_INTERNAL_KEY", "").strip()
    if not expected:
        return
    if not x_internal_key or x_internal_key.strip() != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


@lombard_intent_internal_router.post("/prepare")
def sync_prepare(
    body: LombardPreparePayload,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_internal_key),
):
    try:
        result = ensure_lombard_parent_intent(
            db,
            person_id=body.person_id,
            group_key=body.group_key,
            market_or_vault=body.market_or_vault,
            wallet_address=body.wallet_address,
            chain_id=body.chain_id,
            steps=[s.model_dump() for s in body.steps],
            logical_borrow_id=body.logical_borrow_id,
            retry_of_group_key=body.retry_of_group_key,
            retry_attempt_number=body.retry_attempt_number,
        )
    except LombardRetryLinkError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result:
        db.commit()
    else:
        db.rollback()
    return {"ok": True, "result": result}


@lombard_intent_internal_router.post("/confirm")
def sync_confirm(
    body: LombardConfirmPayload,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_internal_key),
):
    last = None
    for item in body.results:
        last = sync_lombard_step_from_ledger_receipt(
            db,
            person_id=body.person_id,
            group_key=body.group_key,
            market_or_vault=body.market_or_vault,
            ledger_entry_id=item.ledger_entry_id,
            tx_hash=item.tx_hash,
            ledger_status=item.ledger_status,
        )
    result = recompute_lombard_parent_intent(
        db,
        person_id=body.person_id,
        group_key=body.group_key,
        market_or_vault=body.market_or_vault,
    ) or last
    if result:
        db.commit()
    else:
        db.rollback()
    return {"ok": True, "result": result}
