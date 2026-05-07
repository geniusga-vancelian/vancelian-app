"""Admin read-only — observabilité Assistance (PR 4B).

Préfixe ``/api/admin/assistance/observability`` :

  * ``GET /summary`` — volume tours router, tours avec data_need « lourd »,
    nombre de gaps policy ``policy_data_need_reads``, taux.
  * ``GET /data-need-gaps`` — répartition gaps par agent, data_need, jour ;
    fréquence des ``expected_read_tools`` persistés sur les lignes gap.
  * ``GET /tool-usage`` — volume d’appels par ``tool_name`` (hors
    ``router_classify`` / ``policy_data_need_reads``).

Définitions :

  * **total_turns** : décisions ``router_classify`` dans la fenêtre
    (un tour utilisateur traité par le routeur ≈ une ligne).
  * **turns_with_data_need** : sous-ensemble dont
    ``arguments_json->orchestration->>data_need`` est l’un de
    ``transaction_data`` / ``account_data`` / ``kyc_data``.
  * **data_need_gap_rate** : ``data_need_gap_count / turns_with_data_need``
    (0 % si le dénominateur est nul).

Source : table ``assistance_agent_decisions`` uniquement (pas de JSONL).

Auth : ``require_admin_or_ops()`` — aligné sur ``admin_cognitive_router``.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from database import AssistanceAgentDecision, get_db
from services.assistance.data_need_read_policy import DATA_NEEDS_REQUIRING_READ
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import (
    require_admin_or_ops,
)

admin_observability_router = APIRouter(
    prefix="/api/admin/assistance/observability",
    tags=["assistance-admin-observability"],
)
_guard = require_admin_or_ops()

_DATA_NEED_VALUES: tuple[str, ...] = tuple(sorted(DATA_NEEDS_REQUIRING_READ))

_ORCH_DATA_NEED = AssistanceAgentDecision.arguments_json.op("->")(
    "orchestration"
).op("->>")("data_need")

_EXCLUDED_FROM_TOOL_USAGE = ("router_classify", "policy_data_need_reads")


# ─────────────────────────────────────────────────────────────────────
# Schémas
# ─────────────────────────────────────────────────────────────────────


class CountBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    count: int
    pct: float = 0.0


class ObservabilitySummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: str
    period_end: str
    period_days: int
    total_turns: int
    turns_with_data_need: int
    data_need_gap_count: int
    data_need_gap_rate: float = Field(
        description=(
            "Pourcentage de gaps sur turns_with_data_need "
            "(0 si dénominateur nul)."
        )
    )


class DataNeedGapsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: str
    period_end: str
    period_days: int
    data_need_gap_count: int
    gap_by_agent: list[CountBucket] = Field(default_factory=list)
    gap_by_data_need: list[CountBucket] = Field(default_factory=list)
    gap_by_day: list[CountBucket] = Field(default_factory=list)
    top_missing_tools: list[CountBucket] = Field(
        default_factory=list,
        description=(
            "Fréquence des entrées ``expected_read_tools`` sur les lignes gap "
            "(liste allowlist au moment du gap)."
        ),
    )


class ToolUsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: str
    period_end: str
    period_days: int
    total_tool_calls: int
    tools: list[CountBucket] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _safe_pct(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return round(100.0 * num / den, 2)


def _period_bounds(*, period_days: int) -> tuple[datetime, datetime]:
    period_end = _now_utc()
    pd = max(1, min(90, int(period_days)))
    period_start = period_end - timedelta(days=pd)
    return period_start, period_end


def _router_time_filter(period_start: datetime, period_end: datetime):
    return and_(
        AssistanceAgentDecision.tool_name == "router_classify",
        AssistanceAgentDecision.created_at >= period_start,
        AssistanceAgentDecision.created_at < period_end,
    )


def _count_router_turns(db: Session, period_start: datetime, period_end: datetime) -> int:
    stmt = (
        select(func.count())
        .select_from(AssistanceAgentDecision)
        .where(_router_time_filter(period_start, period_end))
    )
    return int(db.execute(stmt).scalar() or 0)


def _count_turns_with_data_need(
    db: Session, period_start: datetime, period_end: datetime
) -> int:
    stmt = (
        select(func.count())
        .select_from(AssistanceAgentDecision)
        .where(
            and_(
                _router_time_filter(period_start, period_end),
                func.lower(func.trim(_ORCH_DATA_NEED)).in_(_DATA_NEED_VALUES),
            )
        )
    )
    return int(db.execute(stmt).scalar() or 0)


def _count_data_need_gaps(
    db: Session, period_start: datetime, period_end: datetime
) -> int:
    stmt = (
        select(func.count())
        .select_from(AssistanceAgentDecision)
        .where(
            and_(
                AssistanceAgentDecision.tool_name == "policy_data_need_reads",
                AssistanceAgentDecision.created_at >= period_start,
                AssistanceAgentDecision.created_at < period_end,
            )
        )
    )
    return int(db.execute(stmt).scalar() or 0)


def _aggregate_gap_buckets(
    db: Session,
    *,
    period_start: datetime,
    period_end: datetime,
) -> tuple[int, list[CountBucket], list[CountBucket], list[CountBucket], list[CountBucket]]:
    base_filter = and_(
        AssistanceAgentDecision.tool_name == "policy_data_need_reads",
        AssistanceAgentDecision.created_at >= period_start,
        AssistanceAgentDecision.created_at < period_end,
    )

    gap_total = (
        db.query(func.count())
        .select_from(AssistanceAgentDecision)
        .filter(base_filter)
        .scalar()
    )
    gap_total = int(gap_total or 0)

    agent_expr = AssistanceAgentDecision.agent_id.label("agent")
    stmt_agent = (
        select(agent_expr, func.count().label("n"))
        .where(base_filter)
        .group_by(agent_expr)
        .order_by(func.count().desc())
    )
    rows_a = db.execute(stmt_agent).all()
    by_agent = [
        CountBucket(
            label=str(r.agent),
            count=int(r.n),
            pct=_safe_pct(int(r.n), gap_total),
        )
        for r in rows_a
    ]

    dn_expr = func.coalesce(
        AssistanceAgentDecision.arguments_json.op("->>")("data_need"),
        "unknown",
    ).label("dn")
    stmt_dn = (
        select(dn_expr, func.count().label("n"))
        .where(base_filter)
        .group_by(dn_expr)
        .order_by(func.count().desc())
    )
    rows_d = db.execute(stmt_dn).all()
    by_dn = [
        CountBucket(label=str(r.dn), count=int(r.n), pct=_safe_pct(int(r.n), gap_total))
        for r in rows_d
    ]

    day_expr = func.date_trunc("day", AssistanceAgentDecision.created_at).label(
        "day_bucket"
    )
    stmt_day = (
        select(day_expr, func.count().label("n"))
        .where(base_filter)
        .group_by(day_expr)
        .order_by(day_expr.asc())
    )
    rows_day = db.execute(stmt_day).all()
    by_day: list[CountBucket] = []
    for r in rows_day:
        ts = r.day_bucket
        if isinstance(ts, datetime):
            lbl = ts.astimezone(timezone.utc).date().isoformat()
        else:
            lbl = str(ts)[:10]
        by_day.append(
            CountBucket(
                label=lbl,
                count=int(r.n),
                pct=_safe_pct(int(r.n), gap_total),
            )
        )

    raw = (
        db.query(AssistanceAgentDecision.arguments_json)
        .filter(base_filter)
        .all()
    )
    tool_ctr: Counter[str] = Counter()
    for (arg,) in raw:
        if not isinstance(arg, dict):
            continue
        arr = arg.get("expected_read_tools")
        if isinstance(arr, list):
            for t in arr:
                s = str(t).strip()
                if s:
                    tool_ctr[s] += 1
    top_tools_total = sum(tool_ctr.values())
    top_missing = [
        CountBucket(
            label=lbl,
            count=n,
            pct=_safe_pct(n, top_tools_total),
        )
        for lbl, n in tool_ctr.most_common(20)
    ]

    return gap_total, by_agent, by_dn, by_day, top_missing


def _aggregate_tool_usage(
    db: Session, period_start: datetime, period_end: datetime
) -> tuple[int, list[CountBucket]]:
    stmt = (
        select(AssistanceAgentDecision.tool_name, func.count().label("n"))
        .where(
            and_(
                AssistanceAgentDecision.created_at >= period_start,
                AssistanceAgentDecision.created_at < period_end,
                AssistanceAgentDecision.tool_name.notin_(_EXCLUDED_FROM_TOOL_USAGE),
            )
        )
        .group_by(AssistanceAgentDecision.tool_name)
        .order_by(func.count().desc(), AssistanceAgentDecision.tool_name.asc())
    )
    rows = db.execute(stmt).all()
    total = sum(int(r.n) for r in rows)
    tools = [
        CountBucket(
            label=str(r.tool_name),
            count=int(r.n),
            pct=_safe_pct(int(r.n), total),
        )
        for r in rows
    ]
    return total, tools


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────


@admin_observability_router.get(
    "/summary",
    response_model=ObservabilitySummaryResponse,
    summary="Vue synthèse observabilité assistance",
)
def get_observability_summary(
    period_days: int = Query(7, ge=1, le=90),
    _: ActorContext = Depends(_guard),
    db: Session = Depends(get_db),
) -> ObservabilitySummaryResponse:
    period_start, period_end = _period_bounds(period_days=period_days)
    pd = max(1, min(90, int(period_days)))

    total_turns = _count_router_turns(db, period_start, period_end)
    turns_with_data_need = _count_turns_with_data_need(db, period_start, period_end)
    gap_count = _count_data_need_gaps(db, period_start, period_end)
    gap_rate = _safe_pct(gap_count, turns_with_data_need)

    return ObservabilitySummaryResponse(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        period_days=pd,
        total_turns=total_turns,
        turns_with_data_need=turns_with_data_need,
        data_need_gap_count=gap_count,
        data_need_gap_rate=gap_rate,
    )


@admin_observability_router.get(
    "/data-need-gaps",
    response_model=DataNeedGapsResponse,
    summary="Répartition des gaps data_need (policy)",
)
def get_data_need_gaps(
    period_days: int = Query(7, ge=1, le=90),
    _: ActorContext = Depends(_guard),
    db: Session = Depends(get_db),
) -> DataNeedGapsResponse:
    period_start, period_end = _period_bounds(period_days=period_days)
    pd = max(1, min(90, int(period_days)))

    gap_total, by_agent, by_dn, by_day, top_missing = _aggregate_gap_buckets(
        db,
        period_start=period_start,
        period_end=period_end,
    )

    return DataNeedGapsResponse(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        period_days=pd,
        data_need_gap_count=gap_total,
        gap_by_agent=by_agent,
        gap_by_data_need=by_dn,
        gap_by_day=by_day,
        top_missing_tools=top_missing,
    )


@admin_observability_router.get(
    "/tool-usage",
    response_model=ToolUsageResponse,
    summary="Volume d'appels par outil (hors routeur / policy gap)",
)
def get_tool_usage(
    period_days: int = Query(7, ge=1, le=90),
    _: ActorContext = Depends(_guard),
    db: Session = Depends(get_db),
) -> ToolUsageResponse:
    period_start, period_end = _period_bounds(period_days=period_days)
    pd = max(1, min(90, int(period_days)))

    total_calls, tools = _aggregate_tool_usage(db, period_start, period_end)

    return ToolUsageResponse(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        period_days=pd,
        total_tool_calls=total_calls,
        tools=tools,
    )
