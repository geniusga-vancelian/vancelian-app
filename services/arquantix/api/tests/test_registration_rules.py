"""Tests for the Registration Rules Engine V1."""
import pytest

from services.registration.rules import evaluate_rule, filter_visible_items


class TestEquals:
    def test_match(self):
        assert evaluate_rule({"field": "country", "operator": "equals", "value": "FR"}, {"country": "FR"}) is True

    def test_no_match(self):
        assert evaluate_rule({"field": "country", "operator": "equals", "value": "FR"}, {"country": "DE"}) is False

    def test_missing_field(self):
        assert evaluate_rule({"field": "country", "operator": "equals", "value": "FR"}, {}) is False


class TestNotEquals:
    def test_match(self):
        assert evaluate_rule({"field": "x", "operator": "not_equals", "value": "a"}, {"x": "b"}) is True

    def test_no_match(self):
        assert evaluate_rule({"field": "x", "operator": "not_equals", "value": "a"}, {"x": "a"}) is False


class TestIn:
    def test_match(self):
        assert evaluate_rule({"field": "tier", "operator": "in", "values": ["low", "medium"]}, {"tier": "low"}) is True

    def test_no_match(self):
        assert evaluate_rule({"field": "tier", "operator": "in", "values": ["low", "medium"]}, {"tier": "high"}) is False


class TestNotIn:
    def test_match(self):
        assert evaluate_rule({"field": "tier", "operator": "not_in", "values": ["low"]}, {"tier": "high"}) is True


class TestExists:
    def test_exists(self):
        assert evaluate_rule({"field": "email", "operator": "exists"}, {"email": "a@b.com"}) is True

    def test_not_exists(self):
        assert evaluate_rule({"field": "email", "operator": "exists"}, {}) is False


class TestNotExists:
    def test_present(self):
        assert evaluate_rule({"field": "email", "operator": "not_exists"}, {"email": "a@b.com"}) is False

    def test_absent(self):
        assert evaluate_rule({"field": "email", "operator": "not_exists"}, {}) is True


class TestComposite:
    def test_all_of_pass(self):
        rule = {"operator": "all_of", "rules": [
            {"field": "a", "operator": "equals", "value": "1"},
            {"field": "b", "operator": "equals", "value": "2"},
        ]}
        assert evaluate_rule(rule, {"a": "1", "b": "2"}) is True

    def test_all_of_fail(self):
        rule = {"operator": "all_of", "rules": [
            {"field": "a", "operator": "equals", "value": "1"},
            {"field": "b", "operator": "equals", "value": "2"},
        ]}
        assert evaluate_rule(rule, {"a": "1", "b": "3"}) is False

    def test_any_of_pass(self):
        rule = {"operator": "any_of", "rules": [
            {"field": "a", "operator": "equals", "value": "X"},
            {"field": "a", "operator": "equals", "value": "Y"},
        ]}
        assert evaluate_rule(rule, {"a": "Y"}) is True

    def test_any_of_fail(self):
        rule = {"operator": "any_of", "rules": [
            {"field": "a", "operator": "equals", "value": "X"},
            {"field": "a", "operator": "equals", "value": "Y"},
        ]}
        assert evaluate_rule(rule, {"a": "Z"}) is False


class TestEdgeCases:
    def test_none_rule(self):
        assert evaluate_rule(None, {"x": "y"}) is True

    def test_empty_rule(self):
        assert evaluate_rule({}, {"x": "y"}) is True

    def test_unknown_operator(self):
        assert evaluate_rule({"field": "x", "operator": "banana", "value": "1"}, {"x": "1"}) is True
