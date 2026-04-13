"""
Tests for project_type extraction.
"""
from services.chatbot_epargne.ai.agents import extractor


def _extract_project_type(text: str):
    out = extractor.run_extractor([{"role": "user", "content": text}], {}, [])
    extracted = {e["field"]: e["value"] for e in (out.get("extracted") or [])}
    return extracted.get("project_type"), extracted.get("project_type_confidence")


def test_project_type_buy_something():
    ptype, conf = _extract_project_type("je veux un sac Chanel")
    assert ptype == "buy_something"
    assert float(conf) >= 0.7


def test_project_type_live_better():
    ptype, conf = _extract_project_type("je veux finir le mois plus à l'aise")
    assert ptype == "live_better"
    assert float(conf) >= 0.7


def test_project_type_prepare_future():
    ptype, conf = _extract_project_type("préparer ma retraite")
    assert ptype == "prepare_future"
    assert float(conf) >= 0.7


def test_project_type_protect_family():
    ptype, conf = _extract_project_type("pour les études de mes enfants")
    assert ptype == "protect_family"
    assert float(conf) >= 0.7


def test_project_type_experiences():
    ptype, conf = _extract_project_type("voyage à NYC")
    assert ptype == "experiences"
    assert float(conf) >= 0.7


def test_project_type_grow_money():
    ptype, conf = _extract_project_type("faire travailler mon argent")
    assert ptype == "grow_money"
    assert float(conf) >= 0.7


def test_project_type_ambiguous_confidence_low():
    ptype, conf = _extract_project_type("je veux un projet pour ma famille et investir")
    assert ptype in ("other", "protect_family", "grow_money")
    assert float(conf) < 0.7


def test_project_type_other():
    ptype, conf = _extract_project_type("je ne sais pas trop")
    assert ptype == "other"
    assert float(conf) <= 0.4
