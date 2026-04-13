"""Governance rule JSON validation — legacy vs structured shapes."""
import services.registration.governance as gov
from services.registration.governance import HealthReport


def test_legacy_validation_rule_json_no_false_warnings():
    rep = HealthReport()
    gov._validate_rule_json({"type": "required"}, "validation", "step-1", None, None, rep)
    assert rep.warnings == []


def test_non_dict_rule_json_warns():
    rep = HealthReport()
    gov._validate_rule_json("not-an-object", "visibility", "step-1", None, None, rep)
    assert len(rep.warnings) == 1


def test_structured_rule_missing_field_warns():
    rep = HealthReport()
    gov._validate_rule_json({"operator": "equals", "value": "x"}, "validation", "step-1", None, None, rep)
    assert any("missing 'field'" in w.message for w in rep.warnings)
