#!/usr/bin/env python3
"""Audit des configurations DATABASE_URL / PostgreSQL pour Arquantix.

Lit les fichiers .env connus (sans exécuter l'API), affiche host/port/dbname
avec mot de passe masqué, et signale les divergences de cluster (host:port).

Usage:
  python3 scripts/db_config_audit.py
  python3 scripts/db_config_audit.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, unquote


ARQ_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class DbEndpoint:
    source: str
    consumer: str
    raw_present: bool
    host: Optional[str]
    port: Optional[int]
    database: Optional[str]
    user: Optional[str]
    masked_url: Optional[str]
    error: Optional[str] = None


def _arq_root() -> Path:
    return ARQ_ROOT


def mask_database_url(url: str) -> str:
    if not url or "@" not in url:
        return url or ""
    try:
        p = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
        if not p.hostname:
            return re.sub(r":([^:@/]+)@", r":***@", url, count=1)
        auth = p.username or ""
        return url.replace(f"{auth}:{p.password or ''}@", f"{auth}:***@", 1) if p.password else url
    except Exception:
        return re.sub(r":([^:@/]+)@", r":***@", url, count=1)


def parse_postgres_url(url: str) -> Tuple[Optional[str], Optional[int], Optional[str], Optional[str], Optional[str]]:
    """Return host, port, database, user, error."""
    if not url or not url.strip():
        return None, None, None, None, "empty"
    u = url.strip().strip('"').strip("'")
    for prefix in ("postgresql+asyncpg://", "postgres://"):
        if u.startswith(prefix):
            u = "postgresql://" + u.split("://", 1)[1]
            break
    if not u.startswith("postgresql://"):
        return None, None, None, None, "not_postgresql"
    try:
        parsed = urlparse(u)
        host = parsed.hostname
        port = parsed.port or 5432
        db = (parsed.path or "").lstrip("/") or None
        if db:
            db = unquote(db.split("?")[0])
        user = unquote(parsed.username) if parsed.username else None
        return host, port, db, user, None
    except Exception as e:
        return None, None, None, None, str(e)


def read_database_url_from_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#") or not s:
            continue
        if s.upper().startswith("DATABASE_URL="):
            return s.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def resolve_api_like_url() -> Tuple[str, List[str]]:
    """Même ordre que database.py / alembic env: .env.local puis .env dans api/."""
    api_dir = _arq_root() / "api"
    chain: List[str] = []
    url: Optional[str] = None
    for name in (".env.local", ".env"):
        p = api_dir / name
        v = read_database_url_from_file(p)
        chain.append(f"api/{name}")
        if v:
            url = v
    if os.environ.get("DATABASE_URL"):
        chain.append("$DATABASE_URL (shell)")
        url = os.environ["DATABASE_URL"]
    if not url:
        # fallback database.py (sans .env)
        user = os.getenv("DB_USER", "arquantix")
        pw = os.getenv("DB_PASSWORD", "arquantix")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5443")
        name = os.getenv("DB_NAME", "arquantix")
        url = f"postgresql://{user}:{pw}@{host}:{port}/{name}"
        chain.append("database.py built-in default (no DATABASE_URL in env files)")
    return url, chain


def collect_endpoints() -> List[DbEndpoint]:
    root = _arq_root()
    repo_root = root.parent.parent  # vancelian-app

    out: List[DbEndpoint] = []

    def add(source: str, consumer: str, url: Optional[str]) -> None:
        if url is None:
            out.append(
                DbEndpoint(
                    source=source,
                    consumer=consumer,
                    raw_present=False,
                    host=None,
                    port=None,
                    database=None,
                    user=None,
                    masked_url=None,
                    error="file missing or no DATABASE_URL",
                )
            )
            return
        h, p, d, u, err = parse_postgres_url(url)
        out.append(
            DbEndpoint(
                source=source,
                consumer=consumer,
                raw_present=True,
                host=h,
                port=p,
                database=d,
                user=u,
                masked_url=mask_database_url(url),
                error=err,
            )
        )

    # Fichiers nominaux
    add("api/.env.local", "API file candidate", read_database_url_from_file(root / "api" / ".env.local"))
    add("api/.env", "API file candidate", read_database_url_from_file(root / "api" / ".env"))
    add("web/.env.local", "Web/Prisma file candidate", read_database_url_from_file(root / "web" / ".env.local"))
    add("web/.env", "Web/Prisma file candidate", read_database_url_from_file(root / "web" / ".env"))
    add("repo/.env", "Repo root (legacy)", read_database_url_from_file(repo_root / ".env"))
    add("web/.env.example", "Web template (placeholder)", read_database_url_from_file(root / "web" / ".env.example"))

    # Résolu API + Alembic (identique si même process)
    api_url, chain = resolve_api_like_url()
    h, p, d, u, err = parse_postgres_url(api_url)
    out.append(
        DbEndpoint(
            source=" → ".join(chain),
            consumer="API + Alembic (effective after dotenv order + shell)",
            raw_present=True,
            host=h,
            port=p,
            database=d,
            user=u,
            masked_url=mask_database_url(api_url),
            error=err,
        )
    )
    return out


def _web_effective_endpoint(endpoints: List[DbEndpoint]) -> Optional[DbEndpoint]:
    """Aligné sur Next.js : DATABASE_URL dans web/.env.local prime sur web/.env si présente."""
    wl = next((e for e in endpoints if e.source == "web/.env.local"), None)
    we = next((e for e in endpoints if e.source == "web/.env"), None)
    if wl and wl.raw_present:
        return wl
    if we and we.raw_present:
        return we
    return None


def analyze(endpoints: List[DbEndpoint]) -> Dict[str, Any]:
    effective = next((e for e in endpoints if e.consumer.startswith("API + Alembic")), None)
    web_main = _web_effective_endpoint(endpoints)
    web_label = (
        web_main.source
        if web_main
        else "web/.env.local → web/.env"
    )
    api_env = next((e for e in endpoints if e.source == "api/.env" and e.raw_present), None)
    repo = next((e for e in endpoints if e.source == "repo/.env" and e.raw_present), None)

    warnings: List[str] = []
    errors: List[str] = []

    if effective and effective.error and effective.error != "empty":
        errors.append(f"API effective URL parse error: {effective.error}")

    clusters = []
    for e in endpoints:
        if e.host and e.port is not None:
            clusters.append((e.host, e.port, e.source))

    if effective and web_main and effective.host and web_main.host:
        if (effective.host, effective.port) != (web_main.host, web_main.port):
            errors.append(
                f"CLUSTER MISMATCH: API effective {effective.host}:{effective.port} "
                f"≠ {web_label} {web_main.host}:{web_main.port} — utiliser le même hôte:port PostgreSQL."
            )
        if effective.database and web_main.database and effective.database != web_main.database:
            errors.append(
                f"DATABASE NAME MISMATCH: API utilise {effective.database!r} mais le web utilise "
                f"{web_main.database!r} — après unification, une seule base (ex. arquantix) pour les deux."
            )

    if effective and api_env and effective.database and api_env.database:
        if effective.database != api_env.database and "shell" not in effective.source.lower():
            warnings.append(
                "API effective DB name diffère de api/.env seul (priorité .env.local ou shell) — vérifier l’ordre de chargement."
            )

    if repo and effective and repo.host and effective.host:
        if (repo.host, repo.port) != (effective.host, effective.port):
            warnings.append(
                f"repo/.env pointe vers {repo.host}:{repo.port} alors que l’API résout "
                f"{effective.host}:{effective.port} — repo/.env peut être legacy si l’API ne le charge pas."
            )

    for label, ep in (("API", effective), ("Web", web_main)):
        if ep and ep.database in ("arquantix_quant", "arquantix_admin"):
            warnings.append(
                f"{label} pointe encore vers {ep.database!r} — migrer vers la base unique "
                f"(ex. arquantix), voir DB_UNIFICATION_PHASE_2_REPORT.md."
            )

    return {
        "warnings": warnings,
        "errors": errors,
        "expected_pattern": {
            "unified_database": "arquantix",
            "same_host_port": "API et Web sur le même host:port PostgreSQL",
            "same_db_name": "DATABASE_URL API et web/.env → même nom de base",
            "note": "Phase 2 unification — DB_RUNBOOK_UPDATED.md",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Arquantix DB config audit")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    endpoints = collect_endpoints()
    analysis = analyze(endpoints)

    if args.json:
        payload = {
            "endpoints": [asdict(e) for e in endpoints],
            **analysis,
        }
        print(json.dumps(payload, indent=2))
        return 1 if analysis["errors"] else 0

    print("=" * 72)
    print("ARQUANTIX — DB CONFIG AUDIT")
    print(f"Racine service: {_arq_root()}")
    print("=" * 72)

    for e in endpoints:
        print(f"\n[{e.consumer}]")
        print(f"  source: {e.source}")
        if not e.raw_present:
            print(f"  status: {e.error or 'absent'}")
            continue
        print(f"  URL (masquée): {e.masked_url}")
        if e.error:
            print(f"  parse: ERROR {e.error}")
        else:
            print(f"  host={e.host} port={e.port} db={e.database} user={e.user}")

    print("\n" + "-" * 72)
    print("Attendu (architecture documentée)")
    print("-" * 72)
    for k, v in analysis["expected_pattern"].items():
        print(f"  {k}: {v}")

    if analysis["warnings"]:
        print("\n⚠️  WARNINGS")
        for w in analysis["warnings"]:
            print(f"  - {w}")
    if analysis["errors"]:
        print("\n❌ ERRORS")
        for w in analysis["errors"]:
            print(f"  - {w}")
        return 1

    print("\n✅ Aucune erreur de cluster détectée (voir warnings ci-dessus).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
