"""Router admin **read-only** — Cognitive Bot v4, Lot 7 (Client Discovery).

Surface HTTP exposée à l'espace admin sous le préfixe
``/api/admin/assistance/client-discovery`` :

  * ``GET /persons/{person_id}`` — état COURANT des projets discovery
    et des paramètres flottants pour une personne donnée. Permet à
    l'admin de visualiser ce que le bot « sait » des projets clients
    (achat maison, retraite, vacances, …) et des paramètres adossés
    (horizon, montant initial, apport récurrent, appétit risque, …).

⚠ État courant uniquement (pas de snapshot historique par tour). Pour
voir ce que le bot a vu **au tour N**, lire le champ
``assistance_agent_decisions.arguments_json.client_discovery_block``
(Lot 7 V1.2, exposé via le diagramme de synthèse cognitive).

Garanties :

  * **Auth** : ``require_admin_or_ops()``.
  * **Read-only stricte** : pas de POST/PUT/DELETE.
  * **Pas de PII supplémentaire** : retourne ce que le bot lui-même a
    en mémoire (déjà visible côté Flutter via les agents).

Cf. ``docs/arquantix/CLIENT_DISCOVERY.md`` (Lot 7).
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import (
    AssistanceClientDiscoveryProject,
    AssistanceFloatingParameter,
    get_db,
)
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import (
    require_admin_or_ops,
)

logger = logging.getLogger(__name__)


admin_client_discovery_router = APIRouter(
    prefix="/api/admin/assistance/client-discovery",
    tags=["assistance-admin-client-discovery"],
)
_guard = require_admin_or_ops()


# ─────────────────────────────────────────────────────────────────────
# Schemas Pydantic
# ─────────────────────────────────────────────────────────────────────


class DiscoveryProjectRead(BaseModel):
    """1 projet client découvert + paramètres adossés."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    status: str  # active | paused | completed | abandoned
    confidence: Optional[float] = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    conversation_id_source: Optional[str] = None
    created_at_turn: Optional[int] = None
    last_touched_at_turn: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FloatingParameterRead(BaseModel):
    """1 paramètre flottant (en attente d'attribution à un projet)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    parameter_kind: str
    parameter_value: dict[str, Any] = Field(default_factory=dict)
    status: str  # pending_attribution | attributed | discarded
    attributed_project_id: Optional[str] = None
    conversation_id: str
    created_at_turn: Optional[int] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None


class ClientDiscoveryStateResponse(BaseModel):
    """Snapshot **courant** (pas historique) du discovery pour une
    personne. À considérer comme "ce que le bot sait aujourd'hui"."""

    model_config = ConfigDict(extra="forbid")

    person_id: str
    projects: list[DiscoveryProjectRead] = Field(default_factory=list)
    floating_parameters: list[FloatingParameterRead] = Field(
        default_factory=list
    )

    project_count_active: int = 0
    project_count_total: int = 0
    floating_count_pending: int = 0


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except Exception:  # noqa: BLE001
        return None


def _project_to_read(p: AssistanceClientDiscoveryProject) -> DiscoveryProjectRead:
    return DiscoveryProjectRead(
        id=str(p.id),
        label=str(p.label),
        status=str(p.status),
        confidence=float(p.confidence) if p.confidence is not None else None,
        parameters=dict(p.parameters or {}),
        notes=p.notes,
        conversation_id_source=str(p.conversation_id_source)
        if p.conversation_id_source
        else None,
        created_at_turn=p.created_at_turn,
        last_touched_at_turn=p.last_touched_at_turn,
        created_at=_iso(p.created_at),
        updated_at=_iso(p.updated_at),
    )


def _floating_to_read(
    f: AssistanceFloatingParameter,
) -> FloatingParameterRead:
    return FloatingParameterRead(
        id=str(f.id),
        parameter_kind=str(f.parameter_kind),
        parameter_value=dict(f.parameter_value or {}),
        status=str(f.status),
        attributed_project_id=str(f.attributed_project_id)
        if f.attributed_project_id
        else None,
        conversation_id=str(f.conversation_id),
        created_at_turn=f.created_at_turn,
        created_at=_iso(f.created_at),
        resolved_at=_iso(f.resolved_at),
    )


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────


@admin_client_discovery_router.get(
    "/persons/{person_id}",
    response_model=ClientDiscoveryStateResponse,
    summary="Snapshot courant des projets discovery + paramètres flottants",
)
def get_person_client_discovery(
    person_id: str,
    db: Session = Depends(get_db),
    _: ActorContext = Depends(_guard),
) -> ClientDiscoveryStateResponse:
    """Retourne l'état courant du discovery pour une personne.

    On ne filtre pas les projets ``paused`` / ``completed`` car
    l'admin a souvent besoin de les voir pour comprendre l'historique
    (un projet « achat maison paused » qui réapparaît est une info
    utile au monitoring).
    """
    try:
        person_uuid = UUID(person_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid person_id",
        ) from exc

    projects_stmt = (
        select(AssistanceClientDiscoveryProject)
        .where(AssistanceClientDiscoveryProject.person_id == person_uuid)
        .order_by(
            # Active en haut (status='active'), puis les autres.
            (AssistanceClientDiscoveryProject.status != "active").asc(),
            AssistanceClientDiscoveryProject.last_touched_at_turn.desc().nullslast(),
            AssistanceClientDiscoveryProject.updated_at.desc(),
        )
    )
    projects = list(db.execute(projects_stmt).scalars().all())

    floating_stmt = (
        select(AssistanceFloatingParameter)
        .where(AssistanceFloatingParameter.person_id == person_uuid)
        .order_by(
            (AssistanceFloatingParameter.status != "pending_attribution").asc(),
            AssistanceFloatingParameter.created_at.desc(),
        )
        .limit(50)
    )
    floating = list(db.execute(floating_stmt).scalars().all())

    project_reads = [_project_to_read(p) for p in projects]
    floating_reads = [_floating_to_read(f) for f in floating]

    return ClientDiscoveryStateResponse(
        person_id=str(person_uuid),
        projects=project_reads,
        floating_parameters=floating_reads,
        project_count_active=sum(1 for p in projects if p.status == "active"),
        project_count_total=len(projects),
        floating_count_pending=sum(
            1 for f in floating if f.status == "pending_attribution"
        ),
    )
