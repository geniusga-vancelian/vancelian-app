"""Identité customer (profil métier) — distinct du vocabulaire auth interne."""

from .profile_phone import ensure_person_collected_phone_e164

__all__ = ["ensure_person_collected_phone_e164"]
