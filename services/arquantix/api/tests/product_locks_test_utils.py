"""Helpers tests S4 Product Locks allowlist."""
from __future__ import annotations


def enable_product_locks_allowlist(monkeypatch, pe) -> None:
    """Associe le client de test à ``TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS``."""
    email = getattr(pe, "email", None) or ""
    monkeypatch.setenv("TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS", email)
