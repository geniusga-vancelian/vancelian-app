#!/usr/bin/env python3
"""Cognitive Funnel CLI — audit local rapide du funnel cognitif.

Cognitive Bot v4 — Lot 5 (2026-05-04). Affiche dans le terminal un
résumé du funnel cognitif en lisant directement la table
``assistance_agent_decisions`` (filtrée sur ``tool_name='router_classify'``)
sur une période ``[now - period_days, now)``.

Aucun appel HTTP, aucune dépendance à l'auth admin — utile pour les
diagnostics locaux pendant le dev. **Read-only stricte**.

Usage local (host) :

::

    docker exec arquantixrecovery-arquantix-api-1 \\
      python scripts/cognitive_funnel.py --period-days 7

Usage à l'intérieur du container API :

::

    python scripts/cognitive_funnel.py --period-days 7 --json

Sort un JSON sur stdout si ``--json``. Sinon affiche un résumé textuel.

Source unique de vérité :
``services/assistance/admin_cognitive_router.py`` — le CLI réutilise
les mêmes fonctions d'agrégation pour rester aligné.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

api_dir = Path(__file__).resolve().parent.parent
os.chdir(api_dir)
sys.path.insert(0, str(api_dir))

# Load .env (cf. db_doctor.py).
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


def _build_session():
    """Crée une SQLAlchemy ``Session`` sur ``DATABASE_URL``."""
    import importlib

    db_module = importlib.import_module("database")
    return db_module.SessionLocal()


def _format_buckets(title: str, buckets: list, max_rows: int = 10) -> str:
    """Format texte d'une distribution catégorielle."""
    if not buckets:
        return f"## {title}\n  (aucune donnée)"
    lines = [f"## {title}"]
    for b in buckets[:max_rows]:
        bar = "█" * max(1, int(b.pct / 5))
        lines.append(
            f"  {b.label:<24s} {b.count:>6d}  {b.pct:>6.2f}%  {bar}"
        )
    if len(buckets) > max_rows:
        lines.append(
            f"  … (+ {len(buckets) - max_rows} buckets non affichés)"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit local du funnel cognitif (Cognitive Bot v4, Lot 5)."
        )
    )
    parser.add_argument(
        "--period-days",
        type=int,
        default=7,
        help="Fenêtre temporelle [now - N jours, now). Défaut : 7.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Sort la réponse en JSON brut (machine-readable).",
    )
    args = parser.parse_args()

    if not (1 <= args.period_days <= 90):
        print(
            f"ERROR: --period-days hors bornes [1, 90] (reçu : {args.period_days})",
            file=sys.stderr,
        )
        return 2

    # Imports différés pour bénéficier du load_dotenv ci-dessus.
    from database import AssistanceAgentDecision
    from services.assistance.admin_cognitive_router import (
        _aggregate_agent_id,
        _aggregate_dimension,
        _trust_level_stats,
    )

    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=int(args.period_days))

    db = _build_session()
    try:
        by_stage = _aggregate_dimension(
            db,
            column=AssistanceAgentDecision.conversation_stage,
            json_path=("cognitive_state", "conversation_stage"),
            period_start=period_start,
            period_end=period_end,
        )
        by_emotional = _aggregate_dimension(
            db,
            column=AssistanceAgentDecision.emotional_intent,
            json_path=("cognitive_state", "emotional_intent"),
            period_start=period_start,
            period_end=period_end,
        )
        by_primary = _aggregate_dimension(
            db,
            column=AssistanceAgentDecision.primary_goal,
            json_path=("objective", "primary_goal"),
            period_start=period_start,
            period_end=period_end,
        )
        by_nba = _aggregate_dimension(
            db,
            column=AssistanceAgentDecision.next_best_action,
            json_path=("objective", "next_best_action"),
            period_start=period_start,
            period_end=period_end,
        )
        by_agent = _aggregate_agent_id(
            db,
            period_start=period_start,
            period_end=period_end,
        )
        trust_stats = _trust_level_stats(
            db,
            period_start=period_start,
            period_end=period_end,
        )
    finally:
        db.close()

    total = sum(b.count for b in by_agent)

    if args.json:
        payload = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "period_days": int(args.period_days),
            "total_decisions": total,
            "by_stage": [b.model_dump() for b in by_stage],
            "by_emotional_intent": [b.model_dump() for b in by_emotional],
            "by_primary_goal": [b.model_dump() for b in by_primary],
            "by_next_best_action": [b.model_dump() for b in by_nba],
            "by_agent_id": [b.model_dump() for b in by_agent],
            "trust_level": trust_stats.model_dump(),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    # Sortie textuelle (lisible, ~80 colonnes).
    print("=" * 78)
    print(
        f"  COGNITIVE FUNNEL — {period_start.isoformat(timespec='minutes')} → "
        f"{period_end.isoformat(timespec='minutes')}"
    )
    print(
        f"  Période : {args.period_days}j · Total décisions router : {total}"
    )
    print("=" * 78)
    print()
    print(_format_buckets("Stages de conversation", by_stage))
    print()
    print(_format_buckets("Emotional intent", by_emotional))
    print()
    print(_format_buckets("Primary goal (objective)", by_primary))
    print()
    print(_format_buckets("Next best action (objective)", by_nba))
    print()
    print(_format_buckets("Agent designé (router → expert)", by_agent))
    print()
    print("## Trust level (sur les décisions avec cognitive_state)")
    if trust_stats.sample_size:
        print(
            f"  sample_size = {trust_stats.sample_size}  "
            f"avg = {trust_stats.avg:.3f}  "
            f"min = {trust_stats.min:.3f}  "
            f"max = {trust_stats.max:.3f}"
        )
    else:
        print("  (aucune donnée trust_level sur la période)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
