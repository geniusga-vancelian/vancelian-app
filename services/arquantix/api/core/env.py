"""
Environment utilities for detecting development mode
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Ensure .env.local is loaded first (if it exists)
api_dir = Path(__file__).parent.parent
def _safe_load_dotenv(path: Path) -> None:
    try:
        load_dotenv(path)
    except PermissionError:
        return

_safe_load_dotenv(api_dir / ".env.local")
_safe_load_dotenv(api_dir / ".env")


def is_dev_mode() -> bool:
    """
    Check if the application is running in development mode.
    
    Returns True if:
    - ENV is set to "local", "dev", or "development"
    - DEBUG is set to "1", "true", "yes", or "on" (case-insensitive)
    - NODE_ENV is set to "development", "dev", or "local"
    
    Returns False otherwise (production mode).
    """
    env = os.getenv("ENV", "").lower().strip()
    debug = os.getenv("DEBUG", "").lower().strip()
    node_env = os.getenv("NODE_ENV", "").lower().strip()
    
    # Check ENV variable
    if env in ("local", "dev", "development"):
        return True
    
    # Check DEBUG variable (accept multiple truthy values)
    if debug in ("1", "true", "yes", "on"):
        return True
    
    # Check NODE_ENV (for compatibility)
    if node_env in ("development", "dev", "local"):
        return True
    
    return False


def get_env_info() -> dict:
    """
    Get environment information for debugging (safe, no secrets).
    """
    return {
        "ENV": os.getenv("ENV", ""),
        "DEBUG": os.getenv("DEBUG", ""),
        "NODE_ENV": os.getenv("NODE_ENV", ""),
        "is_dev_mode": is_dev_mode(),
    }


def _truthy(var: str, default: str = "false") -> bool:
    return os.getenv(var, default).lower().strip() in ("1", "true", "yes", "on")


def allow_legacy_unauthenticated_kyc() -> bool:
    """When True, GET /api/persons/{id} and POST /{id}/fields accept
    unauthenticated requests (with a WARNING log).  Set to False in
    production once all callers send a JWT.

    Phase 4C: ces routes sont **dépréciées** (en-tête ``Deprecation``, OpenAPI
    ``deprecated``) ; la lecture doit migrer vers ``GET .../identity`` ; l’écriture
    de champs vers des flux authentifiés. Voir ``PHASE_4C_LEGACY_PERSONS_DEPRECATION_PLAN.md``.
    """
    return _truthy("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")


def enable_aml_blocking() -> bool:
    """When True, aml_ok=False blocks eligibility.  Keep False until
    Sumsub is wired (Phase 2).
    """
    return _truthy("ENABLE_AML_BLOCKING", "false")


def disable_eligibility_checks() -> bool:
    """Emergency bypass for product eligibility gates.  Must be False
    in production.
    """
    return _truthy("DISABLE_ELIGIBILITY_CHECKS", "false")


