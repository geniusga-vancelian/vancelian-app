"""Unit tests for registration audit masking helpers."""
from services.registration.masking import mask_email, mask_phone, mask_slug_value, mask_answers_for_audit


def test_mask_email():
    assert mask_email("user@example.com") == "u***@example.com"
    assert mask_email(None) is None


def test_mask_phone():
    assert "***7890" in mask_phone("+33 6 12 34 56 78 90")


def test_mask_slug_value_email_slug():
    masked = mask_slug_value("work_email", "secret@domain.com")
    assert "@" in str(masked)
    assert "secret" not in str(masked)


def test_mask_answers_for_audit():
    out = mask_answers_for_audit({"full_name": "Jean Dupont", "user_email": "a@b.co"})
    assert out["full_name"] == "Jean Dupont"
    assert "@" in str(out["user_email"])
