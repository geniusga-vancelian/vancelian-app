"""Router admin **read-only** pour le **funnel cognitif** (Cognitive Bot v4 — Lot 5).

Surface HTTP exposée à l'espace admin sous le préfixe
``/api/admin/assistance/cognitive`` :

  * ``GET /funnel`` — agrégats sur les décisions ``router_classify``
    persistées dans ``assistance_agent_decisions.arguments_json`` :

      - distribution des ``conversation_stage``
        (discovery / clarification / recommendation / conversion),
      - distribution des ``emotional_intent``
        (FEAR_RISK, CURIOSITY, COMPLIANCE_BLOCKED, TRANSACTION,
        ANGER, OPPORTUNITY, NEUTRAL, …),
      - distribution des ``primary_goal`` d'objectif
        (reassure / de_escalate / unblock / inform / educate /
        convert / …),
      - distribution des ``next_best_action``
        (give_proof / give_control / micro_step / ask_question /
        recommend / call_to_action / …),
      - distribution des ``agent_id`` finalement choisis par le
        router,
      - moyenne / min / max du ``trust_level`` (0..1).

Aucune écriture, aucune table créée — toute l'agrégation lit le
JSONB déjà persisté (cf. ``service._persist_router_decision`` et
``base.RouterDecision.cognitive_state / objective``).

Garanties :

  * **Auth** : ``require_admin_or_ops()``.
  * **Read-only stricte** : pas de POST/PUT/DELETE.
  * **Best-effort** : si une dimension cognitive est manquante (legacy
    pré-Lot 1), elle est comptée sous ``"unknown"`` plutôt que
    d'écarter la ligne, pour ne pas biaiser le total.
  * **Bornes temporelles** : ``period_days`` ∈ [1, 90], défaut 7.
    Pas d'index dédié — le volume admin est faible (< 100k
    décisions/mois en V1) et l'index existant
    ``ix_assistance_agent_decisions_agent_created`` couvre déjà la
    sélection ``agent_id='router'``.

Cf. ``docs/arquantix/COGNITIVE_BOT.md`` (Lot 5 — Métriques & Funnel).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Float, and_, func, select
from sqlalchemy.orm import Session

from database import AssistanceAgentDecision, get_db
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import (
    require_admin_or_ops,
)

logger = logging.getLogger(__name__)


admin_cognitive_router = APIRouter(
    prefix="/api/admin/assistance/cognitive",
    tags=["assistance-admin-cognitive"],
)
_guard = require_admin_or_ops()


# ─────────────────────────────────────────────────────────────────────
# Schemas Pydantic
# ─────────────────────────────────────────────────────────────────────


class CountBucket(BaseModel):
    """1 ligne d'une distribution catégorielle ``{label: n}``."""

    model_config = ConfigDict(extra="forbid")

    label: str
    count: int
    pct: float = 0.0


class TrustLevelStats(BaseModel):
    model_config = ConfigDict(extra="forbid")

    avg: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    sample_size: int = 0


class CognitiveFunnelResponse(BaseModel):
    """Agrégats funnel cognitif sur ``[period_start, period_end]``."""

    model_config = ConfigDict(extra="forbid")

    period_start: str
    period_end: str
    period_days: int
    total_decisions: int

    by_stage: list[CountBucket] = Field(default_factory=list)
    by_emotional_intent: list[CountBucket] = Field(default_factory=list)
    by_primary_goal: list[CountBucket] = Field(default_factory=list)
    by_next_best_action: list[CountBucket] = Field(default_factory=list)
    by_agent_id: list[CountBucket] = Field(default_factory=list)

    trust_level: TrustLevelStats = Field(default_factory=TrustLevelStats)


# ─────────────────────────────────────────────────────────────────────
# Helpers d'agrégation
# ─────────────────────────────────────────────────────────────────────


def _now_utc() -> datetime:
    """Indirection pour faciliter le mocking en test."""
    return datetime.now(timezone.utc)


def _safe_pct(num: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * num / total, 2)


def _jsonb_path_text(json_path: tuple[str, ...]):
    """Construit une expression SQLAlchemy ``arguments_json->p1->...->>pN``.

    On chaîne ``->`` pour les niveaux intermédiaires (renvoient JSONB)
    et ``->>`` pour la feuille (renvoie ``text``). Cette forme évite
    le piège du ``#>>`` qui attend un *Postgres text array* et que
    SQLAlchemy sérialise en JSON array (provoque une ``DataError``
    "malformed array literal" sur les versions récentes du driver).
    """
    if not json_path:
        raise ValueError("json_path must not be empty")
    expr = AssistanceAgentDecision.arguments_json
    for key in json_path[:-1]:
        expr = expr.op("->")(key)
    return expr.op("->>")(json_path[-1])


def _aggregate_dimension(
    db: Session,
    *,
    column,
    json_path: tuple[str, ...],
    period_start: datetime,
    period_end: datetime,
) -> list[CountBucket]:
    """Agrège une dimension cognitive en distribution
    ``[{label, count, pct}]`` triée par count décroissant.

    Cognitive Bot v4 — Lot 6 (2026-05-04). Préfère la **colonne native**
    (migration 152) au chemin JSONB (Lots 1+2) via ``COALESCE`` : les
    décisions postérieures à la migration ont la colonne renseignée par
    le double-write ``service._persist_router_decision`` ; les
    décisions antérieures ont été backfillées par la migration ; le
    fallback JSONB couvre tout résidu.

    Les valeurs ``NULL`` (colonne **et** JSONB) sont comptées sous
    ``"unknown"`` plutôt qu'exclues — ce qui permet d'apprécier la
    couverture du pipeline cognitif (combien de décisions ont émis ce
    champ).
    """
    label_expr = func.coalesce(
        column,
        _jsonb_path_text(json_path),
        "unknown",
    ).label("label")
    count_expr = func.count().label("n")

    stmt = (
        select(label_expr, count_expr)
        .where(
            and_(
                AssistanceAgentDecision.tool_name == "router_classify",
                AssistanceAgentDecision.created_at >= period_start,
                AssistanceAgentDecision.created_at < period_end,
            )
        )
        .group_by(label_expr)
        .order_by(count_expr.desc(), label_expr.asc())
    )

    rows = db.execute(stmt).all()
    total = sum(int(r.n) for r in rows)
    return [
        CountBucket(
            label=str(r.label),
            count=int(r.n),
            pct=_safe_pct(int(r.n), total),
        )
        for r in rows
    ]


def _aggregate_jsonb_path(
    db: Session,
    *,
    json_path: tuple[str, ...],
    period_start: datetime,
    period_end: datetime,
) -> list[CountBucket]:
    """Variante legacy (Lot 5) qui n'agrège que sur le chemin JSONB.

    Conservée pour le CLI ``scripts/cognitive_funnel.py`` et les tests
    historiques. Les nouveaux callers doivent préférer
    ``_aggregate_dimension`` qui exploite les colonnes natives
    (migration 152).
    """
    if not json_path:
        return []
    text_expr = _jsonb_path_text(json_path)
    label_expr = func.coalesce(text_expr, "unknown").label("label")
    count_expr = func.count().label("n")
    stmt = (
        select(label_expr, count_expr)
        .where(
            and_(
                AssistanceAgentDecision.tool_name == "router_classify",
                AssistanceAgentDecision.created_at >= period_start,
                AssistanceAgentDecision.created_at < period_end,
            )
        )
        .group_by(label_expr)
        .order_by(count_expr.desc(), label_expr.asc())
    )
    rows = db.execute(stmt).all()
    total = sum(int(r.n) for r in rows)
    return [
        CountBucket(
            label=str(r.label),
            count=int(r.n),
            pct=_safe_pct(int(r.n), total),
        )
        for r in rows
    ]


def _aggregate_agent_id(
    db: Session,
    *,
    period_start: datetime,
    period_end: datetime,
) -> list[CountBucket]:
    """Distribution de ``arguments_json->>'agent_id'`` (l'agent
    finalement désigné par le router pour répondre).
    """
    text_expr = AssistanceAgentDecision.arguments_json.op("->>")("agent_id")
    label_expr = func.coalesce(text_expr, "unknown").label("label")
    count_expr = func.count().label("n")

    stmt = (
        select(label_expr, count_expr)
        .where(
            and_(
                AssistanceAgentDecision.tool_name == "router_classify",
                AssistanceAgentDecision.created_at >= period_start,
                AssistanceAgentDecision.created_at < period_end,
            )
        )
        .group_by(label_expr)
        .order_by(count_expr.desc(), label_expr.asc())
    )
    rows = db.execute(stmt).all()
    total = sum(int(r.n) for r in rows)
    return [
        CountBucket(
            label=str(r.label),
            count=int(r.n),
            pct=_safe_pct(int(r.n), total),
        )
        for r in rows
    ]


def _trust_level_stats(
    db: Session,
    *,
    period_start: datetime,
    period_end: datetime,
) -> TrustLevelStats:
    """Stats min/avg/max sur ``trust_level``.

    Cognitive Bot v4 — Lot 6 : préfère la colonne native
    ``AssistanceAgentDecision.trust_level`` (real, migration 152) ;
    fallback sur ``arguments_json #>> '{cognitive_state,trust_level}'``
    castée en float pour les décisions résiduelles non-backfillées.
    """
    jsonb_text = _jsonb_path_text(("cognitive_state", "trust_level"))
    jsonb_float = func.cast(func.nullif(jsonb_text, ""), Float())
    value_expr = func.coalesce(
        AssistanceAgentDecision.trust_level,
        jsonb_float,
    ).label("v")

    stmt = (
        select(
            func.avg(value_expr).label("avg"),
            func.min(value_expr).label("min"),
            func.max(value_expr).label("max"),
            func.count(value_expr).label("n"),
        )
        .where(
            and_(
                AssistanceAgentDecision.tool_name == "router_classify",
                AssistanceAgentDecision.created_at >= period_start,
                AssistanceAgentDecision.created_at < period_end,
                value_expr.isnot(None),
            )
        )
    )
    row = db.execute(stmt).one_or_none()
    if row is None or row.n in (None, 0):
        return TrustLevelStats(sample_size=0)
    return TrustLevelStats(
        avg=float(row.avg) if row.avg is not None else None,
        min=float(row.min) if row.min is not None else None,
        max=float(row.max) if row.max is not None else None,
        sample_size=int(row.n or 0),
    )


# ─────────────────────────────────────────────────────────────────────
# Endpoint GET /funnel
# ─────────────────────────────────────────────────────────────────────


@admin_cognitive_router.get(
    "/funnel",
    response_model=CognitiveFunnelResponse,
    summary="Funnel cognitif (Cognitive Bot v4)",
)
def get_cognitive_funnel(
    period_days: int = Query(7, ge=1, le=90),
    actor: ActorContext = Depends(_guard),
    db: Session = Depends(get_db),
) -> CognitiveFunnelResponse:
    """Retourne la distribution des dimensions cognitives sur la
    fenêtre ``[now - period_days, now)``.

    Aucun argument personnel — c'est une vue admin **agrégée**, sans
    PII. Sécurité : ``require_admin_or_ops()``.
    """
    period_end = _now_utc()
    period_start = period_end - timedelta(days=int(period_days))

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

    total = sum(b.count for b in by_agent)

    return CognitiveFunnelResponse(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        period_days=int(period_days),
        total_decisions=total,
        by_stage=by_stage,
        by_emotional_intent=by_emotional,
        by_primary_goal=by_primary,
        by_next_best_action=by_nba,
        by_agent_id=by_agent,
        trust_level=_trust_level_stats(
            db,
            period_start=period_start,
            period_end=period_end,
        ),
    )
