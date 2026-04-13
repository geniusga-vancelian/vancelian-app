"""Parcours d’activation Home — logique métier + projection profil."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import Person
from services.activation_journey import (
    build_activation_journey,
    should_show_registration_resume,
)
from services.portfolio_engine.clients.models import Client
from tests.conftest import make_linked_client


def test_should_show_registration_resume_partial() -> None:
    assert should_show_registration_resume(
        client_status="PARTIAL",
        registration_macro_stage=None,
        registration_completion_ratio=None,
        registration_derived_total_count=None,
        registration_derived_completed_count=None,
        registration_missing_steps=None,
        registration_derived_next_step_key=None,
        registration_derived_progress_percent=None,
    )


def test_build_activation_registration_complete_still_needs_deposit_invest(
    db: Session,
) -> None:
    pe = make_linked_client(db)
    person = db.query(Person).filter(Person.id == pe.person_id).first()
    assert person is not None
    profile_dict = {
        "client_status": "ACTIVE",
        "registration_macro_stage": "active_client",
        "registration_completion_ratio": 1.0,
        "registration_derived_total_count": 13,
        "registration_derived_completed_count": 13,
        "registration_missing_steps": [],
        "registration_derived_next_step_key": None,
        "registration_derived_progress_percent": 100,
    }
    # Sans dépôt / invest en base : le module reste visible (étapes 2–3).
    j = build_activation_journey(db, person=person, client=pe, profile_dict=profile_dict)
    assert j["show_module"] is True
    assert j["activation_complete"] is False
    assert j["completion_message"] is None
    assert j["weighted_progress_percent"] == 70
    assert j["primary_cta_label"] == "Alimenter mon compte"
    assert j["primary_cta_target_route"] == "deposit"
    by_id = {s["id"]: s for s in j["stages"]}
    assert by_id["account_verification"]["status"] == "completed"
    assert by_id["first_deposit"]["status"] == "available"
    assert by_id["first_deposit"]["is_next_step"] is True
    assert by_id["first_investment"]["status"] == "locked"


def test_build_activation_registration_not_started_is_available(db: Session) -> None:
    """Ratio 0 % : l’étape 1 est ``available`` (pas encore ``in_progress``)."""
    pid = uuid.uuid4()
    person = Person(
        id=pid,
        status="active",
        jurisdiction="EU",
        profile_json={"collected": {}, "computed": {}, "compliance": {}},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    pe = Client(
        id=uuid.uuid4(),
        email=f"b-{uuid.uuid4().hex[:6]}@example.com",
        status="PARTIAL",
        kyc_status="not_started",
        person_id=pid,
    )
    db.add(pe)
    db.commit()
    profile_dict = {
        "client_status": "PARTIAL",
        "registration_macro_stage": "registration_active",
        "registration_completion_ratio": 0.0,
        "registration_derived_total_count": 13,
        "registration_derived_completed_count": 0,
        "registration_missing_steps": ["x"],
        "registration_derived_next_step_key": "start",
        "registration_derived_progress_percent": 0,
    }
    j = build_activation_journey(db, person=person, client=pe, profile_dict=profile_dict)
    by_id = {s["id"]: s for s in j["stages"]}
    assert by_id["account_verification"]["status"] == "available"
    assert by_id["first_deposit"]["status"] == "locked"


def test_build_activation_stage1_pending_when_registration_incomplete(db: Session) -> None:
    pid = uuid.uuid4()
    person = Person(
        id=pid,
        status="active",
        jurisdiction="EU",
        profile_json={"collected": {}, "computed": {}, "compliance": {}},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    pe = Client(
        id=uuid.uuid4(),
        email=f"a-{uuid.uuid4().hex[:6]}@example.com",
        status="PARTIAL",
        kyc_status="not_started",
        person_id=pid,
    )
    db.add(pe)
    db.commit()
    profile_dict = {
        "client_status": "PARTIAL",
        "registration_macro_stage": "registration_active",
        "registration_completion_ratio": 0.2,
        "registration_derived_total_count": 13,
        "registration_derived_completed_count": 2,
        "registration_missing_steps": ["x"],
        "registration_derived_next_step_key": "kyc",
        "registration_derived_progress_percent": 20,
    }
    j = build_activation_journey(db, person=person, client=pe, profile_dict=profile_dict)
    assert j["show_module"] is True
    assert j["weighted_progress_percent"] == 14  # 0.7 × 20 %
    assert j["primary_cta_label"] == "Continuer votre profil"
    assert j["primary_cta_target_route"] == "registration_resume"
    by_id = {s["id"]: s for s in j["stages"]}
    assert by_id["account_verification"]["status"] == "in_progress"
    assert by_id["account_verification"]["is_next_step"] is True
    assert by_id["first_deposit"]["status"] == "locked"
    assert by_id["first_investment"]["status"] == "locked"


def test_build_activation_deposit_done_invest_available(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    pe = make_linked_client(db)
    person = db.query(Person).filter(Person.id == pe.person_id).first()
    assert person is not None
    profile_dict = {
        "client_status": "ACTIVE",
        "registration_macro_stage": "active_client",
        "registration_completion_ratio": 1.0,
        "registration_derived_total_count": 13,
        "registration_derived_completed_count": 13,
        "registration_missing_steps": [],
        "registration_derived_next_step_key": None,
        "registration_derived_progress_percent": 100,
    }
    import services.activation_journey.build as build_mod

    monkeypatch.setattr(build_mod, "has_first_deposit", lambda _db, _c: True)
    monkeypatch.setattr(build_mod, "has_first_investment", lambda _db, _c: False)

    j = build_activation_journey(db, person=person, client=pe, profile_dict=profile_dict)
    assert j["show_module"] is True
    assert j["weighted_progress_percent"] == 90
    assert j["primary_cta_label"] == "Investir maintenant"
    assert j["primary_cta_target_route"] == "invest_crypto"
    by_id = {s["id"]: s for s in j["stages"]}
    assert by_id["account_verification"]["status"] == "completed"
    assert by_id["first_deposit"]["status"] == "completed"
    assert by_id["first_investment"]["status"] == "available"
    assert by_id["first_investment"]["is_next_step"] is True


def test_build_activation_all_complete(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    pe = make_linked_client(db)
    person = db.query(Person).filter(Person.id == pe.person_id).first()
    assert person is not None
    profile_dict = {
        "client_status": "ACTIVE",
        "registration_macro_stage": "active_client",
        "registration_completion_ratio": 1.0,
        "registration_derived_total_count": 13,
        "registration_derived_completed_count": 13,
        "registration_missing_steps": [],
        "registration_derived_next_step_key": None,
        "registration_derived_progress_percent": 100,
    }
    import services.activation_journey.build as build_mod

    monkeypatch.setattr(build_mod, "has_first_deposit", lambda _db, _c: True)
    monkeypatch.setattr(build_mod, "has_first_investment", lambda _db, _c: True)

    j = build_activation_journey(db, person=person, client=pe, profile_dict=profile_dict)
    assert j["show_module"] is False
    assert j["activation_complete"] is True
    assert j["completion_message"] == "Tout est en place"
    assert j["weighted_progress_percent"] == 100
    assert j["primary_cta_label"] is None
    assert j["primary_cta_target_route"] is None
    for s in j["stages"]:
        assert s["status"] == "completed"
