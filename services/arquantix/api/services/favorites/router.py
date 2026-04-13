"""Client Favorites REST endpoints — mounted under /api/app/favorites."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.favorites.models import (
    ALLOWED_ENTITY_TYPES,
    MAX_FAVORITES_PER_TYPE,
    ClientFavorite,
)
from services.portfolio_engine.clients.models import Client as PeClient
from services.test_clients.mobile_identity import mobile_app_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/app/favorites", tags=["favorites"])


class AddFavoriteRequest(BaseModel):
    entity_type: str = Field(..., min_length=1, max_length=30)
    entity_id: str = Field(..., min_length=1, max_length=100)


def _favorite_to_response(fav: ClientFavorite) -> dict:
    return {
        "id": str(fav.id),
        "entity_type": fav.entity_type,
        "entity_id": fav.entity_id,
        "created_at": fav.created_at.isoformat() if fav.created_at else None,
    }


@router.get("")
def list_favorites(
    entity_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    q = db.query(ClientFavorite).filter(ClientFavorite.client_id == client.id)
    if entity_type:
        if entity_type not in ALLOWED_ENTITY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"entity_type must be one of: {', '.join(sorted(ALLOWED_ENTITY_TYPES))}",
            )
        q = q.filter(ClientFavorite.entity_type == entity_type)
    favorites = q.order_by(ClientFavorite.created_at.desc()).all()
    return [_favorite_to_response(f) for f in favorites]


@router.post("", status_code=status.HTTP_201_CREATED)
def add_favorite(
    body: AddFavoriteRequest,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):

    if body.entity_type not in ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"entity_type must be one of: {', '.join(sorted(ALLOWED_ENTITY_TYPES))}",
        )

    existing = (
        db.query(ClientFavorite)
        .filter(
            ClientFavorite.client_id == client.id,
            ClientFavorite.entity_type == body.entity_type,
            ClientFavorite.entity_id == body.entity_id,
        )
        .first()
    )
    if existing:
        return _favorite_to_response(existing)

    count = (
        db.query(ClientFavorite)
        .filter(
            ClientFavorite.client_id == client.id,
            ClientFavorite.entity_type == body.entity_type,
        )
        .count()
    )
    if count >= MAX_FAVORITES_PER_TYPE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Maximum {MAX_FAVORITES_PER_TYPE} favorites per type reached.",
        )

    fav = ClientFavorite(
        client_id=client.id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
    )
    db.add(fav)
    db.commit()
    db.refresh(fav)
    logger.info("Favorite added: client=%s type=%s entity=%s", client.id, body.entity_type, body.entity_id)
    return _favorite_to_response(fav)


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite_by_id(
    favorite_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    fav = (
        db.query(ClientFavorite)
        .filter(ClientFavorite.id == favorite_id, ClientFavorite.client_id == client.id)
        .first()
    )
    if not fav:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found.")
    db.delete(fav)
    db.commit()
    logger.info("Favorite removed: id=%s client=%s", favorite_id, client.id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite_by_entity(
    entity_type: str = Query(...),
    entity_id: str = Query(...),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Remove a favorite by entity_type + entity_id (alternative to DELETE by id)."""
    fav = (
        db.query(ClientFavorite)
        .filter(
            ClientFavorite.client_id == client.id,
            ClientFavorite.entity_type == entity_type,
            ClientFavorite.entity_id == entity_id,
        )
        .first()
    )
    if not fav:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite not found.")
    db.delete(fav)
    db.commit()
    logger.info("Favorite removed by entity: client=%s type=%s entity=%s", client.id, entity_type, entity_id)
