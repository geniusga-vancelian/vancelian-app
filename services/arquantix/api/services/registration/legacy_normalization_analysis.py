"""Analysis, validation gates, and delta reporting for legacy normalization JSON reports.

Pure functions on report dicts — no DB, no mutation of legacy_normalization logic.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# Human-readable aliases for reason_codes (console)
REASON_DISPLAY = {
    "unknown_component_type": "UNKNOWN_COMPONENT_TYPE",
    "field_bound_missing_binding_and_fd": "MISSING_BINDING_AND_FIELD_DEF",
    "orphan_field_definition_id": "ORPHAN_FIELD_DEFINITION_ID",
    "no_field_definition_for_binding": "NO_FIELD_MATCH",
    "multiple_field_definitions_for_binding": "MULTIPLE_FIELD_MATCH",
    "content_has_binding_or_field_def": "CONTENT_HAS_BINDING_OR_FD",
}


def load_report(path: Union[str, Path]) -> Dict[str, Any]:
    """Load a JSON report written by run_registration_legacy_normalization or API."""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        return json.load(f)


@dataclass
class LegacyReportAnalysis:
    total_components: int
    ok_count: int
    auto_fixable_count: int
    ambiguous_count: int
    pct_auto_fixable: float
    pct_ambiguous: float
    top_ambiguous_reasons: List[Tuple[str, int]]
    top_ambiguous_bindings: List[Tuple[str, int]]
    flows_total: int
    publishable_before: int
    blocked_before: int
    publishable_after_reported: Optional[int]
    blocked_after_reported: Optional[int]
    estimated_publishable_after_heuristic: int
    dangerous_unknown_type_count: int
    dangerous_orphan_fd_count: int
    multiple_field_match_count: int


def analyze_legacy_normalization_report(data: Dict[str, Any]) -> LegacyReportAnalysis:
    """
    Compute structured metrics from a report dict (dry-run, diagnose, or post-apply).

    ``estimated_publishable_after_heuristic`` is an optimistic upper bound:
    publishable today + blocked flows that contain at least one auto-fixable component.
    """
    totals = data.get("totals") or {}
    total = int(totals.get("components_total", 0))
    ok_c = int(totals.get("ok", 0))
    auto_c = int(totals.get("auto_fixable", 0))
    amb_c = int(totals.get("ambiguous", 0))

    if total <= 0:
        total = ok_c + auto_c + amb_c

    pct_auto = (100.0 * auto_c / total) if total else 0.0
    pct_amb = (100.0 * amb_c / total) if total else 0.0

    reason_counter: Counter[str] = Counter()
    binding_counter: Counter[str] = Counter()
    unknown_type = 0
    orphan_fd = 0
    multi_match = 0

    for row in data.get("ambiguous") or []:
        rcs = row.get("reason_codes") or []
        for rc in rcs:
            reason_counter[rc] += 1
        rset = set(rcs)
        if "unknown_component_type" in rset:
            unknown_type += 1
        if "orphan_field_definition_id" in rset:
            orphan_fd += 1
        if "multiple_field_definitions_for_binding" in rset:
            multi_match += 1
        bs = row.get("binding_slug")
        if bs:
            binding_counter[str(bs)] += 1

    top_reasons = reason_counter.most_common(15)
    top_bindings = binding_counter.most_common(15)

    hb = data.get("health_before") or {}
    flows = hb.get("flows") or []
    pub_b = int(hb.get("publishable", 0))
    blk_b = int(hb.get("blocked", 0))
    ft = int(hb.get("flows_total", len(flows)))

    ha = data.get("health_after")
    pub_a = blk_a = None
    if isinstance(ha, dict) and ha.get("flows_total") is not None:
        pub_a = int(ha.get("publishable", 0))
        blk_a = int(ha.get("blocked", 0))

    flow_by_id = {str(f.get("flow_id")): f for f in flows if f.get("flow_id")}
    touched_blocked: set = set()
    for row in data.get("auto_fixable") or []:
        fid = row.get("flow_id")
        if not fid:
            continue
        f = flow_by_id.get(str(fid))
        if f and f.get("can_publish") is False:
            touched_blocked.add(str(fid))

    est_after = min(ft, pub_b + len(touched_blocked)) if ft else pub_b

    return LegacyReportAnalysis(
        total_components=total,
        ok_count=ok_c,
        auto_fixable_count=auto_c,
        ambiguous_count=amb_c,
        pct_auto_fixable=round(pct_auto, 2),
        pct_ambiguous=round(pct_amb, 2),
        top_ambiguous_reasons=top_reasons,
        top_ambiguous_bindings=top_bindings,
        flows_total=ft,
        publishable_before=pub_b,
        blocked_before=blk_b,
        publishable_after_reported=pub_a,
        blocked_after_reported=blk_a,
        estimated_publishable_after_heuristic=est_after,
        dangerous_unknown_type_count=unknown_type,
        dangerous_orphan_fd_count=orphan_fd,
        multiple_field_match_count=multi_match,
    )


def format_console_analysis(a: LegacyReportAnalysis) -> str:
    """Human-readable block for terminal."""
    lines = [
        "==== LEGACY NORMALIZATION REPORT ====",
        f"Total components: {a.total_components}",
        f"OK: {a.ok_count}",
        f"Auto-fixable: {a.auto_fixable_count} ({a.pct_auto_fixable}%)",
        f"Ambiguous: {a.ambiguous_count} ({a.pct_ambiguous}%)",
        "",
        "Top ambiguous reasons:",
    ]
    for rc, n in a.top_ambiguous_reasons:
        disp = REASON_DISPLAY.get(rc, rc)
        lines.append(f"  - {disp}: {n}")
    if not a.top_ambiguous_reasons:
        lines.append("  (none)")

    lines.extend(["", "Top ambiguous binding_slug (non résolus):"])
    for slug, n in a.top_ambiguous_bindings:
        lines.append(f"  - {slug!r}: {n}")
    if not a.top_ambiguous_bindings:
        lines.append("  (none)")

    lines.extend(
        [
            "",
            "Dangerous signals:",
            f"  - Unknown component_type rows: {a.dangerous_unknown_type_count}",
            f"  - Orphan field_definition_id rows: {a.dangerous_orphan_fd_count}",
            f"  - MULTIPLE_FIELD_MATCH (ambiguous rows): {a.multiple_field_match_count}",
            "",
            "Flows publishable:",
            f"  - Before (report): {a.publishable_before} / {a.flows_total}",
        ]
    )
    if a.publishable_after_reported is not None:
        lines.append(
            f"  - After (report): {a.publishable_after_reported} / {a.flows_total}"
        )
    lines.append(
        f"  - After (heuristic upper bound): {a.estimated_publishable_after_heuristic} / {a.flows_total}"
    )
    lines.append(
        "    (heuristic = blocked flows touched by auto-fix list may become publishable; not guaranteed)"
    )
    return "\n".join(lines)


@dataclass
class ValidationResult:
    safe: bool
    blockers: List[str]


def validate_safe_to_apply(
    analysis: LegacyReportAnalysis,
    *,
    max_ambiguous_pct: float = 10.0,
    max_multiple_match_abs: int = 50,
    max_multiple_match_pct_of_ambiguous: float = 30.0,
    max_orphan_fd_abs: int = 100,
) -> ValidationResult:
    """
    Gate before apply. Conservative defaults; tune per environment.

    Blocks if:
    - ambiguous share of all components > max_ambiguous_pct
    - MULTIPLE_FIELD_MATCH count > max_multiple_match_abs OR > % of ambiguous rows
    - orphan field_definition_id count > max_orphan_fd_abs (massive inconsistency)
    """
    blockers: List[str] = []

    if analysis.total_components > 0 and analysis.pct_ambiguous > max_ambiguous_pct:
        blockers.append(
            f"Ambiguous ratio {analysis.pct_ambiguous}% > threshold {max_ambiguous_pct}% "
            f"({analysis.ambiguous_count} / {analysis.total_components})"
        )

    if analysis.multiple_field_match_count > max_multiple_match_abs:
        blockers.append(
            f"MULTIPLE_FIELD_MATCH count {analysis.multiple_field_match_count} > {max_multiple_match_abs}"
        )

    if analysis.ambiguous_count > 0:
        m_pct = 100.0 * analysis.multiple_field_match_count / analysis.ambiguous_count
        if m_pct > max_multiple_match_pct_of_ambiguous and analysis.multiple_field_match_count >= 3:
            blockers.append(
                f"MULTIPLE_FIELD_MATCH share {m_pct:.1f}% of ambiguous > {max_multiple_match_pct_of_ambiguous}% "
                f"(count={analysis.multiple_field_match_count})"
            )

    if analysis.dangerous_orphan_fd_count > max_orphan_fd_abs:
        blockers.append(
            f"Orphan field_definition_id rows {analysis.dangerous_orphan_fd_count} > {max_orphan_fd_abs}"
        )

    return ValidationResult(safe=len(blockers) == 0, blockers=blockers)


def format_validation_result(v: ValidationResult, analysis: LegacyReportAnalysis) -> str:
    if v.safe:
        return (
            f"Safe to apply auto-fixes ({analysis.auto_fixable_count} component(s) will be updated).\n"
            "Confirm explicitly before apply (CLI prompt or API {\"confirm\": true})."
        )
    lines = ["NOT safe to apply — resolve blockers first:", ""]
    lines.extend(f"  - {b}" for b in v.blockers)
    return "\n".join(lines)


def count_actions_in_applied(applied: List[Dict[str, Any]]) -> Dict[str, int]:
    c: Counter[str] = Counter()
    for row in applied or []:
        act = row.get("action") or "unknown"
        c[act] += 1
    return dict(c)


def compute_post_apply_delta(
    before: Dict[str, Any],
    after: Dict[str, Any],
    apply_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compare two dry-run style reports + optional apply payload for action counts."""
    ab = analyze_legacy_normalization_report(before)
    aa = analyze_legacy_normalization_report(after)
    actions = count_actions_in_applied((apply_report or {}).get("applied") or [])

    hb0 = before.get("health_before") or {}
    hb1 = after.get("health_before") or {}

    return {
        "auto_fixable": {"before": ab.auto_fixable_count, "after": aa.auto_fixable_count},
        "ambiguous": {"before": ab.ambiguous_count, "after": aa.ambiguous_count},
        "ok": {"before": ab.ok_count, "after": aa.ok_count},
        "publishable_flows": {
            "before": ab.publishable_before,
            "after": aa.publishable_before,
        },
        "blocked_flows": {
            "before": ab.blocked_before,
            "after": aa.blocked_before,
        },
        "flows_total": ab.flows_total,
        "actions_from_apply_report": actions,
    }


def format_post_apply_delta(delta: Dict[str, Any]) -> str:
    af = delta["auto_fixable"]
    amb = delta["ambiguous"]
    pub = delta["publishable_flows"]
    blk = delta["blocked_flows"]
    lines = [
        "==== POST APPLY DELTA ====",
        f"Auto-fixable: {af['before']} → {af['after']}",
        f"Ambiguous: {amb['before']} → {amb['after']}",
        f"Publishable flows: {pub['before']} → {pub['after']}",
        f"Blocked flows: {blk['before']} → {blk['after']}",
        "",
        "Actions (from apply report):",
    ]
    for k, v in sorted((delta.get("actions_from_apply_report") or {}).items()):
        lines.append(f"  - {k}: {v}")
    if not delta.get("actions_from_apply_report"):
        lines.append("  (no apply report provided)")
    return "\n".join(lines)


def build_execution_summary_markdown(
    delta: Dict[str, Any],
    before_report: Dict[str, Any],
    after_report: Dict[str, Any],
    apply_report: Optional[Dict[str, Any]] = None,
) -> str:
    """Content for REGISTRATION_LEGACY_NORMALIZATION_EXECUTION_SUMMARY.md."""
    totals0 = before_report.get("totals") or {}
    ar = apply_report or {}
    applied = ar.get("applied") or []

    amb_list = after_report.get("ambiguous") or []
    actions = count_actions_in_applied(applied)

    af = delta["auto_fixable"]
    pub = delta["publishable_flows"]
    blk = delta["blocked_flows"]

    lines = [
        "## Summary",
        "",
        f"- Total components (last scan): {totals0.get('components_total', '—')}",
        f"- Auto-fix applied (rows in apply report): {len(applied)}",
        f"- Ambiguous remaining: {delta['ambiguous']['after']}",
        "",
        "## Before vs After",
        "",
        f"- Publishable flows: {pub['before']} → {pub['after']}",
        f"- Blocked flows: {blk['before']} → {blk['after']}",
        "",
        "## Key Fixes",
        "",
    ]
    act_show = actions or (delta.get("actions_from_apply_report") or {})
    for k, v in sorted(act_show.items()):
        lines.append(f"- {k}: {v}")
    if not act_show:
        lines.append("- (see apply JSON `applied` array)")

    lines.extend(["", "## Remaining Issues", "", "Ambiguous components (sample ids):"])
    for row in amb_list[:50]:
        cid = row.get("component_id", "?")
        lines.append(f"- `{cid}` — {row.get('reason_codes')} — type={row.get('component_type')}")
    if len(amb_list) > 50:
        lines.append(f"- … and {len(amb_list) - 50} more (full list in after JSON)")

    return "\n".join(lines) + "\n"
