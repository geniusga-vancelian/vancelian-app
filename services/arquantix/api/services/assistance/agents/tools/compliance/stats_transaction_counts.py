"""Tool ``stats_transaction_counts`` — agent **compliance.transactional**, autonomy **L0**.

Compte agrégé des transactions cash du client selon une dimension :

  - ``direction`` (default) : entrées (credit) vs sorties (debit)
  - ``status`` : completed / pending / failed / etc.
  - ``kind`` : bank_transfer_in / card_in / crypto_in / …
  - ``month`` : nombre de transactions par mois calendaire

Phase 2c.5 — premier des deux tools « stats » (counts + amounts) du
sub-agent transactional. Format de retour identique à
``list_transactions`` : ``markdown_table`` prêt-à-coller que le LLM
inclut tel quel dans sa réponse.

Cf. ``docs/arquantix/COMPLIANCE_TOPICS.md`` § 3.3 (stats).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.assistance.agents.repositories import compliance_repo
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "stats_transaction_counts",
        "description": (
            "Compte les transactions cash du client agrégées selon une "
            "dimension (direction par défaut, statut, kind ou mois). "
            "Retourne un `markdown_table` prêt-à-coller (Catégorie / "
            "Nombre). À utiliser pour TOUTE question quantitative en "
            "NOMBRE de transactions (« combien de dépôts ? », "
            "« combien de retraits ? », « combien de transactions par "
            "mois ? »). Pour les MONTANTS totaux, utilise plutôt "
            "`stats_transaction_amounts`. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "Catégorie de transactions à filtrer. Si "
                        "omis, toutes catégories sont incluses."
                    ),
                    "enum": [
                        "deposits",
                        "withdrawals",
                        "cards",
                        "crypto",
                        "bank_transfer",
                        "all",
                    ],
                },
                "direction": {
                    "type": "string",
                    "description": "Filtre direction supplémentaire.",
                    "enum": ["credit", "debit"],
                },
                "status": {
                    "type": "string",
                    "description": "Filtre par statut.",
                    "enum": [
                        "pending",
                        "completed",
                        "failed",
                        "rejected",
                        "on_hold",
                        "cancelled",
                    ],
                },
                "since": {
                    "type": "string",
                    "description": (
                        "Date min ISO8601 (ex. `2026-01-01`). "
                        "Les transactions antérieures sont exclues."
                    ),
                },
                "group_by": {
                    "type": "string",
                    "description": (
                        "Dimension d'agrégation. `direction` (défaut) "
                        "= entrées vs sorties. `status` = ventilation "
                        "par statut. `kind` = par type d'opération. "
                        "`month` = par mois calendaire."
                    ),
                    "enum": ["direction", "status", "kind", "month"],
                    "default": "direction",
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "compliance.transactional",
}


# Mapping des labels SQL bruts → libellés FR, par dimension. Tout
# label non mappé tombe en humanize générique.
_LABELS_BY_GROUP: dict[str, dict[str, str]] = {
    "direction": {
        "credit": "Entrées (dépôts)",
        "debit": "Sorties (retraits)",
    },
    "status": {
        "pending": "En attente",
        "completed": "Complété",
        "failed": "Échec",
        "rejected": "Rejeté",
        "on_hold": "En attente",
        "cancelled": "Annulé",
    },
    "kind": {
        "bank_transfer_in": "Virement entrant",
        "bank_transfer_out": "Virement sortant",
        "card_in": "Dépôt par carte",
        "crypto_in": "Dépôt crypto",
        "deposit": "Dépôt",
        "withdrawal": "Retrait",
        "swap": "Échange",
        "fee": "Frais",
    },
    "month": {},  # déjà au format YYYY-MM, pas besoin de mapping
}


def _label(dim: str, raw: str) -> str:
    if dim == "month":
        return raw  # YYYY-MM lisible tel quel
    table = _LABELS_BY_GROUP.get(dim, {})
    if raw in table:
        return table[raw]
    # Fallback : humanize
    return (
        raw.replace("_", " ").strip().capitalize() if raw else "Autre"
    )


def execute(
    ctx: ToolContext,
    *,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    status: Optional[str] = None,
    since: Optional[str] = None,
    group_by: str = "direction",
    **_kwargs: Any,
) -> dict[str, Any]:
    if not ctx.client_id:
        return {
            "total": 0,
            "items": [],
            "markdown_table": "_Aucune transaction trouvée._",
            "filters_applied": {},
        }

    safe_group = (group_by or "direction").strip().lower()
    if safe_group not in {"direction", "status", "kind", "month"}:
        safe_group = "direction"

    try:
        rows = compliance_repo.fetch_transaction_counts(
            ctx.db,
            client_id=ctx.client_id,
            category=category,
            direction=direction,
            status=status,
            since=since,
            group_by=safe_group,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "stats_transaction_counts.repo_error agent=%s conv=%s",
            ctx.agent_id,
            ctx.conversation_id,
        )
        return {
            "total": 0,
            "items": [],
            "markdown_table": "_Aucune transaction trouvée._",
            "filters_applied": _filters_applied(
                category, direction, status, since, safe_group
            ),
            "error": "repo_unavailable",
        }

    items = [
        {
            "raw_label": r["label"],
            "label": _label(safe_group, r["label"]),
            "count": r["count"],
        }
        for r in rows
    ]
    total = sum(it["count"] for it in items)

    if not items:
        markdown = "_Aucune transaction trouvée pour ces critères._"
    else:
        header_label = {
            "direction": "Catégorie",
            "status": "Statut",
            "kind": "Type",
            "month": "Mois",
        }.get(safe_group, "Catégorie")
        lines = [
            f"| {header_label} | Nombre |",
            "|---|---:|",
        ]
        for it in items:
            lines.append(f"| **{_escape_pipe(it['label'])}** | {it['count']} |")
        # Ligne total uniquement si > 1 item.
        if len(items) > 1:
            lines.append(f"| _Total_ | **{total}** |")
        markdown = "\n".join(lines)

    return {
        "total": total,
        "items": items,
        "markdown_table": markdown,
        "filters_applied": _filters_applied(
            category, direction, status, since, safe_group
        ),
    }


def _filters_applied(
    category: Optional[str],
    direction: Optional[str],
    status: Optional[str],
    since: Optional[str],
    group_by: str,
) -> dict[str, Any]:
    out: dict[str, Any] = {"group_by": group_by}
    if category:
        out["category"] = category
    if direction:
        out["direction"] = direction
    if status:
        out["status"] = status
    if since:
        out["since"] = since
    return out


def _escape_pipe(s: Any) -> str:
    return str(s).replace("|", r"\|") if s is not None else "—"
