"""PDF Customer 360 — proxies vers les mêmes pipelines que l’app mobile (/api/app/*)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from database import get_db
from pdf.operation_statement_schema import OperationStatementPayload
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops
from services.test_clients.debug_operation_statement_payload import build_debug_operation_statement_payload
from services.test_clients.iban_statement_payload import build_iban_statement_payload_for_client
from services.test_clients.operation_statement_errors import OperationStatementHttpError
from services.test_clients.operation_statement_payload_load import (
    load_operation_statement_payload_for_transaction,
)
from services.test_clients.router import (
    get_euro_account_statement_pdf,
    get_transaction_operation_statement_pdf,
)

from .latest_operation import find_latest_completed_operation_transaction_id
from .service import pe_client_for_person_or_raise

_logger = logging.getLogger(__name__)

router = APIRouter(tags=["customers-admin-documents"])
_guard = require_admin_or_ops()


def _month_stamp_utc() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def _render_operation_statement_pdf_response(
    payload: OperationStatementPayload,
    *,
    filename: str,
    inline: bool,
) -> Response:
    """PDF relevé d’opération — même mapper/renderer que ``/api/app/.../operation-statement.pdf``."""
    from pdf.operation_statement_mapper import operation_statement_payload_to_template_context
    from pdf.operation_statement_renderer import render_operation_statement_pdf

    try:
        ctx = operation_statement_payload_to_template_context(payload)
        pdf_bytes = render_operation_statement_pdf(ctx)
    except FileNotFoundError:
        _logger.exception("admin operation_statement: ressource template/CSS manquante")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ressource de rendu PDF manquante sur le serveur.",
        ) from None
    except (OSError, ImportError):
        _logger.exception("admin operation_statement: WeasyPrint / libs")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Génération PDF indisponible : le serveur n'a pas les bibliothèques "
                "nécessaires (WeasyPrint). En local : lancer l'API via Docker."
            ),
        ) from exc
    except Exception:
        _logger.exception("admin operation_statement: rendu PDF")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération du relevé.",
        ) from None

    disp = "inline" if inline else "attachment"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disp}; filename="{filename}"'},
    )


@router.get("/{person_id}/documents/month-statement.pdf")
def admin_customer_month_statement_pdf(
    person_id: UUID,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Relevé EUR — mois calendaire courant (UTC). Même rendu WeasyPrint que l’app, fenêtre mensuelle."""
    from pdf.iban_statement_mapper import payload_to_template_context
    from pdf.iban_statement_renderer import render_iban_statement_pdf

    client = pe_client_for_person_or_raise(db, person_id)
    now = datetime.now(timezone.utc)
    payload = build_iban_statement_payload_for_client(
        db,
        client,
        calendar_month=(now.year, now.month),
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pas de compte dépôt EUR actif pour ce client.",
        )
    try:
        ctx = payload_to_template_context(payload)
        pdf_bytes = render_iban_statement_pdf(ctx)
    except FileNotFoundError:
        _logger.exception("admin month_statement: ressource template/CSS manquante")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ressource de rendu PDF manquante sur le serveur.",
        ) from None
    except (OSError, ImportError) as exc:
        _logger.exception("admin month_statement: WeasyPrint / libs")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Génération PDF indisponible : le serveur n'a pas les bibliothèques "
                "nécessaires (WeasyPrint). En local : lancer l'API via Docker."
            ),
        ) from exc
    except Exception:
        _logger.exception("admin month_statement: rendu PDF")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération du relevé.",
        ) from None

    stamp = _month_stamp_utc()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="releve-euro-mois-{stamp}.pdf"'},
    )


@router.get("/{person_id}/documents/iban-account-statement.pdf")
def admin_customer_iban_account_statement_pdf(
    person_id: UUID,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Relevé compte EUR / IBAN — même pipeline que ``GET /api/app/euro-account/statement.pdf`` (app mobile)."""
    client = pe_client_for_person_or_raise(db, person_id)
    return get_euro_account_statement_pdf(db=db, client=client)


@router.get("/{person_id}/documents/latest-operation.json")
def admin_customer_latest_operation_statement_json(
    person_id: UUID,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Payload JSON du relevé d’opération pour la dernière transaction ``completed`` (debug / design)."""
    client = pe_client_for_person_or_raise(db, person_id)
    tid = find_latest_completed_operation_transaction_id(db, client)
    if tid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune transaction complétée trouvée pour ce client — pas de payload à exposer.",
        )
    try:
        payload = load_operation_statement_payload_for_transaction(db, client, tid)
    except OperationStatementHttpError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
            headers={"X-Vancelian-Error-Code": exc.code},
        ) from exc
    return JSONResponse(content=payload.model_dump(mode="json"))


@router.get("/{person_id}/documents/latest-operation-statement.pdf")
def admin_customer_latest_operation_statement_pdf(
    person_id: UUID,
    db: Session = Depends(get_db),
    debug_sample: bool = Query(False, description="Payload factice — design sans données réelles."),
    _actor=Depends(_guard),
):
    """PDF relevé unitaire pour la dernière opération ``completed`` (custody ou exchange)."""
    client = pe_client_for_person_or_raise(db, person_id)
    if debug_sample:
        payload = build_debug_operation_statement_payload()
        return _render_operation_statement_pdf_response(
            payload,
            filename="releve-derniere-operation-debug-sample.pdf",
            inline=True,
        )
    tid = find_latest_completed_operation_transaction_id(db, client)
    if tid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune transaction complétée trouvée pour ce client — pas de relevé d'opération à générer.",
        )
    return get_transaction_operation_statement_pdf(
        db=db,
        transaction_id=tid,
        client=client,
    )
