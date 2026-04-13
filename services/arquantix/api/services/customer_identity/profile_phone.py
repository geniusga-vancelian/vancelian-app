"""Téléphone customer : source canonique affichée = ``person.profile_json[\"collected\"][\"phone_e164\"]``.

Les comptes app stockent aussi le mobile sur ``admin_users.mobile_e164`` (identifiant de connexion).
Cette fonction aligne le profil customer lorsque ``collected.phone_e164`` est absent ou vide.
"""
from __future__ import annotations

import logging
from sqlalchemy.orm.attributes import flag_modified

from database import Person

logger = logging.getLogger(__name__)


def ensure_person_collected_phone_e164(
    person: Person,
    phone_e164: str,
) -> bool:
    """Remplit ``collected.phone_e164`` si vide. Retourne True si ``profile_json`` a été modifié."""
    raw = (phone_e164 or "").strip()
    if not raw:
        return False

    pj = dict(person.profile_json or {})
    col = dict(pj.get("collected") or {}) if isinstance(pj.get("collected"), dict) else {}
    if str(col.get("phone_e164") or "").strip():
        return False

    col = {**col, "phone_e164": raw}
    pj["collected"] = col
    person.profile_json = pj
    flag_modified(person, "profile_json")
    logger.info(
        "customer_identity: ensured collected.phone_e164 for person_id=%s",
        person.id,
    )
    return True
