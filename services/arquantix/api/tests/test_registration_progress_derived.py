"""Progression dérivée depuis profile_json.collected uniquement."""
from __future__ import annotations

from services.registration_progress_derived import (
    ORDERED_CANONICAL_KEYS,
    compute_next_registration_step_from_collected,
    compute_registration_progress_from_collected,
    is_canonical_step_complete,
)


def test_empty_collected_identity_next() -> None:
    nxt = compute_next_registration_step_from_collected({})
    assert nxt is not None
    assert nxt[0] == "identity"


def test_employed_missing_sector_next_is_work_sector() -> None:
    collected = {
        "first_name": "A",
        "last_name": "B",
        "date_of_birth": "1990-01-01",
        "country_of_residence": "FR",
        "address_line_1": "1 rue",
        "email": "a@b.com",
        "email_verification_skipped": True,
        "terms_accepted": True,
        "employment_status": "employed",
    }
    nxt = compute_next_registration_step_from_collected(collected)
    assert nxt is not None
    assert nxt[0] == "work_sector"


def test_progress_halfway() -> None:
    collected = {
        "first_name": "A",
        "last_name": "B",
        "date_of_birth": "1990-01-01",
        "country_of_residence": "FR",
        "address_line_1": "1 rue",
        "email": "a@b.com",
        "email_verification_skipped": True,
        "terms_accepted": True,
        "employment_status": "student",
    }
    ratio, pct, done, total = compute_registration_progress_from_collected(collected)
    assert total == len(ORDERED_CANONICAL_KEYS)
    assert done >= 8
    assert ratio == round(done / float(total), 4)
    assert pct == min(100, int(round(ratio * 100)))
    nxt = compute_next_registration_step_from_collected(collected)
    assert nxt is not None
    assert nxt[0] == "annual_income"


def test_all_complete_no_next() -> None:
    collected = {
        "first_name": "A",
        "last_name": "B",
        "date_of_birth": "1990-01-01",
        "country_of_residence": "FR",
        "address_line_1": "x",
        "email": "a@b.com",
        "email_verification_skipped": True,
        "terms_accepted": True,
        "employment_status": "student",
        "annual_income_range": "50k_100k",
        "net_worth_range": "100k_250k",
        "source_of_wealth": ["salary"],
        "info_true_and_accurate": True,
        "compliance_usage_ack": True,
        "not_us_person": True,
    }
    assert is_canonical_step_complete(collected, "work_details") is True
    assert compute_next_registration_step_from_collected(collected) is None
    _, pct, done, total = compute_registration_progress_from_collected(collected)
    assert done == total
    assert pct == 100
