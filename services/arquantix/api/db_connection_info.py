"""Helpers pour journaliser la cible PostgreSQL au démarrage (sans mot de passe)."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)


def mask_database_url(url: str) -> str:
    if not url or "@" not in url:
        return url or ""
    try:
        p = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
        auth = p.username or ""
        if p.password:
            return url.replace(f"{auth}:{p.password}@", f"{auth}:***@", 1)
    except Exception:
        pass
    return re.sub(r":([^:@/]+)@", r":***@", url, count=1)


def parse_postgres_target(url: str) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[str]]:
    u = (url or "").strip().strip('"').strip("'")
    for prefix in ("postgresql+asyncpg://", "postgres://"):
        if u.startswith(prefix):
            u = "postgresql://" + u.split("://", 1)[1]
            break
    if not u.startswith("postgresql://"):
        return None, None, None, "not_postgresql"
    try:
        p = urlparse(u)
        host = p.hostname
        port = p.port or 5432
        db = (p.path or "").lstrip("/").split("?")[0] or None
        if db:
            db = unquote(db)
        return host, port, db, None
    except Exception as exc:
        return None, None, None, str(exc)


def db_target_dict(database_url: str) -> Dict[str, Any]:
    host, port, db, err = parse_postgres_target(database_url)
    return {
        "host": host,
        "port": port,
        "database": db,
        "masked_url": mask_database_url(database_url),
        "parse_error": err,
    }


def log_database_target(label: str, database_url: str) -> None:
    """Log + print une ligne host/port/db (URL masquée)."""
    info = db_target_dict(database_url)
    if info.get("parse_error"):
        logger.warning("%s DB: could not parse DATABASE_URL (%s)", label, info["parse_error"])
        print(f"[{label}] WARNING: parse error — {info['parse_error']}")
        return
    msg = (
        f"host={info['host']} port={info['port']} database={info['database']} "
        f"url={info['masked_url']}"
    )
    logger.info("%s DB: %s", label, msg)
    print(f"[{label}] {msg}")


def log_api_database_at_startup(database_url: str) -> None:
    """Appeler depuis le startup FastAPI (hors mode testing)."""
    log_database_target("API", database_url)
