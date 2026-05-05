"""Cognitive Bot v4 — Lot 7 — repo persistance discovery projet client.

Source de vérité : tables ``assistance_client_discovery_projects`` et
``assistance_floating_parameters`` (migration 153). Cf. doc
``CLIENT_DISCOVERY.md``.

──────────────────────────────────────────────────────────────────────
Responsabilités
──────────────────────────────────────────────────────────────────────

  * Lookup cross-conversation par ``person_id`` (un même projet
    « achat maison » peut traverser plusieurs conversations).
  * Création/maj projet avec **merge non destructif** des paramètres
    (cf. ``ClientProjectParameters.merge``).
  * Lifecycle : ``set_status_*`` (active/paused/completed/abandoned).
  * Floating parameters : add, list pending, attribute, discard.

Toutes les fonctions sont **best-effort** : une exception SQLAlchemy ne
remonte jamais — on log et on retourne ``None`` ou ``[]``. Le runtime
agentique ne doit pas planter à cause d'un bug discovery.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from database import (
    AssistanceClientDiscoveryProject,
    AssistanceFloatingParameter,
)
from services.assistance.agents.client_discovery import (
    FLOATING_STATUS_ATTRIBUTED,
    FLOATING_STATUS_DISCARDED,
    FLOATING_STATUS_PENDING,
    MAX_ACTIVE_PROJECTS_PER_PERSON,
    PROJECT_STATUS_ABANDONED,
    PROJECT_STATUS_ACTIVE,
    PROJECT_STATUS_COMPLETED,
    PROJECT_STATUS_PAUSED,
    ClientProject,
    ClientProjectParameters,
    FloatingParameter,
    KNOWN_PARAMETER_KINDS,
    KNOWN_PROJECT_LABELS,
    KNOWN_PROJECT_STATUSES,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Lookup
# ─────────────────────────────────────────────────────────────────────


def list_active_projects_for_person(
    db: Session,
    person_id: Any,
    *,
    limit: int = 5,
) -> list[ClientProject]:
    """Retourne les projets ``active`` de la personne, triés par
    ``last_touched_at_turn DESC NULLS LAST`` puis ``updated_at DESC``.
    """
    pid = _coerce_uuid(person_id)
    if pid is None:
        return []
    try:
        q = (
            db.query(AssistanceClientDiscoveryProject)
            .filter(
                AssistanceClientDiscoveryProject.person_id == pid,
                AssistanceClientDiscoveryProject.status
                == PROJECT_STATUS_ACTIVE,
            )
            .order_by(
                AssistanceClientDiscoveryProject.last_touched_at_turn.desc().nullslast(),
                AssistanceClientDiscoveryProject.updated_at.desc(),
            )
            .limit(int(max(1, limit)))
        )
        rows = q.all()
        return [_row_to_project(r) for r in rows]
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo.list_active_projects_for_person_failed person=%s",
            person_id,
        )
        return []


def get_active_project_by_label(
    db: Session,
    person_id: Any,
    label: str,
) -> Optional[ClientProject]:
    """Retourne le projet ``active`` de la personne avec ce label
    canonique, ou ``None``.
    """
    pid = _coerce_uuid(person_id)
    if pid is None or not label:
        return None
    try:
        row = (
            db.query(AssistanceClientDiscoveryProject)
            .filter(
                AssistanceClientDiscoveryProject.person_id == pid,
                AssistanceClientDiscoveryProject.label == label,
                AssistanceClientDiscoveryProject.status
                == PROJECT_STATUS_ACTIVE,
            )
            .order_by(desc(AssistanceClientDiscoveryProject.updated_at))
            .first()
        )
        return _row_to_project(row) if row else None
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo.get_active_project_by_label_failed "
            "person=%s label=%s",
            person_id,
            label,
        )
        return None


# ─────────────────────────────────────────────────────────────────────
# Upsert (merge non destructif)
# ─────────────────────────────────────────────────────────────────────


def upsert_project(
    db: Session,
    *,
    person_id: Any,
    conversation_id: Any,
    project: ClientProject,
    current_turn: Optional[int] = None,
) -> Optional[ClientProject]:
    """Crée ou met à jour un projet pour la personne.

    Match sur ``(person_id, label, status='active')``. Si trouvé :
    merge non destructif des paramètres (les valeurs ``None`` du nouveau
    n'écrasent pas les anciennes), confidence = max(old, new),
    ``last_touched_at_turn`` mis à jour.

    Si non trouvé : insert. Si > ``MAX_ACTIVE_PROJECTS_PER_PERSON`` projets
    actifs déjà, on **pause** le plus ancien (``status=paused``) avant
    insert.
    """
    pid = _coerce_uuid(person_id)
    cid = _coerce_uuid(conversation_id)
    if pid is None:
        logger.warning(
            "discovery_repo.upsert_project invalid person_id=%r — skip",
            person_id,
        )
        return None
    if not project.label or project.label not in KNOWN_PROJECT_LABELS:
        logger.warning(
            "discovery_repo.upsert_project unknown label=%r — skip",
            project.label,
        )
        return None

    now = datetime.now(timezone.utc)
    try:
        with db.begin_nested():
            existing = (
                db.query(AssistanceClientDiscoveryProject)
                .filter(
                    AssistanceClientDiscoveryProject.person_id == pid,
                    AssistanceClientDiscoveryProject.label == project.label,
                    AssistanceClientDiscoveryProject.status
                    == PROJECT_STATUS_ACTIVE,
                )
                .order_by(
                    desc(AssistanceClientDiscoveryProject.updated_at)
                )
                .first()
            )

            if existing:
                old_params = ClientProjectParameters.from_dict(
                    existing.parameters or {}
                )
                merged = old_params.merge(project.parameters)
                existing.parameters = merged.to_dict()
                existing.confidence = max(
                    float(existing.confidence or 0.0),
                    float(project.confidence or 0.0),
                )
                if current_turn is not None:
                    existing.last_touched_at_turn = current_turn
                existing.updated_at = now
                if project.notes:
                    existing.notes = (project.notes or "")[:500]
                db.add(existing)
                # le commit est délégué au caller
                return _row_to_project(existing)

            # Pas trouvé → cap des projets actifs avant insert
            _cap_active_projects(db, pid, now=now)

            row = AssistanceClientDiscoveryProject(
                person_id=pid,
                conversation_id_source=cid,
                label=project.label,
                status=project.status or PROJECT_STATUS_ACTIVE,
                confidence=float(project.confidence or 0.7),
                parameters=project.parameters.to_dict(),
                created_at_turn=current_turn,
                last_touched_at_turn=current_turn,
                notes=(project.notes or None),
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            db.flush()
            return _row_to_project(row)
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo.upsert_project_failed person=%s label=%s",
            person_id,
            project.label,
        )
        return None


def _cap_active_projects(
    db: Session,
    person_uuid: UUID,
    *,
    now: datetime,
) -> None:
    """Si plus de ``MAX_ACTIVE_PROJECTS_PER_PERSON`` projets actifs,
    pause le plus ancien.
    """
    try:
        active = (
            db.query(AssistanceClientDiscoveryProject)
            .filter(
                AssistanceClientDiscoveryProject.person_id == person_uuid,
                AssistanceClientDiscoveryProject.status
                == PROJECT_STATUS_ACTIVE,
            )
            .order_by(
                AssistanceClientDiscoveryProject.last_touched_at_turn.asc().nullsfirst(),
                AssistanceClientDiscoveryProject.updated_at.asc(),
            )
            .all()
        )
        if len(active) >= MAX_ACTIVE_PROJECTS_PER_PERSON:
            to_pause = active[: len(active) - MAX_ACTIVE_PROJECTS_PER_PERSON + 1]
            for r in to_pause:
                r.status = PROJECT_STATUS_PAUSED
                r.updated_at = now
                db.add(r)
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo._cap_active_projects_failed person=%s",
            person_uuid,
        )


# ─────────────────────────────────────────────────────────────────────
# Lifecycle
# ─────────────────────────────────────────────────────────────────────


def set_project_status(
    db: Session,
    *,
    project_id: Any,
    status: str,
) -> bool:
    """Transition de status. Retourne ``True`` si appliqué."""
    if status not in KNOWN_PROJECT_STATUSES:
        return False
    pid = _coerce_uuid(project_id)
    if pid is None:
        return False
    try:
        with db.begin_nested():
            row = (
                db.query(AssistanceClientDiscoveryProject)
                .filter(AssistanceClientDiscoveryProject.id == pid)
                .first()
            )
            if not row:
                return False
            row.status = status
            row.updated_at = datetime.now(timezone.utc)
            db.add(row)
        return True
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo.set_project_status_failed id=%s status=%s",
            project_id,
            status,
        )
        return False


def pause_other_active_projects(
    db: Session,
    *,
    person_id: Any,
    keep_label: Optional[str],
) -> int:
    """Pause tous les projets actifs de la personne SAUF celui de label
    ``keep_label``. Utile sur signal de switch (« parlons d'autre chose »).
    Retourne le nombre de projets pausés.
    """
    pid = _coerce_uuid(person_id)
    if pid is None:
        return 0
    try:
        with db.begin_nested():
            q = db.query(AssistanceClientDiscoveryProject).filter(
                AssistanceClientDiscoveryProject.person_id == pid,
                AssistanceClientDiscoveryProject.status
                == PROJECT_STATUS_ACTIVE,
            )
            if keep_label:
                q = q.filter(
                    AssistanceClientDiscoveryProject.label != keep_label
                )
            rows = q.all()
            now = datetime.now(timezone.utc)
            for r in rows:
                r.status = PROJECT_STATUS_PAUSED
                r.updated_at = now
                db.add(r)
            return len(rows)
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo.pause_other_active_projects_failed person=%s",
            person_id,
        )
        return 0


# ─────────────────────────────────────────────────────────────────────
# Floating parameters
# ─────────────────────────────────────────────────────────────────────


def add_floating_parameter(
    db: Session,
    *,
    conversation_id: Any,
    person_id: Any,
    floating: FloatingParameter,
    current_turn: Optional[int] = None,
) -> Optional[str]:
    """Persiste un FloatingParameter en status pending_attribution.

    Retourne l'id stringifié, ``None`` en cas d'échec.
    """
    cid = _coerce_uuid(conversation_id)
    pid = _coerce_uuid(person_id)
    if cid is None or pid is None:
        return None
    if floating.parameter_kind not in KNOWN_PARAMETER_KINDS:
        return None

    try:
        with db.begin_nested():
            row = AssistanceFloatingParameter(
                conversation_id=cid,
                person_id=pid,
                parameter_kind=floating.parameter_kind,
                parameter_value=dict(floating.parameter_value or {}),
                status=FLOATING_STATUS_PENDING,
                created_at_turn=current_turn,
            )
            db.add(row)
            db.flush()
            return str(row.id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo.add_floating_parameter_failed kind=%s",
            floating.parameter_kind,
        )
        return None


def list_pending_floating_parameters(
    db: Session,
    conversation_id: Any,
    *,
    limit: int = 10,
) -> list[FloatingParameter]:
    cid = _coerce_uuid(conversation_id)
    if cid is None:
        return []
    try:
        rows = (
            db.query(AssistanceFloatingParameter)
            .filter(
                AssistanceFloatingParameter.conversation_id == cid,
                AssistanceFloatingParameter.status
                == FLOATING_STATUS_PENDING,
            )
            .order_by(desc(AssistanceFloatingParameter.created_at))
            .limit(int(max(1, limit)))
            .all()
        )
        return [
            FloatingParameter(
                id=str(r.id),
                parameter_kind=r.parameter_kind,
                parameter_value=dict(r.parameter_value or {}),
                created_at_turn=r.created_at_turn,
                status=r.status,
            )
            for r in rows
        ]
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo.list_pending_floating_parameters_failed conv=%s",
            conversation_id,
        )
        return []


def attribute_floating_to_project(
    db: Session,
    *,
    floating_id: Any,
    project_id: Any,
) -> bool:
    fid = _coerce_uuid(floating_id)
    pid = _coerce_uuid(project_id)
    if fid is None or pid is None:
        return False
    try:
        with db.begin_nested():
            row = (
                db.query(AssistanceFloatingParameter)
                .filter(AssistanceFloatingParameter.id == fid)
                .first()
            )
            if not row or row.status != FLOATING_STATUS_PENDING:
                return False
            row.attributed_project_id = pid
            row.status = FLOATING_STATUS_ATTRIBUTED
            row.resolved_at = datetime.now(timezone.utc)
            db.add(row)
        return True
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo.attribute_floating_to_project_failed "
            "fid=%s pid=%s",
            floating_id,
            project_id,
        )
        return False


def discard_floating(db: Session, floating_id: Any) -> bool:
    fid = _coerce_uuid(floating_id)
    if fid is None:
        return False
    try:
        with db.begin_nested():
            row = (
                db.query(AssistanceFloatingParameter)
                .filter(AssistanceFloatingParameter.id == fid)
                .first()
            )
            if not row or row.status != FLOATING_STATUS_PENDING:
                return False
            row.status = FLOATING_STATUS_DISCARDED
            row.resolved_at = datetime.now(timezone.utc)
            db.add(row)
        return True
    except Exception:  # noqa: BLE001
        logger.exception(
            "discovery_repo.discard_floating_failed fid=%s", floating_id
        )
        return False


# ─────────────────────────────────────────────────────────────────────
# Helpers internes
# ─────────────────────────────────────────────────────────────────────


def _coerce_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _row_to_project(
    row: Optional[AssistanceClientDiscoveryProject],
) -> ClientProject:
    if row is None:
        # Caller guaranteed non-None, mais on est défensif
        return ClientProject(label="autre")
    return ClientProject(
        id=str(row.id),
        label=row.label,
        status=row.status,
        confidence=float(row.confidence or 0.0),
        parameters=ClientProjectParameters.from_dict(row.parameters or {}),
        created_at_turn=row.created_at_turn,
        last_touched_at_turn=row.last_touched_at_turn,
        notes=row.notes,
    )
