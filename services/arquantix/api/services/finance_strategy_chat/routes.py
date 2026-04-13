"""
FastAPI routes for Finance Strategy Chat
"""
from fastapi import APIRouter, HTTPException, status
import logging

from .schemas import StartRequest, StartResponse, StepRequest, StepResponse, StateResponse
from .orchestrator import start_session, step_session, get_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/finance/strategy-chat", tags=["finance-strategy-chat"])


@router.post("/start", response_model=StartResponse)
def start_chat(request: StartRequest):
    """
    Start a new strategy chat session (Phase 1 with OpenAI).
    """
    try:
        return start_session(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Failed to start strategy chat")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/step", response_model=StepResponse)
def step_chat(request: StepRequest):
    """
    Advance the strategy chat state machine.
    """
    try:
        return step_session(request)
    except ValueError as e:
        detail = str(e)
        if "Session not found" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    except Exception as e:
        logger.exception("Failed to advance strategy chat")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/state", response_model=StateResponse)
def state_chat(session_id: str):
    """
    Get current session state.
    """
    try:
        return get_state(session_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception("Failed to fetch strategy chat state")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
