"""Portfolios API endpoints (Portfolio Engine — portfolio layer).

Includes nested endpoints:
- GET/POST /portfolios/{id}/sleeves
- GET /portfolios/{id}/positions
- GET /portfolios/{id}/strategies
- GET /portfolios/{id}/target-allocations
- GET /portfolios/{id}/rebalance-policy
- GET /portfolios/{id}/risk-policy
- GET /portfolios/{id}/rebalance-preview/latest
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from .schemas import PortfolioCreate, PortfolioListResponse, PortfolioRead, PortfolioUpdate
from .service import OriginProductReferenceError, PortfolioNotFoundError, PortfolioService
from ..hardening.authorization.dependencies import require_portfolio_access
from ..hardening.authorization.service import AuthorizationService
from ..hardening.security.context import ActorContext
from ..hardening.security.dependencies import get_actor_context
from ..sleeves.schemas import SleeveCreate, SleeveListResponse, SleeveRead
from ..sleeves.service import PortfolioReferenceError, SleeveService
from ..positions.schemas import PositionListResponse, PositionRead
from ..positions.service import PositionAtomService
from ..strategies.schemas import InstanceListResponse, InstanceRead
from ..strategies.service import StrategyInstanceService
from ..allocations.schemas import AllocationListResponse, AllocationRead
from ..allocations.service import TargetAllocationService
from ..rebalancing.schemas import RebalancePolicyRead
from ..rebalancing.service import RebalancePolicyService
from ..risk.schemas import RiskPolicyRead
from ..risk.service import RiskPolicyService
from ..rebalance_preview.schemas import PreviewRead
from ..rebalance_preview.service import RebalancePreviewService

router = APIRouter()

_portfolio_service = PortfolioService()
_sleeve_service = SleeveService()
_position_service = PositionAtomService()
_strategy_instance_service = StrategyInstanceService()
_allocation_service = TargetAllocationService()
_rebalance_service = RebalancePolicyService()
_risk_service = RiskPolicyService()
_preview_service = RebalancePreviewService()
_authz = AuthorizationService()


# ── Portfolio CRUD ──────────────────────────────────────────

@router.get("", response_model=PortfolioListResponse)
def list_portfolios(
    client_id: Optional[UUID] = Query(None, description="Filter by client_id"),
    portfolio_type: Optional[str] = Query(None, description="Filter by portfolio_type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor_context),
):
    scoped_client_id = client_id
    scoped_client_ids = None

    if actor.has_role("client"):
        scoped_client_id = UUID(actor.actor_id) if actor.actor_id else None
    elif actor.has_role("advisor") and actor.actor_id:
        assigned = _authz.get_accessible_client_ids_for_advisor(db, actor.actor_id)
        if client_id and client_id in assigned:
            scoped_client_id = client_id
        else:
            scoped_client_ids = assigned
            scoped_client_id = None

    items, total = _portfolio_service.list_portfolios(
        db, client_id=scoped_client_id, client_ids=scoped_client_ids,
        portfolio_type=portfolio_type, status=status_filter,
        skip=skip, limit=limit,
    )
    return PortfolioListResponse(
        data=[PortfolioRead.model_validate(p) for p in items],
        total=total,
    )


@router.post("", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    payload: PortfolioCreate,
    db: Session = Depends(get_db),
):
    # TODO: wire auth (get_current_user dependency)
    try:
        portfolio = _portfolio_service.create_portfolio(db, payload)
        db.commit()
        db.refresh(portfolio)
        return PortfolioRead.model_validate(portfolio)
    except OriginProductReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{portfolio_id}", response_model=PortfolioRead)
def get_portfolio(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    return PortfolioRead.model_validate(_portfolio)


@router.patch("/{portfolio_id}", response_model=PortfolioRead)
def update_portfolio(
    portfolio_id: UUID,
    payload: PortfolioUpdate,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        portfolio = _portfolio_service.update_portfolio(db, portfolio_id, payload)
        db.commit()
        db.refresh(portfolio)
        return PortfolioRead.model_validate(portfolio)
    except PortfolioNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    except OriginProductReferenceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ── Nested sleeve endpoints ─────────────────────────────────

@router.get("/{portfolio_id}/sleeves", response_model=SleeveListResponse)
def list_portfolio_sleeves(
    portfolio_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    items, total = _sleeve_service.list_sleeves(db, portfolio_id, skip=skip, limit=limit)
    return SleeveListResponse(
        data=[SleeveRead.model_validate(s) for s in items],
        total=total,
    )


@router.post("/{portfolio_id}/sleeves", response_model=SleeveRead, status_code=status.HTTP_201_CREATED)
def create_portfolio_sleeve(
    portfolio_id: UUID,
    payload: SleeveCreate,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    try:
        sleeve = _sleeve_service.create_sleeve(db, portfolio_id, payload)
        db.commit()
        db.refresh(sleeve)
        return SleeveRead.model_validate(sleeve)
    except PortfolioReferenceError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")


# ── Nested position endpoints ────────────────────────────────

@router.get("/{portfolio_id}/positions", response_model=PositionListResponse)
def list_portfolio_positions(
    portfolio_id: UUID,
    position_type: Optional[str] = Query(None, description="Filter by position_type"),
    position_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    items, total = _position_service.list_positions(
        db, portfolio_id=portfolio_id, position_type=position_type,
        status=position_status, skip=skip, limit=limit,
    )
    return PositionListResponse(
        items=[PositionRead.model_validate(p) for p in items],
        total=total,
    )


# ── Nested strategy endpoints ────────────────────────────────

@router.get("/{portfolio_id}/strategies", response_model=InstanceListResponse)
def list_portfolio_strategies(
    portfolio_id: UUID,
    instance_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    items, total = _strategy_instance_service.list_instances_by_portfolio(
        db, portfolio_id, status=instance_status, skip=skip, limit=limit,
    )
    return InstanceListResponse(
        items=[InstanceRead.model_validate(i) for i in items],
        total=total,
    )


# ── Nested target allocation endpoints ───────────────────────

@router.get("/{portfolio_id}/target-allocations", response_model=AllocationListResponse)
def list_portfolio_target_allocations(
    portfolio_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    items, total = _allocation_service.list_allocations_by_portfolio(
        db, portfolio_id, skip=skip, limit=limit,
    )
    return AllocationListResponse(
        items=[AllocationRead.model_validate(a) for a in items],
        total=total,
    )


# ── Nested rebalance policy endpoint ────────────────────────

@router.get("/{portfolio_id}/rebalance-policy", response_model=Optional[RebalancePolicyRead])
def get_portfolio_rebalance_policy(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    policy = _rebalance_service.get_policy_by_portfolio(db, portfolio_id)
    if policy is None:
        return None
    return RebalancePolicyRead.model_validate(policy)


# ── Nested risk policy endpoint ──────────────────────────────

@router.get("/{portfolio_id}/risk-policy", response_model=Optional[RiskPolicyRead])
def get_portfolio_risk_policy(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    policy = _risk_service.get_policy_by_portfolio(db, portfolio_id)
    if policy is None:
        return None
    return RiskPolicyRead.model_validate(policy)


# ── Nested rebalance preview endpoint ────────────────────────

@router.get("/{portfolio_id}/rebalance-preview/latest", response_model=Optional[PreviewRead])
def get_portfolio_latest_preview(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    _portfolio=Depends(require_portfolio_access),
):
    preview = _preview_service.get_latest_by_portfolio(db, portfolio_id)
    if preview is None:
        return None
    return PreviewRead.model_validate(preview)
