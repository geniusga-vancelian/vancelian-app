"""E-mail de contact dans ``profile_json.collected`` (inscription e-mail / KYC)."""
from __future__ import annotations

from typing import Any

from database import Person


def ensure_person_collected_email(person: Person, email: str) -> bool:
    """Renseigne ``email`` et ``contact_email`` si absents. Retourne ``True`` si modifié."""
    raw = (email or "").strip().lower()
    if not raw or "@" not in raw:
        return False

    pj: dict[str, Any] = dict(person.profile_json or {})
    collected: dict[str, Any] = dict(pj.get("collected") or {})
    if collected.get("email") or collected.get("contact_email"):
        return False

    collected["email"] = raw
    collected["contact_email"] = raw
    pj["collected"] = collected
    person.profile_json = pj
    return True
