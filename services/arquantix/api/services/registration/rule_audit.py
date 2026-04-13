"""Batched visibility rule evaluation snapshots for audit (read-only, no runtime change)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from database import RegistrationFlow

from .masking import mask_context_subset
from .rules import evaluate_rule


def extract_rule_referenced_fields(rule: Optional[Dict[str, Any]]) -> Set[str]:
    if not rule:
        return set()
    op = rule.get("operator")
    if op in ("all_of", "any_of"):
        return set().union(
            *(extract_rule_referenced_fields(r) for r in rule.get("rules", []))
        )
    field = rule.get("field")
    if field:
        return {str(field)}
    return set()


def build_visibility_evaluation_batch(
    flow: RegistrationFlow,
    context: Dict[str, Any],
    *,
    max_items: int = 80,
    batch_source: str = "runtime",
) -> List[Dict[str, Any]]:
    """Collect visibility rule outcomes for all steps / screens / components (ordered).

    Does not change which items are visible at runtime; mirrors evaluation for audit.
    """
    evaluations: List[Dict[str, Any]] = []
    steps = sorted(flow.steps or [], key=lambda s: s.position)

    for step in steps:
        if len(evaluations) >= max_items:
            break
        rule = step.visibility_rule_json
        if rule:
            result = evaluate_rule(rule, context)
            fields = extract_rule_referenced_fields(rule)
            evaluations.append({
                "scope": "step",
                "step_key": step.step_key,
                "screen_key": None,
                "component_key": None,
                "rule_type": "visibility",
                "rule_json": rule,
                "result": result,
                "resolved_values": mask_context_subset(context, fields),
            })
        step_visible = evaluate_rule(rule, context) if rule else True
        if not step_visible:
            continue

        screens = sorted(step.screens or [], key=lambda sc: sc.position)
        for screen in screens:
            if len(evaluations) >= max_items:
                break
            # Screens have no visibility_rule_json in the current schema; only steps/components do.
            comps = sorted(screen.components or [], key=lambda c: c.position)
            for comp in comps:
                if len(evaluations) >= max_items:
                    break
                crule = comp.visibility_rule_json
                if not crule:
                    continue
                result = evaluate_rule(crule, context)
                fields = extract_rule_referenced_fields(crule)
                evaluations.append({
                    "scope": "component",
                    "step_key": step.step_key,
                    "screen_key": screen.screen_key,
                    "component_key": comp.component_key,
                    "rule_type": "visibility",
                    "rule_json": crule,
                    "result": result,
                    "resolved_values": mask_context_subset(context, fields),
                })

    return evaluations
