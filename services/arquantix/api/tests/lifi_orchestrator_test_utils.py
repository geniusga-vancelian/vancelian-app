"""Helpers tests Phase 2 — allowlist pilot prod."""
from __future__ import annotations


def enable_lifi_orchestrator_allowlist(monkeypatch, pe) -> None:
    """Associe le client de test à ``LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS``."""
    email = getattr(pe, "email", None) or ""
    monkeypatch.setenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", email)
