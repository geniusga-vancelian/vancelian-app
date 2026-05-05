"""Router admin **read-only** pour le monitoring des conversations IA.

Surface HTTP exposée à l'espace admin web (Next.js) sous le préfixe
``/api/admin/assistance/conversations`` :

  - ``GET    /``                       → liste paginée des conversations
                                          d'un client (``client_id``
                                          ou ``person_id`` requis), avec
                                          counts pré-agrégés (msg, tools).
  - ``GET    /{conversation_id}``      → détail conversation + tous les
                                          messages ordonnés par
                                          ``turn_index``, + facts +
                                          summary + topic.
  - ``GET    /{conversation_id}/decisions`` → tous les tool calls
                                              (workflow trace) ordonnés
                                              par ``iteration``.

Garanties :

  - **Auth** : ``require_admin_or_ops()`` (rôle ``admin`` ou ``ops``).
  - **Read-only stricte** : aucun endpoint POST/PUT/DELETE ici. Les
    actions destructrices (close, replay, delete) sont volontairement
    hors scope du v1.
  - **Pas de PII supplémentaire** exposée vs ce que le client lui-même
    voit déjà (les contenus de messages sont les mêmes que ceux servis
    via `/api/assistance/conversations/...` côté Flutter).
  - **Pagination** : `limit` ∈ [1, 100], défaut 20. `offset` ≥ 0.

Cf. ``docs/arquantix/MULTI_AGENTS.md`` §10 (Admin monitoring v1, 2026-05-04).
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import (
    AssistanceAgentDecision,
    AssistanceConversation,
    AssistanceMessage,
    get_db,
)
from services.portfolio_engine.clients.models import Client as PEClient
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

logger = logging.getLogger(__name__)


admin_conversations_router = APIRouter(
    prefix="/api/admin/assistance/conversations",
    tags=["assistance-admin-conversations"],
)
_guard = require_admin_or_ops()


# ─────────────────────────────────────────────────────────────────────
# Schemas Pydantic
# ─────────────────────────────────────────────────────────────────────


class ConversationListItem(BaseModel):
    """1 ligne de la vue liste (résumé + counts pour la fiche customer)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    client_id: str
    title: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_message_at: Optional[str] = None
    last_assistant_message_at: Optional[str] = None
    summarized_until_turn: Optional[int] = None
    current_topic: Optional[dict[str, Any]] = None

    # Counts pré-agrégés (jointure window dans le query principal).
    message_count: int = 0
    tool_call_count: int = 0
    tool_error_count: int = 0


class ConversationListResponse(BaseModel):
    items: list[ConversationListItem]
    total: int
    limit: int
    offset: int

    # Aggrégats globaux pour le widget customer.
    total_messages: int = 0
    total_tool_calls: int = 0
    total_tool_errors: int = 0
    last_activity_at: Optional[str] = None


class MessageRead(BaseModel):
    """1 message dans le détail d'une conversation."""

    model_config = ConfigDict(extra="forbid")

    id: str
    turn_index: int
    role: str  # 'user' | 'assistant'
    content: str
    agent_used: Optional[str] = None
    message_type: str = "text"
    message_payload: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None


class ConversationDetailResponse(BaseModel):
    """Détail conversation + messages."""

    model_config = ConfigDict(extra="forbid")

    id: str
    client_id: str
    title: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_message_at: Optional[str] = None
    last_assistant_message_at: Optional[str] = None
    last_read_at: Optional[str] = None

    # Mémoire / contexte
    conversation_summary: Optional[str] = None
    conversation_facts: list[dict[str, Any]] = Field(default_factory=list)
    summarized_until_turn: Optional[int] = None
    summary_updated_at: Optional[str] = None
    current_topic: Optional[dict[str, Any]] = None

    messages: list[MessageRead] = Field(default_factory=list)

    # Counts pour les badges header
    message_count: int = 0
    tool_call_count: int = 0
    tool_error_count: int = 0


class AgentDecisionRead(BaseModel):
    """1 ligne du workflow trace = 1 tool call."""

    model_config = ConfigDict(extra="forbid")

    id: str
    conversation_id: str
    message_id: Optional[str] = None
    agent_id: str
    iteration: int
    tool_name: str
    autonomy_level: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_summary: Optional[dict[str, Any]] = None
    proposed_action: Optional[str] = None
    target_client_id: Optional[str] = None
    target_person_id: Optional[str] = None
    reasoning_summary: Optional[str] = None
    review_status: str
    duration_ms: Optional[int] = None
    error_code: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: Optional[str] = None


class DecisionsResponse(BaseModel):
    decisions: list[AgentDecisionRead]
    total: int


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _iso(dt: Any) -> Optional[str]:
    """Sérialise un datetime en ISO 8601 si présent, sinon None."""
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except Exception:  # noqa: BLE001
        return None


def _resolve_client_uuid(
    db: Session,
    *,
    client_id: Optional[str],
    person_id: Optional[str],
) -> UUID:
    """Résout le ``client_id`` (pe_clients.id) à partir de l'un ou
    l'autre des paramètres. Lève 400 si aucun, 404 si introuvable."""
    if not client_id and not person_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either client_id or person_id is required.",
        )

    if client_id:
        try:
            return UUID(client_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid client_id: {exc}",
            ) from exc

    # Resolve via person_id → pe_clients.person_id
    try:
        person_uuid = UUID(person_id)  # type: ignore[arg-type]
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid person_id: {exc}",
        ) from exc

    row = db.execute(
        select(PEClient.id).where(PEClient.person_id == person_uuid).limit(1)
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pe_clients row found for person_id={person_id}",
        )
    return row[0]


# ─────────────────────────────────────────────────────────────────────
# GET /  → liste paginée + counts
# ─────────────────────────────────────────────────────────────────────


@admin_conversations_router.get(
    "",
    response_model=ConversationListResponse,
    summary="Liste les conversations IA d'un client (admin monitoring).",
)
def list_conversations(
    client_id: Optional[str] = Query(
        default=None,
        description="UUID pe_clients. Soit client_id soit person_id requis.",
    ),
    person_id: Optional[str] = Query(
        default=None,
        description="UUID persons. Résolu en client_id côté serveur.",
    ),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filtre 'active' ou 'closed'. Vide = toutes.",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
) -> ConversationListResponse:
    client_uuid = _resolve_client_uuid(
        db, client_id=client_id, person_id=person_id
    )

    # Sub-queries de counts pré-agrégés via window — single round-trip.
    msg_count_subq = (
        select(
            AssistanceMessage.conversation_id,
            func.count().label("msg_count"),
        )
        .group_by(AssistanceMessage.conversation_id)
        .subquery()
    )
    tool_count_subq = (
        select(
            AssistanceAgentDecision.conversation_id,
            func.count().label("tool_count"),
            func.count(AssistanceAgentDecision.error_code).label("err_count"),
        )
        .group_by(AssistanceAgentDecision.conversation_id)
        .subquery()
    )

    base_query = (
        select(
            AssistanceConversation,
            func.coalesce(msg_count_subq.c.msg_count, 0),
            func.coalesce(tool_count_subq.c.tool_count, 0),
            func.coalesce(tool_count_subq.c.err_count, 0),
        )
        .outerjoin(
            msg_count_subq,
            msg_count_subq.c.conversation_id == AssistanceConversation.id,
        )
        .outerjoin(
            tool_count_subq,
            tool_count_subq.c.conversation_id == AssistanceConversation.id,
        )
        .where(AssistanceConversation.client_id == client_uuid)
        .order_by(
            AssistanceConversation.last_message_at.desc().nullslast(),
            AssistanceConversation.created_at.desc(),
        )
    )
    if status_filter:
        if status_filter not in ("active", "closed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="status must be 'active' or 'closed'",
            )
        base_query = base_query.where(
            AssistanceConversation.status == status_filter
        )

    # Total après application du filtre `status_filter` pour permettre
    # à la pagination de fonctionner correctement (sinon la page 1 d'un
    # filtre vide pourrait afficher `total > 0` à tort).
    count_query = (
        select(func.count())
        .select_from(AssistanceConversation)
        .where(AssistanceConversation.client_id == client_uuid)
    )
    if status_filter:
        count_query = count_query.where(
            AssistanceConversation.status == status_filter
        )
    total_count = db.execute(count_query).scalar() or 0

    rows = db.execute(base_query.limit(limit).offset(offset)).all()
    items: list[ConversationListItem] = []
    total_msg = 0
    total_tool = 0
    total_err = 0
    last_activity = None
    for conv, msg_count, tool_count, err_count in rows:
        total_msg += int(msg_count)
        total_tool += int(tool_count)
        total_err += int(err_count)
        if conv.last_message_at and (
            last_activity is None or conv.last_message_at > last_activity
        ):
            last_activity = conv.last_message_at
        items.append(
            ConversationListItem(
                id=str(conv.id),
                client_id=str(conv.client_id),
                title=conv.title,
                status=conv.status,
                created_at=_iso(conv.created_at),
                updated_at=_iso(conv.updated_at),
                last_message_at=_iso(conv.last_message_at),
                last_assistant_message_at=_iso(conv.last_assistant_message_at),
                summarized_until_turn=conv.summarized_until_turn,
                current_topic=conv.current_topic,
                message_count=int(msg_count),
                tool_call_count=int(tool_count),
                tool_error_count=int(err_count),
            )
        )

    logger.info(
        "admin_conversations.list actor=%s client=%s returned=%d total=%d",
        getattr(actor, "user_id", None),
        client_uuid,
        len(items),
        total_count,
    )
    return ConversationListResponse(
        items=items,
        total=int(total_count),
        limit=limit,
        offset=offset,
        total_messages=total_msg,
        total_tool_calls=total_tool,
        total_tool_errors=total_err,
        last_activity_at=_iso(last_activity),
    )


# ─────────────────────────────────────────────────────────────────────
# GET /{id} → détail conversation + messages
# ─────────────────────────────────────────────────────────────────────


@admin_conversations_router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Détail d'une conversation IA (messages + mémoire).",
)
def get_conversation_detail(
    conversation_id: str,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
) -> ConversationDetailResponse:
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid conversation_id: {exc}",
        ) from exc

    conv = db.get(AssistanceConversation, conv_uuid)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    messages_rows = db.execute(
        select(AssistanceMessage)
        .where(AssistanceMessage.conversation_id == conv_uuid)
        .order_by(AssistanceMessage.turn_index.asc())
    ).scalars().all()
    messages = [
        MessageRead(
            id=str(m.id),
            turn_index=m.turn_index,
            role=m.role,
            content=m.content,
            agent_used=m.agent_used,
            message_type=m.message_type,
            message_payload=m.message_payload,
            created_at=_iso(m.created_at),
        )
        for m in messages_rows
    ]

    # Counts pour le header
    tool_count_row = db.execute(
        select(
            func.count().label("total"),
            func.count(AssistanceAgentDecision.error_code).label("errors"),
        ).where(AssistanceAgentDecision.conversation_id == conv_uuid)
    ).first()
    tool_count = int(tool_count_row.total or 0) if tool_count_row else 0
    err_count = int(tool_count_row.errors or 0) if tool_count_row else 0

    facts = conv.conversation_facts or []
    if not isinstance(facts, list):
        facts = []

    logger.info(
        "admin_conversations.detail actor=%s conv=%s msgs=%d tools=%d",
        getattr(actor, "user_id", None),
        conv_uuid,
        len(messages),
        tool_count,
    )
    return ConversationDetailResponse(
        id=str(conv.id),
        client_id=str(conv.client_id),
        title=conv.title,
        status=conv.status,
        created_at=_iso(conv.created_at),
        updated_at=_iso(conv.updated_at),
        last_message_at=_iso(conv.last_message_at),
        last_assistant_message_at=_iso(conv.last_assistant_message_at),
        last_read_at=_iso(conv.last_read_at),
        conversation_summary=conv.conversation_summary,
        conversation_facts=facts,
        summarized_until_turn=conv.summarized_until_turn,
        summary_updated_at=_iso(conv.summary_updated_at),
        current_topic=conv.current_topic,
        messages=messages,
        message_count=len(messages),
        tool_call_count=tool_count,
        tool_error_count=err_count,
    )


# ─────────────────────────────────────────────────────────────────────
# GET /{id}/decisions → workflow trace (tool calls)
# ─────────────────────────────────────────────────────────────────────


@admin_conversations_router.get(
    "/{conversation_id}/decisions",
    response_model=DecisionsResponse,
    summary="Workflow trace : tous les tool calls (audit Karpathy).",
)
def get_conversation_decisions(
    conversation_id: str,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
) -> DecisionsResponse:
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid conversation_id: {exc}",
        ) from exc

    # Existence check (404 propre).
    if db.get(AssistanceConversation, conv_uuid) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found.",
        )

    rows = (
        db.execute(
            select(AssistanceAgentDecision)
            .where(AssistanceAgentDecision.conversation_id == conv_uuid)
            .order_by(
                AssistanceAgentDecision.iteration.asc(),
                AssistanceAgentDecision.created_at.asc(),
            )
        )
        .scalars()
        .all()
    )

    decisions = [
        AgentDecisionRead(
            id=str(d.id),
            conversation_id=str(d.conversation_id),
            message_id=str(d.message_id) if d.message_id else None,
            agent_id=d.agent_id,
            iteration=d.iteration,
            tool_name=d.tool_name,
            autonomy_level=d.autonomy_level,
            arguments=d.arguments_json or {},
            result_summary=d.result_summary,
            proposed_action=d.proposed_action,
            target_client_id=str(d.target_client_id) if d.target_client_id else None,
            target_person_id=str(d.target_person_id) if d.target_person_id else None,
            reasoning_summary=d.reasoning_summary,
            review_status=d.review_status,
            duration_ms=d.duration_ms,
            error_code=d.error_code,
            correlation_id=d.correlation_id,
            created_at=_iso(d.created_at),
        )
        for d in rows
    ]

    logger.info(
        "admin_conversations.decisions actor=%s conv=%s returned=%d",
        getattr(actor, "user_id", None),
        conv_uuid,
        len(decisions),
    )
    return DecisionsResponse(
        decisions=decisions,
        total=len(decisions),
    )
