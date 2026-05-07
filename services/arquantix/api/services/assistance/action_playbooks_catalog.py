"""Catalogue CAL (playbooks) — lecture cache + rendu Markdown pour l'agent product."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from database import AssistanceActionPlaybook

logger = logging.getLogger(__name__)

_CACHE_ROWS: Optional[list[AssistanceActionPlaybook]] = None
_CACHE_AT: float = 0.0
_TTL_SEC = 30.0


def invalidate_playbook_cache() -> None:
    global _CACHE_ROWS, _CACHE_AT
    _CACHE_ROWS = None
    _CACHE_AT = 0.0


def _load_enabled_ordered(db: Session) -> list[AssistanceActionPlaybook]:
    return (
        db.query(AssistanceActionPlaybook)
        .filter(AssistanceActionPlaybook.is_enabled.is_(True))
        .order_by(
            AssistanceActionPlaybook.sort_order.asc(),
            AssistanceActionPlaybook.action_key.asc(),
        )
        .all()
    )


def get_cached_enabled_playbooks(db: Session) -> list[AssistanceActionPlaybook]:
    """Liste des playbooks actifs (cache court TTL)."""
    global _CACHE_ROWS, _CACHE_AT
    now = time.monotonic()
    if _CACHE_ROWS is not None and (now - _CACHE_AT) < _TTL_SEC:
        return _CACHE_ROWS
    rows = _load_enabled_ordered(db)
    _CACHE_ROWS = rows
    _CACHE_AT = now
    return rows


def render_enabled_playbooks_markdown(db: Session) -> str:
    """Bloc Markdown injecté sous ``[ACTION_PLAYBOOKS_CATALOG]``."""
    rows = get_cached_enabled_playbooks(db)
    if not rows:
        return (
            "_Aucun playbook CAL activé en base._ "
            "Configure-les dans l'admin (Assistance → Playbooks CAL)."
        )

    chunks: list[str] = []
    for row in rows:
        title = row.label.strip() or row.action_key
        desc = (row.description or "").strip()
        tk = row.transaction_kind
        ak = row.action_key
        definition = row.definition if isinstance(row.definition, dict) else {}
        steps = definition.get("steps") if isinstance(definition.get("steps"), list) else []
        req = definition.get("required_slots_fr") or ""
        bad = definition.get("unavailable_message_fr") or ""

        lines: list[str] = [
            f"### [{ak}] {title}",
            f"- **transaction_kind (routeur)** : `{tk}`",
            f"- **agent** : `{row.agent_id}`",
        ]
        if desc:
            lines.append(f"- **Résumé** : {desc}")
        if steps:
            lines.append("- **Étapes (ordre)** :")
            for s in steps:
                if not isinstance(s, dict):
                    continue
                sid = str(s.get("id") or "").strip() or "?"
                tool = str(s.get("tool") or "").strip() or "?"
                inst = str(s.get("instruction_fr") or "").strip()
                order = s.get("order")
                oh = f"{order}. " if order is not None else "- "
                lines.append(f"  - {oh}`{tool}` ({sid}) — {inst}")
        if req:
            lines.append(f"- **Infos requises** : {req}")
        if bad:
            lines.append(f"- **Si indisponible** : {bad}")
        chunks.append("\n".join(lines))

    return "\n\n".join(chunks)


def definition_pretty_json(definition: Any) -> str:
    if isinstance(definition, dict):
        return json.dumps(definition, ensure_ascii=False, indent=2)
    return "{}"


__all__ = [
    "get_cached_enabled_playbooks",
    "invalidate_playbook_cache",
    "render_enabled_playbooks_markdown",
    "definition_pretty_json",
]
