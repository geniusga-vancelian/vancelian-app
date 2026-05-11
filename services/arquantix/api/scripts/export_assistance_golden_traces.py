#!/usr/bin/env python3
"""PR 4A — export JSONL « golden traces » Assistance (read-only DB).

Une ligne JSON par **tour user** (historique jusqu’à ce message inclus,
snapshot router, état agrégé, tools, gaps policy).

Usage (container API ou host avec PYTHONPATH=api) :

    python scripts/export_assistance_golden_traces.py \\
        --conversation-id <UUID> \\
        --output traces.jsonl

Plage conversations (``updated_at``) :

    python scripts/export_assistance_golden_traces.py \\
        --since 2026-05-01 \\
        --limit-conversations 15 \\
        --output batch.jsonl
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
os.chdir(api_dir)
sys.path.insert(0, str(api_dir))

try:
    from dotenv import load_dotenv

    env_local_path = api_dir / ".env.local"
    env_path = api_dir / ".env"
    if env_local_path.exists():
        load_dotenv(env_local_path)
    elif env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass


def _parse_dt_iso(s: str) -> datetime:
    raw = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if raw.tzinfo is None:
        raw = raw.replace(tzinfo=timezone.utc)
    return raw.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export golden traces Assistance (JSONL)."
    )
    parser.add_argument(
        "--conversation-id",
        help="Filtrer une conversation unique.",
    )
    parser.add_argument(
        "--since",
        help="ISO-8601 (conv.updated_at >= since) si pas de --conversation-id.",
    )
    parser.add_argument(
        "--until",
        help="ISO-8601 excluant la borne sup (conv.updated_at < until).",
    )
    parser.add_argument(
        "--limit-conversations",
        type=int,
        default=50,
        help="Nombre max de convs (--since sans --conversation-id).",
    )
    parser.add_argument(
        "--recent-turn-cap",
        type=int,
        default=24,
        help="Nb max de tours bruts précédents dans ``recent_turns``.",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=True,
        help="Fichier de sortie .jsonl",
    )
    args = parser.parse_args()
    if not args.conversation_id and not args.since:
        parser.error("Requis : --conversation-id **ou** --since (fenêtre temporelle).")

    from database import SessionLocal

    from services.assistance.golden_trace_export import (
        conversation_ids_between,
        export_conversation_turns_jsonl_strings,
    )

    ids: list[UUID]
    if args.conversation_id:
        ids = [UUID(str(args.conversation_id).strip())]
    else:
        since_dt = _parse_dt_iso(args.since) if args.since else None
        until_dt = _parse_dt_iso(args.until) if args.until else None
        db0 = SessionLocal()
        try:
            ids = conversation_ids_between(
                db0,
                since=since_dt,
                until=until_dt,
                limit=max(1, int(args.limit_conversations)),
            )
        finally:
            db0.close()
        if not ids:
            print("aucune conversation match", file=sys.stderr)
            return 1

    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    db = SessionLocal()
    try:
        with out_path.open("w", encoding="utf-8") as fh:
            for cid in ids:
                lines = export_conversation_turns_jsonl_strings(
                    db,
                    conversation_id=cid,
                    recent_turn_cap=max(2, int(args.recent_turn_cap)),
                )
                for line in lines:
                    fh.write(line + "\n")
                    written += 1
    finally:
        db.close()

    print(f"wrote {written} lines → {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
