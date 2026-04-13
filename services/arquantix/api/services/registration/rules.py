"""Registration Flow Rules Engine V1.

Evaluates visibility and completion rules expressed as JSON.

Supported operators:
  - equals   : field == value
  - not_equals: field != value
  - in       : field in [values]
  - not_in   : field not in [values]
  - exists   : field is present and non-null
  - not_exists: field is null or absent
  - all_of   : all sub-rules must pass (AND)
  - any_of   : at least one sub-rule must pass (OR)

Rule format:
  {"field": "country", "operator": "equals", "value": "UAE"}
  {"operator": "all_of", "rules": [...]}
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def evaluate_rule(rule: Optional[Dict[str, Any]], context: Dict[str, Any]) -> bool:
    """Evaluate a single rule against a data context.

    Args:
        rule: Rule definition (JSON dict). None or empty → always True.
        context: Flat dict of field_slug → value collected so far.

    Returns:
        True if the rule passes (item is visible / step is complete).
    """
    if not rule:
        return True

    operator = rule.get("operator", "equals")

    if operator == "all_of":
        return all(evaluate_rule(r, context) for r in rule.get("rules", []))

    if operator == "any_of":
        return any(evaluate_rule(r, context) for r in rule.get("rules", []))

    field = rule.get("field")
    if field is None:
        return True

    field_value = context.get(field)
    target = rule.get("value")

    if operator == "equals":
        return field_value == target

    if operator == "not_equals":
        return field_value != target

    if operator == "in":
        values = rule.get("values", rule.get("value", []))
        if not isinstance(values, list):
            values = [values]
        return field_value in values

    if operator == "not_in":
        values = rule.get("values", rule.get("value", []))
        if not isinstance(values, list):
            values = [values]
        return field_value not in values

    if operator == "exists":
        return field_value is not None

    if operator == "not_exists":
        return field_value is None

    logger.warning("Unknown rule operator '%s', defaulting to True", operator)
    return True


def evaluate_rules_list(rules: Optional[List[Dict[str, Any]]], context: Dict[str, Any]) -> bool:
    """Evaluate a list of rules as AND (all must pass)."""
    if not rules:
        return True
    return all(evaluate_rule(r, context) for r in rules)


def filter_visible_items(items: list, context: Dict[str, Any], rule_attr: str = "visibility_rule_json") -> list:
    """Filter a list of ORM objects by their visibility rule."""
    return [item for item in items if evaluate_rule(getattr(item, rule_attr, None), context)]
