"""
FastAPI routes for Diagnostics
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field
import sys
from pathlib import Path

# Add api directory to path for auth import
api_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(api_dir))

from auth import get_current_user, AdminUser, decode_token_debug, _get_current_user_internal
from database import get_db, DATABASE_URL
from core.env import is_dev_mode, get_env_info
from pathlib import Path as PathLib
# market_backtest (pandas, numpy) imported lazily in run_diagnostic only
from fastapi import Header
import os
import re

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])

def get_dbname_from_url(url: str) -> str:
    """Extract database name from URL"""
    match = re.search(r"/([^/?]+)(?:\?|$)", url)
    return match.group(1) if match else "unknown"


@router.get("/db-status")
def db_status(db: Session = Depends(get_db)):
    """
    Database diagnostic: name, host, migration version, key row counts.
    Public in dev mode, auth-required otherwise.
    """
    from sqlalchemy import text

    db_name = get_dbname_from_url(DATABASE_URL)
    host_match = re.search(r"@([^:/]+)", DATABASE_URL)
    host = host_match.group(1) if host_match else "unknown"
    port_match = re.search(r":(\d+)/", DATABASE_URL)
    port = port_match.group(1) if port_match else "5432"

    alembic_version = None
    try:
        row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
        if row:
            alembic_version = row[0]
    except Exception:
        alembic_version = "table_missing"

    count_tables = [
        "pe_product_definitions", "pe_portfolio_templates", "pe_template_allocations",
        "pe_clients", "pe_ledger_accounts", "pe_ledger_entries",
        "custody_accounts", "custody_transactions", "custody_webhook_events",
        "app_runtime_settings",
    ]
    counts = {}
    for t in count_tables:
        try:
            row = db.execute(text(f"SELECT count(*) FROM {t}")).fetchone()  # noqa: S608
            counts[t] = row[0] if row else 0
        except Exception:
            counts[t] = "missing"

    return {
        "database": db_name,
        "host": host,
        "port": port,
        "alembic_version": alembic_version,
        "row_counts": counts,
        "canonical_unified_db": "arquantix",
        "note": "API (Alembic) et Web (Prisma) doivent utiliser la même base — voir DB_RUNBOOK_UPDATED.md",
    }


@router.get("/whoami")
async def whoami(current_user: AdminUser = Depends(get_current_user)):
    """
    DEV endpoint to verify JWT authentication works.
    Returns current user info if JWT is valid.
    """
    # Check if user was auto-created (dev bootstrap)
    # We check if email is admin@local.dev and created_at is very recent (within last 5 minutes)
    from datetime import datetime, timedelta
    is_bootstrap = False
    if current_user.email == "admin@local.dev" and current_user.created_at:
        # Handle timezone-aware datetime
        if current_user.created_at.tzinfo:
            now = datetime.now(current_user.created_at.tzinfo)
            user_created = current_user.created_at
        else:
            now = datetime.utcnow()
            user_created = current_user.created_at
        
        time_diff = now - user_created
        is_bootstrap = time_diff < timedelta(minutes=5)
    
    return {
        "authenticated": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": getattr(current_user, 'role', None),
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "source": "dev_bootstrap" if is_bootstrap else "db",
        "is_admin": True,  # All AdminUser are admins in this system
    }


@router.post("/auth-trace")
async def auth_trace(authorization: str = Header(None)):
    """
    DEV-ONLY endpoint to trace authentication decision step by step.
    Returns detailed information about why auth succeeds or fails.
    """
    # Restrict to dev/local only
    if not is_dev_mode():
        raise HTTPException(status_code=404, detail="Not found")
    
    result = {
        "jwt_verify_ok": False,
        "jwt_verified_claims": None,
        "get_current_user_ok": False,
        "get_current_user_error": None,
        "get_current_user_error_type": None,
        "step": None,
        "db_name": get_dbname_from_url(DATABASE_URL),
        "notes": None,
        "dev_mode": is_dev_mode(),
        "env_info": get_env_info(),
    }
    
    if not authorization:
        result["step"] = "missing_authorization_header"
        result["notes"] = "Missing Authorization header"
        return result
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            result["step"] = "invalid_scheme"
            result["notes"] = f"Expected 'Bearer', got '{scheme}'"
            return result
    except ValueError:
        result["step"] = "invalid_header_format"
        result["notes"] = "Invalid authorization header format"
        return result
    
    # Step 1: Verify JWT
    from auth import decode_token_debug, SECRET_KEY, ALGORITHM
    from jose import jwt, JWTError
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        result["jwt_verify_ok"] = True
        # Only return safe claims (sub, exp, iat)
        result["jwt_verified_claims"] = {
            "sub": payload.get("sub"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
        }
    except JWTError as e:
        result["jwt_verify_ok"] = False
        result["step"] = "jwt_verify_failed"
        result["notes"] = f"JWT verification failed: {str(e)}"
        return result
    except Exception as e:
        result["jwt_verify_ok"] = False
        result["step"] = "jwt_verify_error"
        result["notes"] = f"Unexpected JWT error: {str(e)}"
        return result
    
    # Step 2: Try get_current_user logic
    from database import get_db
    
    db = next(get_db())
    try:
        user, error_reason, error_type = _get_current_user_internal(token, db)
        
        if user is None:
            result["get_current_user_ok"] = False
            result["get_current_user_error"] = error_reason
            result["get_current_user_error_type"] = error_type
            
            # Map error to step
            if "missing" in (error_reason or "").lower() and "claim" in (error_reason or "").lower():
                result["step"] = "missing_claim"
            elif "user_not_found" in (error_reason or "").lower() or "not found" in (error_reason or "").lower():
                result["step"] = "user_not_found"
            elif "bootstrap" in (error_reason or "").lower():
                result["step"] = "bootstrap_failed"
            else:
                result["step"] = "other"
        else:
            result["get_current_user_ok"] = True
            result["step"] = "success"
            result["notes"] = f"User authenticated: {user.email} (id={user.id})"
    except Exception as e:
        result["get_current_user_ok"] = False
        result["get_current_user_error"] = f"Unexpected error: {str(e)}"
        result["get_current_user_error_type"] = type(e).__name__
        result["step"] = "other"
    finally:
        db.close()
    
    return result


@router.post("/jwt-debug")
async def jwt_debug(authorization: str = Header(None)):
    """
    DEV-ONLY endpoint to debug JWT token validation.
    Accepts Authorization: Bearer <token> header and returns debug info.
    Only available in local/dev environment.
    """
    # Restrict to dev/local only
    if not is_dev_mode():
        raise HTTPException(status_code=404, detail="Not found")
    
    if not authorization:
        return {
            "error": "Missing Authorization header",
            "hint": "Send Authorization: Bearer <token>",
        }
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return {
                "error": "Invalid authorization scheme",
                "expected": "Bearer",
                "received": scheme,
            }
    except ValueError:
        return {
            "error": "Invalid authorization header format",
            "expected": "Bearer <token>",
        }
    
    # Decode token with debug info
    debug_info = decode_token_debug(token)
    
    # Add database info
    debug_info["database_name"] = get_dbname_from_url(DATABASE_URL)
    
    return debug_info


class DiagnosticRequest(BaseModel):
    mode: str = Field(default="quick", pattern="^(quick|full)$")
    start_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


@router.get("/pnl-invariants")
def pnl_invariants(
    client_id: str = Query(..., description="UUID du client (pe_clients)"),
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compute PnL accounting invariants for a client (A, B, C).
    """
    from uuid import UUID

    from services.accounting.invariants import compute_pnl_invariants

    try:
        cid = UUID(client_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid client_id format")

    return compute_pnl_invariants(db, cid)


@router.post("/market-backtest/run")
async def run_diagnostic(
    request: DiagnosticRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run diagnostic checks for Market Data and Backtest modules.
    Lazy-import of market_backtest (pandas, numpy) to avoid loading them at app startup.
    """
    try:
        from .market_backtest import run_full_diagnostic, generate_markdown_report
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Diagnostic module unavailable (missing deps: pandas, numpy). {e!s}",
        ) from e
    try:
        start_date_py = None
        end_date_py = None
        
        if request.start_date:
            start_date_py = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        if request.end_date:
            end_date_py = datetime.strptime(request.end_date, "%Y-%m-%d").date()
        
        report = run_full_diagnostic(
            db=db,
            mode=request.mode,
            start_date=start_date_py,
            end_date=end_date_py,
        )
        
        # Generate markdown report
        docs_dir = PathLib(__file__).parent.parent.parent.parent / "docs"
        output_path = docs_dir / "DIAGNOSTIC_MARKET_DATA_BACKTEST.md"
        markdown = generate_markdown_report(report, str(output_path))
        
        # Add markdown to response
        report["markdown"] = markdown
        
        return report
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Diagnostic failed: {str(e)}")

