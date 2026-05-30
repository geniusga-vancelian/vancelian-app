"""API interne — sync intents Morpho depuis le portal Next.js."""
from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db

from .morpho_intent_sync import (
    ensure_morpho_intent_for_vault_transaction,
    mark_morpho_intent_confirmed,
    mark_morpho_intent_failed,
    mark_morpho_intent_submitted,
    sync_morpho_vault_approve_attempt,
)

morpho_intent_internal_router = APIRouter(
    prefix="/api/internal/transaction-intents/morpho",
    tags=["transaction-intents-morpho-internal"],
)


class MorphoVaultTxPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    vault_transaction_id: str = Field(..., min_length=1, max_length=80)
    vault_address: str
    chain_id: int
    wallet_address: str
    operation: str
    idempotency_key: str
    tx_index: int = 0
    tx_hash: Optional[str] = None
    vault_status: Optional[str] = None


class MorphoReceiptPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    vault_transaction_id: str
    tx_hash: Optional[str] = None
    vault_status: str = Field(..., description="success | reverted | failed | pending")


def _verify_internal_key(x_internal_key: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("TRANSACTION_INTENTS_INTERNAL_KEY", "").strip()
    if not expected:
        return
    if not x_internal_key or x_internal_key.strip() != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")


@morpho_intent_internal_router.post("/pending")
def sync_pending(
    body: MorphoVaultTxPayload,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_internal_key),
):
    result = ensure_morpho_intent_for_vault_transaction(
        db,
        person_id=body.person_id,
        vault_transaction_id=body.vault_transaction_id,
        vault_address=body.vault_address,
        chain_id=body.chain_id,
        wallet_address=body.wallet_address,
        operation=body.operation,
        idempotency_key=body.idempotency_key,
        tx_index=body.tx_index,
        tx_hash=body.tx_hash,
        vault_status=body.vault_status,
    )
    if result:
        db.commit()
    else:
        db.rollback()
    return {"ok": True, "result": result}


@morpho_intent_internal_router.post("/receipt")
def sync_receipt(
    body: MorphoReceiptPayload,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_internal_key),
):
    status_norm = body.vault_status.strip().lower()
    if status_norm == "success":
        result = mark_morpho_intent_confirmed(
            db,
            person_id=body.person_id,
            vault_transaction_id=body.vault_transaction_id,
            tx_hash=body.tx_hash,
        )
    elif status_norm in ("reverted", "failed"):
        result = mark_morpho_intent_failed(
            db,
            person_id=body.person_id,
            vault_transaction_id=body.vault_transaction_id,
            tx_hash=body.tx_hash,
            reason=status_norm,
        )
    else:
        result = None

    if result is None:
        result = sync_morpho_vault_approve_attempt(
            db,
            person_id=body.person_id,
            vault_transaction_id=body.vault_transaction_id,
            tx_hash=body.tx_hash,
            vault_status=status_norm,
        )

    if result:
        db.commit()
    else:
        db.rollback()
    return {"ok": True, "result": result}
