"""Sleeves standalone API (Portfolio Engine — sleeve layer).

Primary sleeve endpoints are nested under /portfolios/{id}/sleeves (see portfolios/router.py).
This router exposes a minimal standalone GET for admin/debugging purposes.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from .schemas import SleeveRead
from .service import SleeveNotFoundError, SleeveService

router = APIRouter()

_service = SleeveService()


@router.get("/{sleeve_id}", response_model=SleeveRead)
def get_sleeve(
    sleeve_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        sleeve = _service.get_sleeve(db, sleeve_id)
        return SleeveRead.model_validate(sleeve)
    except SleeveNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sleeve not found")
