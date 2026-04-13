"""
Routes for Bot IA épargne: session, conversation/turn, profile.
Public endpoints - no JWT required, uses session_id only.
"""
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database import get_db, ChatbotSession, ChatbotProfile, ChatbotConversationTurn
from core.env import is_dev_mode
from services.chatbot_epargne.schemas import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    TurnRequest,
    TurnResponse,
    ProfileResponse,
)
from services.chatbot_epargne.orchestrator import process_turn
from services.chatbot_epargne.security import (
    validate_session,
    create_session_with_security,
)

router = APIRouter(prefix="/api/chatbot", tags=["chatbot-epargne"])


def get_llm_client() -> Optional[object]:
    """Dependency: LLM client if OPENAI_API_KEY is set, else None. Overridable in tests with FakeLLMClient."""
    if os.getenv("OPENAI_API_KEY"):
        from services.chatbot_epargne.ai.llm import LLMClient
        return LLMClient()
    return None


@router.post("/session", response_model=SessionResponse)
def create_session(
    body: Optional[SessionCreate] = Body(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """POST /session -> { session_id } - Public endpoint, no JWT required"""
    try:
        sess = create_session_with_security(
            db=db,
            request=request,
            user_id=(body.user_id if body else None) or None,
        )
        return SessionResponse(session_id=str(sess.id))
    except Exception as e:
        db.rollback()
        # If error is due to missing columns, provide helpful message
        error_msg = str(e)
        missing_cols = []
        if "conversation_summary" in error_msg or "conversation_facts" in error_msg or "last_next_question_id" in error_msg:
            missing_cols.append("013")
        if "expires_at" in error_msg or "ip_hash" in error_msg or "user_agent_hash" in error_msg:
            missing_cols.append("014")
        
        if missing_cols:
            migrations_needed = ", ".join(missing_cols)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database migration required. Please apply migrations: {migrations_needed}. Use: POST /api/admin/migrations/apply/{missing_cols[-1]}"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {error_msg}"
        )


@router.get("/session/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """GET /session/{id} -> meta + last turns - Public endpoint, no JWT required"""
    # Validate session (checks expiration, rate limit)
    sess = validate_session(db, session_id, request)
    turns = (
        db.query(ChatbotConversationTurn)
        .filter(ChatbotConversationTurn.session_id == sid)
        .order_by(ChatbotConversationTurn.turn_index.desc())
        .limit(20)
        .all()
    )
    last_turns = [
        {"role": t.role, "content": (t.content or "")[:500], "turn_index": t.turn_index}
        for t in reversed(turns)
    ]
    return SessionDetailResponse(
        session_id=session_id,
        meta={"created_at": sess.created_at.isoformat() if sess.created_at else None},
        last_turns=last_turns,
    )


@router.post("/conversation/turn", response_model=TurnResponse)
def conversation_turn(
    body: TurnRequest,
    request: Request,
    db: Session = Depends(get_db),
    llm_client: Optional[object] = Depends(get_llm_client),
):
    """POST /conversation/turn : { session_id, message } -> { reply, ... } - Public endpoint, no JWT required"""
    # Validate session (checks expiration, rate limit)
    validate_session(db, body.session_id, request)
    
    try:
        out = process_turn(db, body.session_id, body.message, llm_client=llm_client)
        return TurnResponse(
            reply=out.get("reply", ""),
            profile_diff=out.get("profile_diff"),
            state=out.get("state", "coach"),
            disclaimers_shown=out.get("disclaimers_shown") or [],
            proposal_preview=out.get("proposal_preview"),
            completeness_score=out.get("completeness_score"),
            project_summary=out.get("project_summary"),
            conversation_summary=out.get("conversation_summary"),
            conversation_facts=out.get("conversation_facts") or [],
            profile=out.get("profile"),
            next_question_id=out.get("next_question_id"),
            goal_phase=out.get("goal_phase"),
            goal_locked=out.get("goal_locked"),
            goal_confidence=out.get("goal_confidence"),
            goal_attempts=out.get("goal_attempts"),
        )
    except ValueError as e:
        if "Session not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        detail = f"Internal error: {str(e)}" if is_dev_mode() else "Internal Server Error"
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """GET /profile?session_id= -> InvestorProfile - Public endpoint, no JWT required"""
    # Validate session (checks expiration, rate limit)
    validate_session(db, session_id, request)
    
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id")
    row = (
        db.query(ChatbotProfile)
        .filter(ChatbotProfile.session_id == sid)
        .order_by(ChatbotProfile.version.desc())
        .first()
    )
    if not row:
        return ProfileResponse(profile={}, completeness_score=0.0, missing_fields=[])
    payload = row.payload or {}
    miss = payload.get("missing_fields")
    if isinstance(miss, list):
        missing_fields = [str(m) for m in miss]
    else:
        missing_fields = []
    comp = float(row.completeness_score or 0)
    return ProfileResponse(profile=payload, completeness_score=comp, missing_fields=missing_fields)
