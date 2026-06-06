"""Tests audit lecture seule person_crypto_reconciliation."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.audit.person_crypto_reconciliation import (
    _classify_recommendations,
    _fmt,
    build_person_crypto_audit,
    resolve_person_ids_by_email,
)
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person
from tests.conftest import make_linked_client


def test_fmt_decimal():
    assert _fmt(Decimal("1.5000")) == "1.5"
    assert _fmt(None) == "0"


def test_resolve_person_ids_by_email_empty(db: Session):
    assert resolve_person_ids_by_email(db, f"no-such-{uuid.uuid4().hex}@test.local") == []


def test_build_audit_minimal_person(db: Session):
    pe = make_linked_client(db)
    email = f"audit-{uuid.uuid4().hex[:8]}@test.local"
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=f"did:privy:{uuid.uuid4().hex[:12]}",
        external_email=email,
    )
    report = build_person_crypto_audit(db, email=email)
    assert report["person"]["person_id"] == str(pe.person_id)
    assert "assets" in report
    assert "recommended_actions" in report


def test_classify_recommendations_swap_safe():
    report = {
        "swaps": {
            "confirmed_incomplete_settlement": [{"swap_id": "abc"}],
            "submitted_confirmed_onchain": [],
        },
        "assets": [],
        "cost_basis": {"missing": []},
        "bundles": {"mismatches": []},
    }
    actions = _classify_recommendations(report)
    assert actions["safe_auto"][0]["type"] == "swap_settlement_repair"
