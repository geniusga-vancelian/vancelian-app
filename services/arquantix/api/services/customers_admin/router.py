"""Routes admin — Customer 360."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

from .customer_documents import router as customer_documents_router
from .lifecycle import set_person_login_frozen, wipe_customer_data
from .schemas import CustomerAdminDetail, CustomerAdminListResponse, CustomerCustodySearchResponse, CustomerPortfolioResponse
from .service import get_customer_detail, list_customers, search_customers_for_custody
from .portfolio import get_customer_portfolio

router = APIRouter(prefix="/api/admin/customers", tags=["customers-admin"])
router.include_router(customer_documents_router)
_guard = require_admin_or_ops()


@router.get("/search", response_model=CustomerCustodySearchResponse)
def search_customers_for_custody_endpoint(
    q: str = Query(
        "",
        min_length=0,
        description="Recherche : téléphone, person_id (UUID), nom — pas d'e-mail PE / technique.",
    ),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Sélection custody : ``phone_e164`` + ``person_id`` ; e-mail optionnel (collecté filtré uniquement)."""
    return search_customers_for_custody(db, q=q, limit=limit)


@router.get("", response_model=CustomerAdminListResponse)
def list_customers_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    q: Optional[str] = Query(None, description="Recherche texte (profil, email, téléphone, nom)"),
    sort: str = Query(
        "-updated_at",
        description="Tri : created_at, -created_at, updated_at, -updated_at",
    ),
    country: Optional[str] = Query(None, description="Filtre pays résidence (code ISO, ex. FR)"),
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Liste les personnes ayant démarré l’inscription avec au moins un signal téléphone."""
    if sort.lstrip("-") not in ("created_at", "updated_at"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort must be created_at, -created_at, updated_at, or -updated_at",
        )
    return list_customers(
        db,
        page=page,
        page_size=page_size,
        q=q,
        sort=sort,
        country=country,
    )


@router.get("/{person_id}", response_model=CustomerAdminDetail)
def get_customer_endpoint(
    person_id: UUID,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Fiche Customer 360 (person_id = identité Person)."""
    detail = get_customer_detail(db, person_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found or not eligible for this dashboard",
        )
    return detail


@router.get("/{person_id}/portfolio", response_model=CustomerPortfolioResponse)
def get_customer_portfolio_endpoint(
    person_id: UUID,
    tx_limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Vue portefeuille unifiée : crypto (PE + Privy), offres exclusives, bundles, transactions."""
    portfolio = get_customer_portfolio(db, person_id, tx_limit=tx_limit)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    return portfolio


@router.post("/{person_id}/freeze")
def freeze_customer_login(
    person_id: UUID,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Interdit toute nouvelle authentification (JWT, OTP, passkeys) pour cette personne."""
    ok = set_person_login_frozen(db, person_id, frozen=True)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )
    return {"ok": True, "login_frozen": True}


@router.post("/{person_id}/unfreeze")
def unfreeze_customer_login(
    person_id: UUID,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Réactive les connexions pour cette personne."""
    ok = set_person_login_frozen(db, person_id, frozen=False)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found",
        )
    return {"ok": True, "login_frozen": False}


@router.delete("/{person_id}")
def delete_customer_permanently(
    person_id: UUID,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Supprime l’identité, l’activité PE liée et les comptes d’auth (admin/app) associés."""
    return wipe_customer_data(db, person_id)
