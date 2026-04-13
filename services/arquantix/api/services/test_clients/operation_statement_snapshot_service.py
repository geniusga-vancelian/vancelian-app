"""
Service snapshot pour ``OperationStatementPayload`` : hash stable, persistance, relecture.

Aucune logique métier : sérialisation / désérialisation / contrainte d’unicité uniquement.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pdf.operation_statement_schema import OperationStatementPayload

from .operation_resolver import OperationRef
from .operation_statement_snapshot_model import ClientOperationStatementSnapshot

# Incrémenter si la forme sémantique du JSON stocké change (hors évolutions de champs optionnels gérées côté parse).
OPERATION_STATEMENT_SNAPSHOT_SCHEMA_VERSION = "1"


def canonical_json_bytes(obj: Any) -> bytes:
    """JSON UTF-8 avec clés triées à tous les niveaux (stable pour hash)."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_payload_hash(payload: OperationStatementPayload) -> str:
    """SHA-256 hex du payload sérialisé de façon canonique."""
    d = payload.model_dump(mode="json")
    return hashlib.sha256(canonical_json_bytes(d)).hexdigest()


def compute_hash_from_payload_dict(d: dict) -> str:
    """Même hash que ``compute_payload_hash`` si ``d`` est le ``model_dump(mode='json')`` du payload."""
    return hashlib.sha256(canonical_json_bytes(d)).hexdigest()


def payload_to_storable_dict(payload: OperationStatementPayload) -> dict:
    """Dict JSON-compatible pour JSONB (même contenu que celui hashé)."""
    return payload.model_dump(mode="json")


def payload_from_snapshot_row(row: ClientOperationStatementSnapshot) -> OperationStatementPayload:
    return OperationStatementPayload.model_validate(row.payload_json)


def get_snapshot(
    db: Session,
    client_id: UUID,
    ref: OperationRef,
) -> ClientOperationStatementSnapshot | None:
    return (
        db.query(ClientOperationStatementSnapshot)
        .filter(
            ClientOperationStatementSnapshot.client_id == client_id,
            ClientOperationStatementSnapshot.source_system == ref.source_system,
            ClientOperationStatementSnapshot.source_id == ref.source_id,
        )
        .first()
    )


def create_snapshot(
    db: Session,
    client_id: UUID,
    ref: OperationRef,
    payload: OperationStatementPayload,
) -> ClientOperationStatementSnapshot:
    """
    Insère le snapshot (``flush`` uniquement). L’appelant doit ``commit`` la session.

    En cas de course sur le premier rendu, renvoie la ligne existante après ``IntegrityError``.
    """
    storable = payload_to_storable_dict(payload)
    digest = compute_hash_from_payload_dict(storable)

    row = ClientOperationStatementSnapshot(
        client_id=client_id,
        source_system=ref.source_system,
        source_id=ref.source_id,
        schema_version=OPERATION_STATEMENT_SNAPSHOT_SCHEMA_VERSION,
        payload_json=storable,
        content_sha256=digest,
        pdf_sha256=None,
    )
    db.add(row)
    try:
        db.flush()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        existing = get_snapshot(db, client_id, ref)
        if existing is not None:
            return existing
        raise
