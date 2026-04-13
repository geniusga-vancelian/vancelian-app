"""
Security guards for public chatbot endpoints: session validation, expiration, rate limiting.
No JWT required - uses session_id only.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database import ChatbotSession, ChatbotConversationTurn

# Rate limiting config
RATE_LIMIT_TURNS_PER_HOUR = 50  # Max turns per session per hour
RATE_LIMIT_TURNS_WINDOW = timedelta(hours=1)
SESSION_EXPIRY_HOURS = 24  # Sessions expire after 24 hours


def hash_ip(ip: str) -> str:
    """Hash IP address (SHA256) - no PII stored"""
    return hashlib.sha256(ip.encode()).hexdigest()


def hash_user_agent(ua: str) -> str:
    """Hash user agent (SHA256) - no PII stored"""
    return hashlib.sha256(ua.encode()).hexdigest()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check X-Forwarded-For header (proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP in chain
        return forwarded.split(",")[0].strip()
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    # Fallback to direct client
    if request.client:
        return request.client.host
    return "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent from request"""
    return request.headers.get("User-Agent", "unknown")


def validate_session(
    db: Session,
    session_id: str,
    request: Request,
) -> ChatbotSession:
    """
    Validate session: exists, not expired, rate limit OK.
    Raises HTTPException if invalid.
    Returns ChatbotSession if valid.
    """
    try:
        from uuid import UUID
        sid = UUID(session_id) if isinstance(session_id, str) else session_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format"
        )
    
    # Load session
    sess = db.query(ChatbotSession).filter(ChatbotSession.id == sid).first()
    if not sess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Check expiration (gracefully handle if column doesn't exist yet)
    now = datetime.now(timezone.utc)
    try:
        expires_at = sess.expires_at
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < now:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expired"
                )
    except AttributeError:
        # Column doesn't exist yet (migration 014 not applied) - skip expiration check
        pass
    
    # Check rate limit (turns in last hour)
    one_hour_ago = now - RATE_LIMIT_TURNS_WINDOW
    recent_turns = (
        db.query(ChatbotConversationTurn)
        .filter(
            and_(
                ChatbotConversationTurn.session_id == sid,
                ChatbotConversationTurn.created_at >= one_hour_ago
            )
        )
        .count()
    )
    
    if recent_turns >= RATE_LIMIT_TURNS_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {RATE_LIMIT_TURNS_PER_HOUR} turns per hour"
        )
    
    # Optional: verify IP/user_agent match (if stored)
    # This is lenient - if not set, allow (for backward compatibility)
    try:
        if sess.ip_hash:
            client_ip_hash = hash_ip(get_client_ip(request))
            if sess.ip_hash != client_ip_hash:
                # Log mismatch but don't block (could be legitimate proxy/CDN)
                pass  # For now, we don't enforce strict IP matching
    except AttributeError:
        # Column doesn't exist yet (migration 014 not applied) - skip IP check
        pass
    
    return sess


def create_session_with_security(
    db: Session,
    request: Request,
    user_id: Optional[str] = None,
) -> ChatbotSession:
    """
    Create a new chatbot session with security fields (IP hash, user agent hash, expiration).
    Gracefully handles missing columns (backward compatible).
    """
    from uuid import uuid4
    from sqlalchemy import inspect
    
    sid = uuid4()
    now = datetime.now(timezone.utc)
    
    # Check if security columns exist by inspecting the table
    inspector = inspect(ChatbotSession)
    column_names = {col.name for col in inspector.columns}
    
    has_security_fields = all(col in column_names for col in ['expires_at', 'ip_hash', 'user_agent_hash'])
    
    if has_security_fields:
        # Migration 014 applied - use all security fields
        expires_at = now + timedelta(hours=SESSION_EXPIRY_HOURS)
        ip_hash = hash_ip(get_client_ip(request))
        ua_hash = hash_user_agent(get_user_agent(request))
        
        sess = ChatbotSession(
            id=sid,
            user_id=user_id,
            expires_at=expires_at,
            ip_hash=ip_hash,
            user_agent_hash=ua_hash,
        )
    else:
        # Migration 014 not applied - create without security fields
        sess = ChatbotSession(
            id=sid,
            user_id=user_id,
        )
    
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess
