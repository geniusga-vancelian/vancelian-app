"""Tests Lot 7 — client_discovery_repo (persistance multi-projet).

Couvre :

  * upsert_project (création + merge non destructif).
  * Cap sur MAX_ACTIVE_PROJECTS_PER_PERSON (5) → pause du plus ancien.
  * pause_other_active_projects.
  * list_active_projects_for_person — cross-conversation.
  * Floating params : add, list pending, attribute, discard.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from database import (
    AssistanceClientDiscoveryProject,
    AssistanceConversation,
    AssistanceFloatingParameter,
    Person,
)
from services.assistance import client_discovery_repo as repo
from services.assistance.agents.client_discovery import (
    FLOATING_STATUS_ATTRIBUTED,
    FLOATING_STATUS_DISCARDED,
    FLOATING_STATUS_PENDING,
    PARAMETER_KIND_HORIZON_YEARS,
    PROJECT_LABEL_HOUSE,
    PROJECT_LABEL_RETIREMENT,
    PROJECT_LABEL_TRAVEL,
    PROJECT_STATUS_ACTIVE,
    PROJECT_STATUS_PAUSED,
    ClientProject,
    ClientProjectParameters,
    FloatingParameter,
)
from services.portfolio_engine.clients.models import Client as PEClient


# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def base_setup(db) -> dict:
    """1 person + 1 pe_client + 1 conversation."""
    person_uuid = uuid4()
    db.add(
        Person(
            id=person_uuid,
            status="active",
            jurisdiction="FR",
            profile_json={},
            kyc_status="not_started",
        )
    )
    db.flush()
    client_uuid = uuid4()
    db.add(PEClient(id=client_uuid, person_id=person_uuid))
    db.flush()
    conv = AssistanceConversation(
        id=uuid4(),
        client_id=client_uuid,
        title="Lot 7 repo test",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(conv)
    db.flush()
    return {
        "person_id": person_uuid,
        "client_id": client_uuid,
        "conversation_id": conv.id,
    }


# ─── 1. Upsert nominal + merge non destructif ─────────────────────────────


class TestUpsertNominal:
    def test_create_then_get(self, db, base_setup):
        proj = ClientProject(
            label=PROJECT_LABEL_HOUSE,
            confidence=0.85,
            parameters=ClientProjectParameters(
                horizon_years=4.0, target_amount=300000.0
            ),
        )
        out = repo.upsert_project(
            db,
            person_id=base_setup["person_id"],
            conversation_id=base_setup["conversation_id"],
            project=proj,
            current_turn=1,
        )
        db.commit()
        assert out is not None
        assert out.label == PROJECT_LABEL_HOUSE
        assert out.id is not None
        # Lookup
        actives = repo.list_active_projects_for_person(
            db, base_setup["person_id"]
        )
        assert len(actives) == 1
        assert actives[0].label == PROJECT_LABEL_HOUSE
        assert actives[0].parameters.horizon_years == 4.0

    def test_merge_non_destructive(self, db, base_setup):
        # Tour 1 : on pose horizon=4, target=300k
        repo.upsert_project(
            db,
            person_id=base_setup["person_id"],
            conversation_id=base_setup["conversation_id"],
            project=ClientProject(
                label=PROJECT_LABEL_HOUSE,
                confidence=0.7,
                parameters=ClientProjectParameters(
                    horizon_years=4.0, target_amount=300000.0
                ),
            ),
            current_turn=1,
        )
        db.commit()
        # Tour 2 : on ajoute risk=low SANS retoucher horizon/target
        repo.upsert_project(
            db,
            person_id=base_setup["person_id"],
            conversation_id=base_setup["conversation_id"],
            project=ClientProject(
                label=PROJECT_LABEL_HOUSE,
                confidence=0.9,
                parameters=ClientProjectParameters(risk_appetite="low"),
            ),
            current_turn=2,
        )
        db.commit()
        # Vérif : horizon et target préservés, risk ajouté, confidence
        # = max(0.7, 0.9) = 0.9
        actives = repo.list_active_projects_for_person(
            db, base_setup["person_id"]
        )
        assert len(actives) == 1
        p = actives[0]
        assert p.parameters.horizon_years == 4.0
        assert p.parameters.target_amount == 300000.0
        assert p.parameters.risk_appetite == "low"
        assert p.confidence == 0.9

    def test_unknown_label_skipped(self, db, base_setup):
        out = repo.upsert_project(
            db,
            person_id=base_setup["person_id"],
            conversation_id=base_setup["conversation_id"],
            project=ClientProject(label="not_a_known_label"),
            current_turn=1,
        )
        assert out is None


# ─── 2. Cap sur 5 projets actifs ──────────────────────────────────────────


class TestActiveCap:
    def test_pauses_oldest_when_cap_reached(self, db, base_setup):
        labels = [
            "achat_maison",
            "achat_voiture",
            "voyage_vacances",
            "retraite",
            "etudes",
            "mariage",  # 6e → doit déclencher le cap → maison passe paused
        ]
        for i, label in enumerate(labels):
            repo.upsert_project(
                db,
                person_id=base_setup["person_id"],
                conversation_id=base_setup["conversation_id"],
                project=ClientProject(label=label, confidence=0.7),
                current_turn=i + 1,
            )
            db.commit()
        actives = repo.list_active_projects_for_person(
            db, base_setup["person_id"], limit=10
        )
        active_labels = {p.label for p in actives}
        # Le plus ancien (maison) doit être paused
        assert "achat_maison" not in active_labels
        assert "mariage" in active_labels
        assert len(actives) == 5  # cap respecté


# ─── 3. pause_other_active_projects ───────────────────────────────────────


class TestPauseOthers:
    def test_pause_all_others(self, db, base_setup):
        # 3 projets actifs
        for label in ["achat_maison", "voyage_vacances", "retraite"]:
            repo.upsert_project(
                db,
                person_id=base_setup["person_id"],
                conversation_id=base_setup["conversation_id"],
                project=ClientProject(label=label),
            )
            db.commit()
        n = repo.pause_other_active_projects(
            db,
            person_id=base_setup["person_id"],
            keep_label="voyage_vacances",
        )
        db.commit()
        assert n == 2
        actives = repo.list_active_projects_for_person(
            db, base_setup["person_id"]
        )
        assert len(actives) == 1
        assert actives[0].label == "voyage_vacances"


# ─── 4. Cross-conversation lookup ─────────────────────────────────────────


class TestCrossConversation:
    def test_project_visible_from_another_conversation(self, db, base_setup):
        repo.upsert_project(
            db,
            person_id=base_setup["person_id"],
            conversation_id=base_setup["conversation_id"],
            project=ClientProject(
                label=PROJECT_LABEL_HOUSE,
                parameters=ClientProjectParameters(horizon_years=4.0),
            ),
            current_turn=1,
        )
        db.commit()
        # Nouvelle conversation pour la même personne
        new_conv = AssistanceConversation(
            id=uuid4(),
            client_id=base_setup["client_id"],
            title="conv suivante",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_conv)
        db.commit()
        actives = repo.list_active_projects_for_person(
            db, base_setup["person_id"]
        )
        assert len(actives) == 1
        assert actives[0].label == PROJECT_LABEL_HOUSE
        assert actives[0].parameters.horizon_years == 4.0


# ─── 5. Floating parameters ───────────────────────────────────────────────


class TestFloatingParameters:
    def test_add_then_list_pending(self, db, base_setup):
        fid = repo.add_floating_parameter(
            db,
            conversation_id=base_setup["conversation_id"],
            person_id=base_setup["person_id"],
            floating=FloatingParameter(
                parameter_kind=PARAMETER_KIND_HORIZON_YEARS,
                parameter_value={"value": 4.0},
                confidence=0.7,
            ),
            current_turn=1,
        )
        db.commit()
        assert fid is not None
        pending = repo.list_pending_floating_parameters(
            db, base_setup["conversation_id"]
        )
        assert len(pending) == 1
        assert pending[0].parameter_kind == PARAMETER_KIND_HORIZON_YEARS
        assert pending[0].parameter_value == {"value": 4.0}

    def test_attribute_to_project(self, db, base_setup):
        # 1 floating + 1 projet
        proj_out = repo.upsert_project(
            db,
            person_id=base_setup["person_id"],
            conversation_id=base_setup["conversation_id"],
            project=ClientProject(label=PROJECT_LABEL_HOUSE),
        )
        fid = repo.add_floating_parameter(
            db,
            conversation_id=base_setup["conversation_id"],
            person_id=base_setup["person_id"],
            floating=FloatingParameter(
                parameter_kind=PARAMETER_KIND_HORIZON_YEARS,
                parameter_value={"value": 4.0},
            ),
        )
        db.commit()
        ok = repo.attribute_floating_to_project(
            db, floating_id=fid, project_id=proj_out.id
        )
        db.commit()
        assert ok is True
        # Le floating ne doit plus être pending
        pending = repo.list_pending_floating_parameters(
            db, base_setup["conversation_id"]
        )
        assert pending == []

    def test_discard(self, db, base_setup):
        fid = repo.add_floating_parameter(
            db,
            conversation_id=base_setup["conversation_id"],
            person_id=base_setup["person_id"],
            floating=FloatingParameter(
                parameter_kind=PARAMETER_KIND_HORIZON_YEARS,
                parameter_value={"value": 4.0},
            ),
        )
        db.commit()
        assert repo.discard_floating(db, fid) is True
        db.commit()
        pending = repo.list_pending_floating_parameters(
            db, base_setup["conversation_id"]
        )
        assert pending == []
