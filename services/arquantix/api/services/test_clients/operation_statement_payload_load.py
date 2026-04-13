"""
Charge un :class:`OperationStatementPayload` sans rendu PDF ni persistance de snapshot.

Usage : endpoint admin JSON debug / introspection.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from pdf.operation_statement_schema import OperationStatementPayload
from services.portfolio_engine.clients.models import Client as PeClient

from .custody_operation_statement import build_custody_operation_statement_payload
from .exchange_operation_statement import build_exchange_operation_statement_payload
from .operation_resolver import OperationResolver
from .operation_statement_errors import OperationStatementHttpError
from .operation_statement_snapshot_service import get_snapshot, payload_from_snapshot_row


def load_operation_statement_payload_for_transaction(
    db: Session,
    client: PeClient,
    transaction_id: UUID,
) -> OperationStatementPayload:
    """
    Même résolution + adapters que ``get_transaction_operation_statement_pdf``,
    sans mapper/renderer PDF et **sans** ``create_snapshot``.
    """
    ref = OperationResolver.resolve(db, client, transaction_id)
    if ref is None:
        raise OperationStatementHttpError(
            "operation_statement_not_found",
            "Relevé indisponible : transaction introuvable ou non associée à votre compte.",
        )

    snap_row = get_snapshot(db, client.id, ref)
    if snap_row is not None:
        try:
            return payload_from_snapshot_row(snap_row)
        except Exception as exc:
            raise OperationStatementHttpError(
                "operation_statement_snapshot_invalid",
                "Relevé indisponible : données de snapshot invalides.",
                status_code=500,
            ) from exc

    if ref.source_system == "custody":
        return build_custody_operation_statement_payload(
            db, client, transaction_id, resolved_ref=ref
        )
    return build_exchange_operation_statement_payload(
        db, client, transaction_id, resolved_ref=ref
    )
